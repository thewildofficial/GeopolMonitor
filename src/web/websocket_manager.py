"""WebSocket connection manager for broadcasting updates."""
from typing import List
from fastapi import WebSocket
import json

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

async def broadcast_news_update(news_item: dict):
    """Broadcast news update to all connected clients."""
    await manager.broadcast(json.dumps({
        "type": "news_update",
        "data": news_item
    }))