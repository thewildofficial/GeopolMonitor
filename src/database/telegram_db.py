"""
Async database configuration and session management for Telegram models.

This module provides async database engine, session factory, and utility functions
for managing Telegram data using SQLAlchemy 2.0 with async support.
"""

import os
import logging
from typing import AsyncGenerator, Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    AsyncEngine, 
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError

from .models.telegram_models import TelegramBase, TelegramChannel, TelegramMessage, ChannelMetric

logger = logging.getLogger(__name__)

# Global variables for the async engine and session factory
_async_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

# Database configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
DEFAULT_SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'telegram_monitor.db')


def get_database_url(db_path: Optional[str] = None) -> str:
    """
    Get the database URL for async SQLAlchemy connection.
    
    Args:
        db_path: Optional custom database path. If not provided, uses default SQLite.
        
    Returns:
        str: Async database URL
    """
    # Check for PostgreSQL configuration first (for production)
    if os.getenv('POSTGRES_URL'):
        return os.getenv('POSTGRES_URL').replace('postgresql://', 'postgresql+asyncpg://')
    
    # Check for custom database URL
    if os.getenv('TELEGRAM_DATABASE_URL'):
        return os.getenv('TELEGRAM_DATABASE_URL')
    
    # Default to SQLite with async driver
    db_path = db_path or DEFAULT_SQLITE_DB_PATH
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    return f"sqlite+aiosqlite:///{db_path}"


def get_sync_database_url(db_path: Optional[str] = None) -> str:
    """
    Get the database URL for synchronous SQLAlchemy connection (used by Alembic).
    
    Args:
        db_path: Optional custom database path. If not provided, uses default SQLite.
        
    Returns:
        str: Synchronous database URL
    """
    # Check for PostgreSQL configuration first (for production)
    if os.getenv('POSTGRES_URL'):
        # Use psycopg2 for sync operations
        return os.getenv('POSTGRES_URL').replace('postgresql://', 'postgresql+psycopg2://')
    
    # Check for custom database URL and convert to sync
    if os.getenv('TELEGRAM_DATABASE_URL'):
        sync_url = os.getenv('TELEGRAM_DATABASE_URL')
        # Convert async drivers to sync equivalents
        sync_url = sync_url.replace('postgresql+asyncpg://', 'postgresql+psycopg2://')
        sync_url = sync_url.replace('sqlite+aiosqlite://', 'sqlite:///')
        return sync_url
    
    # Default to SQLite with sync driver
    db_path = db_path or DEFAULT_SQLITE_DB_PATH
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    return f"sqlite:///{db_path}"


async def init_telegram_db(database_url: Optional[str] = None, echo: bool = False) -> AsyncEngine:
    """
    Initialize the async database engine and create tables if they don't exist.
    
    Args:
        database_url: Optional database URL. If not provided, uses get_database_url()
        echo: Whether to echo SQL statements for debugging
        
    Returns:
        AsyncEngine: The initialized async database engine
    """
    global _async_engine, _async_session_factory
    
    try:
        # Get database URL
        db_url = database_url or get_database_url()
        logger.info(f"Initializing Telegram database with URL: {db_url.split('://')[0]}://...")
        
        # Create async engine
        _async_engine = create_async_engine(
            db_url,
            echo=echo,
            poolclass=NullPool if 'sqlite' in db_url else None,  # SQLite doesn't need pooling
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections every hour
        )
        
        # Create session factory
        _async_session_factory = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        )
        
        # Create all tables
        async with _async_engine.begin() as conn:
            await conn.run_sync(TelegramBase.metadata.create_all)
            logger.info("Telegram database tables created/verified successfully")
        
        # Test connection
        async with get_telegram_session() as session:
            result = await session.execute(text("SELECT 1"))
            logger.info("Telegram database connection test successful")
        
        return _async_engine
        
    except Exception as e:
        logger.error(f"Failed to initialize Telegram database: {e}")
        raise


def get_telegram_session():
    """
    Get an async database session for Telegram operations.
    
    This returns a session factory that can be used as an async context manager.
    
    Usage:
        async with get_telegram_session() as session:
            # Use session for database operations
            result = await session.execute(select(TelegramChannel))
    
    Returns:
        AsyncSession context manager
    """
    if _async_session_factory is None:
        raise RuntimeError("Telegram database not initialized. Call init_telegram_db() first.")
    
    return _async_session_factory()


async def get_telegram_engine() -> AsyncEngine:
    """
    Get the async database engine.
    
    Returns:
        AsyncEngine: The async database engine
        
    Raises:
        RuntimeError: If database is not initialized
    """
    if _async_engine is None:
        raise RuntimeError("Telegram database not initialized. Call init_telegram_db() first.")
    return _async_engine


async def close_telegram_db():
    """
    Close the async database engine and clean up connections.
    
    This should be called when shutting down the application.
    """
    global _async_engine, _async_session_factory
    
    if _async_engine:
        await _async_engine.dispose()
        logger.info("Telegram database engine disposed")
        
    _async_engine = None
    _async_session_factory = None


# Utility functions for common database operations

async def channel_exists(channel_id: int) -> bool:
    """
    Check if a Telegram channel exists in the database.
    
    Args:
        channel_id: Telegram channel ID
        
    Returns:
        bool: True if channel exists, False otherwise
    """
    from sqlalchemy import select
    
    async with get_telegram_session() as session:
        result = await session.execute(
            select(TelegramChannel).where(TelegramChannel.channel_id == channel_id)
        )
        return result.scalar_one_or_none() is not None


async def message_exists(message_id: int, channel_id: int) -> bool:
    """
    Check if a specific message exists in the database.
    
    Args:
        message_id: Telegram message ID
        channel_id: Telegram channel ID
        
    Returns:
        bool: True if message exists, False otherwise
    """
    from sqlalchemy import select
    
    async with get_telegram_session() as session:
        result = await session.execute(
            select(TelegramMessage).where(
                TelegramMessage.message_id == message_id,
                TelegramMessage.channel_id == channel_id
            )
        )
        return result.scalar_one_or_none() is not None


async def get_active_channels() -> list[TelegramChannel]:
    """
    Get all active Telegram channels.
    
    Returns:
        list[TelegramChannel]: List of active channels
    """
    from sqlalchemy import select
    
    async with get_telegram_session() as session:
        result = await session.execute(
            select(TelegramChannel).where(TelegramChannel.is_active == True)
        )
        return list(result.scalars().all())


async def get_channel_by_username(username: str) -> Optional[TelegramChannel]:
    """
    Get a channel by its username.
    
    Args:
        username: Channel username (without @)
        
    Returns:
        Optional[TelegramChannel]: Channel if found, None otherwise
    """
    from sqlalchemy import select
    
    async with get_telegram_session() as session:
        result = await session.execute(
            select(TelegramChannel).where(TelegramChannel.username == username)
        )
        return result.scalar_one_or_none()


async def get_recent_messages(
    channel_id: Optional[int] = None, 
    limit: int = 100,
    hours_back: int = 24
) -> list[TelegramMessage]:
    """
    Get recent messages from channels.
    
    Args:
        channel_id: Optional specific channel ID. If None, gets from all channels.
        limit: Maximum number of messages to return
        hours_back: How many hours back to look for messages
        
    Returns:
        list[TelegramMessage]: List of recent messages
    """
    from sqlalchemy import select, and_
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    async with get_telegram_session() as session:
        query = select(TelegramMessage).where(TelegramMessage.date >= cutoff_time)
        
        if channel_id:
            query = query.where(TelegramMessage.channel_id == channel_id)
            
        query = query.order_by(TelegramMessage.date.desc()).limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())


async def health_check() -> dict:
    """
    Perform a health check on the Telegram database.
    
    Returns:
        dict: Health check results
    """
    try:
        async with get_telegram_session() as session:
            # Test basic connectivity
            await session.execute(text("SELECT 1"))
            
            # Get basic statistics
            from sqlalchemy import select, func
            
            channel_count = await session.scalar(select(func.count(TelegramChannel.channel_id)))
            message_count = await session.scalar(select(func.count(TelegramMessage.message_id)))
            
            return {
                "status": "healthy",
                "connection": "ok",
                "channels": channel_count or 0,
                "messages": message_count or 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def save_telegram_message(
    message_data: Dict[str, Any],
    session: Optional[AsyncSession] = None,
    update_if_exists: bool = True
) -> Optional[TelegramMessage]:
    """
    Save a single Telegram message to the database with duplicate handling.
    
    Args:
        message_data: Dictionary containing message data from Telethon
        session: Optional existing async session. If None, creates a new one.
        update_if_exists: If True, update existing messages. If False, skip duplicates.
        
    Returns:
        Optional[TelegramMessage]: The saved message object, or None if failed
        
    Raises:
        ValueError: If required fields are missing from message_data
    """
    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from sqlalchemy import select, and_
    from datetime import datetime
    
    # Validate required fields
    required_fields = ['message_id', 'channel_id', 'date']
    missing_fields = [field for field in required_fields if field not in message_data or message_data[field] is None]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")
    
    # Extract and validate message data
    try:
        message_id = int(message_data['message_id'])
        channel_id = int(message_data['channel_id'])
        
        # Handle date - convert from various formats
        date_value = message_data['date']
        if isinstance(date_value, str):
            # Try to parse ISO format
            try:
                date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except ValueError:
                logger.error(f"Invalid date format: {date_value}")
                date_value = datetime.now()
        elif not isinstance(date_value, datetime):
            logger.warning(f"Unexpected date type: {type(date_value)}, using current time")
            date_value = datetime.now()
            
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid data types for message_id or channel_id: {e}")
    
    # Handle session management
    session_provided = session is not None
    if not session_provided:
        session = get_telegram_session()
    
    try:
        if session_provided:
            async_session = session
            # For provided sessions, we need to handle duplicates manually
            # Check if message already exists
            existing_message = await async_session.execute(
                select(TelegramMessage).where(
                    and_(
                        TelegramMessage.message_id == message_id,
                        TelegramMessage.channel_id == channel_id
                    )
                )
            )
            existing_message = existing_message.scalar_one_or_none()
            
            if existing_message:
                if update_if_exists:
                    # Update existing message with new data
                    existing_message.text = message_data.get('text', '')
                    existing_message.raw_text = message_data.get('raw_text') or message_data.get('text', '')
                    existing_message.views = message_data.get('views') or existing_message.views
                    existing_message.forwards = message_data.get('forwards') or existing_message.forwards
                    existing_message.replies = message_data.get('replies') or existing_message.replies
                    existing_message.updated_at = datetime.now()
                    
                    # Update edit_date if provided
                    if 'edit_date' in message_data and message_data['edit_date']:
                        existing_message.edit_date = message_data['edit_date']
                    
                    # Merge raw data
                    if existing_message.raw_data and message_data.get('raw_data'):
                        existing_message.raw_data.update(message_data['raw_data'])
                    elif message_data.get('raw_data'):
                        existing_message.raw_data = message_data['raw_data']
                    
                    await async_session.flush()
                    logger.debug(f"Updated existing message {message_id} from channel {channel_id}")
                    return existing_message
                else:
                    logger.debug(f"Message {message_id} from channel {channel_id} already exists, skipping")
                    return existing_message
            
            # Create new message if not exists
            telegram_message = TelegramMessage(
                message_id=message_id,
                channel_id=channel_id,
                text=message_data.get('text', ''),
                raw_text=message_data.get('raw_text') or message_data.get('text', ''),
                date=date_value,
                edit_date=None,  # Will be updated later if needed
                
                # Author information
                from_user_id=message_data.get('from_user_id') or message_data.get('from_user'),
                from_username=message_data.get('from_username'),
                author_signature=message_data.get('author_signature'),
                
                # Message metadata
                message_type=message_data.get('media_type', 'text'),
                has_media=bool(message_data.get('media_type')),
                media_type=message_data.get('media_type'),
                
                # Interaction metrics
                views=message_data.get('views'),
                forwards=message_data.get('forwards'),
                replies=message_data.get('replies'),
                
                # Thread/forwarding info
                reply_to_message_id=message_data.get('reply_to_message_id'),
                forward_from_channel_id=message_data.get('forward_from_channel_id'),
                forward_from_message_id=message_data.get('forward_from_message_id'),
                
                # Store raw data for debugging/analysis
                raw_data=message_data.get('raw_data', message_data)
            )
            
            async_session.add(telegram_message)
            await async_session.flush()
            logger.debug(f"Added new message {message_id} from channel {channel_id} to session")
            return telegram_message
            
        else:
            # Use our own session with context manager
            async with session:
                # Try to get the database URL to determine dialect
                engine = await get_telegram_engine()
                dialect_name = engine.dialect.name
                
                # Prepare message data for upsert
                message_values = {
                    'message_id': message_id,
                    'channel_id': channel_id,
                    'text': message_data.get('text', ''),
                    'raw_text': message_data.get('raw_text') or message_data.get('text', ''),
                    'date': date_value,
                    'from_user_id': message_data.get('from_user_id') or message_data.get('from_user'),
                    'from_username': message_data.get('from_username'),
                    'author_signature': message_data.get('author_signature'),
                    'message_type': message_data.get('media_type', 'text'),
                    'has_media': bool(message_data.get('media_type')),
                    'media_type': message_data.get('media_type'),
                    'views': message_data.get('views'),
                    'forwards': message_data.get('forwards'),
                    'replies': message_data.get('replies'),
                    'reply_to_message_id': message_data.get('reply_to_message_id'),
                    'forward_from_channel_id': message_data.get('forward_from_channel_id'),
                    'forward_from_message_id': message_data.get('forward_from_message_id'),
                    'raw_data': message_data.get('raw_data', message_data),
                    'updated_at': datetime.now()
                }
                
                if dialect_name == 'postgresql':
                    # Use PostgreSQL's ON CONFLICT
                    stmt = insert(TelegramMessage).values(**message_values)
                    if update_if_exists:
                        # Update all fields except primary keys and created_at
                        update_dict = {k: v for k, v in message_values.items() 
                                     if k not in ['message_id', 'channel_id']}
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['message_id', 'channel_id'],
                            set_=update_dict
                        )
                    else:
                        # Do nothing on conflict
                        stmt = stmt.on_conflict_do_nothing(
                            index_elements=['message_id', 'channel_id']
                        )
                    
                    result = await session.execute(stmt)
                    await session.commit()
                    
                    # Get the message object
                    message_result = await session.execute(
                        select(TelegramMessage).where(
                            and_(
                                TelegramMessage.message_id == message_id,
                                TelegramMessage.channel_id == channel_id
                            )
                        )
                    )
                    telegram_message = message_result.scalar_one()
                    
                elif dialect_name == 'sqlite':
                    # Use SQLite's ON CONFLICT
                    stmt = sqlite_insert(TelegramMessage).values(**message_values)
                    if update_if_exists:
                        # Update all fields except primary keys
                        update_dict = {k: v for k, v in message_values.items() 
                                     if k not in ['message_id', 'channel_id']}
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['message_id', 'channel_id'],
                            set_=update_dict
                        )
                    else:
                        # Do nothing on conflict
                        stmt = stmt.on_conflict_do_nothing(
                            index_elements=['message_id', 'channel_id']
                        )
                    
                    result = await session.execute(stmt)
                    await session.commit()
                    
                    # Get the message object
                    message_result = await session.execute(
                        select(TelegramMessage).where(
                            and_(
                                TelegramMessage.message_id == message_id,
                                TelegramMessage.channel_id == channel_id
                            )
                        )
                    )
                    telegram_message = message_result.scalar_one()
                    
                else:
                    # Fallback for other databases - manual check and insert/update
                    existing_message = await session.execute(
                        select(TelegramMessage).where(
                            and_(
                                TelegramMessage.message_id == message_id,
                                TelegramMessage.channel_id == channel_id
                            )
                        )
                    )
                    existing_message = existing_message.scalar_one_or_none()
                    
                    if existing_message:
                        if update_if_exists:
                            # Update existing message
                            for key, value in message_values.items():
                                if key not in ['message_id', 'channel_id'] and value is not None:
                                    setattr(existing_message, key, value)
                            await session.commit()
                            telegram_message = existing_message
                        else:
                            telegram_message = existing_message
                    else:
                        # Create new message
                        telegram_message = TelegramMessage(**message_values)
                        session.add(telegram_message)
                        await session.commit()
                
                logger.info(f"✅ Saved/updated message {message_id} from channel {channel_id}")
                return telegram_message
                
    except Exception as e:
        logger.error(f"Failed to save message {message_id} from channel {channel_id}: {e}")
        if not session_provided and session:
            await session.rollback()
        return None


async def save_telegram_messages_bulk(
    messages_data: List[Dict[str, Any]],
    session: Optional[AsyncSession] = None,
    update_if_exists: bool = True,
    batch_size: int = 100
) -> Dict[str, int]:
    """
    Save multiple Telegram messages to the database efficiently with duplicate handling.
    
    Args:
        messages_data: List of dictionaries containing message data from Telethon
        session: Optional existing async session. If None, creates a new one.
        update_if_exists: If True, update existing messages. If False, skip duplicates.
        batch_size: Number of messages to process in each batch
        
    Returns:
        Dict[str, int]: Statistics about the operation (inserted, updated, skipped, errors)
    """
    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from sqlalchemy import select, and_
    from datetime import datetime
    
    stats = {
        'inserted': 0,
        'updated': 0, 
        'skipped': 0,
        'errors': 0,
        'total_processed': 0
    }
    
    if not messages_data:
        return stats
    
    # Handle session management
    session_provided = session is not None
    if not session_provided:
        session = get_telegram_session()
    
    try:
        # Process messages in batches
        for i in range(0, len(messages_data), batch_size):
            batch = messages_data[i:i + batch_size]
            
            if session_provided:
                # For provided sessions, process individually with manual duplicate checking
                for message_data in batch:
                    try:
                        result = await save_telegram_message(
                            message_data, 
                            session=session, 
                            update_if_exists=update_if_exists
                        )
                        if result:
                            stats['inserted'] += 1
                        stats['total_processed'] += 1
                    except Exception as e:
                        logger.error(f"Error in bulk save for message {message_data.get('message_id')}: {e}")
                        stats['errors'] += 1
                        
            else:
                # Use our own session with bulk operations
                async with session:
                    try:
                        # Get database dialect
                        engine = await get_telegram_engine()
                        dialect_name = engine.dialect.name
                        
                        # Prepare batch data
                        batch_values = []
                        for message_data in batch:
                            try:
                                # Validate and extract data
                                message_id = int(message_data['message_id'])
                                channel_id = int(message_data['channel_id'])
                                
                                # Handle date
                                date_value = message_data['date']
                                if isinstance(date_value, str):
                                    try:
                                        date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                                    except ValueError:
                                        date_value = datetime.now()
                                elif not isinstance(date_value, datetime):
                                    date_value = datetime.now()
                                
                                batch_values.append({
                                    'message_id': message_id,
                                    'channel_id': channel_id,
                                    'text': message_data.get('text', ''),
                                    'raw_text': message_data.get('raw_text') or message_data.get('text', ''),
                                    'date': date_value,
                                    'from_user_id': message_data.get('from_user_id') or message_data.get('from_user'),
                                    'from_username': message_data.get('from_username'),
                                    'author_signature': message_data.get('author_signature'),
                                    'message_type': message_data.get('media_type', 'text'),
                                    'has_media': bool(message_data.get('media_type')),
                                    'media_type': message_data.get('media_type'),
                                    'views': message_data.get('views'),
                                    'forwards': message_data.get('forwards'),
                                    'replies': message_data.get('replies'),
                                    'reply_to_message_id': message_data.get('reply_to_message_id'),
                                    'forward_from_channel_id': message_data.get('forward_from_channel_id'),
                                    'forward_from_message_id': message_data.get('forward_from_message_id'),
                                    'raw_data': message_data.get('raw_data', message_data),
                                    'updated_at': datetime.now()
                                })
                                
                            except Exception as e:
                                logger.error(f"Error preparing message data for bulk insert: {e}")
                                stats['errors'] += 1
                                continue
                        
                        if not batch_values:
                            continue
                        
                        if dialect_name == 'postgresql':
                            # Use PostgreSQL bulk upsert
                            stmt = insert(TelegramMessage).values(batch_values)
                            if update_if_exists:
                                # Update all fields except primary keys
                                update_dict = {c.name: stmt.excluded[c.name] 
                                             for c in TelegramMessage.__table__.columns 
                                             if c.name not in ['message_id', 'channel_id', 'created_at']}
                                stmt = stmt.on_conflict_do_update(
                                    index_elements=['message_id', 'channel_id'],
                                    set_=update_dict
                                )
                            else:
                                stmt = stmt.on_conflict_do_nothing(
                                    index_elements=['message_id', 'channel_id']
                                )
                            
                            result = await session.execute(stmt)
                            await session.commit()
                            stats['inserted'] += len(batch_values)
                            
                        elif dialect_name == 'sqlite':
                            # Use SQLite bulk upsert  
                            stmt = sqlite_insert(TelegramMessage).values(batch_values)
                            if update_if_exists:
                                update_dict = {c.name: stmt.excluded[c.name] 
                                             for c in TelegramMessage.__table__.columns 
                                             if c.name not in ['message_id', 'channel_id', 'created_at']}
                                stmt = stmt.on_conflict_do_update(
                                    index_elements=['message_id', 'channel_id'],
                                    set_=update_dict
                                )
                            else:
                                stmt = stmt.on_conflict_do_nothing(
                                    index_elements=['message_id', 'channel_id']
                                )
                            
                            result = await session.execute(stmt)
                            await session.commit()
                            stats['inserted'] += len(batch_values)
                            
                        else:
                            # Fallback: Use individual saves for other databases
                            for values in batch_values:
                                try:
                                    # Check if exists
                                    existing = await session.execute(
                                        select(TelegramMessage).where(
                                            and_(
                                                TelegramMessage.message_id == values['message_id'],
                                                TelegramMessage.channel_id == values['channel_id']
                                            )
                                        )
                                    )
                                    existing = existing.scalar_one_or_none()
                                    
                                    if existing:
                                        if update_if_exists:
                                            for key, value in values.items():
                                                if key not in ['message_id', 'channel_id'] and value is not None:
                                                    setattr(existing, key, value)
                                            stats['updated'] += 1
                                        else:
                                            stats['skipped'] += 1
                                    else:
                                        message_obj = TelegramMessage(**values)
                                        session.add(message_obj)
                                        stats['inserted'] += 1
                                        
                                except Exception as e:
                                    logger.error(f"Error in fallback bulk save: {e}")
                                    stats['errors'] += 1
                            
                            await session.commit()
                        
                        stats['total_processed'] += len(batch_values)
                        
                    except Exception as e:
                        logger.error(f"Error in bulk save batch: {e}")
                        await session.rollback()
                        stats['errors'] += len(batch)
                        
            logger.info(f"Processed batch of {len(batch)} messages")
        
        logger.info(f"✅ Bulk save completed: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Failed in bulk message save: {e}")
        if not session_provided and session:
            await session.rollback()
        stats['errors'] = len(messages_data)
        return stats


async def save_telegram_channel(
    channel_data: Dict[str, Any],
    session: Optional[AsyncSession] = None
) -> Optional[TelegramChannel]:
    """
    Save or update a Telegram channel in the database.
    
    Args:
        channel_data: Dictionary containing channel data from Telethon
        session: Optional existing async session. If None, creates a new one.
        
    Returns:
        Optional[TelegramChannel]: The saved channel object, or None if failed
    """
    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy import select
    
    # Validate required fields
    if 'id' not in channel_data or channel_data['id'] is None:
        raise ValueError("Missing required field: id")
    
    try:
        channel_id = int(channel_data['id'])
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid channel_id type: {e}")
    
    # Create or update channel object
    telegram_channel = TelegramChannel(
        channel_id=channel_id,
        username=channel_data.get('username'),
        title=channel_data.get('title', 'Unknown Channel'),
        description=channel_data.get('description') or channel_data.get('about'),
        member_count=channel_data.get('participants_count') or channel_data.get('member_count'),
        
        # Platform metadata
        is_verified=channel_data.get('is_verified', False),
        is_scam=channel_data.get('is_scam', False),
        is_fake=channel_data.get('is_fake', False),
        
        # Update timestamps
        last_checked=datetime.now(),
    )
    
    # Handle session management
    session_provided = session is not None
    if not session_provided:
        session = get_telegram_session()
    
    try:
        if session_provided:
            # Use provided session - merge to handle updates
            session.add(telegram_channel)
            await session.flush()
            logger.debug(f"Added/updated channel {channel_id} ({telegram_channel.title}) to session")
            return telegram_channel
        else:
            # Use our own session - commit automatically
            async with session:
                # Use merge to handle existing records
                merged_channel = await session.merge(telegram_channel)
                await session.commit()
                logger.info(f"✅ Saved/updated channel {channel_id} ({merged_channel.title})")
                return merged_channel
                
    except Exception as e:
        logger.error(f"Failed to save channel {channel_id}: {e}")
        if not session_provided:
            await session.rollback()
        return None


# Export all the important functions and classes
__all__ = [
    'init_telegram_db',
    'get_telegram_session', 
    'get_telegram_engine',
    'close_telegram_db',
    'channel_exists',
    'message_exists',
    'get_active_channels',
    'get_channel_by_username',
    'get_recent_messages',
    'save_telegram_message',
    'save_telegram_messages_bulk',
    'save_telegram_channel',
    'health_check',
    'TelegramChannel',
    'TelegramMessage', 
    'ChannelMetric'
] 