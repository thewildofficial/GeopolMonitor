"""FastAPI web interface for GeopolMonitor."""
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import atexit

from ..database.models import init_db, get_db, cleanup_db
from ..core.processor import ImageExtractor
from ..utils.text import clean_text
from .websocket_manager import manager
from config.settings import STATIC_DIR, TEMPLATES_DIR

# Ensure static directory exists
STATIC_DIR.mkdir(exist_ok=True)

def create_app():
    """Create and configure FastAPI application"""
    app = FastAPI()
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files and templates
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @app.on_event("startup")
    async def startup_event():
        """Initialize database on startup."""
        init_db()

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up database on shutdown."""
        cleanup_db()

    def format_news_item(item):
        """Format news item for API response"""
        image_url = item.get('image_url') or ImageExtractor.extract_first_image_from_content(item.get('content', ''))
        
        return {
            'title': clean_text(item.get('title', '')),
            'description': clean_text(item.get('description', '')),
            'content': item.get('content', ''),
            'link': item.get('link', ''),
            'timestamp': item.get('pub_date', ''),  # Changed from timestamp to pub_date
            'image_url': image_url,
            'feed_url': item.get('feed_url', ''),
            'emoji1': item.get('emoji1', ''),
            'emoji2': item.get('emoji2', '')
        }

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

    @app.get("/about", response_class=HTMLResponse)
    async def about(request: Request):
        return templates.TemplateResponse(
            "about.html",
            {"request": request}
        )

    @app.get("/api/news")
    async def get_news():
        try:
            with get_db() as conn:
                cursor = conn.execute('''
                    SELECT 
                        title, description, content, link, pub_date,
                        feed_url, image_url, message, emoji1, emoji2
                    FROM news_entries
                    ORDER BY pub_date DESC
                    LIMIT 100
                ''')
                columns = [column[0] for column in cursor.description]
                news_items = [dict(zip(columns, row)) for row in cursor]
                
            formatted_news = [format_news_item(item) for item in news_items]
            return {"news": formatted_news}
        except Exception as e:
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