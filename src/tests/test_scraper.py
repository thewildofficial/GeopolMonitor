import unittest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import aiohttp
import io
from src.utils.scraper import ArticleScraper
from src.utils.date_utils import ensure_utc

class TestArticleScraper(unittest.TestCase):
    """Test suite for ArticleScraper class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scraper = ArticleScraper()

    def tearDown(self):
        """Clean up after tests."""
        # Run the close method to clean up any resources
        if self.scraper.session and not self.scraper.session.closed:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.scraper.close())
    
    def test_normalize_date(self):
        """Test the _normalize_date method."""
        # Test with a datetime object
        dt = datetime(2023, 5, 1, 12, 0, 0)
        normalized = self.scraper._normalize_date(dt)
        self.assertEqual(normalized.tzinfo, timezone.utc)
        
        # Test with ISO format string
        iso = "2023-05-01T12:00:00Z"
        normalized = self.scraper._normalize_date(iso)
        self.assertEqual(normalized.tzinfo, timezone.utc)
        self.assertEqual(normalized.year, 2023)
        self.assertEqual(normalized.month, 5)
        self.assertEqual(normalized.day, 1)
        self.assertEqual(normalized.hour, 12)
        
        # Test with different timezone
        tz_string = "2023-05-01T12:00:00+02:00"
        normalized = self.scraper._normalize_date(tz_string)
        self.assertEqual(normalized.tzinfo, timezone.utc)
        self.assertEqual(normalized.hour, 10)  # 12 CEST = 10 UTC
        
        # Test with human-readable format
        human = "May 1, 2023 12:00 PM"
        normalized = self.scraper._normalize_date(human)
        self.assertEqual(normalized.tzinfo, timezone.utc)
        self.assertEqual(normalized.year, 2023)
        self.assertEqual(normalized.month, 5)
        self.assertEqual(normalized.day, 1)
        
        # Test future date rejection
        future = datetime.now(timezone.utc) + timedelta(days=10)
        normalized = self.scraper._normalize_date(future)
        self.assertIsNone(normalized)
        
        # Test very old date rejection
        old = datetime.now(timezone.utc) - timedelta(days=365 * 50)  # 50 years ago
        normalized = self.scraper._normalize_date(old)
        self.assertIsNone(normalized)
        
        # Test invalid input
        self.assertIsNone(self.scraper._normalize_date("not a date"))
        self.assertIsNone(self.scraper._normalize_date(""))
        self.assertIsNone(self.scraper._normalize_date(None))
    
    @patch('newspaper.Article')
    @patch('asyncio.to_thread')
    async def test_fetch_with_newspaper(self, mock_to_thread, mock_article_class):
        """Test _fetch_with_newspaper method handles dates correctly."""
        # Mock newspaper Article and its methods
        mock_article = MagicMock()
        mock_article_class.return_value = mock_article
        
        # Mock article attributes
        mock_article.title = "Test Article"
        mock_article.text = "Test content"
        mock_article.authors = ["Test Author"]
        mock_article.publish_date = datetime(2023, 5, 1, 12, 0, 0)  # Naive datetime
        mock_article.top_image = "https://example.com/image.jpg"
        mock_article.meta_description = "Test description"
        mock_article.images = ["https://example.com/image.jpg", "https://example.com/image2.jpg"]
        
        # Setup mock for asyncio.to_thread
        mock_to_thread.side_effect = lambda func, *args: asyncio.sleep(0)
        
        # Test with naive datetime
        result = await self.scraper._fetch_with_newspaper("https://example.com/article")
        
        # Check if date was converted to UTC
        self.assertIsNotNone(result.get('publish_date'))
        self.assertEqual(result['publish_date'].tzinfo, timezone.utc)
        self.assertEqual(result['publish_date'].year, 2023)
        self.assertEqual(result['publish_date'].month, 5)
        self.assertEqual(result['publish_date'].day, 1)
        self.assertEqual(result['publish_date'].hour, 12)
        
        # Test with timezone-aware datetime
        est = timezone(timedelta(hours=-5))
        mock_article.publish_date = datetime(2023, 5, 1, 12, 0, 0, tzinfo=est)
        
        result = await self.scraper._fetch_with_newspaper("https://example.com/article")
        
        # Check if date was converted to UTC
        self.assertIsNotNone(result.get('publish_date'))
        self.assertEqual(result['publish_date'].tzinfo, timezone.utc)
        self.assertEqual(result['publish_date'].hour, 17)  # 12 EST = 17 UTC
    
    def test_clean_content(self):
        """Test _clean_content method handles dates correctly."""
        # Test with publish_date present
        content = {
            'title': "Test Article",
            'text': "Test content",
            'publish_date': datetime(2023, 5, 1, 12, 0, 0)  # Naive datetime
        }
        
        cleaned = self.scraper._clean_content(content)
        self.assertIsNotNone(cleaned.get('publish_date'))
        self.assertEqual(cleaned['publish_date'].tzinfo, timezone.utc)
        
        # Test with timezone-aware datetime
        est = timezone(timedelta(hours=-5))
        content['publish_date'] = datetime(2023, 5, 1, 12, 0, 0, tzinfo=est)
        
        cleaned = self.scraper._clean_content(content)
        self.assertIsNotNone(cleaned.get('publish_date'))
        self.assertEqual(cleaned['publish_date'].tzinfo, timezone.utc)
        self.assertEqual(cleaned['publish_date'].hour, 17)  # 12 EST = 17 UTC
        
        # Test with None
        content['publish_date'] = None
        cleaned = self.scraper._clean_content(content)
        self.assertIsNone(cleaned.get('publish_date'))

if __name__ == "__main__":
    unittest.main()