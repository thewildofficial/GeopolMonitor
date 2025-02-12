"""Tests for feed watching functionality."""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from ..core.feed_watcher import FeedWatcher, FeedConfiguration
from ..core.processor import process_article
import aiohttp

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

