"""Feed watching and processing module."""
import feedparser
import asyncio
import random
import datetime
from datetime import timezone
import aiohttp
import logging
import traceback
from typing import Set, Dict, Any, Optional, List, Callable
from email.utils import parsedate_to_datetime
from .processor import process_article
from ..database.models import (
    get_db, load_feed_cache, update_feed_cache, 
    get_feed_metrics, exists_in_db, get_source_priority,
    add_tag, tag_article
)
from ..utils.text import clean_url
from ..web.websocket_manager import broadcast_news_update

# Enhanced logging configuration with colored output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - \x1b[36m%(message)s\x1b[0m'
)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for API calls."""
    def __init__(self, calls_per_minute: int = 15, calls_per_day: int = 1500):
        self.calls_per_minute = calls_per_minute
        self.calls_per_day = calls_per_day
        self.minute_calls = 0
        self.daily_calls = 0
        self.last_minute_reset = datetime.datetime.now()
        self.last_daily_reset = datetime.datetime.now()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Try to acquire a rate limit token."""
        async with self._lock:
            now = datetime.datetime.now()
            
            # Reset counters if needed
            if (now - self.last_minute_reset).total_seconds() >= 60:
                self.minute_calls = 0
                self.last_minute_reset = now
                
            if (now - self.last_daily_reset).total_seconds() >= 86400:
                self.daily_calls = 0
                self.last_daily_reset = now
            
            # Check limits
            if self.minute_calls >= self.calls_per_minute:
                delay = 60 - (now - self.last_minute_reset).total_seconds()
                if delay > 0:
                    logger.warning(f"⏳ Rate limit reached. Waiting {delay:.1f}s")
                    await asyncio.sleep(delay)
                    self.minute_calls = 0
                    self.last_minute_reset = datetime.datetime.now()
            
            if self.daily_calls >= self.calls_per_day:
                delay = 86400 - (now - self.last_daily_reset).total_seconds()
                if delay > 0:
                    logger.error(f"❌ Daily limit reached. Waiting {delay:.1f}s")
                    await asyncio.sleep(delay)
                    self.daily_calls = 0
                    self.last_daily_reset = datetime.datetime.now()
            
            self.minute_calls += 1
            self.daily_calls += 1

class FeedConfiguration:
    """Configuration for feed watcher."""
    def __init__(self, 
                 max_concurrent_feeds: int = 10,
                 min_poll_interval: int = 30,
                 max_poll_interval: int = 3600,
                 error_backoff_delay: int = 60,
                 process_timeout: int = 100,
                 connect_timeout: float = 30.0,
                 total_timeout: float = 60.0,
                 batch_size: int = 5,
                 max_entries_per_feed: int = 20):
        self.max_concurrent_feeds = max_concurrent_feeds
        self.min_poll_interval = min_poll_interval
        self.max_poll_interval = max_poll_interval
        self.error_backoff_delay = error_backoff_delay
        self.process_timeout = process_timeout
        self.connect_timeout = connect_timeout
        self.total_timeout = total_timeout
        self.batch_size = batch_size
        self.max_entries_per_feed = max_entries_per_feed

class FeedEntry:
    """Represents a processed feed entry."""
    def __init__(self, entry: Any, entry_time: datetime.datetime, feed_url: str):
        self.entry = entry
        self.entry_time = entry_time
        self.feed_url = feed_url
        self.processed_result: Optional[Dict] = None

class FeedWatcher:
    """Watches RSS feeds for updates and processes new entries."""
    
    def __init__(self, config: Optional[FeedConfiguration] = None):
        self.config = config or FeedConfiguration()
        self.feeds: Dict[str, Dict[str, Any]] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.logged_entries: Set[str] = set()
        self.logged_urls: Set[str] = set()
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_feeds)
        self.rate_limiter = RateLimiter()
        self._on_entry_processed_callbacks: List[Callable] = []
        logger.info("🚀 Initializing FeedWatcher")

    def add_entry_processed_callback(self, callback: Callable):
        """Add a callback to be called when an entry is processed."""
        self._on_entry_processed_callbacks.append(callback)

    async def _notify_entry_processed(self, entry: FeedEntry, result: Any):
        """Notify all callbacks that an entry has been processed."""
        for callback in self._on_entry_processed_callbacks:
            try:
                await callback(entry, result)
            except Exception as e:
                logger.error(f"Error in entry processed callback: {e}")

    async def init(self):
        """Initialize aiohttp session and logged entries."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("📡 HTTP session initialized")
        await self._load_logged_entries()
        logger.info(f"🗄️ Loaded {len(self.logged_entries)} cached entries")
        
    async def _load_logged_entries(self):
        """Load previously processed entries from database."""
        with get_db() as conn:
            # Load both messages and URLs
            cursor = conn.execute('SELECT message, link FROM news_entries')
            for row in cursor:
                if row[0]: self.logged_entries.add(row[0])
                if row[1]: self.logged_urls.add(clean_url(row[1]))

    async def close(self):
        """Cleanup resources."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    def _update_feed_metrics(self, feed_url: str, had_updates: bool, error: bool = False):
        """Update feed metrics based on check results."""
        metrics = get_feed_metrics(feed_url)
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        if error:
            metrics['consecutive_failures'] += 1
            metrics['update_frequency'] = min(
                metrics['update_frequency'] * 2,
                self.config.max_poll_interval
            )
        else:
            if had_updates:
                metrics['update_frequency'] = max(
                    metrics['update_frequency'] // 2,
                    self.config.min_poll_interval
                )
                metrics['consecutive_failures'] = 0
                metrics['last_success_time'] = current_time
            else:
                metrics['update_frequency'] = min(
                    int(metrics['update_frequency'] * 1.5),
                    self.config.max_poll_interval
                )
                metrics['consecutive_failures'] = 0

        # Get updated source priority
        metrics['source_priority'] = get_source_priority(feed_url)
        
        update_feed_cache(feed_url, metrics)
        return metrics['update_frequency']

    async def check_feed_headers(self, feed_url: str) -> str:
        """Check feed headers for changes using conditional GET."""
        if not self.session:
            raise FeedError("Session not initialized")
            
        logger.info(f"🔍 Checking feed: {feed_url}")
        headers = {}
        feed_info = self.feeds.get(feed_url, {})
        
        if 'etag' in feed_info:
            headers['If-None-Match'] = feed_info['etag']
        if 'last_modified' in feed_info:
            headers['If-Modified-Since'] = feed_info['last_modified']
            
        try:
            timeout = aiohttp.ClientTimeout(
                connect=self.config.connect_timeout,
                total=self.config.total_timeout
            )
            async with self.session.get(feed_url, headers=headers, timeout=timeout) as response:
                if response.status == 304:  # Not modified
                    logger.info(f"📭 No changes in feed: {feed_url}")
                    return ""
                    
                logger.info(f"📬 Retrieved feed content: {feed_url} (Status: {response.status})")
                self.feeds[feed_url] = {
                    'etag': response.headers.get('ETag'),
                    'last_modified': response.headers.get('Last-Modified'),
                    'content_type': response.headers.get('Content-Type', '')
                }
                
                text = await response.text()
                # Check if content was actually received
                if not text:
                    raise ValueError("Empty response received")
                return text
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error checking feed {feed_url}: {str(e)}")
            self._update_feed_metrics(feed_url, had_updates=False, error=True)
            return ""
        except Exception as e:
            logger.error(f"Unexpected error checking feed {feed_url}: {str(e)}")
            self._update_feed_metrics(feed_url, had_updates=False, error=True)
            return ""

    async def process_entry(self, entry: FeedEntry) -> Optional[datetime.datetime]:
        """Process a single feed entry."""
        async with self.semaphore:
            try:
                logger.info(f"🔄 Processing entry from: {entry.feed_url}")
                result = await asyncio.wait_for(
                    process_article(entry.entry), 
                    timeout=self.config.process_timeout
                )
                
                if result:
                    # Check both content and URL for duplicates, including in database
                    clean_link = clean_url(result.link)
                    is_duplicate = (
                        result.combined in self.logged_entries or 
                        (clean_link and (clean_link in self.logged_urls or exists_in_db(clean_link)))
                    )
                    
                    if not is_duplicate:
                        logger.info(f"📝 New unique entry found: {result.title}")
                        await self._store_entry(entry, result)
                        await self._notify_entry_processed(entry, result)
                        self.logged_entries.add(result.combined)
                        if clean_link:
                            self.logged_urls.add(clean_link)
                        
                        # Broadcast update to web clients
                        news_item = {
                            'title': result.title,
                            'description': result.description,
                            'link': result.link,
                            'image_url': result.image_url,
                            'timestamp': entry.entry_time.isoformat(),
                            'emoji1': result.emoji1,
                            'emoji2': result.emoji2,
                            'feed_url': entry.feed_url
                        }
                        await broadcast_news_update(news_item)
                        
                        return entry.entry_time
                    else:
                        logger.info(f"🔄 Duplicate entry skipped: {result.title}")
                return None
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Timeout processing entry from {entry.feed_url}")
                return None
            except Exception as e:
                logger.error(f"❌ Error processing entry: {e}\nTraceback:\n{traceback.format_exc()}")
                return None

    async def _store_entry(self, entry: FeedEntry, result):
        """Store processed entry in database."""
        try:
            with get_db() as conn:
                # Insert article
                cursor = conn.execute('''
                    INSERT INTO news_entries 
                    (message, pub_date, processed_date, feed_url, title, description, 
                     link, image_url, content, emoji1, emoji2)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.message,
                    entry.entry_time.isoformat(),
                    datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    entry.feed_url,
                    result.title,
                    result.description,
                    result.link,
                    result.image_url,
                    result.content,
                    result.emoji1,
                    result.emoji2
                ))
                
                article_id = cursor.lastrowid
                logger.info(f"💾 Stored article in DB: {result.title} (ID: {article_id})")
                
                # Store tags
                tag_ids = []
                
                # Add topic tags
                for tag in result.topic_tags:
                    if tag and tag.strip():
                        tag_ids.append(add_tag(tag.strip(), 'topic'))
                        
                # Add geography tags
                for tag in result.geography_tags:
                    if tag and tag.strip():
                        tag_ids.append(add_tag(tag.strip(), 'geography'))
                        
                # Add event tags
                for tag in result.event_tags:
                    if tag and tag.strip():
                        tag_ids.append(add_tag(tag.strip(), 'event'))
                
                # Link tags to article
                if tag_ids:
                    tag_article(article_id, tag_ids)
                    logger.info(f"🏷️ Added {len(tag_ids)} tags to article {article_id}")
                
                conn.commit()
                logger.info(f"✅ Database transaction committed for {result.title}")

                # Create news item for broadcast
                news_item = {
                    'title': result.title,
                    'description': result.description,
                    'link': result.link,
                    'timestamp': entry.entry_time.isoformat(),
                    'image_url': result.image_url,
                    'feed_url': entry.feed_url,
                    'emoji1': result.emoji1,
                    'emoji2': result.emoji2
                }
                
                # Broadcast with article ID for tag inclusion
                await broadcast_news_update(news_item, article_id)
                logger.info(f"📡 Broadcasted to web clients: {result.title}")
                
        except Exception as e:
            logger.error(f"❌ Error storing entry {result.title}: {str(e)}")
            raise

    async def process_entry_batch(self, entries: List[FeedEntry]) -> List[Optional[datetime.datetime]]:
        """Process a batch of feed entries with rate limiting."""
        results = []
        for entry in entries:
            try:
                await self.rate_limiter.acquire()
                logger.info(f"🔄 Processing entry from: {entry.feed_url}")
                
                result = await asyncio.wait_for(
                    process_article(entry.entry),
                    timeout=self.config.process_timeout
                )
                
                if not result:
                    logger.warning(f"❌ Entry processing failed or returned None: {getattr(entry.entry, 'title', 'Unknown title')}")
                    results.append(None)
                    continue
                
                clean_link = clean_url(result.link)
                is_content_duplicate = result.combined in self.logged_entries
                is_url_duplicate = clean_link and (clean_link in self.logged_urls or exists_in_db(clean_link))
                
                if is_content_duplicate:
                    logger.info(f"🔄 Duplicate content detected: {result.title}")
                    results.append(None)
                elif is_url_duplicate:
                    logger.info(f"🔄 Duplicate URL detected: {result.link}")
                    results.append(None)
                else:
                    logger.info(f"📝 New unique entry found: {result.title}")
                    await self._store_entry(entry, result)
                    await self._notify_entry_processed(entry, result)
                    self.logged_entries.add(result.combined)
                    if clean_link:
                        self.logged_urls.add(clean_link)
                    results.append(entry.entry_time)
                    
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Timeout processing entry from {entry.feed_url}")
                results.append(None)
            except Exception as e:
                logger.error(f"❌ Error processing entry from {entry.feed_url}: {str(e)}")
                results.append(None)
                
        return results

    async def process_feed_content(self, feed_url: str, content: str) -> None:
        """Process feed content if it has changed."""
        if not content:
            self._update_feed_metrics(feed_url, had_updates=False)
            return
            
        logger.info(f"📋 Processing content from: {feed_url}")
        feed = feedparser.parse(content)
        if not feed.entries:
            logger.info(f"📭 No entries found in feed: {feed_url}")
            self._update_feed_metrics(feed_url, had_updates=False)
            return
            
        cache = load_feed_cache()
        feed_info = cache.get(feed_url, {})
        last_check = feed_info.get('last_check', datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
        
        new_entries = self._get_new_entries(feed, last_check, feed_url)
        if not new_entries:
            logger.info(f"📭 No new entries since last check: {feed_url}")
            self._update_feed_metrics(feed_url, had_updates=False)
            return
        
        # Sort entries by date (newest first) and limit max entries
        new_entries.sort(key=lambda x: x.entry_time, reverse=True)
        new_entries = new_entries[:self.config.max_entries_per_feed]
        
        logger.info(f"📰 Processing {len(new_entries)} new entries in batches from: {feed_url}")
        processed_entries = 0
        new_entry_times = []
        
        # Process entries in batches
        for i in range(0, len(new_entries), self.config.batch_size):
            batch = new_entries[i:i + self.config.batch_size]
            results = await self.process_entry_batch(batch)
            processed_entries += sum(1 for r in results if r is not None)
            new_entry_times.extend([t for t in results if t is not None])
            
            if i + self.config.batch_size < len(new_entries):
                logger.info(f"⏳ Processed {processed_entries} entries, waiting before next batch...")
                await asyncio.sleep(2)  # Small delay between batches
        
        if new_entry_times:
            latest = max(new_entry_times)
            logger.info(f"✅ Successfully processed {processed_entries} entries from: {feed_url}")
            update_feed_cache(feed_url, {
                'last_check': latest,
                'etag': self.feeds.get(feed_url, {}).get('etag'),
                'last_modified': self.feeds.get(feed_url, {}).get('last_modified')
            })
            self._update_feed_metrics(feed_url, had_updates=True)

    def _get_new_entries(self, feed: Any, last_check: datetime.datetime, feed_url: str) -> List[FeedEntry]:
        """Get new entries from feed that haven't been processed yet."""
        new_entries = []
        
        # Validate and ensure last_check has timezone info
        if last_check is None:
            last_check = datetime.datetime.min.replace(tzinfo=timezone.utc)
        elif last_check.tzinfo is None:
            last_check = last_check.replace(tzinfo=timezone.utc)
        
        for entry in feed.entries:
            try:
                # Try different date fields in order of preference
                pub_date = None
                
                # Try standard RSS date formats with error handling
                if hasattr(entry, 'published') and entry.published:
                    try:
                        pub_date = parsedate_to_datetime(entry.published)
                    except (TypeError, ValueError, AttributeError):
                        pass
                
                if pub_date is None and hasattr(entry, 'updated') and entry.updated:
                    try:
                        pub_date = parsedate_to_datetime(entry.updated)
                    except (TypeError, ValueError, AttributeError):
                        pass
                
                # Try parsed tuples from feedparser
                if pub_date is None and hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        timestamp = datetime.datetime(*entry.published_parsed[:6])
                        pub_date = timestamp.replace(tzinfo=timezone.utc)
                    except (TypeError, ValueError, AttributeError):
                        pass
                
                if pub_date is None and hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    try:
                        timestamp = datetime.datetime(*entry.updated_parsed[:6])
                        pub_date = timestamp.replace(tzinfo=timezone.utc)
                    except (TypeError, ValueError, AttributeError):
                        pass
                
                # If no valid date found, use current time as fallback
                if pub_date is None:
                    pub_date = datetime.datetime.now(timezone.utc)
                    logger.warning(f"No valid date found for entry from {feed_url}, using current time")
                elif pub_date.tzinfo is None:
                    # Ensure pub_date has timezone info
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                
                # Double check we have a valid datetime before comparing
                if isinstance(pub_date, datetime.datetime) and isinstance(last_check, datetime.datetime):
                    if pub_date > last_check:
                        new_entries.append(FeedEntry(entry, pub_date, feed_url))
                else:
                    logger.warning(f"Invalid date comparison skipped for {feed_url}: pub_date={pub_date}, last_check={last_check}")
                    
            except Exception as e:
                logger.warning(f"Error parsing entry date from {feed_url}: {e}")
                continue
                
        return new_entries

    async def watch_feed(self, feed_url: str) -> None:
        """Watch a single feed for updates."""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while True:
            try:
                # Get current metrics including source priority
                metrics = get_feed_metrics(feed_url)
                source_priority = metrics.get('source_priority', 100)
                
                content = await self.check_feed_headers(feed_url)
                
                if content:
                    await self.process_feed_content(feed_url, content)
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                
                # Get updated poll interval
                metrics = get_feed_metrics(feed_url)
                poll_interval = metrics['update_frequency']
                
                # Add priority-based jitter
                # Higher priority (less frequent source) = less jitter
                priority_factor = source_priority / 100.0  # Will be between 0.1 and 1.0
                jitter = random.uniform(-0.3, 0.3) * (1 - priority_factor)  # More jitter for lower priority
                sleep_time = poll_interval * (1 + jitter)
                
                # Apply exponential backoff for errors
                if consecutive_errors > max_consecutive_errors:
                    backoff_multiplier = min(2 ** (consecutive_errors - max_consecutive_errors), 8)
                    sleep_time *= backoff_multiplier
                    logger.warning(f"Feed {feed_url} experiencing repeated errors. Backing off for {sleep_time:.1f}s")
                
                # Add priority-based delay
                # Lower priority = longer delay between checks
                priority_delay = (100 - source_priority) * 0.01 * poll_interval  # Up to 90% additional delay for lowest priority
                sleep_time += priority_delay
                
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.info(f"Feed watcher for {feed_url} cancelled")
                raise
            except Exception as e:
                logger.error(f"Error watching feed {feed_url}: {str(e)}")
                consecutive_errors += 1
                backoff_time = self.config.error_backoff_delay * min(2 ** (consecutive_errors - 1), 8)
                await asyncio.sleep(backoff_time)