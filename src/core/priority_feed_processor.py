import asyncio
import logging
import time
import os
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from queue import PriorityQueue
from ..database.models import update_feed_cache, get_source_priority, add_tag, tag_article

logger = logging.getLogger(__name__)

# ANSI Color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    CLEAR = '\033[2J\033[H'  # Clear screen and move cursor to home
    CURSOR_UP = '\033[F'     # Move cursor up one line
    ERASE_LINE = '\033[K'    # Erase from cursor to end of line

def clear_terminal():
    """Clear the terminal screen in a cross-platform way."""
    # Clear screen and move cursor to home
    sys.stdout.write(Colors.CLEAR)
    sys.stdout.flush()
    
    # Additional clear for certain terminals
    if os.name == 'posix':  # For Unix/Linux/MacOS
        os.system('clear')
    elif os.name == 'nt':   # For Windows
        os.system('cls')

def format_relative_time(dt: Optional[datetime]) -> str:
    """Format a datetime as a relative time string."""
    if not dt:
        return "Never"
    
    now = datetime.now()
    diff = now - dt
    
    if diff.total_seconds() < 60:
        return f"{int(diff.total_seconds())}s ago"
    elif diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds() / 60)}m ago"
    elif diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds() / 3600)}h ago"
    else:
        return f"{int(diff.total_seconds() / 86400)}d ago"

def colorize_rate(value: float, warning: float = 70.0, critical: float = 90.0) -> str:
    """Colorize a rate/percentage value based on thresholds."""
    if value >= critical:
        return f"{Colors.RED}{value:.1f}%{Colors.END}"
    elif value >= warning:
        return f"{Colors.YELLOW}{value:.1f}%{Colors.END}"
    return f"{Colors.GREEN}{value:.1f}%{Colors.END}"

@dataclass(order=True)
class ArticleEntry:
    # Priority based on publication date (newer = higher priority)
    priority: float = field(init=False)
    pub_date: datetime = field(compare=False)
    feed_url: str = field(compare=False)
    title: str = field(compare=False)
    content: str = field(compare=False)
    link: str = field(compare=False)
    guid: str = field(compare=False)
    added_time: datetime = field(default_factory=datetime.now, compare=False)

    def __post_init__(self):
        # Convert to timestamp priority (newer articles = negative numbers = higher priority)
        # This ensures newest articles have highest priority (lowest number)
        self.priority = -self.pub_date.timestamp()

    def get_age_minutes(self) -> float:
        """Get article age in minutes"""
        return (datetime.now() - self.pub_date).total_seconds() / 60
        
class PriorityFeedProcessor:
    def __init__(self, api_rate_limit: int = 60):
        self.article_queue = PriorityQueue()
        self.processing_stats = {
            'total_articles': 0,
            'processed_articles': 0,
            'queued_articles': 0,
            'api_calls': 0,
            'start_time': time.time(),
            'errors': 0,
            'oldest_queued_article': None,
            'newest_queued_article': None,
            'avg_processing_time': 0,
            'total_processing_time': 0,
            'feeds_with_updates': set(),
            'articles_by_age': {
                '5min': 0,
                '15min': 0,
                '30min': 0,
                '60min': 0,
                'older': 0
            },
            'last_processed_article': None,
            'last_processed_time': None,
            'consecutive_errors': 0,
            'success_streak': 0,
            'peak_queue_size': 0,
            'min_processing_time': float('inf'),
            'max_processing_time': 0
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
        status_update_interval = 1  # Update status every 1 second (decreased from 5)
        
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
        self.processing_stats['peak_queue_size'] = max(
            self.processing_stats['peak_queue_size'], 
            self.processing_stats['queued_articles']
        )
        
        # Update article age statistics
        age_minutes = article.get_age_minutes()
        if age_minutes <= 5:
            self.processing_stats['articles_by_age']['5min'] += 1
        elif age_minutes <= 15:
            self.processing_stats['articles_by_age']['15min'] += 1
        elif age_minutes <= 30:
            self.processing_stats['articles_by_age']['30min'] += 1
        elif age_minutes <= 60:
            self.processing_stats['articles_by_age']['60min'] += 1
        else:
            self.processing_stats['articles_by_age']['older'] += 1

        # Update newest/oldest article tracking
        if (not self.processing_stats['newest_queued_article'] or 
            article.pub_date > self.processing_stats['newest_queued_article']):
            self.processing_stats['newest_queued_article'] = article.pub_date
            
        if (not self.processing_stats['oldest_queued_article'] or 
            article.pub_date < self.processing_stats['oldest_queued_article']):
            self.processing_stats['oldest_queued_article'] = article.pub_date

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
        if self.article_queue.empty():
            return None

        current_time = time.time()
        if current_time - self.last_api_call < (1.0 / self.api_rate_limit):
            await asyncio.sleep(0.1)
            return None

        try:
            start_time = time.time()
            article = self.article_queue.get()
            
            # Basic cleanup first
            from ..utils.text import clean_text, clean_url
            cleaned_title = clean_text(article.title)
            cleaned_content = clean_text(article.content)
            cleaned_url = clean_url(article.link)

            # Process with AI
            from ..utils.ai import content_processor
            
            try:
                # Process title
                title_emoji_str, processed_title = await content_processor.process_content(
                    cleaned_title, 
                    cleaned_url, 
                    is_title=True
                )
                
                # Process content with tags
                emoji_str, processed_text, topic_tags, geography_tags, event_tags = await content_processor.process_content_with_tags(
                    cleaned_content,
                    cleaned_url,
                    is_title=False
                )
                
                # Get sentiment and bias analysis
                sentiment_score, bias_category, bias_score = await content_processor.analyze_sentiment_and_bias(processed_text)
                
                if emoji_str == "📰🌐":
                    emoji_str = title_emoji_str
                
            except Exception as ai_error:
                processed_title = cleaned_title
                processed_text = cleaned_content
                emoji_str = "📰🌐"
                sentiment_score = 0.0
                bias_category = "ai_error"
                bias_score = 0.0
                topic_tags, geography_tags, event_tags = [], [], []
                logger.error(f"AI processing error: {str(ai_error)}")
            
            # Extract image URL from the article
            from ..core.processor import ImageExtractor
            image_extractor = ImageExtractor()
            images = image_extractor.extract_images(article)
            image_url = images[0] if images else None
            
            if not image_url and hasattr(article, 'content'):
                # Try to extract from content as fallback
                image_url = image_extractor.extract_first_image_from_content(article.content)
            
            # Store processed article
            from ..database.models import store_article
            article_id = await store_article(
                title=processed_title or cleaned_title,
                content=processed_text or cleaned_content,
                link=cleaned_url,
                guid=article.guid,
                feed_url=article.feed_url,
                pub_date=article.pub_date,
                emoji1=emoji_str[0] if emoji_str else "📰",
                emoji2=emoji_str[1] if len(emoji_str) > 1 else "🌐",
                image_url=image_url,
                sentiment_score=sentiment_score,
                bias_category=bias_category,
                bias_score=bias_score
            )

            # Store tags if article was successfully stored and we got a valid article ID
            if article_id > 0:
                # Create a list to store tag IDs for this article
                article_tag_ids = []
                
                # Process tags by category
                for tag_list, tag_type in [
                    (topic_tags, 'topic'),
                    (geography_tags, 'geography'),
                    (event_tags, 'event')
                ]:
                    # Clean and deduplicate tags
                    unique_tags = set()
                    for tag_name in tag_list:
                        if tag_name and len(tag_name) > 1:
                            # Normalize tag name to prevent duplicates
                            normalized_tag = tag_name.strip().lower()
                            if normalized_tag not in unique_tags:
                                unique_tags.add(normalized_tag)
                                try:
                                    # Add tag if it doesn't exist and get its ID
                                    tag_id = add_tag(tag_name, tag_type)
                                    if tag_id:
                                        article_tag_ids.append(tag_id)
                                except Exception as tag_error:
                                    logger.error(f"Error processing tag {tag_name}: {str(tag_error)}")
                
                # Associate all tags with the article in a single operation
                if article_tag_ids:
                    tag_article(article_id, article_tag_ids)

                self.processing_stats['processed_articles'] += 1
                self.processing_stats['queued_articles'] -= 1
                self.processing_stats['api_calls'] += 1
                self.last_api_call = current_time
                self.feed_stats[article.feed_url]['articles_processed'] += 1
                
                # Update feed cache less frequently
                if self.processing_stats['processed_articles'] % 20 == 0:
                    source_priority = get_source_priority(article.feed_url)
                    update_feed_cache(article.feed_url, {
                        'last_success_time': datetime.now(),
                        'source_priority': source_priority
                    })

            # Update processing stats
            processing_time = time.time() - start_time
            self.processing_stats['total_processing_time'] += processing_time
            self.processing_stats['min_processing_time'] = min(self.processing_stats['min_processing_time'], processing_time)
            self.processing_stats['max_processing_time'] = max(self.processing_stats['max_processing_time'], processing_time)
            self.processing_stats['last_processed_article'] = article.pub_date
            self.processing_stats['last_processed_time'] = datetime.now()
            self.processing_stats['success_streak'] += 1
            self.processing_stats['consecutive_errors'] = 0
            
            return article

        except Exception as e:
            self.processing_stats['errors'] += 1
            self.processing_stats['consecutive_errors'] += 1
            self.processing_stats['success_streak'] = 0
            logger.error(f"Error processing article: {str(e)}")
            return None

    def get_processing_status(self) -> dict:
        """Get current processing status and metrics."""
        runtime = time.time() - self.processing_stats['start_time']
        processing_rate = (self.processing_stats['processed_articles'] / runtime) * 60 if runtime > 0 else 0
        avg_time = (self.processing_stats['total_processing_time'] / 
                   self.processing_stats['processed_articles'] 
                   if self.processing_stats['processed_articles'] > 0 else 0)
        
        api_utilization = (self.processing_stats['api_calls'] / runtime * 60)
        error_rate = (self.processing_stats['errors'] / self.processing_stats['total_articles'] * 100 
                     if self.processing_stats['total_articles'] > 0 else 0)
        
        return {
            'queue_size': self.processing_stats['queued_articles'],
            'peak_queue_size': self.processing_stats['peak_queue_size'],
            'total_articles': self.processing_stats['total_articles'],
            'processed_articles': self.processing_stats['processed_articles'],
            'processing_rate': f"{processing_rate:.2f} articles/minute",
            'avg_processing_time': f"{avg_time:.2f}s",
            'min_processing_time': f"{self.processing_stats['min_processing_time']:.2f}s" if self.processing_stats['min_processing_time'] != float('inf') else "N/A",
            'max_processing_time': f"{self.processing_stats['max_processing_time']:.2f}s",
            'api_utilization': api_utilization,
            'api_utilization_str': colorize_rate(api_utilization),
            'runtime': f"{int(runtime // 3600)}h {int((runtime % 3600) // 60)}m {int(runtime % 60)}s",
            'runtime_seconds': runtime,
            'error_rate': error_rate,
            'error_rate_str': colorize_rate(error_rate),
            'articles_by_age': self.processing_stats['articles_by_age'],
            'newest_article': self.processing_stats['newest_queued_article'],
            'newest_article_str': self.processing_stats['newest_queued_article'].strftime('%Y-%m-%d %H:%M:%S') if self.processing_stats['newest_queued_article'] else "None",
            'newest_article_age': format_relative_time(self.processing_stats['newest_queued_article']),
            'oldest_article': self.processing_stats['oldest_queued_article'],
            'oldest_article_str': self.processing_stats['oldest_queued_article'].strftime('%Y-%m-%d %H:%M:%S') if self.processing_stats['oldest_queued_article'] else "None",
            'oldest_article_age': format_relative_time(self.processing_stats['oldest_queued_article']),
            'last_processed': self.processing_stats['last_processed_article'],
            'last_processed_str': self.processing_stats['last_processed_article'].strftime('%Y-%m-%d %H:%M:%S') if self.processing_stats['last_processed_article'] else "None",
            'last_processed_age': format_relative_time(self.processing_stats['last_processed_article']),
            'success_streak': self.processing_stats['success_streak'],
            'consecutive_errors': self.processing_stats['consecutive_errors'],
            'active_feeds': len(self.feed_stats),
            'feed_stats': self.feed_stats
        }

    def print_status(self):
        """Print current processing status in a clean format."""
        status = self.get_processing_status()
        
        print(f"\n{Colors.HEADER}{'='*20} Feed Processing Status {'='*20}{Colors.END}")
        
        # Queue Status Section
        print(f"\n{Colors.BOLD}📊 Queue Status:{Colors.END}")
        print(f"   Current Queue Size: {Colors.CYAN}{status['queue_size']}{Colors.END} articles")
        print(f"   Peak Queue Size: {Colors.CYAN}{status['peak_queue_size']}{Colors.END} articles")
        print(f"   Total Articles: {Colors.CYAN}{status['total_articles']}{Colors.END}")
        print(f"   Processed: {Colors.CYAN}{status['processed_articles']}{Colors.END}")
        
        # Performance Metrics
        print(f"\n{Colors.BOLD}⚡ Performance Metrics:{Colors.END}")
        print(f"   Processing Rate: {Colors.GREEN}{status['processing_rate']}{Colors.END}")
        print(f"   Average Time: {Colors.CYAN}{status['avg_processing_time']}{Colors.END}")
        print(f"   Peak Time: {Colors.YELLOW}{status['max_processing_time']}{Colors.END}")
        print(f"   Best Time: {Colors.GREEN}{status['min_processing_time']}{Colors.END}")
        
        # System Status
        print(f"\n{Colors.BOLD}🔄 System Status:{Colors.END}")
        print(f"   Runtime: {Colors.CYAN}{status['runtime']}{Colors.END}")
        print(f"   API Utilization: {status['api_utilization_str']}")
        print(f"   Error Rate: {status['error_rate_str']}")
        print(f"   Success Streak: {Colors.GREEN}{status['success_streak']}{Colors.END}")
        print(f"   Active Feeds: {Colors.CYAN}{status['active_feeds']}{Colors.END}")
        
        # Queue Timeline
        print(f"\n{Colors.BOLD}🕒 Queue Timeline:{Colors.END}")
        print(f"   Latest Processed: {Colors.GREEN}{status['last_processed_str']}{Colors.END} ({status['last_processed_age']})")
        print(f"   Newest in Queue: {Colors.CYAN}{status['newest_article_str']}{Colors.END} ({status['newest_article_age']})")
        print(f"   Oldest in Queue: {Colors.YELLOW}{status['oldest_article_str']}{Colors.END} ({status['oldest_article_age']})")
        
        # Article Age Distribution
        print(f"\n{Colors.BOLD}📈 Article Age Distribution:{Colors.END}")
        print(f"   ≤5min : {Colors.GREEN}{status['articles_by_age']['5min']}{Colors.END}")
        print(f"   ≤15min: {Colors.CYAN}{status['articles_by_age']['15min']}{Colors.END}")
        print(f"   ≤30min: {Colors.BLUE}{status['articles_by_age']['30min']}{Colors.END}")
        print(f"   ≤60min: {Colors.YELLOW}{status['articles_by_age']['60min']}{Colors.END}")
        print(f"   >60min: {Colors.RED}{status['articles_by_age']['older']}{Colors.END}")
        
        print(f"\n{Colors.HEADER}{'='*58}{Colors.END}\n")

    def _update_status_display(self):
        """Update the status display in place."""
        status = self.get_processing_status()
        
        # Clear screen thoroughly
        clear_terminal()
        
        # Build status string
        status_str = (
            f"{Colors.HEADER}{'='*20} Feed Processing Status {'='*20}{Colors.END}\n"
            f"\n{Colors.BOLD}📊 Queue Status:{Colors.END}\n"
            f"   Queue Size: {Colors.CYAN}{status['queue_size']}/{status['peak_queue_size']}{Colors.END} (current/peak)\n"
            f"   Processed: {Colors.GREEN}{status['processed_articles']}/{status['total_articles']}{Colors.END}\n"
            f"\n{Colors.BOLD}⚡ Processing:{Colors.END}\n"
            f"   Rate: {Colors.GREEN}{status['processing_rate']}{Colors.END}\n"
            f"   API Load: {status['api_utilization_str']}\n"
            f"   Errors: {status['error_rate_str']}\n"
            f"\n{Colors.BOLD}🕒 Timeline:{Colors.END}\n"
            f"   Latest: {Colors.GREEN}{status['last_processed_str']}{Colors.END} ({status['last_processed_age']})\n"
            f"   Newest: {Colors.CYAN}{status['newest_article_str']}{Colors.END} ({status['newest_article_age']})\n"
            f"   Oldest: {Colors.YELLOW}{status['oldest_article_str']}{Colors.END} ({status['oldest_article_age']})\n"
            f"\n{Colors.BOLD}📈 Article Age:{Colors.END}\n"
            f"   ≤5min : {Colors.GREEN}{status['articles_by_age']['5min']}{Colors.END}\n"
            f"   ≤15min: {Colors.CYAN}{status['articles_by_age']['15min']}{Colors.END}\n"
            f"   ≤30min: {Colors.BLUE}{status['articles_by_age']['30min']}{Colors.END}\n"
            f"   ≤60min: {Colors.YELLOW}{status['articles_by_age']['60min']}{Colors.END}\n"
            f"   >60min: {Colors.RED}{status['articles_by_age']['older']}{Colors.END}\n"
            f"\n{Colors.BOLD}⚙️ System:{Colors.END}\n"
            f"   Runtime: {Colors.CYAN}{status['runtime']}{Colors.END}\n"
            f"   Success Streak: {Colors.GREEN}{status['success_streak']}{Colors.END}\n"
            f"   Active Feeds: {Colors.CYAN}{status['active_feeds']}{Colors.END}\n"
            f"\n{Colors.HEADER}{'='*58}{Colors.END}\n"
        )
        
        # Print status and ensure output is flushed
        sys.stdout.write(status_str)
        sys.stdout.flush()