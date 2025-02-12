"""Stand-alone feed watcher service."""
import asyncio
from src.core.feed_watcher import FeedWatcher, FeedConfiguration
from config.settings import FEED_POLL_INTERVAL, MAX_CONCURRENT_FEEDS
from src.database.models import init_db

def load_feed_urls():
    """Load feed URLs from feeds.txt"""
    try:
        with open("feeds.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error loading feeds: {e}")
        return []

async def run_feed_watcher():
    """Initialize and run the feed watcher service"""
    config = FeedConfiguration(
        max_concurrent_feeds=MAX_CONCURRENT_FEEDS,
        min_poll_interval=FEED_POLL_INTERVAL[0],
        max_poll_interval=FEED_POLL_INTERVAL[1]
    )
    
    feed_watcher = FeedWatcher(config)
    await feed_watcher.init()
    
    try:
        feed_urls = load_feed_urls()
        tasks = [feed_watcher.watch_feed(url) for url in feed_urls]
        await asyncio.gather(*tasks)
    finally:
        await feed_watcher.close()

if __name__ == "__main__":
    # Initialize database
    init_db()
    
    try:
        asyncio.run(run_feed_watcher())
    except KeyboardInterrupt:
        print("\n🛑 Feed watcher service stopped")
    except Exception as e:
        print(f"Fatal error: {e}")
        exit(1)