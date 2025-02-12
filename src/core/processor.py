"""Core news processing functionality."""
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List, NamedTuple
import re
import html
import urllib.parse
import feedparser

from ..database.models import get_db
from ..utils.text import clean_text, clean_url
from ..utils.ai import process_with_gemini

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

class ImageExtractor:
    """Handles extraction of images from feed entries."""
    
    @staticmethod
    def extract_images(entry: Any) -> List[str]:
        """Extract images from feed entry using multiple methods."""
        image_urls = []
        
        # Extract from description
        if hasattr(entry, 'description') and entry.description:
            image_urls.extend(
                re.findall(r'(https?://[^\s]+(?:jpg|jpeg|png|gif|bmp|svg|webp))', 
                          entry.description)
            )

        # Extract from media content
        if hasattr(entry, 'media_content'):
            image_urls.extend(
                [m['url'] for m in entry.media_content 
                 if 'url' in m and m['url'].lower().endswith(
                     ('.jpg', '.png', '.jpeg', '.gif', '.bmp', '.svg', '.webp'))]
            )

        # Extract from enclosures
        if hasattr(entry, 'enclosures'):
            image_urls.extend(
                [e['href'] for e in entry.enclosures 
                 if e.get('href', '').lower().endswith(
                     ('.jpg', '.png', '.jpeg', '.gif', '.bmp', '.svg', '.webp'))]
            )

        return list(set(image_urls))

    @staticmethod
    def extract_first_image_from_content(content: Optional[str]) -> Optional[str]:
        """Extract first valid image URL from content."""
        if not content:
            return None
            
        urls = re.findall(r'(https?://[^\s]+(?:jpg|jpeg|png|gif|bmp|svg|webp))', content)
        return urls[0] if urls else None

class ArticleProcessor:
    """Processes articles from feed entries."""
    
    def __init__(self):
        self.image_extractor = ImageExtractor()
    
    async def process_article(self, entry: Any) -> Optional[ProcessedContent]:
        """Process an article by extracting and formatting information."""
        try:
            # Extract images
            images = self.image_extractor.extract_images(entry)
            
            # Initial cleaning
            title_cleaned = self._clean_html(getattr(entry, 'title', 'Untitled'))
            description_cleaned = self._clean_html(getattr(entry, 'description', ''))
            link = clean_url(getattr(entry, 'link', ''))
            content = getattr(entry, 'description', '')
            
            # Process with AI and pattern matching
            emojis, title_processed = await process_with_gemini(title_cleaned, is_title=True)
            _, description_processed = await process_with_gemini(description_cleaned, is_title=False)

            # Fallback checks and emoji splitting
            emoji1, emoji2 = self._split_emojis(emojis)
            if not emoji1 or len(emoji1) > 4:
                emoji1 = self._detect_location(title_cleaned) or '🌎'
            if not emoji2 or len(emoji2) > 4:
                emoji2 = self._detect_topic(title_cleaned) or '📰'
            
            # Format for output - raw text without escaping
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
                content=content
            )
            
        except Exception as e:
            logger.error(f"Error processing article: {e}\nTraceback:\n{traceback.format_exc()}")
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