"""Text processing utilities."""
import logging
import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse, urlunparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TextCleanerConfig:
    """Configuration for text cleaning."""
    remove_html: bool = True
    normalize_whitespace: bool = True
    min_length: int = 10
    max_length: int = 100000
    remove_urls: bool = True
    remove_emails: bool = True

class TextCleaner:
    """Handles text cleaning and normalization."""
    
    def __init__(self, config: Optional[TextCleanerConfig] = None):
        self.config = config or TextCleanerConfig()
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text or not isinstance(text, str):
            return ""
            
        # Remove HTML tags
        if self.config.remove_html:
            text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove URLs if configured
        if self.config.remove_urls:
            text = re.sub(r'http[s]?://\S+', '', text)
        
        # Remove email addresses if configured
        if self.config.remove_emails:
            text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        # Normalize whitespace
        if self.config.normalize_whitespace:
            # Replace newlines and tabs with spaces
            text = re.sub(r'[\n\t\r]+', ' ', text)
            # Remove multiple spaces
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
        
        # Enforce length limits
        if len(text) < self.config.min_length:
            return ""
        if len(text) > self.config.max_length:
            text = text[:self.config.max_length] + "..."
            
        return text

class URLCleaner:
    """Clean and normalize URLs."""
    
    def clean_url(self, url: str) -> str:
        """Clean and normalize a URL."""
        if not url or not isinstance(url, str):
            return ""
            
        try:
            # Parse URL
            parsed = urlparse(url)
            
            # Ensure scheme is present
            if not parsed.scheme:
                parsed = urlparse(f"https://{url}")
            
            # Remove fragments
            cleaned = parsed._replace(fragment="")
            
            # Remove default ports
            if cleaned.port in (80, 443):
                netloc = cleaned.netloc.replace(f":{cleaned.port}", "")
                cleaned = cleaned._replace(netloc=netloc)
            
            # Convert to string
            cleaned_url = urlunparse(cleaned)
            
            # Remove trailing slash if present
            if cleaned_url.endswith("/"):
                cleaned_url = cleaned_url[:-1]
                
            return cleaned_url
            
        except Exception as e:
            logger.error(f"Error cleaning URL {url}: {e}")
            return url

# Create singleton instances
text_cleaner = TextCleaner()
url_cleaner = URLCleaner()

# Export convenience functions
clean_text = text_cleaner.clean_text
clean_url = url_cleaner.clean_url