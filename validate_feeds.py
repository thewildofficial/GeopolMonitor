"""Validate RSS feed URLs."""
import asyncio
import aiohttp
import feedparser
from typing import List, Dict, Tuple
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_feed(session: aiohttp.ClientSession, url: str) -> Tuple[str, bool, str]:
    """Check if a feed URL is valid and accessible."""
    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                return url, False, f"HTTP {response.status}"
            
            content = await response.text()
            feed = feedparser.parse(content)
            
            if feed.bozo:  # feedparser sets this flag for invalid feeds
                return url, False, str(feed.bozo_exception)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                return url, False, "No entries found"
                
            return url, True, f"OK - {len(feed.entries)} entries"
    except Exception as e:
        return url, False, str(e)

async def validate_feeds(feed_urls: List[str]) -> Dict[str, Dict[str, str]]:
    """Validate multiple feed URLs concurrently."""
    async with aiohttp.ClientSession() as session:
        tasks = [check_feed(session, url) for url in feed_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        validated = {"valid": {}, "invalid": {}}
        for url, is_valid, message in results:
            if is_valid:
                validated["valid"][url] = message
            else:
                validated["invalid"][url] = message
        
        return validated

def load_feeds() -> List[str]:
    """Load feed URLs from feeds.txt."""
    feed_path = Path(__file__).parent / 'feeds.txt'
    with open(feed_path) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

async def main():
    feed_urls = load_feeds()
    logger.info(f"Checking {len(feed_urls)} feeds...")
    
    results = await validate_feeds(feed_urls)
    
    logger.info("\n=== Valid Feeds ===")
    for url, message in results["valid"].items():
        logger.info(f"✅ {url}: {message}")
    
    logger.info("\n=== Invalid Feeds ===")
    for url, message in results["invalid"].items():
        logger.info(f"❌ {url}: {message}")
    
    logger.info(f"\nSummary: {len(results['valid'])} valid, {len(results['invalid'])} invalid")
    
    # Don't overwrite feeds.txt automatically
    if results["invalid"]:
        logger.warning("\nInvalid feeds detected. Review them manually in feeds.txt")
        for url, error in results["invalid"].items():
            logger.warning(f"{url}: {error}")

    # prompt user if they want to remove invalid feeds
    # if yes, remove invalid feeds from feeds.txt
    # if no, exit the script
    
    feed_path = Path(__file__).parent / 'feeds.txt'
    choice = input("Do you want to remove invalid feeds from feeds.txt? (y/n): ")
    if choice.lower() == 'y':
        with open(feed_path, 'w') as f:
            for url in results["valid"]:
                f.write(f"{url}\n")
        logger.info("Removed invalid feeds from feeds.txt")
    else:
        logger.info("Exiting without modifying feeds.txt")

if __name__ == "__main__":
    asyncio.run(main())