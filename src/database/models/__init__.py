"""
Deprecated legacy SQLite helpers.
Kept as thin shims to avoid import errors. Prefer async Postgres via
`src/database/news_db.py` and `src/database/telegram_db.py`.
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

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional, List, Dict
import logging

# Get project root directory and set database path
_connection = None
_last_backup = datetime.now()
logger = logging.getLogger(__name__)

def init_db(connection=None):
    """No-op legacy initializer (use Postgres migrations instead)."""
    logger.info("init_db() legacy call ignored; use Alembic migrations on Postgres")

def exists_in_db(link: str) -> bool:
    """Check if an entry with this link already exists in the database."""
    with get_db() as conn:
        cursor = conn.execute('SELECT COUNT(*) FROM news_entries WHERE link = ?', (link,))
        count = cursor.fetchone()[0]
        return count > 0

@contextmanager
def get_db():
    """Legacy no-op context manager to avoid import breakage."""
    yield None

def cleanup_db():
    """Cleanup function to be called on program exit."""
    global _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
        _connection = None

try:
    import atexit
    atexit.register(cleanup_db)
except Exception:
    pass

def load_feed_cache():
    """Load feed cache from database."""
    # Legacy path not supported; return defaults
    try:
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
    except Exception:
        return {}

def update_feed_cache(url: str, data: dict):
    """Update feed cache with new metrics."""
    try:
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
    except Exception:
        return

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