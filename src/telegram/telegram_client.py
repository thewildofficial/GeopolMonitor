"""
Telegram Client Infrastructure for GeopolMonitor

This module provides a robust Telegram client for monitoring geopolitical channels
with proper rate limiting, connection management, and error handling.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import redis
import json

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (
    FloodWait, 
    RPCError, 
    AuthKeyUnregistered, 
    UserDeactivated,
    SessionPasswordNeeded
)

from config.settings import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_SESSION_NAME,
    REDIS_URL,
    TELEGRAM_RATE_LIMIT_DELAY
)


@dataclass
class ChannelInfo:
    """Information about a monitored Telegram channel"""
    channel_id: str
    username: str
    title: str
    subscriber_count: int
    credibility_tier: str
    region: str
    is_active: bool = True
    last_message_time: Optional[datetime] = None
    
    
@dataclass
class TelegramMessage:
    """Processed Telegram message for the monitoring system"""
    message_id: int
    channel_id: str
    channel_username: str
    text: str
    date: datetime
    media_type: Optional[str] = None
    forward_from: Optional[str] = None
    views: Optional[int] = None
    urgency_level: str = "normal"  # flash, breaking, important, normal
    geographic_tags: List[str] = None
    

class RateLimiter:
    """Rate limiter for Telegram API compliance"""
    
    def __init__(self, calls_per_second: float = 1.0):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0
        
    async def wait_if_needed(self):
        """Wait if necessary to comply with rate limits"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_interval:
            wait_time = self.min_interval - time_since_last_call
            await asyncio.sleep(wait_time)
            
        self.last_call_time = time.time()


class TelegramMonitorClient:
    """
    Main Telegram monitoring client with enterprise-grade reliability features
    """
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.redis_client: Optional[redis.Redis] = None
        self.rate_limiter = RateLimiter(calls_per_second=0.5)  # Conservative rate limiting
        self.monitored_channels: Dict[str, ChannelInfo] = {}
        self.message_handlers: List[Callable] = []
        self.is_running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.logger = logging.getLogger(__name__)
        
        # Statistics tracking
        self.stats = {
            'messages_processed': 0,
            'reconnections': 0,
            'errors_handled': 0,
            'start_time': None
        }
        
    async def initialize(self) -> bool:
        """Initialize the Telegram client and Redis connection"""
        try:
            # Initialize Redis for message buffering
            self.redis_client = redis.from_url(
                REDIS_URL, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test Redis connection
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.ping
            )
            self.logger.info("Redis connection established")
            
            # Initialize Pyrogram client with proper session directory
            from pathlib import Path
            session_dir = Path("data/telegram_sessions")
            session_dir.mkdir(parents=True, exist_ok=True)
            
            self.client = Client(
                name=TELEGRAM_SESSION_NAME,
                api_id=TELEGRAM_API_ID,
                api_hash=TELEGRAM_API_HASH,
                workdir=str(session_dir)
            )
            
            # Set up message handlers
            self._setup_handlers()
            
            self.logger.info("Telegram client initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram client: {e}")
            return False
    
    def _setup_handlers(self):
        """Set up Pyrogram message handlers"""
        
        @self.client.on_message(filters.channel & ~filters.service)
        async def handle_channel_message(client: Client, message: Message):
            """Handle incoming channel messages"""
            try:
                await self._process_message(message)
            except Exception as e:
                self.logger.error(f"Error processing message {message.id}: {e}")
                self.stats['errors_handled'] += 1
                
    async def _process_message(self, message: Message):
        """Process a received Telegram message"""
        try:
            # Rate limiting
            await self.rate_limiter.wait_if_needed()
            
            # Convert to our message format
            telegram_msg = TelegramMessage(
                message_id=message.id,
                channel_id=str(message.chat.id),
                channel_username=message.chat.username or "unknown",
                text=message.text or message.caption or "",
                date=message.date,
                media_type=self._get_media_type(message),
                forward_from=self._get_forward_from(message),
                views=getattr(message, 'views', None)
            )
            
            # Buffer message in Redis for processing
            await self._buffer_message(telegram_msg)
            
            # Call registered message handlers
            for handler in self.message_handlers:
                try:
                    await handler(telegram_msg)
                except Exception as e:
                    self.logger.error(f"Message handler error: {e}")
                    
            self.stats['messages_processed'] += 1
            self.logger.debug(f"Processed message {message.id} from {telegram_msg.channel_username}")
            
        except Exception as e:
            self.logger.error(f"Error in _process_message: {e}")
            self.stats['errors_handled'] += 1
    
    def _get_media_type(self, message: Message) -> Optional[str]:
        """Determine the media type of a message"""
        if message.photo:
            return "photo"
        elif message.video:
            return "video"
        elif message.document:
            return "document"
        elif message.voice:
            return "voice"
        elif message.audio:
            return "audio"
        elif message.sticker:
            return "sticker"
        return None
    
    def _get_forward_from(self, message: Message) -> Optional[str]:
        """Get the forward source if message is forwarded"""
        if message.forward_from_chat:
            return message.forward_from_chat.username or str(message.forward_from_chat.id)
        elif message.forward_from:
            return message.forward_from.username or str(message.forward_from.id)
        return None
    
    async def _buffer_message(self, telegram_msg: TelegramMessage):
        """Buffer message in Redis for processing pipeline"""
        try:
            message_data = {
                'message_id': telegram_msg.message_id,
                'channel_id': telegram_msg.channel_id,
                'channel_username': telegram_msg.channel_username,
                'text': telegram_msg.text,
                'date': telegram_msg.date.isoformat(),
                'media_type': telegram_msg.media_type,
                'forward_from': telegram_msg.forward_from,
                'views': telegram_msg.views,
                'processed_at': datetime.utcnow().isoformat()
            }
            
            # Push to Redis queue for processing
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.lpush,
                'telegram_messages',
                json.dumps(message_data)
            )
            
            # Keep only last 10000 messages in buffer
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.ltrim,
                'telegram_messages',
                0, 9999
            )
            
        except Exception as e:
            self.logger.error(f"Error buffering message: {e}")
    
    async def add_channel(self, channel_identifier: str, credibility_tier: str = "emerging", region: str = "global") -> bool:
        """Add a channel to monitoring list"""
        try:
            await self.rate_limiter.wait_if_needed()
            
            # Get channel info
            chat = await self.client.get_chat(channel_identifier)
            
            channel_info = ChannelInfo(
                channel_id=str(chat.id),
                username=chat.username or channel_identifier,
                title=chat.title or "Unknown",
                subscriber_count=getattr(chat, 'members_count', 0),
                credibility_tier=credibility_tier,
                region=region
            )
            
            self.monitored_channels[str(chat.id)] = channel_info
            
            # Join the channel for monitoring
            await self.client.join_chat(channel_identifier)
            
            self.logger.info(f"Added channel {channel_info.username} ({channel_info.title}) to monitoring")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding channel {channel_identifier}: {e}")
            return False
    
    async def remove_channel(self, channel_identifier: str) -> bool:
        """Remove a channel from monitoring"""
        try:
            # Leave the channel
            await self.client.leave_chat(channel_identifier)
            
            # Remove from monitoring list
            for channel_id, info in list(self.monitored_channels.items()):
                if info.username == channel_identifier or channel_id == channel_identifier:
                    del self.monitored_channels[channel_id]
                    self.logger.info(f"Removed channel {info.username} from monitoring")
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing channel {channel_identifier}: {e}")
            return False
    
    def add_message_handler(self, handler: Callable):
        """Add a custom message handler function"""
        self.message_handlers.append(handler)
    
    async def start(self) -> bool:
        """Start the Telegram monitoring client"""
        try:
            if not await self.initialize():
                return False
                
            await self.client.start()
            self.is_running = True
            self.stats['start_time'] = datetime.utcnow()
            self.logger.info("Telegram monitoring client started successfully")
            
            # Keep the client running
            await self._keep_alive()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting Telegram client: {e}")
            return False
    
    async def stop(self):
        """Stop the Telegram monitoring client"""
        try:
            self.is_running = False
            if self.client:
                await self.client.stop()
            if self.redis_client:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_client.close
                )
            self.logger.info("Telegram monitoring client stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping Telegram client: {e}")
    
    async def _keep_alive(self):
        """Keep the client alive and handle reconnections"""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Health check every 30 seconds
                
                # Check if client is still connected
                if not self.client.is_connected:
                    self.logger.warning("Client disconnected, attempting reconnection...")
                    await self._reconnect()
                    
            except Exception as e:
                self.logger.error(f"Error in keep_alive: {e}")
                await self._reconnect()
    
    async def _reconnect(self):
        """Handle reconnection with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error("Max reconnection attempts reached, stopping client")
            self.is_running = False
            return
            
        self.reconnect_attempts += 1
        backoff_time = min(2 ** self.reconnect_attempts, 300)  # Max 5 minutes
        
        self.logger.info(f"Reconnection attempt {self.reconnect_attempts}, waiting {backoff_time}s")
        await asyncio.sleep(backoff_time)
        
        try:
            if self.client:
                await self.client.stop()
            await self.client.start()
            self.reconnect_attempts = 0  # Reset on successful reconnection
            self.stats['reconnections'] += 1
            self.logger.info("Reconnection successful")
            
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        stats = self.stats.copy()
        stats['monitored_channels_count'] = len(self.monitored_channels)
        stats['is_running'] = self.is_running
        stats['reconnect_attempts'] = self.reconnect_attempts
        
        if self.stats['start_time']:
            uptime = datetime.utcnow() - self.stats['start_time']
            stats['uptime_seconds'] = uptime.total_seconds()
            
        return stats
    
    def get_monitored_channels(self) -> List[ChannelInfo]:
        """Get list of currently monitored channels"""
        return list(self.monitored_channels.values())


# Global client instance
telegram_monitor = TelegramMonitorClient() 