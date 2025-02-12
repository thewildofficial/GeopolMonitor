"""Main entry point for the GeopolMonitor bot."""
import asyncio
import argparse
from src.core.feed_watcher import FeedWatcher

async def main(feed_file: str):
    """Main function to start feed watching"""
    watcher = None
    try:
        with open(feed_file) as f:
            feeds = f.read().splitlines()
            
        watcher = FeedWatcher()
        await watcher.init()
        
        tasks = []
        for feed_url in feeds:
            tasks.append(asyncio.create_task(watcher.watch_feed(feed_url)))
            
        print("▶ Starting real-time feed monitoring...")
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")
    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        if tasks:
            for task in tasks:
                task.cancel()
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                pass
        if watcher:
            await watcher.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--feeds", default="feeds.txt", help="Path to RSS feeds file")
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.feeds))
    except KeyboardInterrupt:
        print("\n🛑 Bot shutdown complete")
    except Exception as e:
        print(f"Fatal error: {e}")
        exit(1)