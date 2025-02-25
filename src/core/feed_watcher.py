import asyncio
import logging
import aiohttp
import ssl
from dataclasses import dataclass
from typing import Dict, Set, Optional
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

    async def process_feed_content(self, feed_url: str, content: str):
        """Process the feed content and extract entries."""
        try:
            import feedparser
            from datetime import datetime
            
            feed = feedparser.parse(content)
            if not feed.entries:
                return

            new_entries = 0
            for entry in feed.entries[:self.config.max_entries_per_feed]:
                guid = entry.get('id', entry.get('guid', entry.get('link', '')))
                if guid in self.logged_entries:
                    continue
                
                pub_date = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
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
            
            if new_entries > 0:
                logger.debug(f"Added {new_entries} entries from {feed_url}")
            self._update_feed_metrics(feed_url, had_updates=new_entries > 0)
            
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {str(e)}")
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

    def _update_feed_metrics(self, feed_url: str, had_updates: bool, error: bool = False):
        """Update feed metrics for monitoring."""
        # Metrics update implementation
        pass

class RateLimiter:
    def __init__(self):
        self._error_count = 0