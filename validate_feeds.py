"""Validate RSS feed URLs."""
import asyncio
import aiohttp
import feedparser
from typing import List, Dict, Tuple, Optional
import logging
from pathlib import Path
from dotenv import load_dotenv
import argparse
import brotli
import random

load_dotenv()  # Load environment variables from .env file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def discover_rss_feed(session: aiohttp.ClientSession, base_url: str, verbose: bool = False) -> Optional[str]:
    """Try to discover RSS feed URL from a website URL using advanced anti-detection techniques."""
    # Common RSS feed paths to check, ordered by likelihood
    common_paths = [
        '/feed',
        '/rss',
        '/feed/',
        '/rss/',
        '/atom.xml',
        '/rss.xml',
        '/feed.xml',
        '/index.xml',
        '/feeds',
        '/blog/feed',
        '/blog/rss',
        '/rss/all.xml',
        '/feed/rss',
        '/feed.rss',
        '/rss/feed',
        '/news/feed',
        '/feed/atom',
        '/news/rss',
        '/rss/news',
        '/rss/index',
        '/feed/news',
        '/news.rss',
        '/news.xml',
        '/rss.aspx',
        '/syndication',
        '/syndication/feed',
        '/syndication/rss'
    ]
    
    # Remove trailing slash from base URL
    base_url = base_url.rstrip('/')
    
    # Enhanced browser fingerprinting
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1'
    ]
    
    # Advanced browser fingerprinting and anti-detection headers
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': f"{random.choice(['en-US', 'en-GB', 'en-CA'])},en;q=0.9",
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': random.choice(['none', 'same-origin']),
        'Sec-Fetch-User': '?1',
        'DNT': random.choice(['0', '1']),
        'Sec-Ch-Ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': f'"{random.choice(["Windows", "macOS", "Linux"])}"',
        'Referer': random.choice([
            'https://www.google.com/',
            'https://www.bing.com/',
            'https://duckduckgo.com/',
            'https://news.google.com/'
        ])
    }
    
    # Add random delay between requests to appear more human-like
    for path in common_paths:
        try:
            # Random delay between 1-3 seconds
            await asyncio.sleep(random.uniform(1, 3))
            
            feed_url = f"{base_url}{path}"
            if verbose:
                logger.debug(f"Checking potential RSS feed path: {feed_url}")
            
            # Randomize timeout between 5-10 seconds
            timeout = aiohttp.ClientTimeout(total=random.uniform(5, 10))
            async with session.get(feed_url, timeout=timeout, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    # Sanitize XML content before parsing
                    content = sanitize_xml_content(content)
                    feed = feedparser.parse(content)
                    
                    if not feed.bozo and hasattr(feed, 'entries') and feed.entries:
                        return feed_url
                elif response.status == 403:
                    logger.debug(f"Access forbidden for {feed_url} - Site may be blocking automated requests")
                    continue
        except Exception as e:
            if verbose:
                logger.debug(f"Error checking {feed_url}: {str(e)}")
            continue
    
    # Try to find feed URL in HTML content
    try:
        async with session.get(base_url, timeout=5, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                # Look for common feed link patterns
                import re
                feed_patterns = [
                    r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+href=["\']([^"\'>]+)',
                    r'<link[^>]+href=["\']([^"\'>]+)["\'][^>]+type=["\']application/(?:rss|atom)\+xml',
                    r'<a[^>]+href=["\']([^"\'>]+\.xml)["\']',
                    r'<a[^>]+href=["\']([^"\'>]+/feed/?)["\']',
                    r'<a[^>]+href=["\']([^"\'>]+/rss/?)["\']'
                ]
                
                for pattern in feed_patterns:
                    matches = re.findall(pattern, content, re.I)
                    for match in matches:
                        feed_url = match if match.startswith('http') else (
                            match if match.startswith('/') else f"/{match}"
                        )
                        feed_url = feed_url if feed_url.startswith('http') else f"{base_url}{feed_url}"
                        
                        try:
                            async with session.get(feed_url, timeout=5, headers=headers) as feed_response:
                                if feed_response.status == 200:
                                    feed_content = await feed_response.text()
                                    feed_content = sanitize_xml_content(feed_content)
                                    feed = feedparser.parse(feed_content)
                                    if not feed.bozo and hasattr(feed, 'entries') and feed.entries:
                                        return feed_url
                        except Exception:
                            continue
    except Exception as e:
        if verbose:
            logger.debug(f"Error searching for feed in HTML: {str(e)}")
    
    return None

def sanitize_xml_content(content: str) -> str:
    """Sanitize XML content by removing invalid characters and fixing common issues."""
    # Remove any null bytes
    content = content.replace('\x00', '')
    
    # Remove invalid XML characters
    import re
    # XML 1.0 valid chars: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    illegal_xml_chars = '[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]'
    content = re.sub(illegal_xml_chars, '', content)
    
    # Fix common XML issues
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)  # Remove control chars
    content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)', '&amp;', content)  # Fix unescaped &
    
    # Fix CDATA sections
    content = re.sub(r'<!\[CDATA\[(.*?)(?:]]>|$)', lambda m: f'<![CDATA[{m.group(1)}]]>', content, flags=re.DOTALL)  # Close unclosed CDATA
    content = re.sub(r']]>(?!\s*<)', ']]>\n', content)  # Add newline after CDATA if needed
    content = re.sub(r']]>\s*]]>', ']]>', content)  # Fix double CDATA closings
    
    # Fix other common XML issues
    content = re.sub(r'[\uFFFE\uFFFF]', '', content)  # Remove Unicode BOM
    content = re.sub(r'[\u0000-\u0008\u000B\u000C\u000E-\u001F]', '', content)  # Remove control characters
    content = re.sub(r'[\uD800-\uDFFF]', '', content)  # Remove surrogate pairs
    content = re.sub(r'<([^>]*)>[\s\r\n]*<\1>', lambda m: f'<{m.group(1)}>', content)  # Fix empty tags
    content = re.sub(r'\s+xmlns="[^"]*"', '', content)  # Remove duplicate xmlns declarations
    
    # Handle encoding issues
    try:
        # Try to decode as UTF-8 and re-encode to catch any encoding issues
        content = content.encode('utf-8', errors='ignore').decode('utf-8')
    except UnicodeError:
        # If that fails, try a more aggressive approach
        content = content.encode('ascii', errors='ignore').decode('ascii')
    
    return content

async def check_feed(session: aiohttp.ClientSession, url: str, verbose: bool = False) -> Tuple[str, bool, str]:
    """Check if a feed URL is valid and accessible with enhanced error reporting."""
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            if verbose:
                logger.debug(f"Checking feed URL: {url} (Attempt {attempt + 1}/{max_retries})")
            
            # Enhanced browser headers with rotating User-Agents
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            try:
                async with session.get(url, timeout=10, headers=headers, allow_redirects=True) as response:
                    if response.status == 403:
                        error_msg = "Access Forbidden (HTTP 403) - Site may be blocking automated requests"
                        logger.error(f"Error checking {url}: {error_msg}")
                        return url, False, error_msg
                    elif response.status != 200:
                        error_msg = f"HTTP {response.status} - {response.reason}"
                        logger.error(f"Error checking {url}: {error_msg}")
                        # If URL is not a valid feed, try to discover RSS feed
                        if not any(ext in url.lower() for ext in ['/feed', '/rss', '.xml', '/atom']):
                            discovered_feed = await discover_rss_feed(session, url)
                            if discovered_feed:
                                return discovered_feed, True, f"Discovered RSS feed: {discovered_feed}"
                        return url, False, error_msg
                    
                    content = await response.text()
                    # Sanitize XML content before parsing
                    content = sanitize_xml_content(content)
                    feed = feedparser.parse(content)
                    
                    if feed.bozo:  # feedparser sets this flag for invalid feeds
                        if verbose:
                            logger.debug(f"Feed parsing error for {url}: {feed.bozo_exception}")
                            if hasattr(feed, 'debug_message'):
                                logger.debug(f"Debug info: {feed.debug_message}")
                        # Provide more detailed error message
                        error_msg = str(feed.bozo_exception)
                        if hasattr(feed, 'debug_message'):
                            error_msg = f"{error_msg} - {feed.debug_message}"
                        
                        # If URL is not a valid feed, try to discover RSS feed
                        if not any(ext in url.lower() for ext in ['/feed', '/rss', '.xml', '/atom']):
                            discovered_feed = await discover_rss_feed(session, url)
                            if discovered_feed:
                                return discovered_feed, True, f"Discovered RSS feed: {discovered_feed}"
                        return url, False, error_msg
                    
                    if not hasattr(feed, 'entries') or not feed.entries:
                        if verbose:
                            logger.debug(f"No entries found in feed: {url}")
                        # If URL is not a valid feed, try to discover RSS feed
                        if not any(ext in url.lower() for ext in ['/feed', '/rss', '.xml', '/atom']):
                            discovered_feed = await discover_rss_feed(session, url)
                            if discovered_feed:
                                return discovered_feed, True, f"Discovered RSS feed: {discovered_feed}"
                        return url, False, "No entries found"
                        
                    return url, True, f"OK - {len(feed.entries)} entries"
            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Network error on attempt {attempt + 1}/{max_retries} for {url}: {str(e)}. Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                return url, False, f"Connection error: {str(e)}"
            except Exception as e:
                # If URL is not a valid feed, try to discover RSS feed
                if not any(ext in url.lower() for ext in ['/feed', '/rss', '.xml', '/atom']):
                    try:
                        discovered_feed = await discover_rss_feed(session, url)
                        if discovered_feed:
                            return discovered_feed, True, f"Discovered RSS feed: {discovered_feed}"
                    except Exception:
                        pass
                error_msg = str(e)
                if isinstance(e, aiohttp.ClientError):
                    error_msg = f"Network error: {error_msg}"
                elif isinstance(e, asyncio.TimeoutError):
                    error_msg = "Connection timed out"
                elif isinstance(e, feedparser.FeedParserError):
                    error_msg = f"Feed parsing error: {error_msg}"
                return url, False, error_msg
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Error on attempt {attempt + 1}/{max_retries} for {url}: {str(e)}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            return url, False, f"Error: {str(e)}"
    
    return url, False, "Max retries exceeded"

async def validate_feeds(feed_urls: List[str], verbose: bool = False) -> Dict[str, Dict[str, str]]:
    """Validate multiple feed URLs concurrently."""
    # WARNING: SSL verification is disabled for testing. In production, proper SSL certificate handling should be implemented
    connector = aiohttp.TCPConnector(ssl=False)
    # Configure client session with decompression support
    async with aiohttp.ClientSession(
        connector=connector,
        headers={
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    ) as session:
        tasks = [check_feed(session, url, verbose) for url in feed_urls]
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Validate RSS feed URLs")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    feed_urls = load_feeds()
    logger.info(f"Checking {len(feed_urls)} feeds...")
    
    results = await validate_feeds(feed_urls, args.verbose)
    
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