import asyncio
import logging
import time
import os
import sys
import math
import re
from urllib.parse import urlparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from queue import PriorityQueue

# Add the project root to PYTHONPATH
import sys
from pathlib import Path
project_root = str(Path(__file__).parent.parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database.models import update_feed_cache, get_source_priority, add_tag, tag_article

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
    
    # Ensure both datetimes have timezone information
    now = datetime.now(timezone.utc)
    
    # If dt doesn't have timezone info, assume UTC for backward compatibility
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        # Convert to UTC for consistent comparison
        dt = dt.astimezone(timezone.utc)
    
    diff = now - dt
    
    # Handle future dates (clock skew case)
    if diff.total_seconds() < 0:
        diff = abs(diff)
        prefix = "in "
    else:
        prefix = ""
    
    if diff.total_seconds() < 60:
        return f"{prefix}{int(diff.total_seconds())}s ago"
    elif diff.total_seconds() < 3600:
        return f"{prefix}{int(diff.total_seconds() / 60)}m ago"
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

def format_time_elapsed(seconds: float) -> str:
    """Format seconds into a human-readable time string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        mins = int((seconds % 3600) / 60)
        return f"{hours}h {mins}m"
    else:
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        return f"{days}d {hours}h"

def estimate_completion_time(queue_size: int, rate: float) -> str:
    """Estimate time to process the queue at the current rate."""
    if rate <= 0 or queue_size <= 0:
        return "Unknown"
    
    seconds = queue_size / (rate / 60)
    return format_time_elapsed(seconds)

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
    added_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc), compare=False)

    def __post_init__(self):
        # Ensure pub_date is timezone aware, convert to UTC if needed
        if not self.pub_date.tzinfo:
            raise ValueError("pub_date must be timezone-aware")
        
        # Convert to UTC for consistent comparisons
        if self.pub_date.tzinfo != timezone.utc:
            self.pub_date = self.pub_date.astimezone(timezone.utc)
            
        # Convert to timestamp priority (newer articles = negative numbers = higher priority)
        self.priority = -self.pub_date.timestamp()

    def get_age_minutes(self) -> float:
        """Get article age in minutes"""
        now = datetime.now(timezone.utc)
        return (now - self.pub_date).total_seconds() / 60
        
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
        self.recently_processed = []  # Store recent articles with details
        self.currently_processing = None
        self.processing_times = []  # Keep last 50 processing times
        self.processing_start_time = None
        self.feed_activity_history = {}  # Track feed activity over time
        self.performance_metrics = {
            'hourly_rates': [0] * 24,  # Last 24 hours
            'last_hour_rate': 0,
            'last_hour_processed': 0,
            'last_hour_timestamp': time.time(),
            'last_minute_processed': 0,
            'last_minute_timestamp': time.time(),
        }
        self.error_history = {}  # Track error types

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
            self.processing_start_time = start_time
            article = self.article_queue.get()
            
            # Track the domain (source) of the article for analytics
            domain = extract_domain(article.link)
            
            self.currently_processing = {
                'title': article.title[:50] + ('...' if len(article.title) > 50 else ''),
                'link': article.link,
                'date': article.pub_date,
                'feed_url': article.feed_url,
                'domain': domain,
                'start_time': start_time
            }
            
            # Basic cleanup first
            from src.utils.text import clean_text, clean_url
            cleaned_title = clean_text(article.title)
            cleaned_content = clean_text(getattr(article, 'content', ''))
            cleaned_url = clean_url(article.link)

            # Process with AI
            from src.utils.ai import content_processor
            
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
            
            # Extract image URL from the article with proper error handling
            image_url = None
            try:
                from src.core.processor import ImageExtractor
                image_extractor = ImageExtractor()
                
                # Only attempt image extraction if we have content
                if hasattr(article, 'content') and article.content:
                    images = image_extractor.extract_images(article)
                    if images:
                        image_url = images[0]
                    else:
                        # Only try content extraction if explicit image extraction failed
                        image_url = image_extractor.extract_first_image_from_content(article.content)
            except Exception as img_error:
                logger.warning(f"Image extraction failed: {str(img_error)}")
                image_url = None
            
            # Store processed article
            from src.database.models import store_article
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
            self.processing_times.append(processing_time)
            if len(self.processing_times) > 50:  # Keep only last 50 times
                self.processing_times.pop(0)
                
            self.processing_stats['total_processing_time'] += processing_time
            self.processing_stats['min_processing_time'] = min(self.processing_stats['min_processing_time'], processing_time)
            self.processing_stats['max_processing_time'] = max(self.processing_stats['max_processing_time'], processing_time)
            self.processing_stats['last_processed_article'] = article.pub_date
            self.processing_stats['last_processed_time'] = datetime.now()
            self.processing_stats['success_streak'] += 1
            self.processing_stats['consecutive_errors'] = 0
            
            # Update feed activity tracking
            feed_url = article.feed_url
            if feed_url not in self.feed_activity_history:
                self.feed_activity_history[feed_url] = {
                    'last_activity': datetime.now(),
                    'processed_count': 0,
                    'error_count': 0,
                    'avg_processing_time': 0,
                    'domains': Counter()
                }
            
            feed_activity = self.feed_activity_history[feed_url]
            feed_activity['last_activity'] = datetime.now()
            feed_activity['processed_count'] += 1
            feed_activity['avg_processing_time'] = ((feed_activity['avg_processing_time'] * 
                                                    (feed_activity['processed_count'] - 1) + 
                                                    processing_time) / feed_activity['processed_count'])
            feed_activity['domains'][domain] = feed_activity['domains'].get(domain, 0) + 1
            
            # Update rate metrics
            current_hour = datetime.now().hour
            self.performance_metrics['hourly_rates'][current_hour] += 1
            
            # Update minute-based metrics
            if time.time() - self.performance_metrics['last_minute_timestamp'] >= 60:
                self.performance_metrics['last_minute_timestamp'] = time.time()
                self.performance_metrics['last_minute_processed'] = 1
            else:
                self.performance_metrics['last_minute_processed'] += 1
                
            # Update hour-based metrics
            if time.time() - self.performance_metrics['last_hour_timestamp'] >= 3600:
                self.performance_metrics['last_hour_timestamp'] = time.time()
                self.performance_metrics['last_hour_processed'] = 1
                self.performance_metrics['last_hour_rate'] = 1
            else:
                self.performance_metrics['last_hour_processed'] += 1
                elapsed_hour_fraction = (time.time() - self.performance_metrics['last_hour_timestamp']) / 3600
                if elapsed_hour_fraction > 0:
                    self.performance_metrics['last_hour_rate'] = self.performance_metrics['last_hour_processed'] / elapsed_hour_fraction
            
            # Store details of recently processed article
            self.recently_processed.append({
                'title': article.title[:50] + ('...' if len(article.title) > 50 else ''),
                'link': article.link,
                'date': article.pub_date,
                'feed_url': article.feed_url,
                'domain': domain,
                'processing_time': processing_time
            })
            # Keep only the 5 most recent articles
            if len(self.recently_processed) > 5:
                self.recently_processed.pop(0)
                
            self.currently_processing = None
            self.processing_start_time = None
            return article

        except Exception as e:
            self.currently_processing = None
            self.processing_start_time = None
            self.processing_stats['errors'] += 1
            self.processing_stats['consecutive_errors'] += 1
            self.processing_stats['success_streak'] = 0
            
            # Track error types
            error_type = type(e).__name__
            if error_type not in self.error_history:
                self.error_history[error_type] = 1
            else:
                self.error_history[error_type] += 1
                
            logger.error(f"Error processing article: {str(e)}")
            return None

    def get_processing_status(self) -> dict:
        """Get current processing status and metrics."""
        runtime = time.time() - self.processing_stats['start_time']
        processing_rate = (self.processing_stats['processed_articles'] / runtime) * 60 if runtime > 0 else 0
        avg_time = (self.processing_stats['total_processing_time'] / 
                   self.processing_stats['processed_articles'] 
                   if self.processing_stats['processed_articles'] > 0 else 0)
        
        # Calculate median processing time
        median_time = 0
        if self.processing_times:
            sorted_times = sorted(self.processing_times)
            if len(sorted_times) % 2 == 0:
                median_time = (sorted_times[len(sorted_times)//2] + sorted_times[len(sorted_times)//2 - 1]) / 2
            else:
                median_time = sorted_times[len(sorted_times)//2]
        
        api_utilization = (self.processing_stats['api_calls'] / runtime * 60)
        error_rate = (self.processing_stats['errors'] / self.processing_stats['total_articles'] * 100 
                     if self.processing_stats['total_articles'] > 0 else 0)
        
        # Calculate estimated queue completion time
        est_completion = estimate_completion_time(self.processing_stats['queued_articles'], processing_rate)
        
        # Calculate most active feeds
        active_feeds = sorted(self.feed_activity_history.items(), 
                             key=lambda x: x[1]['processed_count'], 
                             reverse=True)[:5]
        
        # Calculate most recent errors
        top_errors = sorted(self.error_history.items(), 
                           key=lambda x: x[1], 
                           reverse=True)[:3]
        
        # Calculate current processing duration if an article is being processed
        current_processing_duration = 0
        if self.processing_start_time:
            current_processing_duration = time.time() - self.processing_start_time
        
        # Find the actual article objects for newest and oldest
        newest_article_info = None
        oldest_article_info = None
        
        # Look through the queue for details (non-destructive peek)
        if not self.article_queue.empty():
            # Create a temporary queue with references to the same articles
            items = []
            temp_items = []
            
            # Empty the queue temporarily
            while not self.article_queue.empty():
                item = self.article_queue.get()
                items.append(item)
                temp_items.append(item)
            
            # Process the items to find newest and oldest
            for item in temp_items:
                if self.processing_stats['newest_queued_article'] == item.pub_date:
                    newest_article_info = {
                        'title': item.title[:50] + ('...' if len(item.title) > 50 else ''),
                        'link': item.link,
                        'pub_date': item.pub_date,
                    }
                if self.processing_stats['oldest_queued_article'] == item.pub_date:
                    oldest_article_info = {
                        'title': item.title[:50] + ('...' if len(item.title) > 50 else ''),
                        'link': item.link,
                        'pub_date': item.pub_date,
                    }
                
            # Put all items back in the original queue
            for item in items:
                self.article_queue.put(item)
        
        # Get latest processed article info
        latest_processed_info = self.recently_processed[-1] if self.recently_processed else None
        currently_processing_info = self.currently_processing
        
        # Include performance trend data
        minute_rate = self.performance_metrics['last_minute_processed']
        hour_rate = self.performance_metrics['last_hour_rate']
        
        return {
            'queue_size': self.processing_stats['queued_articles'],
            'peak_size': self.processing_stats['peak_queue_size'],
            'total': self.processing_stats['total_articles'],
            'processed': self.processing_stats['processed_articles'],
            'processing_rate': processing_rate,
            'avg_time': avg_time,
            'median_time': median_time,
            'api_load': api_utilization,
            'error_rate': error_rate,
            'age_distribution': self.processing_stats['articles_by_age'],
            'newest_article': newest_article_info,
            'oldest_article': oldest_article_info,
            'latest_article': latest_processed_info,
            'current_article': currently_processing_info,
            'current_time': current_processing_duration,
            'success_streak': self.processing_stats['success_streak'],
            'est_completion': est_completion,
            'rate_per_minute': minute_rate,
            'rate_per_hour': hour_rate
        }

def extract_domain(url: str) -> str:
    """Extract the domain name from a URL."""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Remove www. prefix if present
        if (domain.startswith('www.')):
            domain = domain[4:]
            
        return domain
    except:
        return "unknown"