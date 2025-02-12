"""Stand-alone feed watcher service."""
import asyncio
import logging
from src.core.feed_watcher import FeedWatcher, FeedConfiguration
from config.settings import FEED_POLL_INTERVAL, MAX_CONCURRENT_FEEDS
from src.database.models import init_db

logger = logging.getLogger(__name__)

def load_feed_urls():
    """Load feed URLs from feeds.txt"""
    try:
        with open("feeds.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Error loading feeds: {e}")
        return []

async def run_feed_watcher():
    """Initialize and run the feed watcher service"""
    config = FeedConfiguration(
        max_concurrent_feeds=MAX_CONCURRENT_FEEDS,
        min_poll_interval=FEED_POLL_INTERVAL[0],
        max_poll_interval=FEED_POLL_INTERVAL[1],
        connect_timeout=30.0,
        total_timeout=60.0
    )
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            feed_watcher = FeedWatcher(config)
            await feed_watcher.init()
            
            feed_urls = load_feed_urls()
            if not feed_urls:
                logger.error("No feed URLs loaded. Check feeds.txt file.")
                return
                
            tasks = []
            for url in feed_urls:
                task = asyncio.create_task(feed_watcher.watch_feed(url))
                tasks.append(task)
            
            logger.info(f"Starting feed watcher with {len(feed_urls)} feeds")
            await asyncio.gather(*tasks)
            return
            
        except Exception as e:
            logger.error(f"Error initializing feed watcher (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("Max retries exceeded. Exiting.")
                raise
        finally:
            if 'feed_watcher' in locals():
                await feed_watcher.close()

if __name__ == "__main__":
    # Initialize logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize database
    init_db()
    
    try:
        asyncio.run(run_feed_watcher())
    except KeyboardInterrupt:
        logger.info("\n🛑 Feed watcher service stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)