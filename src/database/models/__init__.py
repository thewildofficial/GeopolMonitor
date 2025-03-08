"""
Database models initialization.
Core database functionality is defined here.
"""

# All exports from this module
__all__ = [
    'init_db',
    'exists_in_db',
    'get_db',
    'cleanup_db',
    'load_feed_cache',
    'update_feed_cache',
    'get_feed_metrics',
    'get_source_priority',
    'add_tag',
    'tag_article',
    'get_article_tags',
    'search_articles_by_tags',
    'store_article',
    'init_briefing_tables',
    'save_briefing',
    'get_current_briefing',
    'get_briefing_by_date',
    'get_briefing_by_id',
    'get_flash_items',
    'update_briefing_metrics',
    'get_regional_summary',
    'get_news_in_timespan'
]

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Optional, List, Dict
import atexit
import logging

# Get project root directory and set database path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'news_monitor.db')

_connection = None
_last_backup = datetime.now()
logger = logging.getLogger(__name__)

def init_db(connection=None):
    """Initialize SQLite database with required tables."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    if connection:
        conn = connection
    else:
        conn = sqlite3.connect(DB_PATH)

    # Create tables
    conn.execute('''
        CREATE TABLE IF NOT EXISTS feed_cache (
            url TEXT PRIMARY KEY,
            last_check TEXT,
            etag TEXT,
            last_modified TEXT,
            update_frequency INTEGER DEFAULT 3600,
            last_success_time TEXT,
            consecutive_failures INTEGER DEFAULT 0,
            source_priority INTEGER DEFAULT 100
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS news_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            link TEXT UNIQUE NOT NULL,
            guid TEXT NOT NULL,
            pub_date TEXT NOT NULL,
            processed_date TEXT NOT NULL,
            feed_url TEXT NOT NULL,
            emoji1 TEXT,
            emoji2 TEXT,
            image_url TEXT,
            sentiment_score REAL DEFAULT 0.0,
            bias_category TEXT DEFAULT 'neutral',
            bias_score REAL DEFAULT 0.0,
            description TEXT,
            message TEXT
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS article_tags (
            article_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (article_id, tag_id),
            FOREIGN KEY (article_id) REFERENCES news_entries(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id)
        )
    ''')

    # Create indices
    conn.execute('CREATE INDEX IF NOT EXISTS idx_link ON news_entries(link)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_feed_url ON news_entries(feed_url)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_pub_date ON news_entries(pub_date)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_guid ON news_entries(guid)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tag_name ON tags(name)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tag_category ON tags(category)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_article_tags ON article_tags(article_id)')

    conn.commit()
    
    if not connection:
        conn.close()

def exists_in_db(link: str) -> bool:
    """Check if an entry with this link already exists in the database."""
    with get_db() as conn:
        cursor = conn.execute('SELECT COUNT(*) FROM news_entries WHERE link = ?', (link,))
        count = cursor.fetchone()[0]
        return count > 0

@contextmanager
def get_db():
    """Context manager for database connections."""
    global _connection, _last_backup
    connection = None
    try:
        if _connection is None:
            _connection = sqlite3.connect(DB_PATH)
        connection = _connection
        yield connection
    except Exception as e:
        if connection:
            connection.rollback()
        raise e
    finally:
        if connection and connection != _connection:
            connection.close()

def cleanup_db():
    """Cleanup function to be called on program exit."""
    global _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
        _connection = None

atexit.register(cleanup_db)

def load_feed_cache():
    """Load feed cache from database."""
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT url, last_check, etag, last_modified, update_frequency 
            FROM feed_cache
        ''')
        cache = {}
        for row in cursor:
            try:
                cache[row[0]] = {
                    'last_check': datetime.fromisoformat(row[1]) if row[1] else None,
                    'etag': row[2],
                    'last_modified': row[3],
                    'update_frequency': row[4] or 3600
                }
            except (ValueError, TypeError):
                continue
        return cache

def update_feed_cache(url: str, data: dict):
    """Update feed cache with new metrics."""
    with get_db() as conn:
        conn.execute('''
            INSERT OR REPLACE INTO feed_cache 
            (url, last_check, etag, last_modified, update_frequency, 
             last_success_time, consecutive_failures, source_priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            url,
            data.get('last_check', '').isoformat() if data.get('last_check') else None,
            data.get('etag'),
            data.get('last_modified'),
            data.get('update_frequency', 3600),
            data.get('last_success_time', '').isoformat() if data.get('last_success_time') else None,
            data.get('consecutive_failures', 0),
            data.get('source_priority', 100)
        ))
        conn.commit()

def get_feed_metrics(url: str) -> dict:
    """Get feed metrics for adaptive polling."""
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT update_frequency, last_success_time, consecutive_failures
            FROM feed_cache WHERE url = ?
        ''', (url,))
        row = cursor.fetchone()
        if row:
            return {
                'update_frequency': row[0] or 3600,
                'last_success_time': row[1],
                'consecutive_failures': row[2] or 0
            }
        return {
            'update_frequency': 3600,
            'last_success_time': None,
            'consecutive_failures': 0
        }

def get_source_priority(feed_url: str) -> int:
    """Get current priority score for a feed source."""
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT COUNT(*) as entry_count 
            FROM news_entries 
            WHERE feed_url = ? 
            AND datetime(pub_date) > datetime('now', '-6 hours')
        ''', (feed_url,))
        count = cursor.fetchone()[0]
        
        priority = max(100 - (count * 10), 5)
        
        conn.execute('''
            UPDATE feed_cache 
            SET source_priority = ? 
            WHERE url = ?
        ''', (priority, feed_url))
        conn.commit()
        
        return priority

def add_tag(name: str, category: str) -> int:
    """Add a new tag or get existing tag ID."""
    with get_db() as conn:
        cursor = conn.execute(
            'INSERT OR IGNORE INTO tags (name, category) VALUES (?, ?)',
            (name.lower(), category)
        )
        if cursor.rowcount == 0:  # Tag already exists
            cursor = conn.execute('SELECT id FROM tags WHERE name = ?', (name.lower(),))
            return cursor.fetchone()[0]
        return cursor.lastrowid

def tag_article(article_id: int, tag_ids: list[int]):
    """Tag an article with multiple tags."""
    with get_db() as conn:
        try:
            conn.execute('DELETE FROM article_tags WHERE article_id = ?', (article_id,))
            conn.executemany(
                'INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)',
                [(article_id, tag_id) for tag_id in tag_ids]
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Error tagging article {article_id}: {str(e)}")
            conn.rollback()

def get_article_tags(article_id: int) -> list[dict]:
    """Get all tags for an article."""
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT t.name, t.category 
            FROM tags t 
            JOIN article_tags at ON t.id = at.tag_id 
            WHERE at.article_id = ?
        ''', (article_id,))
        return [{'name': row[0], 'category': row[1]} for row in cursor.fetchall()]

def search_articles_by_tags(tag_names: list[str], limit: int = 20, offset: int = 0) -> list[dict]:
    """Search articles by tags with pagination support."""
    with get_db() as conn:
        placeholders = ','.join('?' * len(tag_names))
        cursor = conn.execute(f'''
            SELECT DISTINCT ne.* 
            FROM news_entries ne
            JOIN article_tags at ON ne.id = at.article_id
            JOIN tags t ON at.tag_id = t.id
            WHERE t.name IN ({placeholders})
            ORDER BY ne.pub_date DESC
            LIMIT ? OFFSET ?
        ''', [*[name.lower() for name in tag_names], limit, offset])
        return [dict(zip([col[0] for col in cursor.description], row))
                for row in cursor.fetchall()]

async def store_article(
    title: str,
    content: str,
    link: str,
    guid: str,
    feed_url: str,
    pub_date: datetime,
    emoji1: str = "📰",
    emoji2: str = "🌐",
    image_url: Optional[str] = None,
    description: Optional[str] = None,
    message: Optional[str] = None,
    sentiment_score: float = 0.0,
    bias_category: str = "neutral",
    bias_score: float = 0.0
) -> int:
    """Store a processed article in the database."""
    if not pub_date.tzinfo:
        pub_date = pub_date.replace(tzinfo=timezone.utc)
    elif pub_date.tzinfo != timezone.utc:
        pub_date = pub_date.astimezone(timezone.utc)
    
    pub_date_str = pub_date.isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id FROM news_entries WHERE link = ?', (link,))
            existing = cursor.fetchone()
            if existing:
                return existing[0]
            
            current_time = datetime.now(timezone.utc).isoformat()
            cursor.execute('''
                INSERT INTO news_entries (
                    title, description, content, link, guid, feed_url, pub_date,
                    processed_date, emoji1, emoji2, image_url, message,
                    sentiment_score, bias_category, bias_score
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                title, description, content, link, guid, feed_url, pub_date_str,
                current_time, emoji1, emoji2, image_url, message,
                sentiment_score, bias_category, bias_score
            ))
            
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error storing article: {str(e)}")
            return -1

# Initialize database on module import
init_db()

# Import briefing models
from .briefing_models import (
    init_briefing_tables,
    save_briefing,
    get_current_briefing,
    get_briefing_by_date,
    get_briefing_by_id,
    get_flash_items,
    update_briefing_metrics,
    get_regional_summary,
    get_news_in_timespan
)