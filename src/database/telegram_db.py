"""
Async database configuration and session management for Telegram models.

This module provides async database engine, session factory, and utility functions
for managing Telegram data using SQLAlchemy 2.0 with async support.
"""

import os
import logging
from typing import AsyncGenerator, Optional
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
    'health_check',
    'TelegramChannel',
    'TelegramMessage', 
    'ChannelMetric'
] 