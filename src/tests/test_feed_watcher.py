"""Tests for feed watching functionality."""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from ..core.feed_watcher import FeedWatcher, FeedConfiguration
from ..core.processor import process_article
import aiohttp

import unittest
from unittest.mock import MagicMock, patch
from datetime import timezone
import time
from src.utils.date_utils import ensure_utc

class MockEntry:
    """Mock feed entry for testing."""
    def __init__(self, published=None, published_parsed=None, updated_parsed=None):
        self.published = published
        self.published_parsed = published_parsed
        self.updated_parsed = updated_parsed

class TestFeedWatcher(unittest.TestCase):
    """Test suite for the FeedWatcher class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.watcher = FeedWatcher(FeedConfiguration())
        
    def test_parse_date_with_timezone(self):
        """Test that _parse_date_with_timezone correctly converts dates to UTC."""
        
        # Test with published_parsed (struct_time format)
        # Create a struct_time-like object for 2023-05-01 12:00:00 UTC
        struct_time = time.struct_time((2023, 5, 1, 12, 0, 0, 0, 0, 0))
        entry = MockEntry(published_parsed=struct_time)
        dt, is_aware = self.watcher._parse_date_with_timezone(entry)
        
        self.assertTrue(is_aware)
        self.assertEqual(dt.year, 2023)
        self.assertEqual(dt.month, 5)
        self.assertEqual(dt.day, 1)
        self.assertEqual(dt.hour, 12)
        self.assertEqual(dt.tzinfo, timezone.utc)
        
        # Test with published (RFC string format)
        # RFC 2822 format: Mon, 01 May 2023 12:00:00 +0000
        entry = MockEntry(published="Mon, 01 May 2023 12:00:00 +0000")
        dt, is_aware = self.watcher._parse_date_with_timezone(entry)
        
        self.assertTrue(is_aware)
        self.assertEqual(dt.year, 2023)
        self.assertEqual(dt.month, 5)
        self.assertEqual(dt.day, 1)
        self.assertEqual(dt.hour, 12)
        self.assertEqual(dt.tzinfo, timezone.utc)
        
        # Test with non-UTC timezone in published
        entry = MockEntry(published="Mon, 01 May 2023 12:00:00 +0200")  # CEST
        dt, is_aware = self.watcher._parse_date_with_timezone(entry)
        
        self.assertTrue(is_aware)
        self.assertEqual(dt.year, 2023)
        self.assertEqual(dt.month, 5)
        self.assertEqual(dt.day, 1)
        self.assertEqual(dt.hour, 10)  # 12 CEST = 10 UTC
        self.assertEqual(dt.tzinfo, timezone.utc)
        
        # Test with ISO format in published
        entry = MockEntry(published="2023-05-01T12:00:00+02:00")
        dt, is_aware = self.watcher._parse_date_with_timezone(entry)
        
        self.assertTrue(is_aware)
        self.assertEqual(dt.hour, 10)  # 12 CEST = 10 UTC
        self.assertEqual(dt.tzinfo, timezone.utc)
        
        # Test with updated_parsed as fallback
        entry = MockEntry(updated_parsed=struct_time)
        dt, is_aware = self.watcher._parse_date_with_timezone(entry)
        
        self.assertTrue(is_aware)
        self.assertEqual(dt.year, 2023)
        self.assertEqual(dt.month, 5)
        self.assertEqual(dt.day, 1)
        self.assertEqual(dt.tzinfo, timezone.utc)
        
        # Test with no date information
        entry = MockEntry()
        dt, is_aware = self.watcher._parse_date_with_timezone(entry)
        
        self.assertTrue(is_aware)  # Should still be aware even with fallback to current time
        self.assertEqual(dt.tzinfo, timezone.utc)
    
    @patch('src.core.feed_watcher.parsedate_to_datetime')
    @patch('src.utils.date_utils.safe_parse_date')
    def test_parse_date_with_timezone_handler_errors(self, mock_safe_parse, mock_parsedate):
        """Test how _parse_date_with_timezone handles errors."""
        
        # Test when parsedate_to_datetime raises an exception
        mock_parsedate.side_effect = ValueError("Bad date format")
        mock_safe_parse.return_value = datetime(2023, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        entry = MockEntry(published="Bad format date")
        dt, is_aware = self.watcher._parse_date_with_timezone(entry)
        
        self.assertTrue(is_aware)
        self.assertEqual(dt.tzinfo, timezone.utc)
        
        # Test when both date parsers fail
        mock_parsedate.side_effect = ValueError("Bad date format")
        mock_safe_parse.return_value = None
        
        dt, is_aware = self.watcher._parse_date_with_timezone(entry)
        
        self.assertTrue(is_aware)  # Should default to current time in UTC
        self.assertEqual(dt.tzinfo, timezone.utc)
        
    def test_process_feed_content_date_handling(self):
        """Test that process_feed_content handles dates correctly."""
        # This is an integration test that requires mocking the feedparser module
        # and our priority_processor. It tests the end-to-end flow of dates through
        # the feed processing pipeline.
        pass  # Implementation would be quite complex

if __name__ == "__main__":
    unittest.main()

@pytest_asyncio.fixture
async def feed_watcher():
    watcher = FeedWatcher()
    await watcher.init()
    yield watcher
    await watcher.close()

@pytest.mark.asyncio
async def test_feed_watcher_initialization(feed_watcher):
    assert feed_watcher.session is not None
    assert isinstance(feed_watcher.logged_entries, set)

@pytest.mark.asyncio
async def test_check_feed_headers():
    watcher = FeedWatcher()
    await watcher.init()
    
    # Test with a known RSS feed
    feed_url = "https://rss.example.com/feed"
    try:
        content = await watcher.check_feed_headers(feed_url)
        assert content is None or isinstance(content, str)
    except aiohttp.ClientError:
        pytest.skip("Network error - skipping feed header test")
    finally:
        await watcher.close()

@pytest.mark.asyncio
async def test_process_feed_content():
    watcher = FeedWatcher()
    await watcher.init()
    
    # Mock feed content
    content = """
    <?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Test News</title>
                <description>Test Description</description>
                <link>https://example.com/news/1</link>
                <pubDate>Thu, 01 Jan 2024 00:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>
    """
    
    try:
        await watcher.process_feed_content("https://example.com/feed", content)
        # Success if no exception is raised
        assert True
    finally:
        await watcher.close()

