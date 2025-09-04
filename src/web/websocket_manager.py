"""
WebSocket connection manager for broadcasting real-time updates.

Enhanced to support both RSS feed updates and real-time Telegram message distribution
via Redis Pub/Sub integration. Provides filtering, channel management, and 
high-performance message broadcasting.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect

from ..database.models import get_article_tags
from ..core.services.redis_pubsub import (
    redis_service, 
    subscribe_to_all_telegram_messages,
    subscribe_to_telegram_messages,
    RedisMessage,
    Priority
)

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages that can be broadcast via WebSocket."""
    RSS_UPDATE = "rss_update"
    TELEGRAM_MESSAGE = "telegram_message"
    CHANNEL_STATS = "channel_stats"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"


@dataclass
class WebSocketFilter:
    """Client-specific filtering configuration."""
    channels: Optional[Set[str]] = None  # Specific Telegram channels to receive
    countries: Optional[Set[str]] = None  # Geographic filter
    keywords: Optional[Set[str]] = None   # Keyword filter
    sentiment_threshold: Optional[float] = None  # Minimum sentiment score
    priority_level: Optional[str] = None  # Minimum priority level
    message_types: Set[MessageType] = None  # Types of messages to receive
    
    def __post_init__(self):
        if self.message_types is None:
            self.message_types = {MessageType.TELEGRAM_MESSAGE, MessageType.RSS_UPDATE}


@dataclass
class WebSocketConnection:
    """Enhanced WebSocket connection with filtering and metadata."""
    websocket: WebSocket
    client_id: str
    filters: WebSocketFilter
    connected_at: datetime
    last_ping: Optional[datetime] = None
    message_count: int = 0
    error_count: int = 0


class EnhancedConnectionManager:
    """
    Enhanced WebSocket connection manager with Redis Pub/Sub integration.
    
    Supports real-time Telegram message distribution, RSS updates, 
    client-specific filtering, and connection management.
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocketConnection] = {}
        self.redis_subscription_task: Optional[asyncio.Task] = None
        self.is_redis_connected = False
        self.stats = {
            "connections": 0,
            "messages_sent": 0,
            "errors": 0,
            "start_time": datetime.now(timezone.utc)
        }
        
    async def connect(
        self, 
        websocket: WebSocket, 
        client_id: str = None,
        filters: WebSocketFilter = None
    ) -> str:
        """
        Connect a new WebSocket client with optional filtering.
        
        Args:
            websocket: FastAPI WebSocket instance
            client_id: Optional custom client ID
            filters: Optional filtering configuration
            
        Returns:
            str: Assigned client ID
        """
        await websocket.accept()
        
        # Generate client ID if not provided
        if not client_id:
            client_id = f"client_{len(self.active_connections)}_{int(datetime.now().timestamp())}"
            
        # Set default filters if none provided
        if filters is None:
            filters = WebSocketFilter()
            
        # Create connection object
        connection = WebSocketConnection(
            websocket=websocket,
            client_id=client_id,
            filters=filters,
            connected_at=datetime.now(timezone.utc)
        )
        
        self.active_connections[client_id] = connection
        self.stats["connections"] += 1
        
        # Start Redis subscription if this is the first connection
        if len(self.active_connections) == 1 and not self.redis_subscription_task:
            await self._start_redis_subscription()
            
        logger.info(f"WebSocket client connected: {client_id} (Total: {len(self.active_connections)})")
        
        # Send welcome message
        await self._send_to_client(client_id, {
            "type": MessageType.SYSTEM_STATUS,
            "data": {
                "status": "connected",
                "client_id": client_id,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "filters": self._serialize_filters(filters)
            }
        })
        
        return client_id

    async def disconnect(self, client_id: str = None, websocket: WebSocket = None):
        """
        Disconnect a WebSocket client.
        
        Args:
            client_id: Client ID to disconnect
            websocket: WebSocket instance to disconnect (alternative to client_id)
        """
        # Find client by websocket if client_id not provided
        if not client_id and websocket:
            for cid, conn in self.active_connections.items():
                if conn.websocket == websocket:
                    client_id = cid
                    break
                    
        if client_id and client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id} (Remaining: {len(self.active_connections)})")
            
            # Stop Redis subscription if no more connections
            if len(self.active_connections) == 0 and self.redis_subscription_task:
                await self._stop_redis_subscription()

    async def update_client_filters(self, client_id: str, filters: WebSocketFilter):
        """Update filtering configuration for a specific client."""
        if client_id in self.active_connections:
            self.active_connections[client_id].filters = filters
            await self._send_to_client(client_id, {
                "type": MessageType.SYSTEM_STATUS,
                "data": {
                    "status": "filters_updated",
                    "filters": self._serialize_filters(filters)
                }
            })

    async def broadcast_telegram_message(self, redis_message: RedisMessage):
        """
        Broadcast a Telegram message to filtered clients.
        
        Args:
            redis_message: RedisMessage from the Redis Pub/Sub system
        """
        if not self.active_connections:
            return
            
        message_data = {
            "type": MessageType.TELEGRAM_MESSAGE,
            "data": {
                "message_id": redis_message.data.get("message_id"),
                "channel_id": redis_message.data.get("channel_id"),
                "channel_username": redis_message.data.get("channel_username"),
                "text": redis_message.data.get("text"),
                "author": redis_message.data.get("author"),
                "timestamp": datetime.fromtimestamp(redis_message.timestamp, tz=timezone.utc).isoformat(),
                "priority": Priority(redis_message.priority).name.lower(),
                "metadata": redis_message.data.get("metadata", {}),
                "ai_analysis": redis_message.data.get("ai_analysis", {}),
                "geographical_relevance": redis_message.data.get("geographical_relevance", [])
            }
        }
        
        # Send to filtered clients
        for client_id, connection in list(self.active_connections.items()):
            if self._should_send_telegram_message(connection, redis_message):
                await self._send_to_client(client_id, message_data)

    async def broadcast_rss_update(self, news_item: dict, article_id: int = None):
        """
        Broadcast RSS news update to all connected clients (existing functionality).
        
        Args:
            news_item: News item dictionary
            article_id: Optional article ID for tag retrieval
        """
        if not self.active_connections:
            return
            
        formatted_item = self._format_rss_item_for_broadcast(news_item, article_id)
        
        # Send to clients that accept RSS updates
        for client_id, connection in list(self.active_connections.items()):
            if MessageType.RSS_UPDATE in connection.filters.message_types:
                await self._send_to_client(client_id, formatted_item)

    async def broadcast_channel_stats(self, stats: dict):
        """Broadcast channel statistics to all connected clients."""
        message = {
            "type": MessageType.CHANNEL_STATS,
            "data": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self._broadcast_to_all(message)

    async def broadcast_system_status(self, status: dict):
        """Broadcast system status updates to all connected clients."""
        message = {
            "type": MessageType.SYSTEM_STATUS,
            "data": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self._broadcast_to_all(message)

    def get_connection_stats(self) -> dict:
        """Get current connection and performance statistics."""
        uptime = datetime.now(timezone.utc) - self.stats["start_time"]
        
        return {
            "active_connections": len(self.active_connections),
            "total_connections": self.stats["connections"],
            "messages_sent": self.stats["messages_sent"],
            "errors": self.stats["errors"],
            "redis_connected": self.is_redis_connected,
            "uptime_seconds": uptime.total_seconds(),
            "connections_detail": [
                {
                    "client_id": conn.client_id,
                    "connected_at": conn.connected_at.isoformat(),
                    "message_count": conn.message_count,
                    "error_count": conn.error_count,
                    "filters": asdict(conn.filters)
                }
                for conn in self.active_connections.values()
            ]
        }

    # Private methods
    
    async def _start_redis_subscription(self):
        """Start Redis Pub/Sub subscription for Telegram messages."""
        try:
            logger.info("Starting Redis subscription for WebSocket broadcast")
            
            # Start Redis service if not already running
            if not redis_service.is_running:
                await redis_service.start()
                
            # Subscribe to the pattern (this sets up the subscription)
            await subscribe_to_all_telegram_messages(self._handle_redis_message)
            
            # If the service wasn't listening before (because no subscriptions existed),
            # we need to start the listener now
            if not redis_service.subscriber.is_listening:
                await redis_service.subscriber.start_listening()
            # If it was already listening, update subscriptions
            else:
                await redis_service.subscriber._update_subscriptions()
                
            self.is_redis_connected = True
            
            logger.info("✅ Redis subscription active for WebSocket broadcast")
            
        except Exception as e:
            logger.error(f"Failed to start Redis subscription: {e}")
            self.is_redis_connected = False

    async def _stop_redis_subscription(self):
        """Stop Redis Pub/Sub subscription."""
        try:
            if self.redis_subscription_task:
                self.redis_subscription_task.cancel()
                try:
                    # Wait for the task to complete with timeout
                    await asyncio.wait_for(self.redis_subscription_task, timeout=5.0)
                except asyncio.CancelledError:
                    # Task was cancelled as expected
                    pass
                except asyncio.TimeoutError:
                    logger.warning("Redis subscription task did not complete within timeout")
                except Exception as e:
                    logger.error(f"Error during Redis subscription task cleanup: {e}")
                finally:
                    self.redis_subscription_task = None
                
            self.is_redis_connected = False
            logger.info("Redis subscription stopped for WebSocket broadcast")
            
        except Exception as e:
            logger.error(f"Error stopping Redis subscription: {e}")

    async def _handle_redis_message(self, channel: str, redis_message: RedisMessage):
        """Handle incoming Redis message and broadcast to WebSocket clients."""
        try:
            logger.debug(f"Received Redis message from channel {channel}")
            await self.broadcast_telegram_message(redis_message)
        except Exception as e:
            logger.error(f"Error handling Redis message for WebSocket broadcast: {e}")
            self.stats["errors"] += 1

    def _should_send_telegram_message(self, connection: WebSocketConnection, redis_message: RedisMessage) -> bool:
        """Check if a Telegram message should be sent to a specific client."""
        filters = connection.filters
        
        # Check message type filter
        if MessageType.TELEGRAM_MESSAGE not in filters.message_types:
            return False
            
        # Check channel filter
        if filters.channels:
            channel_username = redis_message.data.get("channel_username")
            if channel_username and channel_username not in filters.channels:
                return False
                
        # Check country filter
        if filters.countries:
            geographical_relevance = redis_message.data.get("geographical_relevance", [])
            if not any(country in filters.countries for country in geographical_relevance):
                return False
                
        # Check keyword filter
        if filters.keywords:
            text = redis_message.data.get("text", "").lower()
            if not any(keyword.lower() in text for keyword in filters.keywords):
                return False
                
        # Check sentiment threshold
        if filters.sentiment_threshold is not None:
            sentiment_score = redis_message.data.get("ai_analysis", {}).get("sentiment_score")
            if sentiment_score is not None and sentiment_score < filters.sentiment_threshold:
                return False
                
        # Check priority level
        if filters.priority_level:
            try:
                # Create mapping from Priority enum to string names
                priority_mapping = {
                    Priority.LOW: "low",
                    Priority.MEDIUM: "medium", 
                    Priority.HIGH: "high",
                    Priority.CRITICAL: "critical"
                }
                
                # Get message priority as string
                message_priority_str = priority_mapping.get(redis_message.priority, "low")
                
                # Validate filter priority level
                valid_priorities = ["low", "medium", "high", "critical"]
                if filters.priority_level not in valid_priorities:
                    logger.warning(f"Invalid priority level filter: {filters.priority_level}, treating as lowest priority")
                    filters.priority_level = "low"
                
                # Compare priority levels using enum values
                min_level_value = Priority[filters.priority_level.upper()].value
                message_level_value = redis_message.priority.value
                
                if message_level_value < min_level_value:
                    return False
                    
            except (KeyError, AttributeError) as e:
                logger.warning(f"Error comparing priority levels: {e}, allowing message through")
                # Allow message through if there's an error in priority comparison
                
        return True

    async def _send_to_client(self, client_id: str, message: dict):
        """Send a message to a specific client."""
        if client_id not in self.active_connections:
            return
            
        connection = self.active_connections[client_id]
        
        try:
            await connection.websocket.send_text(json.dumps(message))
            connection.message_count += 1
            self.stats["messages_sent"] += 1
            
        except WebSocketDisconnect:
            await self.disconnect(client_id)
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
            connection.error_count += 1
            self.stats["errors"] += 1
            
            # Disconnect client after too many errors
            if connection.error_count > 5:
                await self.disconnect(client_id)

    async def _broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected clients."""
        for client_id in list(self.active_connections.keys()):
            await self._send_to_client(client_id, message)
    
    def _serialize_filters(self, filters: WebSocketFilter) -> dict:
        """Convert WebSocketFilter to JSON-serializable dict."""
        result = {}
        
        if filters.channels is not None:
            result['channels'] = list(filters.channels)
        if filters.countries is not None:
            result['countries'] = list(filters.countries)
        if filters.keywords is not None:
            result['keywords'] = list(filters.keywords)
        if filters.sentiment_threshold is not None:
            result['sentiment_threshold'] = filters.sentiment_threshold
        if filters.priority_level is not None:
            result['priority_level'] = filters.priority_level
        if filters.message_types is not None:
            result['message_types'] = [msg_type.value for msg_type in filters.message_types]
            
        return result

    def _format_rss_item_for_broadcast(self, news_item: dict, article_id: int = None) -> dict:
        """Format an RSS news item for WebSocket broadcast (preserves existing functionality)."""
        formatted = {
            "type": MessageType.RSS_UPDATE,
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
            # Get tags and format geography tags
            tags = get_article_tags(article_id)
            for tag in tags:
                if tag['category'] == 'geography':
                    tag['name'] = format_tag_name(tag['name'])
            formatted["data"]["tags"] = tags
        
        return formatted


# Utility functions (preserving existing functionality)

def format_tag_name(name: str) -> str:
    """Format tag names with proper capitalization and handle special cases."""
    # Handle special cases with hyphens first
    special_cases = {
        'united-states': 'United States',
        'united-kingdom': 'United Kingdom',
        'europe': 'Europe'  # Single word but commonly used
    }
    
    # Replace hyphens with spaces for processing
    name_normalized = name.lower().replace('-', ' ')
    
    # Check for special cases first
    if name_normalized in special_cases:
        return special_cases[name_normalized]
        
    # For regular cases, capitalize each word
    return ' '.join(word.capitalize() for word in name_normalized.split())


# Global instances

# Enhanced connection manager
manager = EnhancedConnectionManager()

# Backward compatibility functions for existing RSS functionality
async def broadcast_news_update(news_item: dict, article_id: int = None):
    """Broadcast RSS news update to all connected clients (backward compatibility)."""
    await manager.broadcast_rss_update(news_item, article_id)


def format_news_item_for_broadcast(news_item: dict, article_id: int = None) -> dict:
    """Format a news item for broadcast (backward compatibility)."""
    return manager._format_rss_item_for_broadcast(news_item, article_id)