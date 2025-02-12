"""Database models and initialization."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path

# Use absolute path for database
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = str(BASE_DIR / 'news_monitor.db')
_connection = None

def init_db(connection=None):
    """Initialize SQLite database with required tables."""
    conn = connection if connection else sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS feed_cache (
            url TEXT PRIMARY KEY,
            last_check TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS news_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            timestamp TIMESTAMP,
            feed_url TEXT,
            title TEXT,
            description TEXT,
            link TEXT,
            image_url TEXT,
            content TEXT,
            emoji1 TEXT,
            emoji2 TEXT,
            UNIQUE(title, link)
        )
    ''')
    conn.commit()
    if not connection:
        conn.close()

@contextmanager
def get_db():
    """Context manager for database connections."""
    global _connection
    
    if DB_PATH == ':memory:':
        if _connection is None:
            _connection = sqlite3.connect(DB_PATH)
            init_db(_connection)
        yield _connection
    else:
        conn = sqlite3.connect(DB_PATH)
        try:
            yield conn
        finally:
            conn.close()

def load_feed_cache():
    """Load feed cache from database."""
    with get_db() as conn:
        cursor = conn.execute('SELECT url, last_check FROM feed_cache')
        cache = {}
        for row in cursor:
            try:
                cache[row[0]] = datetime.fromisoformat(row[1])
            except (ValueError, TypeError):
                # Skip invalid timestamps
                continue
        return cache

def update_feed_cache(url, timestamp):
    """Update last check time for a feed."""
    with get_db() as conn:
        conn.execute('''
            INSERT OR REPLACE INTO feed_cache (url, last_check)
            VALUES (?, ?)
        ''', (url, timestamp.isoformat()))
        conn.commit()

# Initialize database on module import
init_db()