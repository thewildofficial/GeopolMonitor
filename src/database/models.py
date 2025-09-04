"""Database models and initialization."""
import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Optional, List, Dict
from .backup import backup_database
from .models.briefing_models import init_briefing_tables
import logging
import asyncio

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
    'store_article'
]

# Get project root directory and set database path
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'news_monitor.db')

_connection = None
_last_backup = datetime.now()

logger = logging.getLogger(__name__)

async def init_db(connection=None):
    """Initialize SQLite database with required tables."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    async with get_db() as conn:
        # Create tags table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create article-tag relationships table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS article_tags (
                article_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (article_id, tag_id),
                FOREIGN KEY (article_id) REFERENCES news_entries(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id)
            )
        ''')

        # Create news entries table with all required columns
        await conn.execute('''
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

        # Create indices for better performance
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_link ON news_entries(link)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_feed_url ON news_entries(feed_url)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_pub_date ON news_entries(pub_date)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_guid ON news_entries(guid)')

        # Create indices for tag tables
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_tag_name ON tags(name)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_tag_category ON tags(category)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_article_tags ON article_tags(article_id)')
        
        await conn.commit()
    
    # Create initial backup
    backup_database(DB_PATH)
    
    # Initialize briefing tables after main tables
    await init_briefing_tables()

async def exists_in_db(link: str) -> bool:
    """Check if an entry with this link already exists in the database."""
    async with get_db() as conn:
        cursor = await conn.execute('SELECT COUNT(*) FROM news_entries WHERE link = ?', (link,))
        row = await cursor.fetchone()
        return row[0] > 0

@asynccontextmanager
async def get_db():
    """Context manager for database connections."""
    global _connection, _last_backup
    connection = None
    try:
        if _connection is None:
            _connection = await aiosqlite.connect(DB_PATH)
            _connection.row_factory = aiosqlite.Row
        connection = _connection
        yield connection
        
        # Create periodic backup every 6 hours
        now = datetime.now()
        if (now - _last_backup).total_seconds() > 21600:  # 6 hours
            backup_database(DB_PATH)
            _last_backup = now
            
    except Exception as e:
        if connection:
            await connection.rollback()
        raise e
    finally:
        # The global connection is managed by the cleanup function
        pass

async def cleanup_db():
    """Cleanup function to be called on program exit."""
    global _connection
    if _connection is not None:
        try:
            backup_database(DB_PATH)  # Final backup
            await _connection.close()
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
        _connection = None

async def load_feed_cache():
    """Load feed cache from database."""
    async with get_db() as conn:
        cursor = await conn.execute('''
            SELECT url, last_check, etag, last_modified, update_frequency 
            FROM feed_cache
        ''')
        rows = await cursor.fetchall()
        cache = {}
        for row in rows:
            try:
                cache[row['url']] = {
                    'last_check': datetime.fromisoformat(row['last_check']) if row['last_check'] else None,
                    'etag': row['etag'],
                    'last_modified': row['last_modified'],
                    'update_frequency': row['update_frequency'] or 3600
                }
            except (ValueError, TypeError):
                continue
        return cache

async def update_feed_cache(url: str, data: dict):
    """Update feed cache with new metrics."""
    async with get_db() as conn:
        await conn.execute('''
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
        await conn.commit()

async def get_feed_metrics(url: str) -> dict:
    """Get feed metrics for adaptive polling."""
    async with get_db() as conn:
        cursor = await conn.execute('''
            SELECT update_frequency, last_success_time, consecutive_failures
            FROM feed_cache WHERE url = ?
        ''', (url,))
        row = await cursor.fetchone()
        if row:
            return {
                'update_frequency': row['update_frequency'] or 3600,
                'last_success_time': row['last_success_time'],
                'consecutive_failures': row['consecutive_failures'] or 0
            }
        return {
            'update_frequency': 3600,
            'last_success_time': None,
            'consecutive_failures': 0
        }

async def get_source_priority(feed_url: str) -> int:
    """Get current priority score for a feed source.
    Lower numbers mean the source has been logged more recently/frequently."""
    async with get_db() as conn:
        # Look at the last 6 hours of entries for more responsive priority adjustment
        cursor = await conn.execute('''
            SELECT COUNT(*) as entry_count 
            FROM news_entries 
            WHERE feed_url = ? 
            AND datetime(pub_date) > datetime('now', '-6 hours')
        ''', (feed_url,))
        row = await cursor.fetchone()
        count = row[0]
        
        # Calculate priority - more entries means lower priority
        # Base priority of 100, subtract 10 for each recent entry, minimum 5
        priority = max(100 - (count * 10), 5)
        
        # Update the cache
        await conn.execute('''
            UPDATE feed_cache 
            SET source_priority = ? 
            WHERE url = ?
        ''', (priority, feed_url))
        await conn.commit()
        
        return priority

# Add new functions for tag operations
async def add_tag(name: str, category: str) -> int:
    """Add a new tag or get existing tag ID."""
    async with get_db() as conn:
        cursor = await conn.execute("SELECT id FROM tags WHERE name = ? AND category = ?", (name.lower(), category))
        row = await cursor.fetchone()
        if row:
            return row['id']
        else:
            cursor = await conn.execute("INSERT INTO tags (name, category) VALUES (?, ?)", (name.lower(), category))
            await conn.commit()
            return cursor.lastrowid

async def tag_article(article_id: int, tag_ids: list[int]):
    """Associate one or more tags with an article."""
    async with get_db() as conn:
        for tag_id in tag_ids:
            await conn.execute("INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)", (article_id, tag_id))
        await conn.commit()

async def get_article_tags(article_id: int) -> list[dict]:
    """Retrieve all tags for a given article."""
    async with get_db() as conn:
        cursor = await conn.execute('''
            SELECT tags.id, tags.name, tags.category 
            FROM tags 
            JOIN article_tags ON tags.id = article_tags.tag_id 
            WHERE article_tags.article_id = ?
        ''', (article_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def search_articles_by_tags(tag_names: list[str], limit: int = 20, offset: int = 0) -> list[dict]:
    """Search for articles that have ALL of the given tags."""
    async with get_db() as conn:
        placeholders = ', '.join('?' for _ in tag_names)
        query = f'''
            SELECT n.* FROM news_entries n
            JOIN (
                SELECT at.article_id
                FROM article_tags at
                JOIN tags t ON at.tag_id = t.id
                WHERE t.name IN ({placeholders})
                GROUP BY at.article_id
                HAVING COUNT(DISTINCT t.id) = ?
            ) AS matching_articles ON n.id = matching_articles.article_id
            ORDER BY n.pub_date DESC
            LIMIT ? OFFSET ?
        '''
        cursor = await conn.execute(query, (*tag_names, len(tag_names), limit, offset))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

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
    """Asynchronously stores an article in the database."""
    pub_date_str = pub_date.isoformat()
    
    async with get_db() as conn:
        cursor = await conn.cursor()
        try:
            # Check if URL already exists
            await cursor.execute('SELECT id FROM news_entries WHERE link = ?', (link,))
            existing = await cursor.fetchone()
            if existing:
                return existing[0]  # Return existing ID, no need to reprocess
            
            # Store article with timestamp
            current_time = datetime.now(timezone.utc).isoformat()
            await cursor.execute('''
                INSERT INTO news_entries (
                    title, description, content, link, guid, feed_url, pub_date,
                    processed_date, emoji1, emoji2, image_url, sentiment_score, 
                    bias_category, bias_score, message
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                title, description, content, link, guid, feed_url, pub_date_str, 
                current_time, emoji1, emoji2, image_url, sentiment_score, 
                bias_category, bias_score, message
            ))
            
            await conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error storing article {link}: {str(e)}")
            await conn.rollback()
            return -1
