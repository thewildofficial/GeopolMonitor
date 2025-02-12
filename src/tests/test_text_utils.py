"""Tests for text processing utilities."""
import pytest
from ..utils.text import TextCleaner, TextCleanerConfig, URLCleaner

def test_text_cleaner_basic():
    cleaner = TextCleaner()
    text = "Hello  World\n\n\nThis is a test."
    cleaned = cleaner.clean_text(text)
    assert cleaned == "This is a test."  # Short line removed, whitespace normalized

def test_text_cleaner_html():
    cleaner = TextCleaner()
    text = "<p>Hello &amp; World</p><br>This is <b>bold</b> text."
    cleaned = cleaner.clean_text(text)
    assert "Hello & World" in cleaned
    assert "bold text" in cleaned
    assert "<b>" not in cleaned

def test_text_cleaner_endmatter():
    cleaner = TextCleaner()
    text = "Important news.\nContinue reading here...\nRead more at our website."
    cleaned = cleaner.clean_text(text)
    assert "Important news" in cleaned
    assert "Continue reading" not in cleaned
    assert "Read more" not in cleaned

def test_text_cleaner_config():
    config = TextCleanerConfig(
        min_line_length=10,
        max_paragraph_length=100,
        max_paragraphs=2
    )
    cleaner = TextCleaner(config)
    text = "Short.\nThis is a longer line.\nAnother long line here.\nYet another long line."
    cleaned = cleaner.clean_text(text)
    assert "Short" not in cleaned
    assert len(cleaned.split('\n\n')) <= 2

def test_url_cleaner():
    url_cleaner = URLCleaner()
    
    # Test basic URL cleaning
    url = "  http://example.com/path?q=1#fragment  "
    cleaned = url_cleaner.clean_url(url)
    assert cleaned == "http://example.com/path?q=1"
    
    # Test adding https
    url = "example.com"
    cleaned = url_cleaner.clean_url(url)
    assert cleaned == "https://example.com"
    
    # Test auth removal
    url = "http://user:pass@example.com"
    cleaned = url_cleaner.clean_url(url)
    assert cleaned == "http://example.com"