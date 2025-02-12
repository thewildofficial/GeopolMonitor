"""Feed watching and processing module."""
import feedparser
import asyncio
import random
import datetime
import aiohttp
import logging
import traceback
from typing import Set, Dict, Any, Optional, List
from .processor import process_article
from ..telegram.bot import send_message
from ..database.models import get_db, load_feed_cache, update_feed_cache
from ..utils.text import clean_url
from ..web.websocket_manager import broadcast_news_update

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime.s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedError(Exception):
    """Base exception for feed-related errors."""
    pass

class FeedConfiguration:
    """Configuration for feed watcher."""
    def __init__(self, 
                 max_concurrent_feeds: int = 10,
                 min_poll_interval: int = 30,
                 max_poll_interval: int = 60,
                 error_backoff_delay: int = 60,
                 process_timeout: int = 100):
        self.max_concurrent_feeds = max_concurrent_feeds
        self.min_poll_interval = min_poll_interval
        self.max_poll_interval = max_poll_interval
        self.error_backoff_delay = error_backoff_delay
        self.process_timeout = process_timeout

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
        self.feeds: Dict[str, Dict[str, str]] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.logged_entries: Set[str] = set()
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_feeds)
        
    async def init(self):
        """Initialize aiohttp session and logged entries."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        await self._load_logged_entries()
        
    async def _load_logged_entries(self):
        """Load previously processed entries from database."""
        with get_db() as conn:
            cursor = conn.execute('SELECT message FROM news_entries')
            self.logged_entries = {row[0] for row in cursor if row[0] is not None}
        
    async def close(self):
        """Cleanup resources."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            
    async def check_feed_headers(self, feed_url: str) -> str:
        """Check feed headers for changes using conditional GET."""
        if not self.session:
            raise FeedError("Session not initialized")
            
        headers = {}
        feed_info = self.feeds.get(feed_url, {})
        
        if 'etag' in feed_info:
            headers['If-None-Match'] = feed_info['etag']
        if 'last_modified' in feed_info:
            headers['If-Modified-Since'] = feed_info['last_modified']
            
        try:
            async with self.session.get(feed_url, headers=headers) as response:
                if response.status == 304:  # Not modified
                    return ""
                    
                self.feeds[feed_url] = {
                    'etag': response.headers.get('ETag'),
                    'last_modified': response.headers.get('Last-Modified'),
                    'content_type': response.headers.get('Content-Type', '')
                }
                
                return await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"Network error checking feed {feed_url}: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error checking feed {feed_url}: {e}")
            return ""
            
    async def process_entry(self, entry: FeedEntry) -> Optional[datetime.datetime]:
        """Process a single feed entry."""
        async with self.semaphore:
            try:
                result = await asyncio.wait_for(
                    process_article(entry.entry), 
                    timeout=self.config.process_timeout
                )
                
                if result and result.combined not in self.logged_entries:
                    await self._store_entry(entry, result)
                    await send_message(result.combined, result.images)
                    self.logged_entries.add(result.combined)
                    
                    # Broadcast update to web clients
                    news_item = {
                        'title': result.title,
                        'description': result.description,
                        'link': result.link,
                        'image_url': result.image_url,
                        'timestamp': datetime.datetime.now().isoformat(),
                        'emoji1': result.emoji1,
                        'emoji2': result.emoji2,
                        'feed_url': entry.feed_url
                    }
                    await broadcast_news_update(news_item)
                    
                return entry.entry_time
            except asyncio.TimeoutError:
                logger.warning(f"Timeout processing entry from {entry.feed_url}")
                return None
            except Exception as e:
                logger.error(f"Error processing entry: {e}\nTraceback:\n{traceback.format_exc()}")
                return None
                
    async def _store_entry(self, entry: FeedEntry, result):
        """Store processed entry in database."""
        with get_db() as conn:
            conn.execute('''
                INSERT INTO news_entries 
                (message, timestamp, feed_url, title, description, link, image_url, content, emoji1, emoji2)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.message,
                datetime.datetime.now().isoformat(),
                entry.feed_url,
                result.title,
                result.description,
                result.link,
                result.image_url,
                result.content,
                result.emoji1,
                result.emoji2
            ))
            conn.commit()
                
    async def process_feed_content(self, feed_url: str, content: str) -> None:
        """Process feed content if it has changed."""
        if not content:
            return
            
        feed = feedparser.parse(content)
        if not feed.entries:
            return
            
        cache = load_feed_cache()
        last_check = cache.get(feed_url, datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
        
        new_entries = self._get_new_entries(feed, last_check, feed_url)
        if not new_entries:
            return
            
        tasks = [self.process_entry(entry) for entry in new_entries]
        results = await asyncio.gather(*tasks)
        
        new_entry_times = [t for t in results if t is not None]
        if new_entry_times:
            update_feed_cache(feed_url, max(new_entry_times))
            
    def _get_new_entries(self, feed: Any, last_check: datetime.datetime, feed_url: str) -> List[FeedEntry]:
        """Get new entries from feed that haven't been processed yet."""
        new_entries = []
        
        for entry in feed.entries:
            try:
                # Try different date fields in order of preference
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    time_tuple = entry.published_parsed
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    time_tuple = entry.updated_parsed
                else:
                    # Skip entries without valid dates
                    continue

                # Ensure we have a valid time tuple
                if not isinstance(time_tuple, tuple) or len(time_tuple) < 6:
                    continue

                year, month, day, hour, minute, second = time_tuple[:6]
                entry_time = datetime.datetime(
                    year, month, day, hour, minute, second,
                    tzinfo=datetime.timezone.utc
                )
                
                if entry_time > last_check:
                    new_entries.append(FeedEntry(entry, entry_time, feed_url))
            except (AttributeError, TypeError, ValueError) as e:
                logger.warning(f"Error parsing entry date from {feed_url}: {e}")
                continue
                
        return new_entries
            
    async def watch_feed(self, feed_url: str) -> None:
        """Watch a single feed for updates."""
        try:
            # Do initial fetch immediately
            content = await self.check_feed_headers(feed_url)
            if content:
                logger.info(f"🔄 Initial fetch from {feed_url}")
                await self.process_feed_content(feed_url, content)
        except Exception as e:
            logger.error(f"Error during initial fetch from {feed_url}: {e}\nTraceback:\n{traceback.format_exc()}")

        # Then start the regular polling loop
        while True:
            try:
                await asyncio.sleep(random.randint(
                    self.config.min_poll_interval,
                    self.config.max_poll_interval
                ))
                
                content = await self.check_feed_headers(feed_url)
                if content:
                    logger.info(f"🔄 Updates found in {feed_url}")
                    await self.process_feed_content(feed_url, content)
                    
            except Exception as e:
                logger.error(f"Error watching feed {feed_url}: {e}\nTraceback:\n{traceback.format_exc()}")
                await asyncio.sleep(self.config.error_backoff_delay)