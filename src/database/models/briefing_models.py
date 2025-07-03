import json
import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Get access to the database connection
try:
    from ..models import get_db
except ImportError:
    # Fallback implementation if the import fails
    logger.warning("Could not import get_db, using fallback implementation")
    
    def get_db():
        """Fallback implementation to get a database connection."""
        from pathlib import Path
        db_path = Path(__file__).parents[3] / "data" / "news_monitor.db"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn


async def init_briefing_tables():
    """Initialize the database tables for briefing storage."""
    with get_db() as conn:
        # Main briefing document table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS briefing_document (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TIMESTAMP NOT NULL,
            refreshed_at TIMESTAMP,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            total_articles INTEGER NOT NULL,
            regional_hotspots TEXT,
            executive_summary TEXT
        )
        ''')
        
        # Briefing sections table (flash, summary, context)
        conn.execute('''
        CREATE TABLE IF NOT EXISTS briefing_section (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            briefing_id INTEGER NOT NULL,
            section_type TEXT NOT NULL,
            item_count INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (briefing_id) REFERENCES briefing_document(id)
        )
        ''')
        
        # Briefing items table (individual news items)
        conn.execute('''
        CREATE TABLE IF NOT EXISTS briefing_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER NOT NULL,
            news_id INTEGER,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            content TEXT,
            sentiment_score REAL,
            position INTEGER NOT NULL,
            FOREIGN KEY (section_id) REFERENCES briefing_section(id)
        )
        ''')
        
        # Regional summaries table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS regional_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            briefing_id INTEGER NOT NULL,
            region_name TEXT NOT NULL,
            count INTEGER NOT NULL,
            avg_sentiment REAL,
            FOREIGN KEY (briefing_id) REFERENCES briefing_document(id)
        )
        ''')
        
        # Briefing metrics table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS briefing_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            briefing_id INTEGER NOT NULL,
            generation_time REAL,
            refresh_time REAL,
            flash_alerts_count INTEGER,
            sentiment_shift REAL,
            coverage_change_pct REAL,
            volume_change_pct REAL,
            FOREIGN KEY (briefing_id) REFERENCES briefing_document(id)
        )
        ''')
        
        conn.commit()
        logger.info("Briefing database tables initialized")


async def save_briefing(briefing: Dict[str, Any]) -> int:
    """Save a briefing to the database.
    
    Args:
        briefing: Complete briefing data structure
        
    Returns:
        int: ID of the created briefing document
    """
    try:
        # Extract metadata
        metadata = briefing.get('metadata', {})
        generated_at = metadata.get('generated_at')
        # Convert datetime object to string if needed
        if isinstance(generated_at, datetime):
            generated_at = generated_at.isoformat()
            
        refreshed_at = metadata.get('refreshed_at')
        if isinstance(refreshed_at, datetime):
            refreshed_at = refreshed_at.isoformat()
            
        start_time = metadata.get('start_time')
        if isinstance(start_time, datetime):
            start_time = start_time.isoformat()
            
        end_time = metadata.get('end_time')
        if isinstance(end_time, datetime):
            end_time = end_time.isoformat()
        
        exec_summary = json.dumps(briefing.get('executive_summary', {}))
        regional_hotspots = json.dumps(metadata.get('regional_hotspots', []))
        
        with get_db() as conn:
            # Insert main document
            cursor = conn.execute('''
            INSERT INTO briefing_document 
            (generated_at, refreshed_at, start_time, end_time, 
             total_articles, regional_hotspots, executive_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                generated_at,
                refreshed_at,
                start_time,
                end_time,
                metadata.get('total_articles', 0),
                regional_hotspots,
                exec_summary
            ))
            
            # Get the document ID
            briefing_id = cursor.lastrowid
            
            # Insert sections
            for section_type in ['flash', 'summary', 'context']:
                section_data = briefing.get(section_type, {})
                items = section_data.get('items', [])
                
                # Skip empty sections
                if not items:
                    continue
                    
                # Insert section
                cursor = conn.execute('''
                INSERT INTO briefing_section
                (briefing_id, section_type, item_count, content)
                VALUES (?, ?, ?, ?)
                ''', (
                    briefing_id,
                    section_type,
                    len(items),
                    json.dumps(section_data)  # Store full section data for easy retrieval
                ))
                
                section_id = cursor.lastrowid
                
                # Insert individual items 
                for i, item in enumerate(items):
                    conn.execute('''
                    INSERT INTO briefing_item
                    (section_id, news_id, title, link, timestamp, content, sentiment_score, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        section_id,
                        item.get('id'),  # This might be None
                        item.get('title', ''),
                        item.get('link', ''),
                        item.get('timestamp', ''),
                        item.get('content', ''),
                        item.get('sentiment_score', 0.0),
                        i  # Position in the list
                    ))
            
            # Insert regional summaries
            for region in briefing.get('summary', {}).get('regions', []):
                conn.execute('''
                INSERT INTO regional_summary
                (briefing_id, region_name, count, avg_sentiment)
                VALUES (?, ?, ?, ?)
                ''', (
                    briefing_id,
                    region.get('name', ''),
                    region.get('count', 0),
                    region.get('avg_sentiment', 0.0)
                ))
            
            conn.commit()
            logger.info(f"Saved briefing document with ID {briefing_id}")
            return briefing_id
            
    except Exception as e:
        logger.error(f"Error saving briefing: {str(e)}", exc_info=True)
        return None


def get_current_briefing() -> Dict[str, Any]:
    """Get the most recently generated briefing.
    
    Returns:
        Complete briefing document or empty dict if none found
    """
    try:
        with get_db() as conn:
            # Get the most recent briefing document
            cursor = conn.execute('''
            SELECT id, generated_at, refreshed_at, start_time, end_time, 
                  total_articles, regional_hotspots, executive_summary
            FROM briefing_document
            ORDER BY generated_at DESC
            LIMIT 1
            ''')
            
            row = cursor.fetchone()
            if not row:
                return {}
                
            # Build the briefing document
            briefing_id = row['id']
            briefing = {
                'metadata': {
                    'generated_at': row['generated_at'],
                    'refreshed_at': row['refreshed_at'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'total_articles': row['total_articles'],
                    'regional_hotspots': json.loads(row['regional_hotspots'])
                },
                'executive_summary': json.loads(row['executive_summary'])
            }
            
            # Get sections
            cursor = conn.execute('''
            SELECT id, section_type, content 
            FROM briefing_section
            WHERE briefing_id = ?
            ''', (briefing_id,))
            
            for section_row in cursor.fetchall():
                section_type = section_row['section_type']
                section_content = json.loads(section_row['content'])
                briefing[section_type] = section_content
            
            return briefing
            
    except Exception as e:
        logger.error(f"Error getting current briefing: {str(e)}", exc_info=True)
        return {}


def get_briefing_by_date(target_date: Union[str, datetime]) -> Dict[str, Any]:
    """Get a briefing for a specific date.
    
    Args:
        target_date: Date to find briefing for (can be string or datetime)
        
    Returns:
        Complete briefing document or empty dict if none found
    """
    try:
        # Convert to datetime if string
        if isinstance(target_date, str):
            try:
                target_date = datetime.fromisoformat(target_date)
            except ValueError:
                # Try simpler format
                target_date = datetime.strptime(target_date, "%Y-%m-%d")
                
        # Convert to UTC timezone if naive
        if target_date.tzinfo is None:
            target_date = target_date.replace(tzinfo=timezone.utc)
            
        # Set to start of day
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        with get_db() as conn:
            # Find a briefing that covers this date
            cursor = conn.execute('''
            SELECT id FROM briefing_document
            WHERE (start_time <= ? AND end_time >= ?)  -- Briefing window contains target
               OR (generated_at >= ? AND generated_at < ?) -- Generated on target date
            ORDER BY generated_at DESC
            LIMIT 1
            ''', (
                target_date.isoformat(), 
                target_date.isoformat(),
                start_of_day.isoformat(),
                end_of_day.isoformat()
            ))
            
            row = cursor.fetchone()
            if not row:
                return {}
                
            # Get full briefing by ID
            return get_briefing_by_id(row['id'])
            
    except Exception as e:
        logger.error(f"Error getting briefing by date: {str(e)}", exc_info=True)
        return {}


def get_briefing_by_id(briefing_id: int) -> Dict[str, Any]:
    """Get a specific briefing by ID.
    
    Args:
        briefing_id: ID of the briefing to retrieve
        
    Returns:
        Complete briefing document or empty dict if not found
    """
    try:
        with get_db() as conn:
            # Get the briefing document
            cursor = conn.execute('''
            SELECT id, generated_at, refreshed_at, start_time, end_time, 
                  total_articles, regional_hotspots, executive_summary
            FROM briefing_document
            WHERE id = ?
            ''', (briefing_id,))
            
            row = cursor.fetchone()
            if not row:
                return {}
                
            # Build the briefing document
            briefing = {
                'id': row['id'],
                'metadata': {
                    'generated_at': row['generated_at'],
                    'refreshed_at': row['refreshed_at'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'total_articles': row['total_articles'],
                    'regional_hotspots': json.loads(row['regional_hotspots'])
                },
                'executive_summary': json.loads(row['executive_summary'])
            }
            
            # Get sections
            cursor = conn.execute('''
            SELECT id, section_type, content 
            FROM briefing_section
            WHERE briefing_id = ?
            ''', (briefing_id,))
            
            for section_row in cursor.fetchall():
                section_type = section_row['section_type']
                section_content = json.loads(section_row['content'])
                briefing[section_type] = section_content
            
            return briefing
            
    except Exception as e:
        logger.error(f"Error getting briefing by ID: {str(e)}", exc_info=True)
        return {}


def get_flash_items(count: int = 5, offset: int = 0) -> List[Dict[str, Any]]:
    """Get the most recent flash items.
    
    Args:
        count: Number of items to return
        offset: Offset for pagination
        
    Returns:
        List of flash items
    """
    try:
        with get_db() as conn:
            # First get the most recent briefing section of type 'flash'
            cursor = conn.execute('''
            SELECT bs.id 
            FROM briefing_section bs
            JOIN briefing_document bd ON bs.briefing_id = bd.id
            WHERE bs.section_type = 'flash'
            ORDER BY bd.generated_at DESC
            LIMIT 1
            ''')
            
            section_row = cursor.fetchone()
            if not section_row:
                return []
                
            section_id = section_row['id']
            
            # Now get the items from this section
            cursor = conn.execute('''
            SELECT title, link, timestamp, content, sentiment_score
            FROM briefing_item
            WHERE section_id = ?
            ORDER BY position ASC
            LIMIT ? OFFSET ?
            ''', (section_id, count, offset))
            
            items = []
            for item_row in cursor.fetchall():
                items.append({
                    'title': item_row['title'],
                    'link': item_row['link'],
                    'timestamp': item_row['timestamp'],
                    'content': item_row['content'],
                    'sentiment_score': item_row['sentiment_score']
                })
                
            return items
            
    except Exception as e:
        logger.error(f"Error getting flash items: {str(e)}", exc_info=True)
        return []


def update_briefing_metrics(briefing_id: int, metrics_data: Dict[str, Any]) -> bool:
    """Update metrics for a briefing.
    
    Args:
        briefing_id: ID of the briefing to update
        metrics_data: Dictionary of metrics to update
        
    Returns:
        bool: Success state
    """
    try:
        with get_db() as conn:
            # Check if metrics exist for this briefing
            cursor = conn.execute('''
            SELECT id FROM briefing_metrics 
            WHERE briefing_id = ?
            ''', (briefing_id,))
            
            row = cursor.fetchone()
            
            if row:
                # Update existing metrics
                conn.execute('''
                UPDATE briefing_metrics
                SET generation_time = ?,
                    refresh_time = ?,
                    flash_alerts_count = ?,
                    sentiment_shift = ?,
                    coverage_change_pct = ?,
                    volume_change_pct = ?
                WHERE briefing_id = ?
                ''', (
                    metrics_data.get('generation_time'),
                    metrics_data.get('refresh_time'),
                    metrics_data.get('flash_alerts_count'),
                    metrics_data.get('sentiment_shift'),
                    metrics_data.get('coverage_change_pct'),
                    metrics_data.get('volume_change_pct'),
                    briefing_id
                ))
            else:
                # Insert new metrics
                conn.execute('''
                INSERT INTO briefing_metrics
                (briefing_id, generation_time, refresh_time, flash_alerts_count,
                 sentiment_shift, coverage_change_pct, volume_change_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    briefing_id,
                    metrics_data.get('generation_time'),
                    metrics_data.get('refresh_time'),
                    metrics_data.get('flash_alerts_count'),
                    metrics_data.get('sentiment_shift'),
                    metrics_data.get('coverage_change_pct'),
                    metrics_data.get('volume_change_pct')
                ))
                
            conn.commit()
            return True
                
    except Exception as e:
        logger.error(f"Error updating briefing metrics: {str(e)}", exc_info=True)
        return False


def get_regional_summary(region_code: str) -> List[Dict[str, Any]]:
    """Get regional summary data for a specific region.
    
    This returns historical data for the specified region across
    multiple briefings to enable trend analysis.
    
    Args:
        region_code: Region code/name to search for
        
    Returns:
        List of regional summary data points
    """
    try:
        with get_db() as conn:
            cursor = conn.execute('''
            SELECT rs.region_name, rs.count, rs.avg_sentiment,
                   bd.generated_at, bd.total_articles
            FROM regional_summary rs
            JOIN briefing_document bd ON rs.briefing_id = bd.id
            WHERE LOWER(rs.region_name) = LOWER(?)
            ORDER BY bd.generated_at DESC
            LIMIT 30
            ''', (region_code,))
            
            summaries = []
            for row in cursor.fetchall():
                summaries.append({
                    'region_name': row['region_name'],
                    'count': row['count'],
                    'avg_sentiment': row['avg_sentiment'],
                    'generated_at': row['generated_at'],
                    'total_articles': row['total_articles'],
                    'coverage_pct': (row['count'] / row['total_articles'] * 100) if row['total_articles'] > 0 else 0
                })
                
            return summaries
            
    except Exception as e:
        logger.error(f"Error getting regional summary: {str(e)}", exc_info=True)
        return []


def get_news_in_timespan(start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
    """Get news articles within the specified time range."""
    try:
        # Convert to strings if needed
        if isinstance(start_time, datetime):
            start_time = start_time.isoformat()
        if isinstance(end_time, datetime):
            end_time = end_time.isoformat()
            
        with get_db() as conn:
            cursor = conn.execute('''
            SELECT id, title, content, description, link, pub_date as timestamp, 
                  sentiment_score, bias_score
            FROM news_entries
            WHERE pub_date >= ? AND pub_date <= ?
            ORDER BY pub_date DESC
            ''', (start_time, end_time))
            
            articles = []
            for row in cursor.fetchall():
                # Get tags for this article
                tag_cursor = conn.execute('''
                SELECT t.name, t.category
                FROM tags t
                JOIN article_tags at ON t.id = at.tag_id
                WHERE at.article_id = ?
                ''', (row['id'],))
                
                tags = []
                for tag_row in tag_cursor.fetchall():
                    tags.append({
                        'name': tag_row['name'],
                        'category': tag_row['category']
                    })
                    
                articles.append({
                    'id': row['id'],
                    'title': row['title'],
                    'content': row['content'],
                    'description': row['description'],
                    'link': row['link'],
                    'timestamp': row['timestamp'],
                    'sentiment_score': row['sentiment_score'],
                    'bias_score': row['bias_score'],
                    'tags': tags
                })
            
            return articles
            
    except Exception as e:
        logger.error(f"Error getting news in timespan: {str(e)}", exc_info=True)
        return []


# Note: Tables will be initialized by the web application startup handler