"""
Core Channel Monitoring Orchestrator for GeopolMonitor.

This module provides the main orchestration layer that coordinates:
- Telethon client initialization and management
- Channel configuration loading and management
- Real-time message monitoring and processing
- Redis Pub/Sub integration for message distribution
- Database persistence and historical message retrieval
- Health monitoring and statistics
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

from config.channels import (
    HIGH_PRIORITY_CHANNELS,
    get_all_channels,
    get_test_channels,
    get_production_channels,
    get_channels_by_priority,
    CHANNEL_SUMMARY,
    CredibilityTier,
    GeographicRegion
)
from config.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH
from src.telegram.telethon_client import TelethonMonitorClient
from src.telegram.telethon_redis_integration import TelethonRedisIntegration
from src.core.services.redis_pubsub import (
    RedisPubSubService,
    Priority,
    redis_service
)
from src.database.telegram_db import init_telegram_db, close_telegram_db

logger = logging.getLogger(__name__)


class ChannelMonitoringOrchestrator:
    """
    Main orchestrator for Telegram channel monitoring.
    
    Manages the complete monitoring pipeline:
    - Client authentication and connection management
    - Channel loading and configuration
    - Real-time message capture and processing
    - Historical message synchronization
    - Health monitoring and statistics
    """
    
    def __init__(
        self,
        phone_number: Optional[str] = None,
        use_test_channels: bool = False,
        max_channels: Optional[int] = None
    ):
        """
        Initialize the monitoring orchestrator.
        
        Args:
            phone_number: Phone number for Telegram authentication
            use_test_channels: If True, only monitor safe test channels
            max_channels: Maximum number of channels to monitor (for testing)
        """
        self.phone_number = phone_number
        self.use_test_channels = use_test_channels
        self.max_channels = max_channels
        
        # Core components
        self.telethon_client: Optional[TelethonMonitorClient] = None
        self.redis_integration: Optional[TelethonRedisIntegration] = None
        self.is_running = False
        self.is_stopping = False
        
        # Channel management
        self.configured_channels: List[Dict[str, Any]] = []
        self.active_channels: Dict[str, Dict[str, Any]] = {}  # channel_id -> metadata
        self.failed_channels: Dict[str, str] = {}  # channel_identifier -> error
        
        # Statistics and monitoring
        self.stats = {
            "start_time": None,
            "channels_configured": 0,
            "channels_active": 0,
            "channels_failed": 0,
            "messages_processed": 0,
            "last_message_time": None,
            "uptime_seconds": 0,
            "errors": 0
        }
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._stats_update_task: Optional[asyncio.Task] = None
        
        logger.info(f"Channel Monitor initialized (test_mode: {use_test_channels})")
    
    async def initialize(self) -> bool:
        """Initialize all components and prepare for monitoring."""
        try:
            logger.info("🚀 Initializing Channel Monitoring System")
            
            # Initialize database
            await init_telegram_db()
            logger.info("✅ Database initialized")
            
            # Initialize Redis service
            if not redis_service.is_running:
                await redis_service.start()
                logger.info("✅ Redis service started")
            
            # Initialize Telethon client
            self.telethon_client = TelethonMonitorClient()
            logger.info("✅ Telethon client created")
            
            # Initialize Redis integration
            self.redis_integration = TelethonRedisIntegration(
                self.telethon_client,
                redis_service
            )
            logger.info("✅ Redis integration initialized")
            
            # Load channel configuration
            await self._load_channel_configuration()
            logger.info(f"✅ Loaded {len(self.configured_channels)} channels")
            
            logger.info("🎯 Channel Monitoring System initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize monitoring system: {e}")
            return False
    
    async def start(self) -> bool:
        """Start the complete monitoring system."""
        try:
            if self.is_running:
                logger.warning("Monitoring system is already running")
                return True
            
            logger.info("🚀 Starting Channel Monitoring System")
            
            # Start Redis integration
            await self.redis_integration.start()
            logger.info("✅ Redis integration started")
            
            # Start Telethon client with monitoring
            if not await self.telethon_client.start_with_monitoring(self.phone_number):
                logger.error("❌ Failed to start Telethon client")
                return False
            logger.info("✅ Telethon client started with monitoring")
            
            # Add channels to monitoring
            await self._setup_channel_monitoring()
            
            # Start background tasks
            await self._start_background_tasks()
            
            # Set running state
            self.is_running = True
            self.stats["start_time"] = datetime.now(timezone.utc)
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            logger.info("🎯 Channel Monitoring System started successfully")
            logger.info(f"📊 Monitoring {len(self.active_channels)} channels")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start monitoring system: {e}")
            await self.stop()
            return False
    
    async def stop(self) -> bool:
        """Stop the monitoring system gracefully."""
        try:
            if self.is_stopping:
                logger.info("Stop already in progress...")
                return True
            
            self.is_stopping = True
            logger.info("🛑 Stopping Channel Monitoring System")
            
            # Stop background tasks
            await self._stop_background_tasks()
            
            # Stop Redis integration
            if self.redis_integration and self.redis_integration.is_running:
                await self.redis_integration.stop()
                logger.info("✅ Redis integration stopped")
            
            # Stop Telethon client
            if self.telethon_client and self.telethon_client.is_running:
                await self.telethon_client.stop()
                logger.info("✅ Telethon client stopped")
            
            # Close database
            await close_telegram_db()
            logger.info("✅ Database closed")
            
            self.is_running = False
            self.is_stopping = False
            
            logger.info("🎯 Channel Monitoring System stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping monitoring system: {e}")
            return False
    
    async def _load_channel_configuration(self):
        """Load and configure channels based on settings."""
        try:
            if self.use_test_channels:
                self.configured_channels = get_test_channels()
                logger.info("📺 Using test channels for development")
            else:
                self.configured_channels = get_production_channels()
                logger.info("📺 Using production channels")
            
            # Apply max channels limit if specified
            if self.max_channels and len(self.configured_channels) > self.max_channels:
                # Prioritize high-priority channels
                high_priority = get_channels_by_priority(Priority.HIGH)
                medium_priority = get_channels_by_priority(Priority.MEDIUM)
                
                selected_channels = []
                selected_channels.extend(high_priority[:min(len(high_priority), self.max_channels // 2)])
                remaining = self.max_channels - len(selected_channels)
                selected_channels.extend(medium_priority[:remaining])
                
                self.configured_channels = selected_channels
                logger.info(f"📊 Limited to {len(self.configured_channels)} highest priority channels")
            
            self.stats["channels_configured"] = len(self.configured_channels)
            
            # Log channel summary
            logger.info(f"📋 Channel Configuration Summary:")
            for tier in CredibilityTier:
                count = len([ch for ch in self.configured_channels if ch.get("credibility_tier") == tier])
                if count > 0:
                    logger.info(f"   {tier.value}: {count} channels")
                    
        except Exception as e:
            logger.error(f"❌ Failed to load channel configuration: {e}")
            raise
    
    async def _setup_channel_monitoring(self):
        """Add all configured channels to monitoring."""
        logger.info("📡 Setting up channel monitoring...")
        
        success_count = 0
        for channel_config in self.configured_channels:
            identifier = channel_config["identifier"]
            
            try:
                # Extract configuration
                priority = channel_config.get("priority", Priority.MEDIUM)
                keywords = channel_config.get("keywords", [])
                
                # Add to monitoring
                result = await self.redis_integration.add_channel_to_monitor(
                    identifier,
                    priority=priority,
                    keywords=keywords
                )
                
                if result:
                    self.active_channels[identifier] = channel_config
                    success_count += 1
                    logger.info(f"✅ Added {channel_config['title']} ({identifier})")
                else:
                    self.failed_channels[identifier] = "Failed to add to monitoring"
                    logger.warning(f"⚠️  Failed to add {identifier}")
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.failed_channels[identifier] = str(e)
                logger.error(f"❌ Error adding {identifier}: {e}")
        
        self.stats["channels_active"] = success_count
        self.stats["channels_failed"] = len(self.failed_channels)
        
        logger.info(f"📊 Channel setup complete: {success_count} active, {len(self.failed_channels)} failed")
        
        # Log failures if any
        if self.failed_channels:
            logger.warning("⚠️  Failed channels:")
            for channel, error in self.failed_channels.items():
                logger.warning(f"   {channel}: {error}")
    
    async def _start_background_tasks(self):
        """Start background monitoring tasks."""
        logger.info("🔄 Starting background tasks")
        
        # Health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Statistics update task  
        self._stats_update_task = asyncio.create_task(self._stats_update_loop())
        
        logger.info("✅ Background tasks started")
    
    async def _stop_background_tasks(self):
        """Stop all background tasks."""
        logger.info("🛑 Stopping background tasks")
        
        tasks = [self._health_check_task, self._stats_update_task]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("✅ Background tasks stopped")
    
    async def _health_check_loop(self):
        """Periodic health check of all components."""
        try:
            while self.is_running and not self.is_stopping:
                await self._perform_health_check()
                await asyncio.sleep(60)  # Check every minute
        except asyncio.CancelledError:
            logger.info("Health check loop cancelled")
        except Exception as e:
            logger.error(f"Health check loop error: {e}")
    
    async def _stats_update_loop(self):
        """Periodic statistics update."""
        try:
            while self.is_running and not self.is_stopping:
                await self._update_statistics()
                await asyncio.sleep(30)  # Update every 30 seconds
        except asyncio.CancelledError:
            logger.info("Stats update loop cancelled")
        except Exception as e:
            logger.error(f"Stats update loop error: {e}")
    
    async def _perform_health_check(self):
        """Perform comprehensive health check."""
        try:
            # Check Telethon client
            if not self.telethon_client.client.is_connected():
                logger.warning("⚠️  Telethon client disconnected")
                
            # Check Redis integration
            if not self.redis_integration.is_running:
                logger.warning("⚠️  Redis integration not running")
                
            # Check active channels vs configured
            expected_active = len(self.configured_channels) - len(self.failed_channels)
            actual_active = len(self.active_channels)
            
            if actual_active < expected_active:
                logger.warning(f"⚠️  Channel count mismatch: {actual_active}/{expected_active}")
                
        except Exception as e:
            logger.error(f"Health check error: {e}")
    
    async def _update_statistics(self):
        """Update monitoring statistics."""
        try:
            # Update uptime
            if self.stats["start_time"]:
                uptime = datetime.now(timezone.utc) - self.stats["start_time"]
                self.stats["uptime_seconds"] = uptime.total_seconds()
            
            # Get integration stats
            if self.redis_integration:
                integration_stats = self.redis_integration.get_stats()
                self.stats["messages_processed"] = integration_stats.get("messages_processed", 0)
                self.stats["last_message_time"] = integration_stats.get("last_message_time")
                
        except Exception as e:
            logger.error(f"Statistics update error: {e}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def get_historical_messages(
        self,
        channel_identifier: str,
        limit: int = 100,
        max_age_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Retrieve historical messages from a specific channel.
        
        Args:
            channel_identifier: Channel username or ID
            limit: Maximum number of messages to retrieve
            max_age_hours: Maximum age of messages in hours
            
        Returns:
            List of message data dictionaries
        """
        try:
            if not self.telethon_client:
                raise RuntimeError("Telethon client not initialized")
                
            return await self.telethon_client.get_recent_messages(channel_identifier, limit)
            
        except Exception as e:
            logger.error(f"Failed to get historical messages for {channel_identifier}: {e}")
            return []
    
    async def add_channel(
        self,
        identifier: str,
        title: str = "Manual Channel",
        priority: Priority = Priority.MEDIUM,
        keywords: Optional[List[str]] = None
    ) -> bool:
        """
        Dynamically add a new channel to monitoring.
        
        Args:
            identifier: Channel username or ID
            title: Display title for the channel
            priority: Monitoring priority level
            keywords: Keywords for filtering
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            if not self.redis_integration:
                logger.error("Redis integration not available")
                return False
            
            result = await self.redis_integration.add_channel_to_monitor(
                identifier,
                priority=priority,
                keywords=keywords or []
            )
            
            if result:
                # Add to active channels
                self.active_channels[identifier] = {
                    "identifier": identifier,
                    "title": title,
                    "priority": priority,
                    "keywords": keywords or [],
                    "manually_added": True
                }
                self.stats["channels_active"] = len(self.active_channels)
                logger.info(f"✅ Dynamically added channel: {title} ({identifier})")
                return True
            else:
                logger.error(f"❌ Failed to add channel: {identifier}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding channel {identifier}: {e}")
            return False
    
    async def remove_channel(self, identifier: str) -> bool:
        """
        Remove a channel from monitoring.
        
        Args:
            identifier: Channel username or ID
            
        Returns:
            True if successfully removed, False otherwise
        """
        try:
            if not self.redis_integration:
                logger.error("Redis integration not available")
                return False
            
            result = await self.redis_integration.remove_channel_from_monitor(identifier)
            
            if result and identifier in self.active_channels:
                channel_info = self.active_channels.pop(identifier)
                self.stats["channels_active"] = len(self.active_channels)
                logger.info(f"✅ Removed channel: {channel_info.get('title')} ({identifier})")
                return True
            else:
                logger.warning(f"⚠️  Channel {identifier} not found or failed to remove")
                return False
                
        except Exception as e:
            logger.error(f"Error removing channel {identifier}: {e}")
            return False
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive monitoring statistics."""
        stats = self.stats.copy()
        
        # Add component stats
        if self.telethon_client:
            stats["telethon_stats"] = self.telethon_client.get_stats()
        
        if self.redis_integration:
            stats["integration_stats"] = self.redis_integration.get_stats()
        
        # Add channel information
        stats["active_channels"] = list(self.active_channels.keys())
        stats["failed_channels"] = self.failed_channels.copy()
        stats["channel_summary"] = CHANNEL_SUMMARY
        
        # Add system status
        stats["system_status"] = {
            "is_running": self.is_running,
            "is_stopping": self.is_stopping,
            "telethon_connected": self.telethon_client.client.is_connected() if self.telethon_client else False,
            "redis_connected": redis_service.is_running if redis_service else False
        }
        
        return stats
    
    def get_active_channels(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active channels."""
        return self.active_channels.copy()
    
    def get_failed_channels(self) -> Dict[str, str]:
        """Get information about failed channels."""
        return self.failed_channels.copy()


# Global instance for the monitoring orchestrator
channel_monitor: Optional[ChannelMonitoringOrchestrator] = None


async def start_channel_monitoring(
    phone_number: Optional[str] = None,
    use_test_channels: bool = False,
    max_channels: Optional[int] = None
) -> bool:
    """
    Start the global channel monitoring system.
    
    Args:
        phone_number: Phone number for Telegram authentication
        use_test_channels: Use only test channels for development
        max_channels: Limit number of channels (for testing)
        
    Returns:
        True if started successfully, False otherwise
    """
    global channel_monitor
    
    try:
        if channel_monitor and channel_monitor.is_running:
            logger.warning("Channel monitoring is already running")
            return True
        
        # Create new orchestrator
        channel_monitor = ChannelMonitoringOrchestrator(
            phone_number=phone_number,
            use_test_channels=use_test_channels,
            max_channels=max_channels
        )
        
        # Initialize and start
        if await channel_monitor.initialize():
            return await channel_monitor.start()
        else:
            logger.error("Failed to initialize channel monitoring")
            return False
            
    except Exception as e:
        logger.error(f"Failed to start channel monitoring: {e}")
        return False


async def stop_channel_monitoring() -> bool:
    """Stop the global channel monitoring system."""
    global channel_monitor
    
    try:
        if channel_monitor:
            return await channel_monitor.stop()
        else:
            logger.info("No channel monitor instance to stop")
            return True
            
    except Exception as e:
        logger.error(f"Failed to stop channel monitoring: {e}")
        return False


def get_channel_monitor() -> Optional[ChannelMonitoringOrchestrator]:
    """Get the global channel monitor instance."""
    return channel_monitor


def get_monitoring_stats() -> Dict[str, Any]:
    """Get comprehensive monitoring statistics."""
    if channel_monitor:
        return channel_monitor.get_comprehensive_stats()
    else:
        return {"error": "Channel monitor not initialized"} 