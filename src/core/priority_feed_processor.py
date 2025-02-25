import asyncio
import logging
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from queue import PriorityQueue
from ..database.models import update_feed_cache, get_source_priority

logger = logging.getLogger(__name__)

@dataclass(order=True)
class ArticleEntry:
    # Priority based on publication date (newer = higher priority)
    priority: int = field(init=False)
    pub_date: datetime = field(compare=False)
    feed_url: str = field(compare=False)
    title: str = field(compare=False)
    content: str = field(compare=False)
    link: str = field(compare=False)
    guid: str = field(compare=False)

    def __post_init__(self):
        # Convert to timestamp priority (newer articles = lower numbers = higher priority)
        self.priority = int(datetime.now().timestamp() - self.pub_date.timestamp())

class PriorityFeedProcessor:
    def __init__(self, api_rate_limit: int = 60):
        self.article_queue = PriorityQueue()
        self.processing_stats = {
            'total_articles': 0,
            'processed_articles': 0,
            'queued_articles': 0,
            'api_calls': 0,
            'start_time': time.time()
        }
        self.api_rate_limit = api_rate_limit
        self.last_api_call = 0
        self.feed_stats: Dict[str, dict] = {}
        self._running = False
        self._processing_task = None

    async def start(self):
        """Start the continuous processing loop."""
        if self._running:
            logger.info("📝 Processing loop already running")
            return
        
        self._running = True
        self._processing_task = asyncio.create_task(self._processing_loop())
        logger.info("🚀 Starting article processing loop")
        logger.info(f"Queue status at start: {self.processing_stats['queued_articles']} articles queued")

    async def stop(self):
        """Stop the processing loop."""
        self._running = False
        if self._processing_task:
            await self._processing_task
        logger.info("⏹️ Stopped article processing loop")

    async def _processing_loop(self):
        """Continuous loop to process articles from the queue."""
        logger.info("✨ Processing loop started")
        last_status_update = time.time()
        status_update_interval = 5  # Update status every 5 seconds
        
        while self._running:
            try:
                current_time = time.time()
                processed_count = 0
                
                # Process up to 10 articles in a batch
                while not self.article_queue.empty() and processed_count < 10:
                    if await self.process_next_article():
                        processed_count += 1
                
                # Only sleep if no articles were processed
                if processed_count == 0:
                    await asyncio.sleep(0.1)
                    
                # Update status display periodically
                if current_time - last_status_update >= status_update_interval:
                    self._update_status_display()
                    last_status_update = current_time
                    
            except Exception as e:
                logger.error(f"Error in processing loop: {str(e)}")
                await asyncio.sleep(0.1)

    def add_article(self, article: ArticleEntry):
        """Add an article to the priority queue."""
        self.article_queue.put(article)
        self.processing_stats['total_articles'] += 1
        self.processing_stats['queued_articles'] += 1
        
        # Only log every 10th article or when queue size hits certain thresholds
        if (self.processing_stats['total_articles'] % 10 == 0 or 
            self.processing_stats['queued_articles'] in [1, 10, 50, 100, 500, 1000]):
            self._update_status_display()
        
        # Update feed statistics
        if article.feed_url not in self.feed_stats:
            self.feed_stats[article.feed_url] = {
                'articles_received': 0,
                'articles_processed': 0,
                'last_article_time': None
            }
        
        self.feed_stats[article.feed_url]['articles_received'] += 1
        self.feed_stats[article.feed_url]['last_article_time'] = article.pub_date

    async def process_next_article(self) -> Optional[ArticleEntry]:
        """Process the next article in the queue and store in database."""
        if self.article_queue.empty():
            return None

        current_time = time.time()
        if current_time - self.last_api_call < (1.0 / self.api_rate_limit):
            await asyncio.sleep(0.1)

        try:
            article = self.article_queue.get()
            
            # Basic cleanup first
            from ..utils.text import clean_text, clean_url
            cleaned_title = clean_text(article.title)
            cleaned_content = clean_text(article.content)
            cleaned_url = clean_url(article.link)

            # Process with AI
            from ..utils.ai import content_processor
            
            try:
                title_emoji_str, processed_title = await content_processor.process_content(
                    cleaned_title, 
                    cleaned_url, 
                    is_title=True
                )
                
                content_result = await content_processor.process_content_with_analysis(
                    cleaned_content,
                    cleaned_url,
                    is_title=False
                )
                emoji_str, processed_text, sentiment_score, bias_category, bias_score = content_result
                
                if emoji_str == "📰🌐":
                    emoji_str = title_emoji_str
                
            except Exception as ai_error:
                processed_title = cleaned_title
                processed_text = cleaned_content
                emoji_str = "📰🌐"
                sentiment_score = 0.0
                bias_category = "ai_error"
                bias_score = 0.0
            
            # Store processed article
            from ..database.models import store_article
            stored = await store_article(
                title=processed_title or cleaned_title,
                content=processed_text or cleaned_content,
                link=cleaned_url,
                guid=article.guid,
                feed_url=article.feed_url,
                pub_date=article.pub_date,
                emoji1=emoji_str[0] if emoji_str else "📰",
                emoji2=emoji_str[1] if len(emoji_str) > 1 else "🌐",
                sentiment_score=sentiment_score,
                bias_category=bias_category,
                bias_score=bias_score
            )

            if stored:
                self.processing_stats['processed_articles'] += 1
                self.processing_stats['queued_articles'] -= 1
                self.processing_stats['api_calls'] += 1
                self.last_api_call = current_time
                self.feed_stats[article.feed_url]['articles_processed'] += 1
                
                # Update feed cache less frequently
                if self.processing_stats['processed_articles'] % 20 == 0:
                    await update_feed_cache(article.feed_url, {
                        'last_success_time': datetime.now(),
                        'source_priority': await get_source_priority(article.feed_url)
                    })

            return article

        except Exception as e:
            self.processing_stats['error_count'] = self.processing_stats.get('error_count', 0) + 1
            return None

    def get_processing_status(self) -> dict:
        """Get current processing status and metrics."""
        runtime = time.time() - self.processing_stats['start_time']
        processing_rate = self.processing_stats['processed_articles'] / runtime if runtime > 0 else 0
        
        return {
            'queue_size': self.processing_stats['queued_articles'],
            'total_articles': self.processing_stats['total_articles'],
            'processed_articles': self.processing_stats['processed_articles'],
            'processing_rate': f"{processing_rate:.2f} articles/second",
            'api_utilization': f"{(self.processing_stats['api_calls'] / runtime * 60):.2f}%",
            'runtime': f"{runtime:.2f} seconds",
            'feed_stats': self.feed_stats
        }

    def print_status(self):
        """Print current processing status in a clean format."""
        status = self.get_processing_status()
        
        logger.info("\n=== Feed Processing Status ===")
        logger.info(f"📊 Queue Status:")
        logger.info(f"   - Queued Articles: {status['queue_size']}")
        logger.info(f"   - Total Articles: {status['total_articles']}")
        logger.info(f"   - Processed: {status['processed_articles']}")
        logger.info(f"\n📈 Performance Metrics:")
        logger.info(f"   - Processing Rate: {status['processing_rate']}")
        logger.info(f"   - API Utilization: {status['api_utilization']}")
        logger.info(f"   - Runtime: {status['runtime']}")


    def _update_status_display(self):
        """Update the status display in place."""
        status = self.get_processing_status()
        
        # Clear previous lines and move cursor to top
        print("\033[2J\033[H", end="")
        
        # Build status string
        status_str = (
            "\n=== Feed Processing Status ===\n"
            f"📊 Queue: {status['queue_size']} queued, "
            f"{status['processed_articles']}/{status['total_articles']} processed\n"
            f"📈 Rate: {status['processing_rate']} | API: {status['api_utilization']}\n"
            f"⏱️  Runtime: {status['runtime']}\n"
            "\n"
            "========================================\n"
        )
        
        # Print status in a single call to minimize flickering
        print(status_str)