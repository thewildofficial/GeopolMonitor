"""Core news processing functionality."""
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List, NamedTuple
import re
import html
import urllib.parse
import feedparser
from bs4 import BeautifulSoup

from ..database.models import get_db, add_tag, tag_article
from ..utils.text import clean_text, clean_url
from ..utils.ai import ContentProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProcessedContent(NamedTuple):
    """Represents processed article content."""
    message: str
    title: str
    description: str
    link: str
    images: List[str]
    combined: str
    emoji1: str
    emoji2: str
    image_url: Optional[str]
    content: str
    topic_tags: List[str]
    geography_tags: List[str]
    event_tags: List[str]
    sentiment_score: float
    bias_category: str
    bias_score: float

"""Image extraction and processing utilities."""
import re
from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin, urlparse

class ImageExtractor:
    """Extract images from article content."""
    
    def __init__(self):
        # Common content image patterns
        self.image_patterns = [
            r'https?://\S+?(?:jpg|jpeg|png|gif)',
            r'data:image/\S+?;base64,\S+'
        ]
    
    def extract_images(self, article) -> List[str]:
        """Extract image URLs from an article entry."""
        images = []
        
        # Try to get image from media content
        if hasattr(article, 'media_content'):
            for media in article.media_content:
                if 'url' in media and self._is_valid_image_url(media['url']):
                    images.append(media['url'])
        
        # Try enclosures
        if hasattr(article, 'enclosures'):
            for enclosure in article.enclosures:
                if hasattr(enclosure, 'href') and self._is_valid_image_url(enclosure.href):
                    images.append(enclosure.href)
        
        # Try to find image in content
        if not images:
            content_images = self.extract_first_image_from_content(getattr(article, 'content', ''))
            if content_images:
                images.append(content_images)
        
        return images

    def extract_first_image_from_content(self, content: Optional[str]) -> Optional[str]:
        """Extract the first valid image URL from HTML content."""
        if not content:
            return None
            
        # First try to parse as HTML
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for img tags
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and self._is_valid_image_url(src):
                    return src
            
            # If no img tags found, try regex patterns
            for pattern in self.image_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    return matches[0]
        except Exception as e:
            logger.warning(f"Error extracting image from content: {e}")
            
        return None

    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid image URL."""
        if not url:
            return False
            
        # Check if URL is absolute
        parsed = urlparse(url)
        if not parsed.scheme:
            return False
            
        # Check file extension
        path = parsed.path.lower()
        return any(path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])

class ArticleProcessor:
    """Processes articles from feed entries."""
    
    def __init__(self):
        self.image_extractor = ImageExtractor()
        self.content_processor = ContentProcessor()
    
    async def process_article(self, entry: Any) -> Optional[ProcessedContent]:
        """Process an article by extracting and formatting information."""
        try:
            # Extract images with improved method
            images = self.image_extractor.extract_images(entry)
            
            # Get article link
            link = clean_url(getattr(entry, 'link', ''))
            if not link:
                logger.error("No valid link found in entry")
                return None
            
            # Initial cleaning
            title_cleaned = self._clean_html(getattr(entry, 'title', 'Untitled'))
            description_cleaned = self._clean_html(getattr(entry, 'description', ''))
            
            # Combine title and description for single API call
            combined_text = f"Title: {title_cleaned}\n\nContent: {description_cleaned}"
            
            # Process combined content with AI and get tags
            emojis, processed_text, topics, geography, events = await self.content_processor.process_content_with_tags(
                combined_text,
                url=link,
                is_title=False,
                instruction="Process title and content: Extract a clear title from the 'Title:' section and summarize the content in three paragraphs."
            )

            # Split processed text into title and description
            processed_parts = processed_text.split('\n\n', 1)
            title_processed = processed_parts[0] if len(processed_parts) > 0 else title_cleaned
            description_processed = processed_parts[1] if len(processed_parts) > 1 else description_cleaned

            # Get sentiment and bias analysis
            sentiment_score, bias_category, bias_score = await self.content_processor.analyze_sentiment_and_bias(description_processed)

            # Process emojis and content
            content = getattr(entry, 'description', '')
            emoji1, emoji2 = self._split_emojis(emojis)
            if not emoji1 or len(emoji1) > 4:
                emoji1 = self._detect_location(title_cleaned) or '🌎'
            if not emoji2 or len(emoji2) > 4:
                emoji2 = self._detect_topic(title_cleaned) or '📰'

            # Format for output
            message = f"{emoji1}{emoji2}: {title_processed}"
            combined = (
                f"{emoji1}{emoji2}: **{title_processed}**\n\n"
                f"{description_processed}\n\n"
                f"[Read More]({link})"
            )

            return ProcessedContent(
                message=message,
                title=title_processed,
                description=description_processed,
                link=link,
                images=images,
                combined=combined,
                emoji1=emoji1,
                emoji2=emoji2,
                image_url=images[0] if images else None,
                content=content,
                topic_tags=topics,
                geography_tags=geography,
                event_tags=events,
                sentiment_score=sentiment_score,
                bias_category=bias_category,
                bias_score=bias_score
            )
            
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return None

    def _clean_html(self, text: str) -> str:
        """Deep clean HTML while preserving certain entities."""
        if not text:
            return ""

        # Special case for encoded script tags
        if text.startswith('&lt;script') and text.endswith('&lt;/script&gt;'):
            return html.unescape(text)

        # For other cases, first unescape all HTML entities
        text = html.unescape(text)
        
        # Then remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up whitespace and special characters
        text = re.sub(r'\\', ' ', text)  # Replace backslash with space
        text = re.sub(r'\n', ' ', text)  # Replace newlines with space
        text = re.sub(r'[\u200b\u200c\u200d]+', ' ', text)  # Replace zero-width chars
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def _escape_markdown(self, text: str) -> str:
        """Escape characters that have special meanings in Telegram MarkdownV2."""
        # First escape all special characters
        special_chars = '_*[]()~`>#+-=|{}.!'
        escaped_text = ''
        for char in text:
            if char in special_chars:
                escaped_text += '\\' + char
            else:
                escaped_text += char
        return escaped_text

    def _split_emojis(self, emojis: str) -> tuple:
        """Split emoji string into location and topic emoji."""
        return emojis[:2], emojis[2:] if len(emojis) > 2 else ""

    def _detect_location(self, text: str) -> Optional[str]:
        """Detect location mentions using enhanced pattern matching."""
        locations = {
            r'\b(us|usa|america|american|washington)\b': '🇺🇸',
            r'\b(uk|britain|british|london|england|english)\b': '🇬🇧',
            r'\b(china|chinese|beijing|shanghai)\b': '🇨🇳',
            r'\b(russia|russian|moscow|putin)\b': '🇷🇺',
            r'\b(eu|europe|european|brussels)\b': '🇪🇺',
            r'\b(australia|australian|sydney|melbourne)\b': '🇦🇺',
            r'\b(india|indian|delhi|mumbai|modi)\b': '🇮🇳',
            r'\b(japan|japanese|tokyo|osaka)\b': '🇯🇵',
            r'\b(france|french|paris|macron)\b': '🇫🇷',
            r'\b(germany|german|berlin|scholz)\b': '🇩🇪'
        }
        
        text_lower = text.lower()
        for pattern, flag in locations.items():
            if re.search(pattern, text_lower):
                return flag
        return None

    def _detect_topic(self, text: str) -> Optional[str]:
        """Detect main topic using enhanced pattern matching."""
        topics = {
            r'\b(bank|banking|profit|loan|finance|stock|market)\b': '🏦',
            r'\b(money|cash|currency|dollar|euro|pound)\b': '💵',
            r'\b(economy|economic|gdp|growth|trade)\b': '📊',
            r'\b(election|vote|ballot|poll|campaign)\b': '🗳️',
            r'\b(law|legal|court|justice|judge)\b': '⚖️',
            r'\b(military|war|army|navy|defense|weapon)\b': '⚔️',
            r'\b(tech|technology|digital|software|cyber)\b': '💻',
            r'\b(health|hospital|medical|doctor|covid)\b': '🏥',
            r'\b(climate|weather|storm|temperature)\b': '🌡️',
            r'\b(protest|demonstration|riot|strike)\b': '✊'
        }
        
        text_lower = text.lower()
        for pattern, emoji in topics.items():
            if re.search(pattern, text_lower):
                return emoji
        return None

# Create singleton instance
processor = ArticleProcessor()
process_article = processor.process_article