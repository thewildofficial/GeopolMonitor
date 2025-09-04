"""
Telethon Client Implementation for GeopolMonitor

This module provides a Telethon-based Telegram client optimized for large-scale 
channel monitoring with proper authentication, session management, and error handling.
"""

import asyncio
import logging
import os
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
from datetime import datetime, timedelta
import json
import random
import time

from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User, Message as TelethonMessage
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    FloodWaitError,
    RPCError,
    AuthKeyUnregisteredError,
    AuthKeyDuplicatedError,
    AuthKeyError,
    ServerError,
    TimedOutError,
    NetworkMigrateError
)
from telethon.sessions import StringSession

from config.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_NAME

logger = logging.getLogger(__name__)


class TelethonMonitorClient:
    """
    Telethon-based Telegram monitoring client for large-scale channel monitoring.
    
    Features:
    - User account authentication with phone/code flow
    - Secure session management
    - Event-driven message monitoring
    - Rate limiting and error handling
    - Channel management utilities
    """

    def __init__(
        self, 
        session_name: Optional[str] = None,
        session_dir: Optional[str] = None
    ):
        """
        Initialize the Telethon client.
        
        Args:
            session_name: Name for the session file (default: telethon_geopol_monitor)
            session_dir: Directory to store session files (default: data/telegram_sessions)
        """
        # Use different session name to avoid conflict with Pyrogram
        self.session_name = session_name or f"telethon_{TELEGRAM_SESSION_NAME}"
        self.session_dir = Path(session_dir or "data/telegram_sessions")
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Session file path
        self.session_path = self.session_dir / f"{self.session_name}.session"
        
        # Initialize Telethon client
        self.client: Optional[TelegramClient] = None
        self._setup_client()
        
        # Event handlers
        self.message_handlers: List[Callable] = []
        self.monitored_channels: Dict[int, Dict[str, Any]] = {}
        
        # Statistics
        self.stats = {
            'messages_received': 0,
            'errors_handled': 0,
            'start_time': None,
            'last_activity': None
        }
        
        # Authentication state
        self.is_authenticated = False
        self.phone_number: Optional[str] = None
        
        # Connection management
        self.is_running = False
        self.is_reconnecting = False
        self.max_retries = 5
        self.base_retry_delay = 1.0  # seconds
        self.max_retry_delay = 60.0  # seconds
        self.connection_timeout = 30.0  # seconds
        self.last_ping = None
        self.ping_interval = 300  # 5 minutes
        
        # Reconnection statistics
        self.reconnection_stats = {
            'total_reconnections': 0,
            'successful_reconnections': 0,
            'failed_reconnections': 0,
            'last_reconnection': None,
            'current_retry_count': 0,
            'last_error': None,
            'connection_uptime_start': None
        }
        
        # Background tasks
        self._connection_monitor_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    def _setup_client(self):
        """Setup the Telethon client with proper configuration."""
        try:
            # Use session file path for persistent sessions
            self.client = TelegramClient(
                str(self.session_path),
                TELEGRAM_API_ID,
                TELEGRAM_API_HASH,
                device_model='GeopolMonitor Client',
                system_version='1.0',
                app_version='1.0',
                lang_code='en',
                system_lang_code='en'
            )
            
            # Register event handlers
            self._register_event_handlers()
            
            logger.info(f"Telethon client initialized with session: {self.session_path}")
            
        except Exception as e:
            logger.error(f"Failed to setup Telethon client: {e}")
            raise

    def _register_event_handlers(self):
        """Register event handlers for message monitoring."""
        
        @self.client.on(events.NewMessage(chats=lambda chat: chat.id in self.monitored_channels))
        async def handle_new_message(event):
            """Handle new messages from monitored channels."""
            try:
                await self._process_message(event)
            except Exception as e:
                logger.error(f"Error processing message {event.message.id}: {e}")
                self.stats['errors_handled'] += 1

    async def authenticate_user(self, phone_number: str) -> bool:
        """
        Authenticate user with phone number and handle the verification flow.
        
        Args:
            phone_number: User's phone number in international format (e.g., +1234567890)
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            logger.info(f"Starting authentication for phone number: {phone_number}")
            self.phone_number = phone_number
            
            # Connect to Telegram
            await self.client.connect()
            
            # Check if already authenticated
            if await self.client.is_user_authorized():
                logger.info("User already authenticated from saved session")
                self.is_authenticated = True
                return True
            
            # Send code request
            logger.info("Sending authentication code...")
            sent_code = await self.client.send_code_request(phone_number)
            
            # Get code from user input
            code = input("Enter the authentication code you received: ").strip()
            
            try:
                # Sign in with code
                await self.client.sign_in(phone_number, code)
                logger.info("Successfully authenticated with code")
                self.is_authenticated = True
                return True
                
            except SessionPasswordNeededError:
                # Two-factor authentication required
                logger.info("Two-factor authentication enabled, requesting password...")
                password = input("Enter your 2FA password: ").strip()
                
                await self.client.sign_in(password=password)
                logger.info("Successfully authenticated with 2FA password")
                self.is_authenticated = True
                return True
                
        except PhoneCodeInvalidError:
            logger.error("Invalid authentication code")
            return False
        except PhoneNumberInvalidError:
            logger.error("Invalid phone number format")
            return False
        except FloodWaitError as e:
            logger.error(f"Rate limited. Wait {e.seconds} seconds before trying again")
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def start(self, phone_number: Optional[str] = None) -> bool:
        """
        Start the Telethon client and authenticate if needed.
        
        Args:
            phone_number: Phone number for authentication (optional if already authenticated)
            
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            logger.info("Starting Telethon client...")
            
            # Connect first
            await self.client.connect()
            
            # Check if already authenticated
            if await self.client.is_user_authorized():
                logger.info("Using existing authentication")
                self.is_authenticated = True
            elif phone_number:
                # Authenticate with provided phone number
                if not await self.authenticate_user(phone_number):
                    return False
            else:
                logger.error("No phone number provided and not already authenticated")
                return False
            
            # Update statistics
            self.stats['start_time'] = datetime.utcnow()
            self.stats['last_activity'] = datetime.utcnow()
            
            logger.info("Telethon client started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Telethon client: {e}")
            return False

    async def stop(self):
        """Stop the Telethon client and disconnect."""
        try:
            self.is_running = False
            
            # Cancel background tasks
            if self._connection_monitor_task and not self._connection_monitor_task.done():
                self._connection_monitor_task.cancel()
                try:
                    await self._connection_monitor_task
                except asyncio.CancelledError:
                    pass
            
            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect client
            if self.client and self.client.is_connected():
                await self.client.disconnect()
                logger.info("Telethon client stopped and disconnected")
                
        except Exception as e:
            logger.error(f"Error stopping Telethon client: {e}")

    async def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        delay = min(self.base_retry_delay * (2 ** attempt), self.max_retry_delay)
        # Add jitter to avoid thundering herd
        jitter = random.uniform(0.1, 0.3) * delay
        return delay + jitter

    async def _handle_connection_error(self, error: Exception, context: str = ""):
        """Handle connection errors with proper logging and statistics."""
        error_msg = f"Connection error in {context}: {type(error).__name__}: {error}"
        logger.error(error_msg)
        
        self.reconnection_stats['last_error'] = error_msg
        self.reconnection_stats['failed_reconnections'] += 1
        self.stats['errors_handled'] += 1

    async def _ensure_connection(self) -> bool:
        """Ensure the client is connected with retry logic."""
        if not self.client:
            logger.error("Client not initialized")
            return False
        
        # Check if already connected and authorized
        if self.client.is_connected() and await self._check_auth_status():
            return True
        
        # Attempt reconnection
        return await self._reconnect_with_retry()

    async def _check_auth_status(self) -> bool:
        """Check if the client is authenticated."""
        try:
            if not self.client.is_connected():
                return False
            return await self.client.is_user_authorized()
        except Exception as e:
            logger.debug(f"Auth check failed: {e}")
            return False

    async def _reconnect_with_retry(self) -> bool:
        """Reconnect with exponential backoff retry logic."""
        if self.is_reconnecting:
            logger.debug("Reconnection already in progress")
            return False
        
        self.is_reconnecting = True
        self.reconnection_stats['total_reconnections'] += 1
        
        try:
            for attempt in range(self.max_retries):
                self.reconnection_stats['current_retry_count'] = attempt + 1
                
                try:
                    logger.info(f"Reconnection attempt {attempt + 1}/{self.max_retries}")
                    
                    # Disconnect if connected but not working
                    if self.client.is_connected():
                        await self.client.disconnect()
                        await asyncio.sleep(1)  # Brief pause
                    
                    # Attempt to connect
                    await asyncio.wait_for(
                        self.client.connect(),
                        timeout=self.connection_timeout
                    )
                    
                    # Verify authentication
                    if await self.client.is_user_authorized():
                        logger.info("Reconnection successful")
                        self.reconnection_stats['successful_reconnections'] += 1
                        self.reconnection_stats['last_reconnection'] = datetime.utcnow()
                        self.reconnection_stats['current_retry_count'] = 0
                        self.reconnection_stats['connection_uptime_start'] = datetime.utcnow()
                        return True
                    else:
                        logger.warning("Connected but not authenticated")
                        
                except asyncio.TimeoutError:
                    await self._handle_connection_error(
                        TimeoutError(f"Connection timeout after {self.connection_timeout}s"),
                        f"reconnect attempt {attempt + 1}"
                    )
                except (OSError, ServerError, TimedOutError) as e:
                    await self._handle_connection_error(e, f"reconnect attempt {attempt + 1}")
                except AuthKeyError as e:
                    logger.error(f"Authentication key error: {e}")
                    logger.error("Session may be corrupted. Manual re-authentication may be required.")
                    await self._handle_connection_error(e, f"reconnect attempt {attempt + 1}")
                except Exception as e:
                    await self._handle_connection_error(e, f"reconnect attempt {attempt + 1}")
                
                # Wait before next attempt (except on last attempt)
                if attempt < self.max_retries - 1:
                    delay = await self._calculate_retry_delay(attempt)
                    logger.info(f"Waiting {delay:.2f}s before next reconnection attempt")
                    await asyncio.sleep(delay)
            
            logger.error(f"Failed to reconnect after {self.max_retries} attempts")
            return False
            
        finally:
            self.is_reconnecting = False

    async def _connection_monitor(self):
        """Background task to monitor connection health."""
        logger.info("Starting connection monitor")
        
        while self.is_running:
            try:
                # Check connection status
                if not self.client.is_connected() or not await self._check_auth_status():
                    logger.warning("Connection lost, attempting to reconnect...")
                    await self._ensure_connection()
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                logger.info("Connection monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Connection monitor error: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _heartbeat(self):
        """Background task to send periodic pings to maintain connection."""
        logger.info("Starting heartbeat task")
        
        while self.is_running:
            try:
                if self.client.is_connected() and await self._check_auth_status():
                    # Send a ping to keep connection alive
                    try:
                        await self.client.get_me()
                        self.last_ping = datetime.utcnow()
                        logger.debug("Heartbeat ping successful")
                    except Exception as e:
                        logger.warning(f"Heartbeat ping failed: {e}")
                        # Connection monitor will handle reconnection
                
                # Wait for next heartbeat
                await asyncio.sleep(self.ping_interval)
                
            except asyncio.CancelledError:
                logger.info("Heartbeat task cancelled")
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(self.ping_interval)

    async def start_with_monitoring(self, phone_number: Optional[str] = None) -> bool:
        """
        Start the client with robust monitoring and auto-reconnection.
        
        Args:
            phone_number: Phone number for authentication (optional if already authenticated)
            
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            # Start the basic client
            if not await self.start(phone_number):
                return False
            
            self.is_running = True
            self.reconnection_stats['connection_uptime_start'] = datetime.utcnow()
            
            # Start background monitoring tasks
            self._connection_monitor_task = asyncio.create_task(self._connection_monitor())
            self._heartbeat_task = asyncio.create_task(self._heartbeat())
            
            logger.info("Telethon client started with robust monitoring")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitored client: {e}")
            self.is_running = False
            return False

    async def robust_operation(self, operation_func, *args, **kwargs):
        """
        Execute an operation with automatic reconnection if needed.
        
        Args:
            operation_func: The async function to execute
            *args, **kwargs: Arguments for the operation function
            
        Returns:
            The result of the operation or None if failed
        """
        max_operation_retries = 3
        
        for attempt in range(max_operation_retries):
            try:
                # Ensure connection before operation
                if not await self._ensure_connection():
                    logger.error("Could not establish connection for operation")
                    return None
                
                # Execute the operation
                return await operation_func(*args, **kwargs)
                
            except (OSError, ServerError, TimedOutError, AuthKeyError) as e:
                logger.warning(f"Operation failed due to connection issue (attempt {attempt + 1}): {e}")
                if attempt < max_operation_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error("Operation failed after all retry attempts")
                    return None
                    
            except Exception as e:
                logger.error(f"Operation failed with non-connection error: {e}")
                return None
        
        return None

    async def add_channel(self, channel_identifier: str, **metadata) -> bool:
        """
        Add a channel to the monitoring list with robust error handling.
        
        Args:
            channel_identifier: Channel username (with or without @) or invite link
            **metadata: Additional metadata for the channel
            
        Returns:
            bool: True if added successfully, False otherwise
        """
        async def _add_channel_operation():
            # Get channel entity
            entity = await self.client.get_entity(channel_identifier)
            
            if not isinstance(entity, Channel):
                logger.error(f"Entity {channel_identifier} is not a channel")
                return False
            
            # Add to monitored channels
            self.monitored_channels[entity.id] = {
                'id': entity.id,
                'username': getattr(entity, 'username', None),
                'title': getattr(entity, 'title', 'Unknown'),
                'added_at': datetime.utcnow().isoformat(),
                **metadata
            }
            
            logger.info(f"Added channel {entity.title} (@{entity.username}) to monitoring")
            return True
        
        try:
            result = await self.robust_operation(_add_channel_operation)
            return result if result is not None else False
        except Exception as e:
            logger.error(f"Failed to add channel {channel_identifier}: {e}")
            return False

    async def remove_channel(self, channel_identifier: str) -> bool:
        """
        Remove a channel from monitoring.
        
        Args:
            channel_identifier: Channel username or ID
            
        Returns:
            bool: True if removed successfully, False otherwise
        """
        try:
            # Find channel to remove
            channel_id = None
            
            if isinstance(channel_identifier, int):
                channel_id = channel_identifier
            else:
                # Find by username
                for cid, info in self.monitored_channels.items():
                    if info.get('username') == channel_identifier.lstrip('@'):
                        channel_id = cid
                        break
            
            if channel_id and channel_id in self.monitored_channels:
                channel_info = self.monitored_channels.pop(channel_id)
                logger.info(f"Removed channel {channel_info.get('title')} from monitoring")
                return True
            else:
                logger.warning(f"Channel {channel_identifier} not found in monitoring list")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove channel {channel_identifier}: {e}")
            return False

    async def _process_message(self, event):
        """Process a new message event."""
        try:
            message = event.message
            chat = await event.get_chat()
            
            # Extract message data
            message_data = {
                'message_id': message.id,
                'channel_id': chat.id,
                'channel_username': getattr(chat, 'username', None),
                'channel_title': getattr(chat, 'title', 'Unknown'),
                'text': message.text or '',
                'date': message.date,
                'views': getattr(message, 'views', None),
                'forwards': getattr(message, 'forwards', None),
                'replies': getattr(message.replies, 'replies', None) if message.replies else None,
                'media_type': self._get_media_type(message),
                'from_user': getattr(message.from_id, 'user_id', None) if message.from_id else None,
                'is_forwarded': bool(message.fwd_from),
                'raw_data': message.to_dict()
            }
            
            # Update statistics
            self.stats['messages_received'] += 1
            self.stats['last_activity'] = datetime.utcnow()
            
            # Call registered message handlers
            for handler in self.message_handlers:
                try:
                    await handler(message_data)
                except Exception as e:
                    logger.error(f"Message handler error: {e}")
            
            logger.debug(f"Processed message {message.id} from {message_data['channel_username']}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.stats['errors_handled'] += 1

    def _get_media_type(self, message: TelethonMessage) -> Optional[str]:
        """Determine the media type of a message."""
        if message.photo:
            return 'photo'
        elif message.video:
            return 'video'
        elif message.document:
            return 'document'
        elif message.voice:
            return 'voice'
        elif message.audio:
            return 'audio'
        elif message.sticker:
            return 'sticker'
        elif message.gif:
            return 'gif'
        return None

    def add_message_handler(self, handler: Callable):
        """Add a message handler function."""
        self.message_handlers.append(handler)
        logger.info(f"Added message handler: {handler.__name__}")

    async def get_channel_info(self, channel_identifier: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a channel with robust error handling.
        
        Args:
            channel_identifier: Channel username or ID
            
        Returns:
            Optional[Dict]: Channel information or None if not found
        """
        async def _get_channel_info_operation():
            entity = await self.client.get_entity(channel_identifier)
            
            if isinstance(entity, Channel):
                return {
                    'id': entity.id,
                    'username': getattr(entity, 'username', None),
                    'title': getattr(entity, 'title', 'Unknown'),
                    'description': getattr(entity, 'about', None),
                    'participants_count': getattr(entity, 'participants_count', None),
                    'is_verified': getattr(entity, 'verified', False),
                    'is_scam': getattr(entity, 'scam', False),
                    'is_fake': getattr(entity, 'fake', False),
                    'restriction_reason': getattr(entity, 'restriction_reason', None),
                    'created_date': getattr(entity, 'date', None)
                }
            return None
        
        try:
            return await self.robust_operation(_get_channel_info_operation)
        except Exception as e:
            logger.error(f"Failed to get channel info for {channel_identifier}: {e}")
            return None

    async def get_recent_messages(self, channel_identifier: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent messages from a channel.
        
        Args:
            channel_identifier: Channel username or ID
            limit: Number of messages to retrieve
            
        Returns:
            List[Dict]: List of message data
        """
        try:
            messages = []
            async for message in self.client.iter_messages(channel_identifier, limit=limit):
                messages.append({
                    'message_id': message.id,
                    'text': message.text or '',
                    'date': message.date,
                    'views': getattr(message, 'views', None),
                    'forwards': getattr(message, 'forwards', None),
                    'media_type': self._get_media_type(message),
                    'is_forwarded': bool(message.fwd_from)
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get recent messages from {channel_identifier}: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive client statistics including connection monitoring."""
        stats = self.stats.copy()
        stats.update({
            'is_authenticated': self.is_authenticated,
            'monitored_channels_count': len(self.monitored_channels),
            'session_path': str(self.session_path),
            'is_connected': self.client.is_connected() if self.client else False,
            'is_running': self.is_running,
            'is_reconnecting': self.is_reconnecting,
            'last_ping': self.last_ping.isoformat() if self.last_ping else None,
            'connection_config': {
                'max_retries': self.max_retries,
                'base_retry_delay': self.base_retry_delay,
                'max_retry_delay': self.max_retry_delay,
                'connection_timeout': self.connection_timeout,
                'ping_interval': self.ping_interval
            }
        })
        
        # Add uptime calculations
        if self.stats['start_time']:
            uptime = datetime.utcnow() - self.stats['start_time']
            stats['uptime_seconds'] = uptime.total_seconds()
        
        # Add connection uptime
        if self.reconnection_stats['connection_uptime_start']:
            connection_uptime = datetime.utcnow() - self.reconnection_stats['connection_uptime_start']
            stats['connection_uptime_seconds'] = connection_uptime.total_seconds()
        
        # Add reconnection statistics
        stats['reconnection_stats'] = self.reconnection_stats.copy()
        if self.reconnection_stats['last_reconnection']:
            stats['reconnection_stats']['last_reconnection'] = self.reconnection_stats['last_reconnection'].isoformat()
        
        return stats

    def get_monitored_channels(self) -> List[Dict[str, Any]]:
        """Get list of monitored channels."""
        return list(self.monitored_channels.values())

    async def run_until_disconnected(self):
        """Run the client until manually disconnected."""
        if self.client:
            await self.client.run_until_disconnected()


# Global client instance
telethon_monitor = TelethonMonitorClient()
