"""WebSocket connection manager for broadcasting updates."""
from typing import List
from fastapi import WebSocket
import json
from ..database.models import get_article_tags

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections[:]:  # Create a copy of the list
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

# Global instance
manager = ConnectionManager()

def format_news_item_for_broadcast(news_item: dict, article_id: int = None) -> dict:
    """Format a news item for broadcast, including tags if article_id is provided."""
    formatted = {
        "type": "news_update",
        "data": {
            "title": news_item.get('title'),
            "description": news_item.get('description'),
            "link": news_item.get('link'),
            "timestamp": news_item.get('timestamp'),
            "image_url": news_item.get('image_url'),
            "feed_url": news_item.get('feed_url'),
            "emoji1": news_item.get('emoji1'),
            "emoji2": news_item.get('emoji2'),
            "tags": []
        }
    }
    
    if article_id:
        formatted["data"]["tags"] = get_article_tags(article_id)
    
    return formatted

async def broadcast_news_update(news_item: dict, article_id: int = None):
    """Broadcast news update to all connected clients."""
    formatted_item = format_news_item_for_broadcast(news_item, article_id)
    await manager.broadcast(json.dumps(formatted_item))