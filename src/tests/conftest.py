"""Test configuration and shared fixtures."""
import pytest
import os
import tempfile
import sqlite3
from ..database.models import init_db

@pytest.fixture(scope="session")
def test_db():
    """Create a temporary test database."""
    db_fd, db_path = tempfile.mkstemp()
    os.environ["DB_PATH"] = db_path
    
    # Initialize the test database
    init_db()
    
    yield db_path
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture(scope="session")
def test_feeds_file():
    """Create a temporary feeds file."""
    feeds_fd, feeds_path = tempfile.mkstemp()
    with os.fdopen(feeds_fd, 'w') as f:
        f.write("https://example.com/feed1\n")
        f.write("https://example.com/feed2\n")
    
    yield feeds_path
    
    # Cleanup
    os.unlink(feeds_path)

@pytest.fixture(autouse=True)
def setup_test_env(test_db):
    """Setup test environment variables."""
    os.environ["TELEGRAM_TOKEN"] = "test_token"
    os.environ["TELEGRAM_CHANNEL_ID"] = "test_channel"
    os.environ["TESTING"] = "1"
    
    yield
    
    # Reset environment
    del os.environ["TELEGRAM_TOKEN"]
    del os.environ["TELEGRAM_CHANNEL_ID"]
    del os.environ["TESTING"]