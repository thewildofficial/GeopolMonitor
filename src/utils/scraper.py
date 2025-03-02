"""Article scraping utilities for news content extraction."""
import asyncio
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin
import aiohttp
from bs4 import BeautifulSoup
from newspaper import Article, Config
from fake_useragent import UserAgent
import dateparser
from datetime import datetime, timedelta, timezone
import json
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize user agent rotator
user_agent = UserAgent()

# Configure newspaper settings
config = Config()
config.browser_user_agent = user_agent.random
config.request_timeout = 15
config.fetch_images = True  # Enable image fetching
config.memoize_articles = False

class ArticleScraper:
    """Handles article scraping with fallback methods and content cleaning."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limits = {}
        self._last_requests = {}
        self.image_patterns = [
            r'https?://[^\s<>"]+?\.(?:jpg|jpeg|png|gif|webp)',
            r'data:image/[^;]+;base64,[a-zA-Z0-9+/]+'
        ]
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _respect_rate_limits(self, domain: str):
        """Implement rate limiting per domain."""
        if domain in self._last_requests:
            time_since_last = asyncio.get_event_loop().time() - self._last_requests[domain]
            if time_since_last < self._rate_limits.get(domain, 1.0):
                await asyncio.sleep(self._rate_limits.get(domain, 1.0) - time_since_last)
        self._last_requests[domain] = asyncio.get_event_loop().time()
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return domain.replace('www.', '')
        except:
            return ""
    
    def _normalize_date(self, date_value) -> Optional[datetime]:
        """Normalize a date value to UTC timezone."""
        try:
            from .date_utils import ensure_utc, safe_parse_date
            
            if isinstance(date_value, datetime):
                # For datetime objects, ensure UTC
                normalized = ensure_utc(date_value)
            elif isinstance(date_value, str):
                # For string dates, parse and ensure UTC
                normalized = safe_parse_date(date_value)
            else:
                return None
                
            if not normalized:
                return None
                
            now = datetime.now(timezone.utc)
            
            # Return None for future dates
            if normalized > now:
                return None
                
            # Return None for very old dates (50+ years)
            if normalized < now - timedelta(days=365 * 50):
                return None
                
            return normalized
            
        except Exception as e:
            logger.warning(f"Date normalization failed for {date_value}: {str(e)}")
            return None

    def _extract_date(self, soup, html: str, url: str) -> Optional[datetime]:
        """Extract publication date using multiple strategies."""
        extracted_date = None
        
        # Strategy 1: Check standard meta tags
        for meta_tag in ['article:published_time', 'og:published_time', 'publication_date', 
                         'publishdate', 'pubdate', 'date', 'created', 'publish-date']:
            meta = soup.find('meta', property=meta_tag) or soup.find('meta', attrs={'name': meta_tag})
            if meta and meta.get('content'):
                extracted_date = meta.get('content')
                logger.debug(f"Found date in meta tag {meta_tag}: {extracted_date}")
                normalized = self._normalize_date(extracted_date)
                if normalized:
                    return normalized
        
        # Strategy 2: Look for JSON-LD data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                date_fields = ['datePublished', 'dateCreated', 'dateModified', 'date']
                
                # Handle nested structures
                def extract_date_from_json(json_obj, fields):
                    if isinstance(json_obj, dict):
                        for field in fields:
                            if field in json_obj:
                                date_str = json_obj[field]
                                logger.debug(f"Found date in JSON-LD {field}: {date_str}")
                                normalized = self._normalize_date(date_str)
                                if normalized:
                                    return normalized
                        
                        # Look in nested structures
                        for value in json_obj.values():
                            if isinstance(value, (dict, list)):
                                result = extract_date_from_json(value, fields)
                                if result:
                                    return result
                    
                    elif isinstance(json_obj, list):
                        for item in json_obj:
                            result = extract_date_from_json(item, fields)
                            if result:
                                return result
                    
                    return None
                
                result = extract_date_from_json(data, date_fields)
                if result:
                    return result
                    
            except Exception as e:
                logger.debug(f"Error parsing JSON-LD: {str(e)}")
        
        # Strategy 3: Look for common date patterns in HTML elements with date-related classes or IDs
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})',  # ISO format
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)',          # ISO format with Z
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',         # Common format
            r'(\d{1,2}\s+[A-Za-z]{3,}\s+\d{4})',                # 25 January 2021
            r'([A-Za-z]{3,}\s+\d{1,2},?\s+\d{4})'               # January 25, 2021
        ]
        
        # Look in elements likely to contain dates
        date_containers = soup.find_all(['time', 'span', 'div', 'p'], 
                                      class_=lambda c: c and any(date_term in str(c).lower() 
                                                                for date_term in ['date', 'time', 'published', 'posted']))
        
        for container in date_containers:
            # Check for datetime attribute
            if container.name == 'time' and container.get('datetime'):
                extracted_date = container.get('datetime')
                logger.debug(f"Found date in time element datetime: {extracted_date}")
                normalized = self._normalize_date(extracted_date)
                if normalized:
                    return normalized
            
            # Check text content
            if container.string:
                for pattern in date_patterns:
                    match = re.search(pattern, container.string)
                    if match:
                        extracted_date = match.group(0)
                        logger.debug(f"Found date with pattern in element: {extracted_date}")
                        normalized = self._normalize_date(extracted_date)
                        if normalized:
                            return normalized
        
        # Strategy 4: Search the entire HTML for date patterns as last resort
        for pattern in date_patterns:
            matches = re.findall(pattern, html)
            if matches:
                for match in matches:
                    # Prioritize recent dates when multiple matches found
                    normalized = self._normalize_date(match)
                    if normalized:
                        logger.debug(f"Found date with pattern in HTML: {match}")
                        return normalized
        
        return None
    
    async def _fetch_with_newspaper(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch article using newspaper3k library."""
        try:
            article = Article(url, config=config)
            await asyncio.to_thread(article.download)
            await asyncio.to_thread(article.parse)
            
            # Get top image and any additional images
            images = []
            if article.top_image:
                images.append(article.top_image)
            
            # Add any additional images from the article object
            if hasattr(article, 'images'):
                images.extend([img for img in article.images if img not in images])
            
            # Get publish date and convert to UTC
            publish_date = None
            if article.publish_date:
                if article.publish_date.tzinfo is None:
                    # If timezone naive, assume it's UTC
                    publish_date = article.publish_date.replace(tzinfo=timezone.utc)
                    logger.debug(f"Added UTC timezone to naive newspaper date: {publish_date}")
                else:
                    # Convert existing timezone to UTC
                    publish_date = article.publish_date.astimezone(timezone.utc)
                    logger.debug(f"Converted newspaper date to UTC: {publish_date}")
            
            return {
                'title': article.title,
                'text': article.text,
                'authors': article.authors,
                'publish_date': publish_date,
                'top_image': article.top_image,
                'images': images,
                'meta_description': article.meta_description
            }
        except Exception as e:
            logger.warning(f"Newspaper3k extraction failed for {url}: {str(e)}")
            return None
    
    async def _fetch_with_beautifulsoup(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch article using BeautifulSoup as fallback."""
        try:
            session = await self._get_session()
            headers = {'User-Agent': user_agent.random}
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove unwanted elements
                for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'iframe']):
                    element.decompose()
                
                # Extract title
                title = None
                title_tag = soup.find('meta', property='og:title') or soup.find('title')
                if title_tag:
                    title = title_tag.get('content', None) or title_tag.string
                
                # Extract images
                images = []
                # Try Open Graph image first
                og_image = soup.find('meta', property='og:image')
                if og_image:
                    image_url = og_image.get('content')
                    if image_url:
                        images.append(urljoin(url, image_url))
                
                # Look for article images
                article_tag = soup.find('article') or soup.find(class_=['article', 'post', 'content', 'main'])
                if article_tag:
                    img_tags = article_tag.find_all('img')
                else:
                    img_tags = soup.find_all('img')
                
                for img in img_tags:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        # Convert relative URLs to absolute
                        absolute_url = urljoin(url, src)
                        if any(absolute_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                            images.append(absolute_url)
                
                # Extract publication date - NEW CODE
                publish_date = self._extract_date(soup, html, url)
                
                # Extract main content
                content = ''
                article_tag = soup.find('article') or soup.find(class_=['article', 'post', 'content', 'main'])
                
                if article_tag:
                    paragraphs = article_tag.find_all('p')
                else:
                    paragraphs = soup.find_all('p')
                
                content = ' '.join(p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 100)
                
                if not content:
                    return None
                
                return {
                    'title': title,
                    'text': content,
                    'authors': None,
                    'publish_date': publish_date,  # Add the extracted date
                    'top_image': images[0] if images else None,
                    'images': images,
                    'meta_description': None
                }
                
        except Exception as e:
            logger.warning(f"BeautifulSoup extraction failed for {url}: {str(e)}")
            return None
    
    def _clean_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize the article content."""
        if not content:
            return {}
            
        # Normalize dates
        if 'publish_date' in content:
            content['publish_date'] = self._normalize_date(content['publish_date'])
            
        # Remove None values
        return {k: v for k, v in content.items() if v is not None}
    
    async def scrape_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape article content with fallback methods."""
        # Validate URL before proceeding
        if not isinstance(url, str) or not url.startswith(('http://', 'https://')):            
            logger.error(f"Invalid URL provided: {url}. URL must be a string starting with http:// or https://")
            return None

        domain = self._extract_domain(url)
        await self._respect_rate_limits(domain)
        
        # Try newspaper3k first
        content = await self._fetch_with_newspaper(url)
        
        # Fallback to BeautifulSoup if newspaper fails
        if not content or not content.get('text'):
            content = await self._fetch_with_beautifulsoup(url)
        
        # Clean and return content
        return self._clean_content(content) if content else None
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

# Create singleton instance
article_scraper = ArticleScraper()

# Export main function
scrape_article = article_scraper.scrape_article
