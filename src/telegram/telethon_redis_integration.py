"""
Telethon-Redis Integration Module.

This module provides seamless integration between the TelethonMonitorClient
and Redis Pub/Sub service for real-time message distribution. Handles message
routing, channel management, and high-performance streaming of Telegram data.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

from telethon import events
from telethon.tl.types import Message, Channel, User

from .telethon_client import TelethonMonitorClient
from ..core.services.redis_pubsub import (
    RedisPubSubService,
    Priority,
    publish_telegram_message,
    subscribe_to_all_telegram_messages,
    redis_service
)
from ..database.telegram_db import (
    init_telegram_db, 
    get_telegram_session, 
    close_telegram_db,
    save_telegram_message,
    save_telegram_channel
)
from ..database.models.telegram_models import TelegramMessage, TelegramChannel
from ..utils.ai import ContentProcessor


logger = logging.getLogger(__name__)


class TelethonRedisIntegration:
    """
    Integrates Telethon client with Redis Pub/Sub for real-time message streaming.
    
    Features:
    - Real-time message capture and distribution
    - Channel management and metadata enrichment
    - Message filtering and prioritization
    - Database persistence with Redis streaming
    - Performance monitoring and statistics
    """
    
    def __init__(
        self,
        telethon_client: TelethonMonitorClient,
        redis_service: RedisPubSubService,
        enable_ai_filtering: bool = True,
        relevance_threshold: float = 0.3
    ):
        self.telethon_client = telethon_client
        self.redis_service = redis_service
        self.database_initialized = False
        
        # AI processing configuration
        self.enable_ai_filtering = enable_ai_filtering
        self.relevance_threshold = relevance_threshold
        self.ai_processor = ContentProcessor() if enable_ai_filtering else None
        
        # State management
        self.is_running = False
        self.monitored_channels: Dict[str, Dict] = {}  # channel_id -> metadata
        self.message_handlers: List[Callable] = []
        
        # Statistics
        self.stats = {
            "messages_processed": 0,
            "messages_published": 0,
            "messages_filtered_out": 0,
            "ai_analyses_performed": 0,
            "channels_monitored": 0,
            "errors": 0,
            "start_time": None,
            "last_message_time": None
        }
        
        # Message filtering
        self.min_message_length = 10  # Minimum characters for processing
        self.priority_keywords = [
            "breaking", "urgent", "alert", "developing", "confirmed",
            "exclusive", "first", "just in", "now", "live"
        ]
        
        logger.info(f"Telethon-Redis integration initialized (AI filtering: {enable_ai_filtering}, threshold: {relevance_threshold})")
    
    async def start(self):
        """Start the integration service."""
        if self.is_running:
            logger.warning("Integration service already running")
            return
        
        try:
            # Start Redis service
            if not self.redis_service.is_running:
                await self.redis_service.start()
                logger.info("Redis Pub/Sub service started")
            
            # Start Telethon client with monitoring
            if not (self.telethon_client.client and self.telethon_client.client.is_connected()):
                await self.telethon_client.start_with_monitoring()
                logger.info("Telethon client started with monitoring")
            
            # Set up message event handler
            await self._setup_message_handlers()
            
            # Initialize database connection
            await init_telegram_db()
            self.database_initialized = True
            logger.info("Database connection established")
            
            self.is_running = True
            self.stats["start_time"] = datetime.now(timezone.utc)
            
            logger.info("🚀 Telethon-Redis integration started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start integration service: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the integration service gracefully."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        try:
            # Remove message handlers
            self.telethon_client.client.remove_event_handler(self._handle_telegram_message)
            
            # Stop Telethon client
            if self.telethon_client.client and self.telethon_client.client.is_connected():
                await self.telethon_client.stop()
            
            # Disconnect database
            if self.database_initialized:
                await close_telegram_db()
                self.database_initialized = False
            
            logger.info("🛑 Telethon-Redis integration stopped")
            
        except Exception as e:
            logger.error(f"Error stopping integration service: {e}")
    
    async def add_channel_to_monitor(
        self, 
        channel_identifier: str,
        priority: Priority = Priority.MEDIUM,
        keywords: Optional[List[str]] = None
    ) -> bool:
        """Add a channel to monitoring with optional filtering."""
        try:
            # Get channel info from Telethon
            channel_info = await self.telethon_client.get_channel_info(channel_identifier)
            
            if not channel_info:
                logger.error(f"Could not get info for channel: {channel_identifier}")
                return False
            
            channel_id = str(channel_info.get('id'))
            
            # Store channel metadata
            self.monitored_channels[channel_id] = {
                "identifier": channel_identifier,
                "title": channel_info.get('title', 'Unknown'),
                "username": channel_info.get('username'),
                "priority": priority,
                "keywords": keywords or [],
                "added_at": datetime.now(timezone.utc).isoformat(),
                "message_count": 0
            }
            
            # Add to Telethon monitoring
            await self.telethon_client.add_channel(channel_identifier)
            
            # Store in database
            await self._store_channel_metadata(channel_info, priority)
            
            self.stats["channels_monitored"] = len(self.monitored_channels)
            
            logger.info(f"✅ Added channel to monitoring: {channel_info.get('title')} ({channel_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add channel {channel_identifier}: {e}")
            self.stats["errors"] += 1
            return False
    
    async def remove_channel_from_monitor(self, channel_identifier: str) -> bool:
        """Remove a channel from monitoring."""
        try:
            # Get channel ID
            channel_info = await self.telethon_client.get_channel_info(channel_identifier)
            if channel_info:
                channel_id = str(channel_info.get('id'))
                if channel_id in self.monitored_channels:
                    del self.monitored_channels[channel_id]
            
            # Remove from Telethon
            await self.telethon_client.remove_channel(channel_identifier)
            
            self.stats["channels_monitored"] = len(self.monitored_channels)
            
            logger.info(f"✅ Removed channel from monitoring: {channel_identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove channel {channel_identifier}: {e}")
            self.stats["errors"] += 1
            return False
    
    async def _setup_message_handlers(self):
        """Set up Telethon event handlers for message processing."""
        @self.telethon_client.client.on(events.NewMessage)
        async def message_handler(event):
            await self._handle_telegram_message(event)
        
        logger.info("Message event handlers configured")
    
    async def _handle_telegram_message(self, event):
        """Process incoming Telegram messages and distribute via Redis."""
        try:
            message = event.message
            
            # Extract basic message data
            message_data = await self._extract_message_data(message, event)
            
            if not message_data:
                return
            
            channel_id = str(message_data.get('channel_id'))
            
            # Check if we're monitoring this channel
            if channel_id not in self.monitored_channels:
                return
            
            channel_metadata = self.monitored_channels[channel_id]
            
            # Apply message filtering
            if not self._should_process_message(message_data, channel_metadata):
                return
            
            # Determine message priority
            priority = self._calculate_message_priority(message_data, channel_metadata)
            
            # Enrich message with metadata and relevance analysis
            enriched_data = await self._enrich_message_data(message_data, channel_metadata)
            
            # Apply relevance filtering
            if not enriched_data.get("is_relevant", False):
                self.stats["messages_filtered_out"] += 1
                logger.debug(f"🚫 Filtered out irrelevant message (score: {enriched_data.get('relevance_score', 0.0):.2f})")
                
                # Still store in database for analysis, but don't publish
                asyncio.create_task(self._store_message_data(enriched_data))
                return
            
            # Publish relevant messages to Redis
            success = await publish_telegram_message(
                channel_id,
                enriched_data,
                priority
            )
            
            if success:
                self.stats["messages_published"] += 1
                relevance_score = enriched_data.get('relevance_score', 0.0)
                logger.info(f"📤 Published relevant message from {enriched_data.get('channel_title')} (score: {relevance_score:.2f}, priority: {priority.name})")
            else:
                logger.warning(f"Failed to publish message from channel {channel_id}")
                self.stats["errors"] += 1
            
            # Store in database (async, non-blocking)
            asyncio.create_task(self._store_message_data(enriched_data))
            
            # Update statistics
            self.stats["messages_processed"] += 1
            self.stats["last_message_time"] = datetime.now(timezone.utc).isoformat()
            channel_metadata["message_count"] += 1
            
        except Exception as e:
            logger.error(f"Error handling Telegram message: {e}")
            self.stats["errors"] += 1
    
    async def _extract_message_data(self, message: Message, event) -> Optional[Dict[str, Any]]:
        """Extract relevant data from Telegram message."""
        try:
            # Skip empty messages
            if not message.text and not message.media:
                return None
            
            # Get sender information
            sender = await event.get_sender()
            sender_data = {}
            
            if isinstance(sender, User):
                sender_data = {
                    "user_id": sender.id,
                    "username": sender.username,
                    "first_name": sender.first_name,
                    "last_name": sender.last_name,
                    "is_bot": sender.bot
                }
            elif isinstance(sender, Channel):
                sender_data = {
                    "channel_id": sender.id,
                    "title": sender.title,
                    "username": sender.username
                }
            
            # Get chat information
            chat = await event.get_chat()
            chat_data = {
                "chat_id": chat.id,
                "chat_title": getattr(chat, 'title', None),
                "chat_username": getattr(chat, 'username', None)
            }
            
            # Extract message content
            message_data = {
                "message_id": message.id,
                "channel_id": chat.id,
                "text": message.text or "",
                "date": message.date.isoformat() if message.date else None,
                "edit_date": message.edit_date.isoformat() if message.edit_date else None,
                "views": getattr(message, 'views', None),
                "forwards": getattr(message, 'forwards', None),
                "replies": getattr(message, 'replies', {}).messages if hasattr(message, 'replies') and message.replies else 0,
                "is_reply": message.reply_to is not None,
                "reply_to_message_id": message.reply_to.reply_to_msg_id if message.reply_to else None,
                "has_media": message.media is not None,
                "media_type": type(message.media).__name__ if message.media else None,
                "sender": sender_data,
                "chat": chat_data,
                "raw_data": {
                    "grouped_id": getattr(message, 'grouped_id', None),
                    "via_bot_id": getattr(message, 'via_bot_id', None),
                    "restriction_reason": getattr(message, 'restriction_reason', None)
                }
            }
            
            return message_data
            
        except Exception as e:
            logger.error(f"Error extracting message data: {e}")
            return None
    
    def _should_process_message(self, message_data: Dict[str, Any], channel_metadata: Dict) -> bool:
        """Determine if a message should be processed based on filters."""
        
        # Skip empty or very short messages
        text = message_data.get('text', '').strip()
        if len(text) < self.min_message_length:
            return False
        
        # Check channel-specific keywords
        keywords = channel_metadata.get('keywords', [])
        if keywords:
            text_lower = text.lower()
            if not any(keyword.lower() in text_lower for keyword in keywords):
                return False
        
        # Skip bot messages (optional filter)
        sender = message_data.get('sender', {})
        if sender.get('is_bot', False):
            return False
        
        return True
    
    def _calculate_message_priority(self, message_data: Dict[str, Any], channel_metadata: Dict) -> Priority:
        """Calculate message priority based on content and channel settings."""
        
        # Start with channel default priority
        priority = channel_metadata.get('priority', Priority.MEDIUM)
        
        # Check for priority keywords
        text = message_data.get('text', '').lower()
        if any(keyword in text for keyword in self.priority_keywords):
            # Boost priority for breaking news
            if priority == Priority.LOW:
                priority = Priority.MEDIUM
            elif priority == Priority.MEDIUM:
                priority = Priority.HIGH
            elif priority == Priority.HIGH:
                priority = Priority.CRITICAL
        
        # High engagement boost
        views = message_data.get('views', 0) or 0
        forwards = message_data.get('forwards', 0) or 0
        
        if views > 10000 or forwards > 100:
            priority = Priority.HIGH
        elif views > 100000 or forwards > 1000:
            priority = Priority.CRITICAL
        
        return priority
    
    async def _enrich_message_data(self, message_data: Dict[str, Any], channel_metadata: Dict) -> Dict[str, Any]:
        """Enrich message data with additional metadata."""
        enriched = message_data.copy()
        
        # Add channel metadata
        enriched.update({
            "channel_title": channel_metadata.get('title'),
            "channel_username": channel_metadata.get('identifier'),
            "channel_priority": channel_metadata.get('priority').name,
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            "integration_version": "1.0.0"
        })
        
        # Add content analysis
        text = message_data.get('text', '')
        enriched["content_analysis"] = {
            "character_count": len(text),
            "word_count": len(text.split()),
            "has_links": "http" in text.lower(),
            "has_mentions": "@" in text,
            "has_hashtags": "#" in text,
            "language_detected": "auto"  # Could integrate language detection
        }
        
        # Add geopolitical relevance analysis
        relevance_analysis = await self._analyze_geopolitical_relevance(text, channel_metadata)
        enriched["relevance_analysis"] = relevance_analysis
        
        # Store relevance score for filtering decisions
        enriched["relevance_score"] = relevance_analysis.get("relevance_score", 0.0)
        enriched["is_relevant"] = relevance_analysis.get("is_relevant", False)
        
        return enriched
    
    async def _analyze_geopolitical_relevance(self, text: str, channel_metadata: Dict) -> Dict[str, Any]:
        """Analyze text for geopolitical relevance using AI or fallback to keywords."""
        
        # Skip analysis for very short messages
        if len(text.strip()) < self.min_message_length:
            return {
                "relevance_score": 0.0,
                "relevance_category": "none",
                "confidence": 1.0,
                "is_relevant": False,
                "method": "length_filter",
                "reasoning": "Message too short for analysis"
            }
        
        # Use AI analysis if enabled and available
        if self.enable_ai_filtering and self.ai_processor:
            try:
                self.stats["ai_analyses_performed"] += 1
                
                # Prepare context information
                channel_context = f"{channel_metadata.get('title', 'Unknown')} ({channel_metadata.get('identifier', 'Unknown')})"
                
                # Get AI analysis
                ai_result = await self.ai_processor.process_telegram_message(
                    message_text=text,
                    analysis_type="relevance",
                    channel_context=channel_context,
                    metadata={"priority": channel_metadata.get('priority', 'medium')}
                )
                
                if ai_result.get("success", False):
                    relevance_score = ai_result.get("relevance_score", 0.0)
                    is_relevant = relevance_score >= self.relevance_threshold
                    
                    return {
                        "relevance_score": relevance_score,
                        "relevance_category": ai_result.get("relevance_category", "unknown"),
                        "confidence": ai_result.get("confidence", 0.0),
                        "primary_topics": ai_result.get("primary_topics", []),
                        "geographic_focus": ai_result.get("geographic_focus", []),
                        "reasoning": ai_result.get("reasoning", ""),
                        "is_relevant": is_relevant,
                        "method": "ai_analysis",
                        "threshold_used": self.relevance_threshold
                    }
                else:
                    logger.warning(f"AI analysis failed: {ai_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Error in AI relevance analysis: {e}")
                self.stats["errors"] += 1
        
        # Fallback to keyword-based analysis
        return await self._keyword_based_relevance(text)
    
    async def _keyword_based_relevance(self, text: str) -> Dict[str, Any]:
        """Fallback keyword-based relevance analysis."""
        geopolitical_keywords = {
            "conflicts": ["war", "conflict", "battle", "invasion", "attack", "military", "combat", "strike"],
            "diplomacy": ["treaty", "agreement", "summit", "negotiation", "ambassador", "diplomatic", "talks"],
            "economics": ["sanctions", "trade", "tariff", "economy", "gdp", "inflation", "economic", "financial"],
            "regions": ["ukraine", "russia", "china", "usa", "middle east", "nato", "eu", "europe", "asia"],
            "security": ["terrorism", "cyber", "intelligence", "security", "threat", "espionage"],
            "politics": ["government", "election", "policy", "parliament", "congress", "minister", "president"]
        }
        
        text_lower = text.lower()
        category_scores = {}
        total_matches = 0
        
        for category, keywords in geopolitical_keywords.items():
            matches = [kw for kw in keywords if kw in text_lower]
            category_scores[category] = {
                "score": len(matches),
                "keywords_found": matches
            }
            total_matches += len(matches)
        
        # Calculate relevance score (normalize to 0-1 scale)
        relevance_score = min(total_matches * 0.15, 1.0)  # Each keyword match adds 0.15
        
        # Determine category
        if relevance_score >= 0.7:
            category = "high"
        elif relevance_score >= 0.4:
            category = "medium"
        elif relevance_score >= 0.1:
            category = "low"
        else:
            category = "none"
        
        return {
            "relevance_score": relevance_score,
            "relevance_category": category,
            "confidence": 0.6,  # Lower confidence for keyword-based
            "category_breakdown": category_scores,
            "total_keyword_matches": total_matches,
            "is_relevant": relevance_score >= self.relevance_threshold,
            "method": "keyword_fallback",
            "threshold_used": self.relevance_threshold,
            "reasoning": f"Found {total_matches} geopolitical keywords"
        }
    
    async def _store_channel_metadata(self, channel_info: Dict, priority: Priority):
        """Store channel metadata in database."""
        try:
            # Prepare channel data for database storage
            channel_data = {
                'id': channel_info.get('id'),
                'username': channel_info.get('username'),
                'title': channel_info.get('title', 'Unknown Channel'),
                'description': channel_info.get('about') or channel_info.get('description'),
                'participants_count': channel_info.get('participants_count'),
                'is_verified': channel_info.get('verified', False),
                'is_scam': channel_info.get('scam', False),
                'is_fake': channel_info.get('fake', False)
            }
            
            # Save to database
            saved_channel = await save_telegram_channel(channel_data)
            
            if saved_channel:
                logger.debug(f"✅ Stored channel metadata for {channel_info.get('title')} (ID: {channel_info.get('id')})")
            else:
                logger.warning(f"Failed to store channel metadata for {channel_info.get('title')}")
                
        except Exception as e:
            logger.error(f"Failed to store channel metadata for {channel_info.get('title', 'Unknown')}: {e}")
            self.stats["errors"] += 1
    
    async def _store_message_data(self, message_data: Dict[str, Any]):
        """Store message data in database asynchronously."""
        try:
            # Prepare message data for database storage
            db_message_data = {
                'message_id': message_data.get('message_id'),
                'channel_id': message_data.get('channel_id'),
                'text': message_data.get('text', ''),
                'raw_text': message_data.get('raw_text') or message_data.get('text', ''),
                'date': message_data.get('date'),
                'edit_date': message_data.get('edit_date'),
                'from_user_id': message_data.get('from_user_id') or message_data.get('from_user'),
                'from_username': message_data.get('from_username'),
                'author_signature': message_data.get('author_signature'),
                'media_type': message_data.get('media_type'),
                'views': message_data.get('views'),
                'forwards': message_data.get('forwards'),
                'replies': message_data.get('replies'),
                'reply_to_message_id': message_data.get('reply_to_message_id'),
                'forward_from_channel_id': message_data.get('forward_from_channel_id'),
                'forward_from_message_id': message_data.get('forward_from_message_id'),
                'raw_data': message_data  # Store entire enriched message data
            }
            
            # Save to database with update_if_exists=True to handle message edits/updates
            saved_message = await save_telegram_message(
                db_message_data, 
                update_if_exists=True
            )
            
            if saved_message:
                logger.debug(f"✅ Stored message {message_data.get('message_id')} from channel {message_data.get('channel_id')}")
            else:
                logger.warning(f"Failed to store message {message_data.get('message_id')}")
                self.stats["errors"] += 1
                
        except Exception as e:
            logger.error(f"Failed to store message {message_data.get('message_id', 'Unknown')}: {e}")
            self.stats["errors"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        stats = self.stats.copy()
        stats.update({
            "is_running": self.is_running,
            "monitored_channels": len(self.monitored_channels),
            "channels_detail": self.monitored_channels,
            "telethon_stats": self.telethon_client.get_stats(),
            "redis_stats": self.redis_service.get_stats()
        })
        
        if stats["start_time"]:
            if isinstance(stats["start_time"], str):
                start_time = datetime.fromisoformat(stats["start_time"].replace('Z', '+00:00'))
            else:
                start_time = stats["start_time"]
            uptime = datetime.now(timezone.utc) - start_time
            stats["uptime_seconds"] = uptime.total_seconds()
        
        return stats
    
    async def get_recent_messages(self, channel_id: str, limit: int = 10) -> List[Dict]:
        """Get recent messages from a monitored channel."""
        if channel_id not in self.monitored_channels:
            raise ValueError(f"Channel {channel_id} is not being monitored")
        
        channel_metadata = self.monitored_channels[channel_id]
        identifier = channel_metadata["identifier"]
        
        return await self.telethon_client.get_recent_messages(identifier, limit)


# Global integration instance
telethon_redis_integration: Optional[TelethonRedisIntegration] = None


async def initialize_integration(
    telethon_client: Optional[TelethonMonitorClient] = None,
    redis_service_instance: Optional[RedisPubSubService] = None,
    enable_ai_filtering: bool = True,
    relevance_threshold: float = 0.3
) -> TelethonRedisIntegration:
    """Initialize the global Telethon-Redis integration."""
    global telethon_redis_integration
    
    if telethon_redis_integration is not None:
        logger.warning("Integration already initialized")
        return telethon_redis_integration
    
    # Use provided clients or create new ones
    if telethon_client is None:
        telethon_client = TelethonMonitorClient()
    
    if redis_service_instance is None:
        redis_service_instance = redis_service
    
    telethon_redis_integration = TelethonRedisIntegration(
        telethon_client,
        redis_service_instance,
        enable_ai_filtering=enable_ai_filtering,
        relevance_threshold=relevance_threshold
    )
    
    logger.info(f"Global Telethon-Redis integration initialized (AI: {enable_ai_filtering}, threshold: {relevance_threshold})")
    return telethon_redis_integration


async def start_monitoring(channels: List[str]) -> bool:
    """Convenience function to start monitoring channels."""
    global telethon_redis_integration
    
    if telethon_redis_integration is None:
        telethon_redis_integration = await initialize_integration()
    
    try:
        await telethon_redis_integration.start()
        
        # Add channels to monitoring
        for channel in channels:
            await telethon_redis_integration.add_channel_to_monitor(channel)
        
        logger.info(f"Started monitoring {len(channels)} channels")
        return True
        
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        return False


async def stop_monitoring():
    """Stop the monitoring service."""
    global telethon_redis_integration
    
    if telethon_redis_integration:
        await telethon_redis_integration.stop()
        telethon_redis_integration = None
        logger.info("Monitoring stopped")


def get_integration_stats() -> Dict[str, Any]:
    """Get current integration statistics."""
    if telethon_redis_integration:
        return telethon_redis_integration.get_stats()
    else:
        return {"error": "Integration not initialized"} 