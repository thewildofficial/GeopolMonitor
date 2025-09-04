"""
Unit tests for Telegram database models.

Tests model definitions, relationships, constraints, and basic database operations.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from src.database.telegram_db import (
    init_telegram_db, 
    get_telegram_session, 
    close_telegram_db,
    channel_exists,
    message_exists,
    get_active_channels,
    get_channel_by_username,
    get_recent_messages,
    health_check
)
from src.database.models.telegram_models import TelegramChannel, TelegramMessage, ChannelMetric


@pytest.fixture(scope="function")
async def telegram_db():
    """Initialize a test database for each test."""
    # Use in-memory SQLite for testing
    engine = await init_telegram_db("sqlite+aiosqlite:///:memory:", echo=False)
    yield engine
    await close_telegram_db()


@pytest.fixture
async def sample_channel(telegram_db):
    """Create a sample channel for testing."""
    channel_data = {
        'channel_id': 123456789,
        'username': 'test_channel',
        'title': 'Test Channel',
        'description': 'A test channel for unit testing',
        'region': 'Europe',
        'country': 'Germany',
        'language': 'en',
        'category': 'news',
        'credibility_score': 8.5,
        'reliability_weight': 1.0,
        'is_active': True,
        'priority_level': 7,
        'channel_type': 'channel',
        'is_verified': True,
        'is_scam': False,
        'is_fake': False
    }
    
    async with get_telegram_session() as session:
        channel = TelegramChannel(**channel_data)
        session.add(channel)
        await session.commit()
        await session.refresh(channel)
        return channel


@pytest.fixture
async def sample_message(telegram_db, sample_channel):
    """Create a sample message for testing."""
    message_data = {
        'message_id': 987654321,
        'channel_id': sample_channel.channel_id,
        'text': 'This is a test message',
        'raw_text': 'This is a test message',
        'date': datetime.now(timezone.utc),
        'from_user_id': 555666777,
        'from_username': 'test_user',
        'message_type': 'text',
        'has_media': False,
        'views': 100,
        'forwards': 5,
        'replies': 2,
        'ai_processed': False,
        'sentiment_score': 0.5,
        'urgency_score': 3.0,
        'relevance_score': 7.5,
        'detected_language': 'en',
        'categories': ['news', 'politics'],
        'detected_locations': ['Berlin', 'Germany'],
        'time_sensitivity': 'normal'
    }
    
    async with get_telegram_session() as session:
        message = TelegramMessage(**message_data)
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message


class TestTelegramChannel:
    """Test cases for TelegramChannel model."""
    
    @pytest.mark.asyncio
    async def test_channel_creation(self, telegram_db):
        """Test basic channel creation."""
        channel_data = {
            'channel_id': 123456789,
            'username': 'test_channel',
            'title': 'Test Channel',
            'language': 'en',
            'category': 'news'
        }
        
        async with get_telegram_session() as session:
            channel = TelegramChannel(**channel_data)
            session.add(channel)
            await session.commit()
            
            # Verify the channel was created
            result = await session.execute(
                select(TelegramChannel).where(TelegramChannel.channel_id == 123456789)
            )
            saved_channel = result.scalar_one()
            
            assert saved_channel.channel_id == 123456789
            assert saved_channel.username == 'test_channel'
            assert saved_channel.title == 'Test Channel'
            assert saved_channel.is_active is True  # Default value
            assert saved_channel.priority_level == 5  # Default value
            assert saved_channel.credibility_score == 5.0  # Default value
    
    @pytest.mark.asyncio
    async def test_channel_unique_constraints(self, telegram_db):
        """Test that username must be unique."""
        channel_data = {
            'channel_id': 123456789,
            'username': 'unique_channel',
            'title': 'First Channel',
            'language': 'en',
            'category': 'news'
        }
        
        async with get_telegram_session() as session:
            # Create first channel
            channel1 = TelegramChannel(**channel_data)
            session.add(channel1)
            await session.commit()
            
            # Try to create second channel with same username
            channel_data['channel_id'] = 987654321
            channel_data['title'] = 'Second Channel'
            channel2 = TelegramChannel(**channel_data)
            session.add(channel2)
            
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
    
    @pytest.mark.asyncio
    async def test_channel_defaults(self, telegram_db):
        """Test that default values are properly set."""
        minimal_data = {
            'channel_id': 123456789,
            'title': 'Minimal Channel'
        }
        
        async with get_telegram_session() as session:
            channel = TelegramChannel(**minimal_data)
            session.add(channel)
            await session.commit()
            await session.refresh(channel)
            
            assert channel.language == 'en'
            assert channel.category == 'general'
            assert channel.credibility_score == 5.0
            assert channel.reliability_weight == 1.0
            assert channel.is_active is True
            assert channel.priority_level == 5
            assert channel.channel_type == 'channel'
            assert channel.is_verified is False
            assert channel.is_scam is False
            assert channel.is_fake is False
    
    @pytest.mark.asyncio
    async def test_channel_relationships(self, telegram_db, sample_channel):
        """Test that channel relationships work correctly."""
        async with get_telegram_session() as session:
            # Reload the channel to test relationships
            result = await session.execute(
                select(TelegramChannel).where(TelegramChannel.channel_id == sample_channel.channel_id)
            )
            channel = result.scalar_one()
            
            # Initially no messages or metrics
            assert len(channel.messages) == 0
            assert len(channel.metrics) == 0


class TestTelegramMessage:
    """Test cases for TelegramMessage model."""
    
    @pytest.mark.asyncio
    async def test_message_creation(self, telegram_db, sample_channel):
        """Test basic message creation."""
        message_data = {
            'message_id': 987654321,
            'channel_id': sample_channel.channel_id,
            'text': 'Test message content',
            'date': datetime.now(timezone.utc),
            'message_type': 'text'
        }
        
        async with get_telegram_session() as session:
            message = TelegramMessage(**message_data)
            session.add(message)
            await session.commit()
            
            # Verify the message was created
            result = await session.execute(
                select(TelegramMessage).where(
                    TelegramMessage.message_id == 987654321,
                    TelegramMessage.channel_id == sample_channel.channel_id
                )
            )
            saved_message = result.scalar_one()
            
            assert saved_message.message_id == 987654321
            assert saved_message.channel_id == sample_channel.channel_id
            assert saved_message.text == 'Test message content'
            assert saved_message.message_type == 'text'
            assert saved_message.has_media is False  # Default value
            assert saved_message.ai_processed is False  # Default value
    
    @pytest.mark.asyncio
    async def test_message_foreign_key_constraint(self, telegram_db):
        """Test that messages require valid channel_id."""
        message_data = {
            'message_id': 987654321,
            'channel_id': 999999999,  # Non-existent channel
            'text': 'Test message',
            'date': datetime.now(timezone.utc)
        }
        
        async with get_telegram_session() as session:
            message = TelegramMessage(**message_data)
            session.add(message)
            
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
    
    @pytest.mark.asyncio
    async def test_message_composite_primary_key(self, telegram_db, sample_channel):
        """Test that composite primary key (message_id, channel_id) works."""
        message_data = {
            'message_id': 123,
            'channel_id': sample_channel.channel_id,
            'text': 'First message',
            'date': datetime.now(timezone.utc)
        }
        
        async with get_telegram_session() as session:
            # Create first message
            message1 = TelegramMessage(**message_data)
            session.add(message1)
            await session.commit()
            
            # Try to create message with same ID in same channel (should fail)
            message_data['text'] = 'Duplicate message'
            message2 = TelegramMessage(**message_data)
            session.add(message2)
            
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
    
    @pytest.mark.asyncio
    async def test_message_relationship_to_channel(self, telegram_db, sample_message):
        """Test message-to-channel relationship."""
        async with get_telegram_session() as session:
            # Load message with relationship
            result = await session.execute(
                select(TelegramMessage)
                .where(TelegramMessage.message_id == sample_message.message_id)
                .where(TelegramMessage.channel_id == sample_message.channel_id)
            )
            message = result.scalar_one()
            
            # Access the related channel
            channel = message.channel
            assert channel is not None
            assert channel.channel_id == sample_message.channel_id
            assert channel.username == 'test_channel'


class TestChannelMetric:
    """Test cases for ChannelMetric model."""
    
    @pytest.mark.asyncio
    async def test_metric_creation(self, telegram_db, sample_channel):
        """Test basic metric creation."""
        metric_data = {
            'channel_id': sample_channel.channel_id,
            'measurement_period': 'daily',
            'total_messages': 150,
            'messages_per_hour': 6.25,
            'avg_views': 250.5,
            'activity_score': 8.5
        }
        
        async with get_telegram_session() as session:
            metric = ChannelMetric(**metric_data)
            session.add(metric)
            await session.commit()
            await session.refresh(metric)
            
            assert metric.channel_id == sample_channel.channel_id
            assert metric.measurement_period == 'daily'
            assert metric.total_messages == 150
            assert metric.messages_per_hour == 6.25
            assert metric.activity_score == 8.5
    
    @pytest.mark.asyncio
    async def test_metric_defaults(self, telegram_db, sample_channel):
        """Test metric default values."""
        minimal_data = {
            'channel_id': sample_channel.channel_id
        }
        
        async with get_telegram_session() as session:
            metric = ChannelMetric(**minimal_data)
            session.add(metric)
            await session.commit()
            await session.refresh(metric)
            
            assert metric.measurement_period == 'daily'
            assert metric.total_messages == 0


class TestDatabaseUtilities:
    """Test utility functions."""
    
    @pytest.mark.asyncio
    async def test_channel_exists(self, telegram_db, sample_channel):
        """Test channel_exists utility function."""
        # Existing channel
        exists = await channel_exists(sample_channel.channel_id)
        assert exists is True
        
        # Non-existent channel
        exists = await channel_exists(999999999)
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_message_exists(self, telegram_db, sample_message):
        """Test message_exists utility function."""
        # Existing message
        exists = await message_exists(sample_message.message_id, sample_message.channel_id)
        assert exists is True
        
        # Non-existent message
        exists = await message_exists(999999999, sample_message.channel_id)
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_get_active_channels(self, telegram_db, sample_channel):
        """Test get_active_channels utility function."""
        # Create an inactive channel
        inactive_channel_data = {
            'channel_id': 888888888,
            'title': 'Inactive Channel',
            'is_active': False
        }
        
        async with get_telegram_session() as session:
            inactive_channel = TelegramChannel(**inactive_channel_data)
            session.add(inactive_channel)
            await session.commit()
        
        # Get active channels
        active_channels = await get_active_channels()
        
        # Should only include the active channel
        assert len(active_channels) == 1
        assert active_channels[0].channel_id == sample_channel.channel_id
        assert active_channels[0].is_active is True
    
    @pytest.mark.asyncio
    async def test_get_channel_by_username(self, telegram_db, sample_channel):
        """Test get_channel_by_username utility function."""
        # Existing username
        channel = await get_channel_by_username('test_channel')
        assert channel is not None
        assert channel.channel_id == sample_channel.channel_id
        
        # Non-existent username
        channel = await get_channel_by_username('nonexistent_channel')
        assert channel is None
    
    @pytest.mark.asyncio
    async def test_health_check(self, telegram_db, sample_channel, sample_message):
        """Test database health check."""
        health = await health_check()
        
        assert health['status'] == 'healthy'
        assert health['connection'] == 'ok'
        assert health['channels'] >= 1  # At least our sample channel
        assert health['messages'] >= 1  # At least our sample message
        assert 'timestamp' in health


class TestModelValidation:
    """Test model validation and constraints."""
    
    @pytest.mark.asyncio
    async def test_invalid_data_types(self, telegram_db):
        """Test that invalid data types are handled."""
        with pytest.raises((ValueError, TypeError)):
            # Invalid channel_id type
            TelegramChannel(channel_id="not_a_number", title="Test")
    
    @pytest.mark.asyncio
    async def test_required_fields(self, telegram_db):
        """Test that required fields are enforced."""
        # Channel without required title
        with pytest.raises(TypeError):
            TelegramChannel(channel_id=123456789)  # Missing title
        
        # Message without required date
        async with get_telegram_session() as session:
            with pytest.raises((ValueError, TypeError)):
                message = TelegramMessage(
                    message_id=123,
                    channel_id=123456789,
                    text="Test"
                    # Missing required date field
                )
                session.add(message)
                await session.commit()


# Async test runner setup
if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 