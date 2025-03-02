"""FastAPI web interface for GeopolMonitor."""
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, WebSocket, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from typing import List, Optional
import json
import atexit
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from . import country_utils

from ..database.models import (
    init_db, get_db, cleanup_db, 
    get_article_tags, search_articles_by_tags
)
from ..core.processor import ImageExtractor
from ..utils.text import clean_text
from .websocket_manager import manager
from config.settings import STATIC_DIR, TEMPLATES_DIR, WEB_HOST

# Ensure static directory exists
STATIC_DIR.mkdir(exist_ok=True)

def is_local_environment():
    """Check if we're running in a local environment"""
    return WEB_HOST in ['localhost', '127.0.0.1', '0.0.0.0']

class CompressedStaticFiles(StarletteStaticFiles):
    """Custom static files handler that adds compression headers"""
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if path.endswith('.json'):
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Vary'] = 'Accept-Encoding'
            response.headers.add('Cache-Control', 'public, max-age=3600')
        return response

def create_app():
    """Create and configure FastAPI application"""
    app = FastAPI(debug=True)
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Mount static files normally without compression
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # Add request middleware to ensure proper URL scheme
    @app.middleware("http")
    async def update_request_scheme(request: Request, call_next):
        forwarded_proto = request.headers.get("x-forwarded-proto")
        if forwarded_proto == "https" or (not is_local_environment() and forwarded_proto != "http"):
            request.scope["scheme"] = "https"
        response = await call_next(request)
        return response

    @app.on_event("startup")
    async def startup_event():
        """Initialize database on startup."""
        init_db()

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up database on shutdown."""
        cleanup_db()

    def ensure_source_tag_exists(conn, source_name):
        """Ensure a source tag exists in the database."""
        cursor = conn.execute(
            'SELECT id FROM tags WHERE name = ? AND category = ?',
            (source_name, 'source')
        )
        tag_id = cursor.fetchone()
        
        if not tag_id:
            cursor = conn.execute(
                'INSERT INTO tags (name, category) VALUES (?, ?)',
                (source_name, 'source')
            )
            conn.commit()
            return cursor.lastrowid
        return tag_id[0]

    def format_news_item(item):
        """Format news item for API response"""
        from ..utils.date_utils import format_iso_date, ensure_utc
        from datetime import datetime, timezone
        
        # Extract image from content if no image_url is present
        image_url = item.get('image_url')
        if not image_url and item.get('content'):
            try:
                image_url = ImageExtractor.extract_first_image_from_content(item.get('content', ''))
            except Exception as e:
                print(f"Error extracting image from content: {str(e)}")
                image_url = None
        
        # Get tags for the article
        tags = get_article_tags(item.get('id')) if item.get('id') else []
        
        # Handle emojis
        emoji1 = item.get('emoji1', '')
        emoji2 = item.get('emoji2', '')
        
        # Format publication date consistently in UTC ISO format
        timestamp = item.get('pub_date', '')
        if timestamp:
            try:
                # Parse the date if it's a string
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except ValueError:
                        # If not ISO format, try a more flexible parser
                        from dateparser import parse
                        timestamp = parse(timestamp)
                        
                # Ensure the date is in UTC timezone
                if timestamp:
                    timestamp = ensure_utc(timestamp)
                    # Format as ISO string with Z timezone indicator for consistency
                    timestamp = format_iso_date(timestamp)
            except Exception as e:
                print(f"Error processing timestamp: {e}")
        
        # Extract source from feed_url and add as a tag if not already present
        feed_url = item.get('feed_url', '')
        if (feed_url and item.get('id')):
            try:
                from urllib.parse import urlparse
                domain = urlparse(feed_url).netloc
                source_name = domain.replace('www.', '').split('.')[0].upper()
                
                with get_db() as conn:
                    # Ensure source tag exists and get its ID
                    tag_id = ensure_source_tag_exists(conn, source_name)
                    
                    # Link tag to article if not already linked
                    cursor = conn.execute(
                        'SELECT 1 FROM article_tags WHERE article_id = ? AND tag_id = ?',
                        (item['id'], tag_id)
                    )
                    if not cursor.fetchone():
                        conn.execute(
                            'INSERT INTO article_tags (article_id, tag_id) VALUES (?, ?)',
                            (item['id'], tag_id)
                        )
                        conn.commit()
                
                # Update tags list to include source tag
                source_tag = {
                    'name': source_name,
                    'category': 'source'
                }
                if source_tag not in tags:
                    tags.append(source_tag)
            except:
                pass  # Skip if URL parsing fails
        
        return {
            'title': clean_text(item.get('title', '')),
            'description': clean_text(item.get('description', '')),
            'content': item.get('content', ''),
            'link': item.get('link', ''),
            'timestamp': timestamp,
            'image_url': image_url,
            'feed_url': feed_url,
            'emoji1': emoji1,
            'emoji2': emoji2,
            'tags': tags,
            'sentiment_score': item.get('sentiment_score', 0.0),
            'bias_category': item.get('bias_category', 'neutral'),
            'bias_score': item.get('bias_score', 0.0)
        }

    def extract_locations_from_text(text):
        """Extract location names from text using simple keyword matching.
        This is a basic implementation that could be improved with NLP."""
        common_locations = {
            'USA', 'RUSSIA', 'CHINA', 'UK', 'FRANCE', 'GERMANY', 'JAPAN',
            'INDIA', 'BRAZIL', 'CANADA', 'AUSTRALIA', 'EUROPE', 'ASIA',
            'AFRICA', 'MIDDLE EAST', 'NORTH AMERICA', 'SOUTH AMERICA'
        }
        
        found_locations = set()
        text_upper = text.upper()
        
        for location in common_locations:
            if location in text_upper:
                found_locations.add(location)
        
        return list(found_locations)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        return templates.TemplateResponse(
            "index.html",
            {"request": request}
        )

    @app.get("/map", response_class=HTMLResponse)
    async def map_page(request: Request):
        return templates.TemplateResponse(
            "map.html",
            {"request": request}
        )

    @app.get("/about", response_class=HTMLResponse)
    async def about(request: Request):
        return templates.TemplateResponse(
            "about.html",
            {"request": request}
        )

    @app.get("/api/news")
    async def get_news(
        tags: Optional[str] = None, 
        page: int = Query(1, ge=1), 
        page_size: int = Query(20, ge=1, le=100)
    ):
        try:
            print(f"Fetching news with params: tags={tags}, page={page}, page_size={page_size}")
            
            # Calculate offset for pagination
            offset = (page - 1) * page_size
            total_count = 0
            news_items = []
            
            with get_db() as conn:
                try:
                    # Get total count first
                    if tags:
                        tag_list = [t.strip() for t in tags.split(',')]
                        placeholders = ','.join('?' * len(tag_list))
                        count_sql = f'''
                            SELECT COUNT(DISTINCT ne.id)
                            FROM news_entries ne
                            JOIN article_tags at ON ne.id = at.article_id
                            JOIN tags t ON at.tag_id = t.id
                            WHERE t.name IN ({placeholders})
                        '''
                        print(f"Executing count query: {count_sql} with params {tag_list}")
                        count_cursor = conn.execute(count_sql, tag_list)
                    else:
                        print("Executing simple count query")
                        count_cursor = conn.execute('SELECT COUNT(*) FROM news_entries')
                    
                    total_count = count_cursor.fetchone()[0] or 0
                    print(f"Total count: {total_count}")

                    # Then get the paginated results
                    if tags:
                        tag_list = [t.strip() for t in tags.split(',')]
                        print(f"Fetching news items with tags: {tag_list}")
                        news_items = search_articles_by_tags(
                            tag_list, 
                            limit=page_size, 
                            offset=offset
                        )
                    else:
                        select_sql = '''
                            SELECT 
                                id, title, description, content, link, pub_date,
                                feed_url, image_url, message, emoji1, emoji2,
                                sentiment_score, bias_category, bias_score
                            FROM news_entries
                            ORDER BY pub_date DESC
                            LIMIT ? OFFSET ?
                        '''
                        print(f"Executing select query: {select_sql} with params {(page_size, offset)}")
                        cursor = conn.execute(select_sql, (page_size, offset))
                        columns = [column[0] for column in cursor.description]
                        news_items = [dict(zip(columns, row)) for row in cursor]

                    print(f"Found {len(news_items)} news items")

                except Exception as db_error:
                    print(f"Database error in get_news: {str(db_error)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Database error: {str(db_error)}"
                    )

                # Format news items
                formatted_news = []
                for item in news_items:
                    if item:
                        try:
                            formatted = format_news_item(item)
                            if formatted:
                                formatted_news.append(formatted)
                        except Exception as format_error:
                            print(f"Error formatting news item {item.get('id')}: {str(format_error)}")
                            continue

                # Always include pagination metadata
                total_pages = max(1, (total_count + page_size - 1) // page_size)
                response = {
                    "news": formatted_news,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_next": page * page_size < total_count,
                        "has_prev": page > 1
                    }
                }
                return response

        except HTTPException:
            raise
        except Exception as e:
            print(f"Unexpected error in get_news: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"Unexpected error: {str(e)}",
                    "news": [],
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_count": 0,
                        "total_pages": 1,
                        "has_next": False,
                        "has_prev": False
                    }
                }
            )

    @app.get("/api/tags")
    async def get_tags(limit: int = 100, offset: int = 0):
        """Get all available tags grouped by category with pagination."""
        try:
            with get_db() as conn:
                cursor = conn.execute('''
                    SELECT name, category, COUNT(at.article_id) as usage_count
                    FROM tags t
                    LEFT JOIN article_tags at ON t.id = at.tag_id
                    GROUP BY t.id
                    ORDER BY usage_count DESC, name ASC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                
                tags = {
                    'source': [],
                    'topic': [],
                    'geography': [],
                    'events': []
                }
                
                for row in cursor.fetchall():
                    category = row[1]
                    if category in tags:
                        tags[category].append({
                            'name': row[0],
                            'count': row[2]
                        })
                
                return tags
        except Exception as e:
            print(f"Error in get_tags: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": str(e),
                    "source": [],
                    "topic": [],
                    "geography": [],
                    "events": []
                }
            )

    @app.get("/api/countries-lite")
    async def get_countries_lite():
        """Serve the countries-lite.json file"""
        try:
            file_path = STATIC_DIR / "assets" / "countries-lite.json"
            print(f"Reading countries data from: {file_path}")
            
            if not file_path.exists():
                raise HTTPException(
                    status_code=404, 
                    detail=f"File not found: {file_path}"
                )
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            return JSONResponse(
                content=data,
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                    "Access-Control-Allow-Origin": "*"
                }
            )
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Invalid JSON data: {str(e)}")
        except Exception as e:
            print(f"Error serving countries data: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()  # Keep connection alive
        except:
            manager.disconnect(websocket)

    return app

app = create_app()
