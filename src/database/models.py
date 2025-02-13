"""Database models and initialization."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path
from .backup import backup_database
import atexit
import logging

# Use absolute path for database
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = str(BASE_DIR / 'news_monitor.db')
_connection = None
_last_backup = datetime.now()

logger = logging.getLogger(__name__)

def init_db(connection=None):
    """Initialize SQLite database with required tables."""
    if connection:
        conn = connection
    else:
        conn = sqlite3.connect(DB_PATH)

    # Create tags table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create article-tag relationships table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS article_tags (
            article_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (article_id, tag_id),
            FOREIGN KEY (article_id) REFERENCES news_entries(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS news_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            pub_date TEXT,
            processed_date TEXT,
            feed_url TEXT,
            title TEXT,
            description TEXT,
            link TEXT UNIQUE,
            image_url TEXT,
            content TEXT,
            emoji1 TEXT,
            emoji2 TEXT,
            source_priority INTEGER DEFAULT 100
        )
    ''')
    
    conn.execute('CREATE INDEX IF NOT EXISTS idx_link ON news_entries(link)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_feed_url ON news_entries(feed_url)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_pub_date ON news_entries(pub_date)')
    
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

    # Create indices for tag tables
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tag_name ON tags(name)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tag_category ON tags(category)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_article_tags ON article_tags(article_id)')
    
    conn.commit()
    
    # Create initial backup
    backup_database(DB_PATH)
    
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
    if _connection is None:
        _connection = sqlite3.connect(DB_PATH)
    try:
        yield _connection
        
        # Create periodic backup every 6 hours
        now = datetime.now()
        if (now - _last_backup).total_seconds() > 21600:  # 6 hours
            backup_database(DB_PATH)
            _last_backup = now
            
    except Exception as e:
        _connection.rollback()
        raise e

def cleanup_db():
    """Cleanup function to be called on program exit."""
    global _connection
    if _connection is not None:
        try:
            backup_database(DB_PATH)  # Final backup
            _connection.close()
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
        _connection = None

# Register cleanup function to run on program exit
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
    """Get current priority score for a feed source.
    Lower numbers mean the source has been logged more recently/frequently."""
    with get_db() as conn:
        # Look at the last 24 hours of entries
        cursor = conn.execute('''
            SELECT COUNT(*) as entry_count 
            FROM news_entries 
            WHERE feed_url = ? 
            AND datetime(pub_date) > datetime('now', '-1 day')
        ''', (feed_url,))
        count = cursor.fetchone()[0]
        
        # Calculate priority - more entries means lower priority
        # Base priority of 100, subtract 5 for each recent entry, minimum 10
        priority = max(100 - (count * 5), 10)
        
        # Update the cache
        conn.execute('''
            UPDATE feed_cache 
            SET source_priority = ? 
            WHERE url = ?
        ''', (priority, feed_url))
        conn.commit()
        
        return priority

# Add new functions for tag operations
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
        conn.executemany(
            'INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)',
            [(article_id, tag_id) for tag_id in tag_ids]
        )
        conn.commit()

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

def search_articles_by_tags(tag_names: list[str]) -> list[dict]:
    """Search articles by tags."""
    with get_db() as conn:
        placeholders = ','.join('?' * len(tag_names))
        cursor = conn.execute(f'''
            SELECT DISTINCT ne.* 
            FROM news_entries ne
            JOIN article_tags at ON ne.id = at.article_id
            JOIN tags t ON at.tag_id = t.id
            WHERE t.name IN ({placeholders})
            ORDER BY ne.pub_date DESC
        ''', [name.lower() for name in tag_names])
        return [dict(zip([col[0] for col in cursor.description], row))
                for row in cursor.fetchall()]

# Initialize database on module import
init_db()