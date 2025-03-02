import asyncio
import logging
import aiohttp
import ssl
import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Dict, Set, Optional, Tuple
from email.utils import parsedate_to_datetime
from time import mktime
from .priority_feed_processor import PriorityFeedProcessor, ArticleEntry

logger = logging.getLogger(__name__)

@dataclass
class FeedConfiguration:
    max_concurrent_feeds: int = 10
    min_poll_interval: int = 300  # 5 minutes
    max_poll_interval: int = 3600  # 1 hour
    connect_timeout: float = 30.0
    total_timeout: float = 60.0
    batch_size: int = 100
    max_entries_per_feed: int = 1000

class FeedWatcher:
    def __init__(self, config: Optional[FeedConfiguration] = None, ssl_context: Optional[ssl.SSLContext] = None):
        self.config = config or FeedConfiguration()
        self.session: Optional[aiohttp.ClientSession] = None
        self.feeds: Dict[str, dict] = {}
        self.logged_entries: Set[str] = set()
        self.rate_limiter = RateLimiter()
        self.ssl_context = ssl_context or ssl.create_default_context()
        self.priority_processor = PriorityFeedProcessor()
        self.feed_metrics = {
            'total_feeds': 0,
            'active_feeds': 0,
            'failed_feeds': 0,
            'feed_stats': {},
            'start_time': time.time(),
            'last_update_time': None,
            'total_bytes_received': 0,
            'articles_by_feed': {},
            'connection_errors': 0,
            'parse_errors': 0
        }

    async def init(self):
        """Initialize the feed watcher with an aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        # Start the priority processor
        await self.priority_processor.start()
        logger.info("🔄 Feed watcher and processor initialized")

    async def close(self):
        """Close the aiohttp session and stop the processor."""
        if self.session:
            await self.session.close()
            self.session = None
        await self.priority_processor.stop()
        logger.info("🛑 Feed watcher and processor closed")

    async def check_feed_headers(self, feed_url: str) -> str:
        """Check feed headers for changes using conditional GET."""
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br'
        }
        feed_info = self.feeds.get(feed_url, {})
        
        # Only add headers if they are strings to prevent serialization errors
        if isinstance(feed_info.get('etag'), str):
            headers['If-None-Match'] = feed_info['etag']
        if isinstance(feed_info.get('last_modified'), str):
            headers['If-Modified-Since'] = feed_info['last_modified']

        max_retries = 3
        retry_delay = 5
            
        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(
                    connect=self.config.connect_timeout,
                    total=self.config.total_timeout
                )
                
                async with self.session.get(feed_url, headers=headers, timeout=timeout, ssl=self.ssl_context) as response:
                    if response.status == 304:  # Not modified
                        return ""
                    
                    # Only store headers if they are strings
                    self.feeds[feed_url] = {
                        'etag': str(response.headers.get('ETag')) if response.headers.get('ETag') else None,
                        'last_modified': str(response.headers.get('Last-Modified')) if response.headers.get('Last-Modified') else None,
                        'content_type': str(response.headers.get('Content-Type', ''))
                    }
                    
                    text = await response.text()
                    if not text:
                        return ""
                    return text
                    
            except aiohttp.ClientError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self._update_feed_metrics(feed_url, had_updates=False, error=True)
                    return ""
            except Exception:
                self._update_feed_metrics(feed_url, had_updates=False, error=True)
                return ""

    def _parse_date_with_timezone(self, entry) -> Tuple[Optional[datetime], bool]:
        """
        Parse the date from a feed entry with timezone awareness.
        All dates are converted to UTC.
        
        Returns (datetime, is_timezone_aware) tuple.
        """
        from ..utils.date_utils import ensure_utc, safe_parse_date
        
        # Try parsing published_parsed first (struct_time format)
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                # Convert time tuple to UTC timestamp then to datetime
                # Since struct_time assumes UTC, we can directly create a UTC datetime
                dt = datetime(
                    year=entry.published_parsed.tm_year,
                    month=entry.published_parsed.tm_mon,
                    day=entry.published_parsed.tm_mday,
                    hour=entry.published_parsed.tm_hour,
                    minute=entry.published_parsed.tm_min,
                    second=entry.published_parsed.tm_sec,
                    tzinfo=timezone.utc
                )
                return dt, True
            except Exception as e:
                logger.debug(f"Failed to parse published_parsed: {e}")
        
        # Try parsing published (string format)
        if hasattr(entry, 'published') and entry.published:
            try:
                # Try parsing with email.utils which handles RFC format dates
                dt = parsedate_to_datetime(entry.published)
                # Ensure date is in UTC
                dt = ensure_utc(dt)
                return dt, True  # Since parsedate_to_datetime always returns timezone-aware
            except Exception as e:
                logger.debug(f"Failed to parse published with email.utils: {e}")
                # Try with dateparser as fallback
                dt = safe_parse_date(entry.published)
                if dt:
                    return dt, True
        
        # Try updated fields as fallback
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                # Use the same direct UTC conversion for updated_parsed
                dt = datetime(
                    year=entry.updated_parsed.tm_year,
                    month=entry.updated_parsed.tm_mon,
                    day=entry.updated_parsed.tm_mday,
                    hour=entry.updated_parsed.tm_hour,
                    minute=entry.updated_parsed.tm_min,
                    second=entry.updated_parsed.tm_sec,
                    tzinfo=timezone.utc
                )
                return dt, True
            except Exception as e:
                logger.debug(f"Failed to parse updated_parsed: {e}")
        
        # Last resort - use current time but mark as timezone-aware
        dt = datetime.now(timezone.utc)
        logger.debug(f"Using current time as fallback: {dt}")
        return dt, True  # Now always returning a timezone-aware datetime in UTC

    async def process_feed_content(self, feed_url: str, content: str):
        """Process the feed content and extract entries."""
        try:
            import feedparser
            
            start_time = time.time()
            self.feed_metrics['total_bytes_received'] += len(content)
            
            feed = feedparser.parse(content)
            if not feed.entries:
                return

            new_entries = 0
            skipped_naive = 0
            feed_articles = self.feed_metrics['articles_by_feed'].get(feed_url, {
                'total': 0,
                'new': 0,
                'duplicates': 0,
                'naive_skipped': 0,
                'last_article_time': None
            })

            for entry in feed.entries[:self.config.max_entries_per_feed]:
                guid = entry.get('id', entry.get('guid', entry.get('link', '')))
                if guid in self.logged_entries:
                    feed_articles['duplicates'] += 1
                    continue
                
                pub_date, is_timezone_aware = self._parse_date_with_timezone(entry)
                
                # Skip entries without timezone information
                if not is_timezone_aware:
                    skipped_naive += 1
                    feed_articles['naive_skipped'] += 1
                    logger.debug(f"Skipping entry from {feed_url} due to naive timezone: {entry.get('title', '')}")
                    continue

                # Track newest article for this feed
                if not feed_articles['last_article_time'] or pub_date > feed_articles['last_article_time']:
                    feed_articles['last_article_time'] = pub_date
                
                article = ArticleEntry(
                    pub_date=pub_date,
                    feed_url=feed_url,
                    title=entry.get('title', ''),
                    content=entry.get('summary', entry.get('description', '')),
                    link=entry.get('link', ''),
                    guid=guid
                )
                
                self.priority_processor.add_article(article)
                self.logged_entries.add(guid)
                new_entries += 1
                feed_articles['new'] += 1
                feed_articles['total'] += 1
            
            # Update feed metrics
            self.feed_metrics['articles_by_feed'][feed_url] = feed_articles
            self.feed_metrics['last_update_time'] = datetime.now(timezone.utc)
            
            if new_entries > 0:
                logger.debug(f"📥 Added {new_entries} entries from {feed_url} (skipped {skipped_naive} naive timezone entries)")
                
            processing_time = time.time() - start_time
            self._update_feed_metrics(feed_url, had_updates=new_entries > 0, processing_time=processing_time)
            
        except Exception as e:
            logger.error(f"❌ Error processing feed {feed_url}: {str(e)}")
            self.feed_metrics['parse_errors'] += 1
            self._update_feed_metrics(feed_url, had_updates=False, error=True)

    async def watch_feed(self, feed_url: str):
        """Watch a feed URL for changes."""
        while True:
            try:
                content = await self.check_feed_headers(feed_url)
                if content:
                    await self.process_feed_content(feed_url, content)
                await asyncio.sleep(self.config.min_poll_interval)
            except Exception as e:
                logger.error(f"Error watching feed {feed_url}: {e}")
                await asyncio.sleep(self.config.min_poll_interval)

    def _update_feed_metrics(self, feed_url: str, had_updates: bool, error: bool = False, processing_time: float = 0.0):
        """Update feed metrics for monitoring."""
        if feed_url not in self.feed_metrics['feed_stats']:
            self.feed_metrics['feed_stats'][feed_url] = {
                'updates': 0,
                'errors': 0,
                'last_update': None,
                'last_error': None,
                'avg_processing_time': 0.0,
                'total_processing_time': 0.0,
                'success_rate': 100.0,
                'total_attempts': 0
            }
        
        stats = self.feed_metrics['feed_stats'][feed_url]
        stats['total_attempts'] += 1
        
        if had_updates:
            stats['updates'] += 1
            stats['last_update'] = datetime.now()
        
        if error:
            stats['errors'] += 1
            stats['last_error'] = datetime.now()
            
        stats['success_rate'] = ((stats['total_attempts'] - stats['errors']) / 
                               stats['total_attempts'] * 100 if stats['total_attempts'] > 0 else 100.0)
        
        if processing_time > 0:
            stats['total_processing_time'] += processing_time
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['total_attempts']

    def get_watcher_status(self) -> dict:
        """Get current status of the feed watcher."""
        now = datetime.now()
        uptime = time.time() - self.feed_metrics['start_time']
        
        return {
            'uptime': f"{uptime:.2f} seconds",
            'active_feeds': len(self.feeds),
            'failed_feeds': self.feed_metrics['failed_feeds'],
            'total_bytes': self.feed_metrics['total_bytes_received'],
            'connection_errors': self.feed_metrics['connection_errors'],
            'parse_errors': self.feed_metrics['parse_errors'],
            'last_update': (self.feed_metrics['last_update_time'].strftime('%Y-%m-%d %H:%M:%S') 
                          if self.feed_metrics['last_update_time'] else "Never"),
            'feed_stats': {
                url: {
                    'success_rate': f"{stats['success_rate']:.1f}%",
                    'updates': stats['updates'],
                    'errors': stats['errors'],
                    'avg_processing_time': f"{stats['avg_processing_time']:.2f}s",
                    'last_update': (stats['last_update'].strftime('%Y-%m-%d %H:%M:%S') 
                                  if stats['last_update'] else "Never"),
                    'last_error': (stats['last_error'].strftime('%Y-%m-%d %H:%M:%S') 
                                 if stats['last_error'] else "Never"),
                    'articles': self.feed_metrics['articles_by_feed'].get(url, {
                        'total': 0,
                        'new': 0,
                        'duplicates': 0,
                        'last_article_time': None
                    })
                }
                for url, stats in self.feed_metrics['feed_stats'].items()
            }
        }

    def print_status(self):
        """Print current watcher status in a clean format."""
        status = self.get_watcher_status()
        queue_status = self.priority_processor.get_processing_status()
        
        logger.info("\n=== Feed Watcher Status ===")
        logger.info(f"⏱️  Uptime: {status['uptime']}")
        logger.info(f"📡 Active Feeds: {status['active_feeds']}")
        logger.info(f"❌ Failed Feeds: {status['failed_feeds']}")
        logger.info(f"📊 Data Received: {status['total_bytes'] / 1024:.1f}KB")
        logger.info(f"🔄 Last Update: {status['last_update']}")
        logger.info(f"\n🚦 Error Stats:")
        logger.info(f"   Connection Errors: {status['connection_errors']}")
        logger.info(f"   Parse Errors: {status['parse_errors']}")
        logger.info(f"\n📈 Processing Queue:")
        logger.info(f"   Articles Queued: {queue_status['queue_size']}")
        logger.info(f"   Processing Rate: {queue_status['processing_rate']}")
        logger.info(f"   Newest Article: {queue_status['newest_article']}")
        logger.info(f"   Oldest Article: {queue_status['oldest_article']}")
        
        if status['feed_stats']:
            logger.info("\n📊 Feed Statistics:")
            for url, feed_stat in status['feed_stats'].items():
                logger.info(f"\n   {url}:")
                logger.info(f"   ├─ Success Rate: {feed_stat['success_rate']}")
                logger.info(f"   ├─ Updates: {feed_stat['updates']}")
                logger.info(f"   ├─ Errors: {feed_stat['errors']}")
                logger.info(f"   ├─ Avg Processing: {feed_stat['avg_processing_time']}")
                logger.info(f"   ├─ Last Update: {feed_stat['last_update']}")
                logger.info(f"   └─ Articles: {feed_stat['articles']['new']} new, "
                          f"{feed_stat['articles']['duplicates']} duplicates")

class RateLimiter:
    def __init__(self):
        self._error_count = 0