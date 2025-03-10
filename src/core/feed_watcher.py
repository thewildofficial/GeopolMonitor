import asyncio
import logging
import aiohttp
import ssl
import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Dict, Set, Optional, Tuple, List
from email.utils import parsedate_to_datetime
from time import mktime
from .priority_feed_processor import PriorityFeedProcessor, ArticleEntry
from config.settings import API_CALLS_PER_MINUTE, API_CALLS_PER_DAY

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
    briefing_refresh_interval: int = 3600  # 1 hour by default

class FeedWatcher:
    """Main class for watching and processing RSS/Atom feeds."""
    
    def __init__(self, config: FeedConfiguration = None, 
                 ssl_context: Optional[ssl.SSLContext] = None):
        """Initialize the feed watcher."""
        self.config = config or FeedConfiguration()
        self.priority_processor = PriorityFeedProcessor(API_CALLS_PER_MINUTE)
        self.feed_metrics = {
            'last_update_time': None,
            'articles_by_feed': {},
        }
        self.ssl_context = ssl_context or ssl.create_default_context()
        self.logged_entries = set()
        self.session = None
        self.healthy_feeds = set()
        self.unhealthy_feeds = {}
        self.briefing_status = {}  # Store briefing system metrics
        self.feeds = {}  # Store feed metadata like etags and last-modified
        self.rate_limiter = RateLimiter(
            calls_per_minute=API_CALLS_PER_MINUTE,
            calls_per_day=API_CALLS_PER_DAY
        )
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
        # Add briefing metrics to track daily briefing generation and updates
        self.briefing_metrics = {
            'last_generation_time': None,
            'last_refresh_time': None,
            'total_briefings_generated': 0,
            'total_refreshes': 0,
            'failed_refreshes': 0,
            'avg_generation_time': 0.0,
            'avg_refresh_time': 0.0,
            'total_generation_time': 0.0,
            'total_refresh_time': 0.0,
            'flash_alerts_today': 0,
            'flash_alerts_total': 0,
            'regional_hotspots': [],
            'briefing_history': []
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
                if not is_timezone_aware:
                    skipped_naive += 1
                    feed_articles['naive_skipped'] += 1
                    logger.debug(f"Skipping entry from {feed_url} due to naive timezone: {entry.get('title', '')}")
                    continue

                # Track newest article for this feed
                if not feed_articles['last_article_time'] or pub_date > feed_articles['last_article_time']:
                    feed_articles['last_article_time'] = pub_date
                
                # Get all possible content fields
                content = entry.get('content', [{}])[0].get('value', '')  # Full content if available
                if not content:
                    content = entry.get('summary', entry.get('description', ''))

                article = ArticleEntry(
                    pub_date=pub_date,
                    feed_url=feed_url,
                    title=entry.get('title', ''),
                    content=content,
                    link=entry.get('link', ''),
                    guid=guid
                )
                
                # Add media content if available
                if hasattr(entry, 'media_content'):
                    setattr(article, 'media_content', entry.media_content)
                if hasattr(entry, 'enclosures'):
                    setattr(article, 'enclosures', entry.enclosures)
                
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

    def update_briefing_metrics(self, 
                               briefing_generated: bool = False, 
                               refresh_success: bool = True, 
                               generation_time: float = 0.0, 
                               refresh_time: float = 0.0,
                               flash_alerts: int = 0,
                               regional_hotspots: List[str] = None):
        """Update metrics related to daily briefing generation and refresh.

        Args:
            briefing_generated: Whether a new briefing was generated (vs just refreshed)
            refresh_success: Whether the refresh operation was successful
            generation_time: Time taken to generate the briefing in seconds
            refresh_time: Time taken to refresh the briefing in seconds
            flash_alerts: Number of new flash alerts in this refresh
            regional_hotspots: List of regions identified as hotspots
        """
        now = datetime.now(timezone.utc)
        
        # Update timestamps
        if briefing_generated:
            self.briefing_metrics['last_generation_time'] = now
            self.briefing_metrics['total_briefings_generated'] += 1
            
            if generation_time > 0:
                self.briefing_metrics['total_generation_time'] += generation_time
                self.briefing_metrics['avg_generation_time'] = (
                    self.briefing_metrics['total_generation_time'] / 
                    self.briefing_metrics['total_briefings_generated']
                )
                
            # Add to history (keep last 10)
            self.briefing_metrics['briefing_history'].append({
                'timestamp': now,
                'generation_time': generation_time,
                'flash_alerts': flash_alerts
            })
            
            # Keep only last 10 entries
            self.briefing_metrics['briefing_history'] = self.briefing_metrics['briefing_history'][-10:]
        
        # Always update refresh metrics
        self.briefing_metrics['last_refresh_time'] = now
        self.briefing_metrics['total_refreshes'] += 1
        
        if not refresh_success:
            self.briefing_metrics['failed_refreshes'] += 1
        
        if refresh_time > 0:
            self.briefing_metrics['total_refresh_time'] += refresh_time
            self.briefing_metrics['avg_refresh_time'] = (
                self.briefing_metrics['total_refresh_time'] / 
                self.briefing_metrics['total_refreshes']
            )
        
        # Track flash alerts
        if flash_alerts > 0:
            self.briefing_metrics['flash_alerts_today'] += flash_alerts
            self.briefing_metrics['flash_alerts_total'] += flash_alerts
        
        # Update regional hotspots if provided
        if regional_hotspots:
            self.briefing_metrics['regional_hotspots'] = regional_hotspots
        
        logger.debug(f"Updated briefing metrics: generation={briefing_generated}, "
                   f"refresh_time={refresh_time:.2f}s, flash_alerts={flash_alerts}")

    def reset_daily_briefing_metrics(self):
        """Reset the daily counters for briefing metrics (call at midnight)"""
        self.briefing_metrics['flash_alerts_today'] = 0
        logger.info("Daily briefing metrics reset for new day")
    
    def get_briefing_status(self) -> dict:
        """Get the current status of the daily briefing system.

        Returns:
            dict: Dictionary containing briefing metrics
        """
        # Calculate time since last generation and refresh
        now = datetime.now(timezone.utc)
        last_gen = self.briefing_metrics['last_generation_time']
        last_refresh = self.briefing_metrics['last_refresh_time']
        
        time_since_generation = None
        if last_gen:
            td = now - last_gen
            hours, remainder = divmod(td.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_since_generation = f"{hours}h {minutes}m {seconds}s"
            
        time_since_refresh = None
        if last_refresh:
            td = now - last_refresh
            hours, remainder = divmod(td.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_since_refresh = f"{hours}h {minutes}m {seconds}s"
        
        # Calculate refresh reliability
        total_refreshes = self.briefing_metrics['total_refreshes']
        failed_refreshes = self.briefing_metrics['failed_refreshes']
        refresh_reliability = 0
        if total_refreshes > 0:
            refresh_reliability = ((total_refreshes - failed_refreshes) / total_refreshes) * 100
            
        return {
            'last_generation': last_gen.strftime('%Y-%m-%d %H:%M:%S') if last_gen else "Never",
            'last_refresh': last_refresh.strftime('%Y-%m-%d %H:%M:%S') if last_refresh else "Never",
            'time_since_generation': time_since_generation or "N/A",
            'time_since_refresh': time_since_refresh or "N/A",
            'total_briefings': self.briefing_metrics['total_briefings_generated'],
            'total_refreshes': total_refreshes,
            'refresh_reliability': f"{refresh_reliability:.1f}%",
            'avg_generation_time': f"{self.briefing_metrics['avg_generation_time']:.2f}s",
            'avg_refresh_time': f"{self.briefing_metrics['avg_refresh_time']:.2f}s",
            'flash_alerts_today': self.briefing_metrics['flash_alerts_today'],
            'flash_alerts_total': self.briefing_metrics['flash_alerts_total'],
            'regional_hotspots': self.briefing_metrics['regional_hotspots'],
            'refresh_interval': f"{self.config.briefing_refresh_interval}s"
        }

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
            'briefing_status': self.get_briefing_status() if hasattr(self, 'briefing_metrics') else {},
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
        # ANSI Color codes
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        BOLD = '\033[1m'
        END = '\033[0m'

        status = self.get_watcher_status()
        queue_status = self.priority_processor.get_processing_status()
        briefing_status = status.get('briefing_status', {})
        
        print(f"\n{BOLD}{BLUE}==================== Feed Processing Status ===================={END}\n")
        
        print(f"{BOLD}{GREEN}⚡ Processing State:{END} RUNNING")
        
        print(f"\n{BOLD}{CYAN}📊 Queue Status:{END}")
        print(f"   Queue Size: {BOLD}{queue_status['queue_size']}/{queue_status['peak_size']}{END} (current/peak)")
        print(f"   Processed: {BOLD}{queue_status['processed']}/{queue_status['total']}{END}")
        
        print(f"\n{BOLD}{CYAN}📊 Performance Trend:{END}")
        print(f"   Last minute: {BOLD}{queue_status['rate_per_minute']:.0f}{END} articles")
        print(f"   Last hour: {BOLD}{queue_status['rate_per_hour']:.1f}{END} articles/hour")
        
        # Color code the completion time based on queue size
        est_completion = queue_status['est_completion']
        if 'hours' in est_completion:
            completion_color = RED
        elif 'minutes' in est_completion:
            completion_color = YELLOW
        else:
            completion_color = GREEN
        print(f"   Est. completion: {completion_color}{est_completion}{END}")

        print(f"\n{BOLD}{CYAN}⚡ Processing:{END}")
        print(f"   Rate: {BOLD}{queue_status['processing_rate']:.2f}{END} articles/minute")
        print(f"   Avg/Med Time: {BOLD}{queue_status['avg_time']:.2f}s / {queue_status['median_time']:.2f}s{END}")
        
        # Color code API load
        api_load = queue_status['api_load']
        if api_load > 90:
            api_color = RED
        elif api_load > 70:
            api_color = YELLOW
        else:
            api_color = GREEN
        print(f"   API Load: {api_color}{api_load:.1f}%{END}")
        
        # Color code error rate
        error_rate = queue_status['error_rate']
        if error_rate > 10:
            error_color = RED
        elif error_rate > 5:
            error_color = YELLOW
        else:
            error_color = GREEN
        print(f"   Errors: {error_color}{error_rate:.1f}%{END}")
        
        if queue_status.get('current_article'):
            print(f"\n{BOLD}{MAGENTA}⚙️ Now Processing ({queue_status['current_time']:.1f}s):{END}")
            print(f"   {BOLD}{queue_status['current_article'].get('title', 'Unknown')[:50]}...{END}")
            print(f"   {BLUE}{queue_status['current_article'].get('link', 'No link')}{END}")
            print(f"   {queue_status['current_article'].get('pub_date', 'No date')}")

        print(f"\n{BOLD}{CYAN}📋 Daily Briefing Status:{END}")
        print(f"   Current Stage: {BOLD}{briefing_status.get('current_stage', 'Not running')}{END}")
        
        # Color code stage progress
        progress = float(briefing_status.get('stage_progress', '0').rstrip('%'))
        if progress > 75:
            progress_color = GREEN
        elif progress > 25:
            progress_color = YELLOW
        else:
            progress_color = RED
        print(f"   Stage Progress: {progress_color}{progress}%{END}")
        
        print(f"   Articles in Analysis: {BOLD}{briefing_status.get('articles_in_analysis', 0)}{END}")
        print(f"   Pending Summaries: {BOLD}{briefing_status.get('pending_summaries', 0)}{END}")
        
        last_gen = briefing_status.get('last_generation', 'Never')
        last_refresh = briefing_status.get('last_refresh', 'Never')
        refresh_reliability = briefing_status.get('refresh_reliability', '0%')
        
        print(f"   Last Generation: {YELLOW}{last_gen}{END}")
        print(f"   Last Refresh: {YELLOW}{last_refresh}{END}")
        print(f"   Reliability: {GREEN}{refresh_reliability}{END}")
        print(f"   Flash Alerts: {RED}{briefing_status.get('flash_alerts_today', 0)}{END} today, {BOLD}{briefing_status.get('flash_alerts_total', 0)}{END} total")

        if briefing_status.get('regional_hotspots'):
            hotspots = briefing_status['regional_hotspots']
            hotspot_str = ", ".join(hotspots[:5])
            if len(hotspots) > 5:
                hotspot_str += f" and {len(hotspots) - 5} more"
            print(f"   Active Hotspots: {RED}{hotspot_str}{END}")

        print(f"\n{BOLD}{CYAN}🕒 Timeline:{END}")
        if queue_status.get('latest_article'):
            print(f"   Latest: {BOLD}{queue_status['latest_article'].get('title', 'Unknown')[:50]}{END}")
            print(f"      {BLUE}{queue_status['latest_article'].get('link', 'No link')}{END}")
            print(f"      {YELLOW}{queue_status['latest_article'].get('pub_date', 'No date')}{END} ({queue_status.get('latest_age', 'unknown')} ago)")

        if queue_status.get('newest_article'):
            print(f"   Newest: {BOLD}{queue_status['newest_article'].get('title', 'Unknown')[:50]}{END}")
            print(f"      {BLUE}{queue_status['newest_article'].get('link', 'No link')}{END}")
            print(f"      {YELLOW}{queue_status['newest_article'].get('pub_date', 'No date')}{END} ({queue_status.get('newest_age', 'unknown')} ago)")

        if queue_status.get('oldest_article'):
            print(f"   Oldest: {BOLD}{queue_status['oldest_article'].get('title', 'Unknown')[:50]}{END}")
            print(f"      {BLUE}{queue_status['oldest_article'].get('link', 'No link')}{END}")
            print(f"      {YELLOW}{queue_status['oldest_article'].get('pub_date', 'No date')}{END} ({queue_status.get('oldest_age', 'unknown')} ago)")

        if status.get('feed_stats'):
            print(f"\n{BOLD}{CYAN}🔍 Trending Domains:{END}")
            domain_counts = {}
            for url, stats in status['feed_stats'].items():
                domain = url.split('/')[2]
                if stats.get('updates', 0) > 0:
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"   {MAGENTA}{domain}{END}: {BOLD}{count}{END}")

        print(f"\n{BOLD}{CYAN}📈 Article Age:{END}")
        if queue_status.get('age_distribution'):
            for age, count in queue_status['age_distribution'].items():
                print(f"   {YELLOW}{age:6}{END}: {BOLD}{count}{END}")

        print(f"\n{BOLD}{CYAN}⚙️ System:{END}")
        print(f"   Runtime: {BOLD}{status['uptime']}{END}")
        print(f"   Success Streak: {GREEN}{queue_status.get('success_streak', 0)}{END}")
        print(f"   Active Feeds: {BOLD}{status['active_feeds']}{END}")
        
        # Print errors in red at the bottom of the status
        if status['connection_errors'] > 0 or status['parse_errors'] > 0:
            print(f"\n{RED}🚦 Error Summary:")
            print(f"   Connection Errors: {status['connection_errors']}")
            print(f"   Parse Errors: {status['parse_errors']}{END}")

        print(f"\n{BOLD}{BLUE}=========================================================={END}\n")

class RateLimiter:
    """Rate limiter for API calls"""
    def __init__(self, calls_per_minute: int, calls_per_day: int):
        self.calls_per_minute = calls_per_minute
        self.calls_per_day = calls_per_day
        self.minute_calls = 0
        self.daily_calls = 0
        self.last_reset_minute = time.time()
        self.last_reset_day = time.time()

    def check_rate_limit(self) -> bool:
        """Check if we can make another API call."""
        current_time = time.time()
        
        # Reset minute counter if a minute has passed
        if current_time - self.last_reset_minute >= 60:
            self.minute_calls = 0
            self.last_reset_minute = current_time
            
        # Reset daily counter if a day has passed
        if current_time - self.last_reset_day >= 86400:
            self.daily_calls = 0
            self.last_reset_day = current_time
            
        # Check limits
        if self.minute_calls >= self.calls_per_minute:
            return False
        if self.daily_calls >= self.calls_per_day:
            return False
            
        return True
        
    def record_call(self):
        """Record that we made an API call."""
        self.minute_calls += 1
        self.daily_calls += 1
        
    def get_remaining_calls(self) -> Tuple[int, int]:
        """Get remaining API calls for minute and day."""
        return (
            max(0, self.calls_per_minute - self.minute_calls),
            max(0, self.calls_per_day - self.daily_calls)
        )