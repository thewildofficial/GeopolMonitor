"""Article scraping utilities for news content extraction."""
import asyncio
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin
import aiohttp
from bs4 import BeautifulSoup
from newspaper import Article, Config
from fake_useragent import UserAgent

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
            
            return {
                'title': article.title,
                'text': article.text,
                'authors': article.authors,
                'publish_date': article.publish_date,
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
                    'publish_date': None,
                    'top_image': images[0] if images else None,
                    'images': images,
                    'meta_description': None
                }
                
        except Exception as e:
            logger.warning(f"BeautifulSoup extraction failed for {url}: {str(e)}")
            return None
    
    def _clean_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize extracted content."""
        if not content:
            return content
        
        # Clean text content
        if content.get('text'):
            # Remove extra whitespace
            content['text'] = ' '.join(content['text'].split())
            
            # Remove very short paragraphs (likely noise)
            paragraphs = [p.strip() for p in content['text'].split('\n') if len(p.strip()) > 50]
            content['text'] = '\n'.join(paragraphs)
        
        # Clean title
        if content.get('title'):
            content['title'] = ' '.join(content['title'].split())
        
        # Clean image URLs
        if content.get('images'):
            content['images'] = [
                url for url in content['images']
                if url and any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
            ]
        
        return content
    
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
