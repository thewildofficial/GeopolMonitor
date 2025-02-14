"""Stand-alone feed watcher service."""
import asyncio
import logging
from src.core.feed_watcher import FeedWatcher, FeedConfiguration
from config.settings import (
    FEED_POLL_INTERVAL, MAX_CONCURRENT_FEEDS,
    BATCH_SIZE, MAX_ENTRIES_PER_FEED,
    API_CALLS_PER_MINUTE, API_CALLS_PER_DAY
)
from src.database.models import init_db

# Configure service-level logging with colored output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - \x1b[32m%(message)s\x1b[0m'
)
logger = logging.getLogger(__name__)

def load_feed_urls():
    """Load feed URLs from feeds.txt"""
    try:
        with open("feeds.txt", "r") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            logger.info(f"📋 Loaded {len(urls)} feed URLs from feeds.txt")
            return urls
    except Exception as e:
        logger.error(f"❌ Error loading feeds: {e}")
        return []

async def run_feed_watcher():
    """Initialize and run the feed watcher service"""
    config = FeedConfiguration(
        max_concurrent_feeds=MAX_CONCURRENT_FEEDS,
        min_poll_interval=FEED_POLL_INTERVAL[0],
        max_poll_interval=FEED_POLL_INTERVAL[1],
        connect_timeout=30.0,
        total_timeout=60.0,
        batch_size=BATCH_SIZE,
        max_entries_per_feed=MAX_ENTRIES_PER_FEED
    )
    
    max_retries = 3
    retry_delay = 5
    
    logger.info("🚀 Starting feed watcher service")
    logger.info(f"""⚙️ Configuration:
    - Poll interval: {FEED_POLL_INTERVAL[0]}-{FEED_POLL_INTERVAL[1]}s
    - Max concurrent feeds: {MAX_CONCURRENT_FEEDS}
    - Batch size: {BATCH_SIZE}
    - Max entries per feed: {MAX_ENTRIES_PER_FEED}
    - API limits: {API_CALLS_PER_MINUTE}/min, {API_CALLS_PER_DAY}/day""")
    
    for attempt in range(max_retries):
        try:
            feed_watcher = FeedWatcher(config)
            await feed_watcher.init()
            
            feed_urls = load_feed_urls()
            if not feed_urls:
                logger.error("❌ No feed URLs loaded. Check feeds.txt file.")
                return
                
            tasks = []
            for url in feed_urls:
                task = asyncio.create_task(feed_watcher.watch_feed(url))
                tasks.append(task)
            
            logger.info(f"✨ Feed watcher initialized with {len(feed_urls)} feeds")
            logger.info("▶️ Starting feed monitoring...")
            await asyncio.gather(*tasks)
            return
            
        except Exception as e:
            logger.error(f"❌ Error initializing feed watcher (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("❌ Max retries exceeded. Exiting.")
                raise
        finally:
            if 'feed_watcher' in locals():
                await feed_watcher.close()

if __name__ == "__main__":
    try:
        # Initialize database
        init_db()
        logger.info("📦 Database initialized")
        
        # Run the feed watcher
        asyncio.run(run_feed_watcher())
    except KeyboardInterrupt:
        logger.info("\n🛑 Feed watcher service stopped")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        exit(1)