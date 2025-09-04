"""
Redis Pub/Sub Service for Real-Time Telegram Message Distribution.

This module provides a comprehensive Redis-based publish/subscribe system for
distributing Telegram messages in real-time across the GeopolMonitor platform.
Supports high-performance message streaming, channel management, and robust
connection handling.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from config.settings import REDIS_URL


# Configure logger
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Message types for Redis channels."""
    TELEGRAM_MESSAGE = "telegram_message"
    CHANNEL_UPDATE = "channel_update"
    SYSTEM_EVENT = "system_event"
    HEALTH_CHECK = "health_check"


class Priority(Enum):
    """Message priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RedisMessage:
    """Standardized message format for Redis Pub/Sub."""
    message_type: str
    priority: int
    timestamp: float
    source: str
    channel_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return json.dumps(asdict(self), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RedisMessage':
        """Deserialize message from JSON string."""
        data = json.loads(json_str)
        return cls(**data)
    
    @classmethod
    def create_telegram_message(
        cls,
        channel_id: str,
        message_data: Dict[str, Any],
        priority: Priority = Priority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'RedisMessage':
        """Create a Telegram message for Redis distribution."""
        return cls(
            message_type=MessageType.TELEGRAM_MESSAGE.value,
            priority=priority.value,
            timestamp=time.time(),
            source="telethon_client",
            channel_id=channel_id,
            data=message_data,
            metadata=metadata or {}
        )


class RedisConnectionManager:
    """Manages Redis connections with auto-reconnection and health monitoring."""
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 60.0
        self.health_check_interval = 30.0
        self._health_check_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self.connection_stats = {
            "total_connections": 0,
            "failed_connections": 0,
            "reconnections": 0,
            "last_connected": None,
            "last_error": None
        }
    
    async def connect(self) -> bool:
        """Establish Redis connection with error handling."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            
            self.is_connected = True
            self.reconnect_attempts = 0
            self.connection_stats["total_connections"] += 1
            self.connection_stats["last_connected"] = datetime.now(timezone.utc).isoformat()
            
            logger.info("Redis connection established successfully")
            return True
            
        except Exception as e:
            self.is_connected = False
            self.connection_stats["failed_connections"] += 1
            self.connection_stats["last_error"] = str(e)
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Close Redis connection gracefully."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
        
        self.is_connected = False
        logger.info("Redis connection closed")
    
    async def reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            return False
        
        self.reconnect_attempts += 1
        delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)), self.max_reconnect_delay)
        
        logger.info(f"Attempting Redis reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s")
        await asyncio.sleep(delay)
        
        if await self.connect():
            self.connection_stats["reconnections"] += 1
            return True
        
        return False
    
    async def ensure_connection(self) -> bool:
        """Ensure Redis connection is active, reconnect if needed."""
        if not self.is_connected or not self.redis_client:
            return await self.connect()
        
        try:
            await self.redis_client.ping()
            return True
        except Exception:
            logger.warning("Redis connection lost, attempting to reconnect...")
            self.is_connected = False
            return await self.reconnect()
    
    async def start_health_monitoring(self):
        """Start background health check monitoring."""
        if self._health_check_task:
            return
        
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Redis health monitoring started")
    
    async def _health_check_loop(self):
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if self.redis_client and self.is_connected:
                    try:
                        await self.redis_client.ping()
                    except Exception:
                        logger.warning("Health check failed, connection lost")
                        self.is_connected = False
                        # Guard against spawning duplicate reconnect tasks
                        if not self._reconnect_task or self._reconnect_task.done():
                            self._reconnect_task = asyncio.create_task(self._reconnect_task_wrapper())
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _reconnect_task_wrapper(self) -> None:
        """Wrapper to manage reconnect task lifecycle and prevent duplicates."""
        try:
            await self.reconnect()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Reconnect task error: {e}")
        finally:
            # Allow future reconnect attempts to be scheduled
            self._reconnect_task = None


class RedisPublisher:
    """High-performance Redis message publisher."""
    
    def __init__(self, connection_manager: RedisConnectionManager):
        self.connection_manager = connection_manager
        self.publish_stats = {
            "total_published": 0,
            "failed_publishes": 0,
            "channels_used": [],
            "last_publish": None
        }
    
    async def publish_message(
        self,
        channel: str,
        message: RedisMessage,
        retry_attempts: int = 3
    ) -> bool:
        """Publish a message to a Redis channel with retry logic."""
        for attempt in range(retry_attempts):
            try:
                if not await self.connection_manager.ensure_connection():
                    if attempt == retry_attempts - 1:
                        logger.error(f"Failed to publish to {channel}: No Redis connection")
                        self.publish_stats["failed_publishes"] += 1
                        return False
                    continue
                
                result = await self.connection_manager.redis_client.publish(
                    channel,
                    message.to_json()
                )
                
                # Update stats
                self.publish_stats["total_published"] += 1
                if channel not in self.publish_stats["channels_used"]:
                    self.publish_stats["channels_used"].append(channel)
                self.publish_stats["last_publish"] = datetime.now(timezone.utc).isoformat()
                
                logger.debug(f"Published message to {channel} (subscribers: {result})")
                return True
                
            except Exception as e:
                logger.warning(f"Publish attempt {attempt + 1} failed: {e}")
                if attempt == retry_attempts - 1:
                    self.publish_stats["failed_publishes"] += 1
                    logger.error(f"Failed to publish to {channel} after {retry_attempts} attempts")
                    return False
                await asyncio.sleep(0.5 * (attempt + 1))  # Progressive delay
        
        return False
    
    async def publish_telegram_message(
        self,
        channel_id: str,
        message_data: Dict[str, Any],
        priority: Priority = Priority.MEDIUM,
        custom_channel: Optional[str] = None
    ) -> bool:
        """Publish a Telegram message with automatic channel routing."""
        redis_message = RedisMessage.create_telegram_message(
            channel_id=channel_id,
            message_data=message_data,
            priority=priority
        )
        
        # Determine Redis channel
        redis_channel = custom_channel or f"telegram:messages:{channel_id}"
        
        return await self.publish_message(redis_channel, redis_message)
    
    async def broadcast_system_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        priority: Priority = Priority.HIGH
    ) -> bool:
        """Broadcast system events to all subscribers."""
        message = RedisMessage(
            message_type=MessageType.SYSTEM_EVENT.value,
            priority=priority.value,
            timestamp=time.time(),
            source="redis_pubsub_service",
            data={"event_type": event_type, **event_data}
        )
        
        return await self.publish_message("system:events", message)


class RedisSubscriber:
    """High-performance Redis message subscriber with pattern support."""
    
    def __init__(self, connection_manager: RedisConnectionManager):
        self.connection_manager = connection_manager
        self.subscriptions: Dict[str, Callable] = {}
        self.pattern_subscriptions: Dict[str, Callable] = {}
        self.pubsub: Optional[redis.client.PubSub] = None
        self.is_listening = False
        self._listen_task: Optional[asyncio.Task] = None
        self.subscription_stats = {
            "total_received": 0,
            "messages_processed": 0,
            "processing_errors": 0,
            "subscriptions": [],
            "last_message": None
        }
    
    async def subscribe(self, channel: str, handler: Callable[[RedisMessage], None]):
        """Subscribe to a specific Redis channel."""
        self.subscriptions[channel] = handler
        self.subscription_stats["subscriptions"].append({
            "channel": channel,
            "type": "exact",
            "subscribed_at": datetime.now(timezone.utc).isoformat()
        })
        
        if self.is_listening and self.pubsub:
            await self._update_subscriptions()
        
        logger.info(f"Subscribed to channel: {channel}")
    
    async def subscribe_pattern(self, pattern: str, handler: Callable[[str, RedisMessage], None]):
        """Subscribe to channels matching a pattern."""
        self.pattern_subscriptions[pattern] = handler
        self.subscription_stats["subscriptions"].append({
            "pattern": pattern,
            "type": "pattern",
            "subscribed_at": datetime.now(timezone.utc).isoformat()
        })
        
        if self.is_listening and self.pubsub:
            await self._update_subscriptions()
        
        logger.info(f"Subscribed to pattern: {pattern}")
    
    async def unsubscribe(self, channel: str):
        """Unsubscribe from a specific channel."""
        if channel in self.subscriptions:
            del self.subscriptions[channel]
            if self.pubsub:
                await self.pubsub.unsubscribe(channel)
            logger.info(f"Unsubscribed from channel: {channel}")
    
    async def start_listening(self):
        """Start listening for messages."""
        if self.is_listening:
            return
        
        connected = await self.connection_manager.ensure_connection()
        if not connected or not self.connection_manager.redis_client or not self.connection_manager.is_connected:
            logger.error("Cannot start Redis subscriber: Redis client is not connected")
            return
        self.pubsub = self.connection_manager.redis_client.pubsub()
        
        # Only start listening task if we have subscriptions
        if self.subscriptions or self.pattern_subscriptions:
            await self._update_subscriptions()
        
        self.is_listening = True
        self._listen_task = asyncio.create_task(self._listen_loop())
        
        logger.info("Redis subscriber started listening")
    
    async def stop_listening(self):
        """Stop listening for messages."""
        self.is_listening = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.close()
            self.pubsub = None
        
        logger.info("Redis subscriber stopped listening")
    
    async def _update_subscriptions(self):
        """Update active subscriptions."""
        if not self.pubsub:
            return
        
        # Subscribe to exact channels
        if self.subscriptions:
            await self.pubsub.subscribe(*self.subscriptions.keys())
        
        # Subscribe to patterns
        if self.pattern_subscriptions:
            await self.pubsub.psubscribe(*self.pattern_subscriptions.keys())
    
    async def _listen_loop(self):
        """Main message listening loop."""
        while self.is_listening:
            try:
                message = await self.pubsub.get_message(timeout=1.0)
                
                if message is None:
                    continue
                
                if message['type'] not in ['message', 'pmessage']:
                    continue
                
                self.subscription_stats["total_received"] += 1
                
                try:
                    redis_message = RedisMessage.from_json(message['data'])
                    self.subscription_stats["last_message"] = datetime.now(timezone.utc).isoformat()
                    
                    # Handle exact channel subscriptions
                    if message['type'] == 'message':
                        channel = message['channel']
                        if channel in self.subscriptions:
                            await self._handle_message(self.subscriptions[channel], redis_message)
                    
                    # Handle pattern subscriptions
                    elif message['type'] == 'pmessage':
                        pattern = message['pattern']
                        channel = message['channel']
                        if pattern in self.pattern_subscriptions:
                            await self._handle_pattern_message(
                                self.pattern_subscriptions[pattern],
                                channel,
                                redis_message
                            )
                    
                    self.subscription_stats["messages_processed"] += 1
                    
                except Exception as e:
                    self.subscription_stats["processing_errors"] += 1
                    logger.error(f"Error processing message: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Listen loop error: {e}")
                await asyncio.sleep(1)
    
    async def _handle_message(self, handler: Callable, message: RedisMessage):
        """Handle message for exact channel subscription."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)
        except Exception as e:
            logger.error(f"Message handler error: {e}")
    
    async def _handle_pattern_message(
        self,
        handler: Callable,
        channel: str,
        message: RedisMessage
    ):
        """Handle message for pattern subscription."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(channel, message)
            else:
                handler(channel, message)
        except Exception as e:
            logger.error(f"Pattern message handler error: {e}")


class RedisPubSubService:
    """Main Redis Pub/Sub service combining all components."""
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.connection_manager = RedisConnectionManager(redis_url)
        self.publisher = RedisPublisher(self.connection_manager)
        self.subscriber = RedisSubscriber(self.connection_manager)
        self.is_running = False
    
    async def start(self):
        """Start the Redis Pub/Sub service."""
        if self.is_running:
            return
        
        # Connect to Redis
        if not await self.connection_manager.connect():
            raise ConnectionError("Failed to connect to Redis")
        
        # Start health monitoring
        await self.connection_manager.start_health_monitoring()
        
        # Start subscriber
        await self.subscriber.start_listening()
        
        self.is_running = True
        logger.info("Redis Pub/Sub service started successfully")
    
    async def stop(self):
        """Stop the Redis Pub/Sub service."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop subscriber
        await self.subscriber.stop_listening()
        
        # Disconnect from Redis
        await self.connection_manager.disconnect()
        
        logger.info("Redis Pub/Sub service stopped")
    
    async def publish_telegram_message(
        self,
        channel_id: str,
        message_data: Dict[str, Any],
        priority: Priority = Priority.MEDIUM
    ) -> bool:
        """Publish a Telegram message."""
        return await self.publisher.publish_telegram_message(
            channel_id, message_data, priority
        )
    
    async def subscribe_to_channel(
        self,
        channel: str,
        handler: Callable[[RedisMessage], None]
    ):
        """Subscribe to a specific Redis channel."""
        await self.subscriber.subscribe(channel, handler)
    
    async def subscribe_to_pattern(
        self,
        pattern: str,
        handler: Callable[[str, RedisMessage], None]
    ):
        """Subscribe to channels matching a pattern."""
        await self.subscriber.subscribe_pattern(pattern, handler)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        return {
            "connection": {
                "is_connected": self.connection_manager.is_connected,
                "stats": self.connection_manager.connection_stats
            },
            "publisher": {
                "stats": {
                    **self.publisher.publish_stats,
                    "channels_used": list(self.publisher.publish_stats["channels_used"])
                }
            },
            "subscriber": {
                "is_listening": self.subscriber.is_listening,
                "stats": self.subscriber.subscription_stats
            },
            "service": {
                "is_running": self.is_running
            }
        }


# Global service instance
redis_service = RedisPubSubService()


# Convenience functions for easy integration
async def publish_telegram_message(
    channel_id: str,
    message_data: Dict[str, Any],
    priority: Priority = Priority.MEDIUM
) -> bool:
    """Quick publish function for Telegram messages."""
    return await redis_service.publish_telegram_message(channel_id, message_data, priority)


async def subscribe_to_telegram_messages(
    channel_id: str,
    handler: Callable[[RedisMessage], None]
):
    """Quick subscribe function for Telegram messages from specific channel."""
    redis_channel = f"telegram:messages:{channel_id}"
    await redis_service.subscribe_to_channel(redis_channel, handler)


async def subscribe_to_all_telegram_messages(
    handler: Callable[[str, RedisMessage], None]
):
    """Quick subscribe function for all Telegram messages."""
    await redis_service.subscribe_to_pattern("telegram:messages:*", handler) 