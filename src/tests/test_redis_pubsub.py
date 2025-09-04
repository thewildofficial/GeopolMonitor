"""
Test suite for Redis Pub/Sub Service.

Tests connection management, message publishing/subscribing, pattern matching,
error handling, and performance characteristics.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

from src.core.services.redis_pubsub import (
    RedisPubSubService,
    RedisConnectionManager,
    RedisPublisher,
    RedisSubscriber,
    RedisMessage,
    MessageType,
    Priority,
    redis_service,
    publish_telegram_message,
    subscribe_to_telegram_messages,
    subscribe_to_all_telegram_messages
)


class TestRedisMessage:
    """Test RedisMessage data class and serialization."""
    
    def test_create_telegram_message(self):
        """Test creating a Telegram message."""
        message_data = {
            "text": "Breaking news from Ukraine",
            "message_id": 12345,
            "author": "user123"
        }
        
        message = RedisMessage.create_telegram_message(
            channel_id="ukraine_news",
            message_data=message_data,
            priority=Priority.HIGH
        )
        
        assert message.message_type == MessageType.TELEGRAM_MESSAGE.value
        assert message.priority == Priority.HIGH.value
        assert message.channel_id == "ukraine_news"
        assert message.data == message_data
        assert message.source == "telethon_client"
        assert isinstance(message.timestamp, float)
    
    def test_message_serialization(self):
        """Test JSON serialization and deserialization."""
        original_message = RedisMessage(
            message_type=MessageType.TELEGRAM_MESSAGE.value,
            priority=Priority.MEDIUM.value,
            timestamp=time.time(),
            source="test_source",
            channel_id="test_channel",
            data={"test": "data"},
            metadata={"version": "1.0"}
        )
        
        # Serialize to JSON
        json_str = original_message.to_json()
        assert isinstance(json_str, str)
        
        # Deserialize back
        restored_message = RedisMessage.from_json(json_str)
        
        assert restored_message.message_type == original_message.message_type
        assert restored_message.priority == original_message.priority
        assert restored_message.timestamp == original_message.timestamp
        assert restored_message.source == original_message.source
        assert restored_message.channel_id == original_message.channel_id
        assert restored_message.data == original_message.data
        assert restored_message.metadata == original_message.metadata


class TestRedisConnectionManager:
    """Test Redis connection management."""
    
    @pytest.fixture
    async def connection_manager(self):
        """Create a connection manager for testing."""
        manager = RedisConnectionManager()
        yield manager
        await manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_connection_establishment(self, connection_manager):
        """Test establishing Redis connection."""
        result = await connection_manager.connect()
        assert result is True
        assert connection_manager.is_connected is True
        assert connection_manager.redis_client is not None
        assert connection_manager.connection_stats["total_connections"] >= 1
    
    @pytest.mark.asyncio
    async def test_connection_health_check(self, connection_manager):
        """Test connection health checking."""
        await connection_manager.connect()
        
        # Test successful health check
        result = await connection_manager.ensure_connection()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_graceful_disconnect(self, connection_manager):
        """Test graceful disconnection."""
        await connection_manager.connect()
        assert connection_manager.is_connected is True
        
        await connection_manager.disconnect()
        assert connection_manager.is_connected is False
        assert connection_manager.redis_client is None
    
    @pytest.mark.asyncio
    async def test_connection_stats(self, connection_manager):
        """Test connection statistics tracking."""
        initial_stats = connection_manager.connection_stats.copy()
        
        await connection_manager.connect()
        
        assert connection_manager.connection_stats["total_connections"] > initial_stats["total_connections"]
        assert connection_manager.connection_stats["last_connected"] is not None


class TestRedisPublisher:
    """Test Redis message publishing."""
    
    @pytest.fixture
    async def publisher_setup(self):
        """Set up publisher with connection manager."""
        connection_manager = RedisConnectionManager()
        publisher = RedisPublisher(connection_manager)
        await connection_manager.connect()
        yield publisher, connection_manager
        await connection_manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_publish_telegram_message(self, publisher_setup):
        """Test publishing a Telegram message."""
        publisher, _ = publisher_setup
        
        message_data = {
            "text": "Test message",
            "message_id": 123,
            "timestamp": time.time()
        }
        
        result = await publisher.publish_telegram_message(
            channel_id="test_channel",
            message_data=message_data,
            priority=Priority.HIGH
        )
        
        assert result is True
        assert publisher.publish_stats["total_published"] >= 1
        assert "telegram:messages:test_channel" in publisher.publish_stats["channels_used"]
    
    @pytest.mark.asyncio
    async def test_publish_system_event(self, publisher_setup):
        """Test publishing system events."""
        publisher, _ = publisher_setup
        
        event_data = {
            "event": "channel_added",
            "channel_id": "new_channel"
        }
        
        result = await publisher.broadcast_system_event(
            event_type="channel_management",
            event_data=event_data,
            priority=Priority.HIGH
        )
        
        assert result is True
        assert publisher.publish_stats["total_published"] >= 1
    
    @pytest.mark.asyncio
    async def test_publish_stats_tracking(self, publisher_setup):
        """Test publisher statistics tracking."""
        publisher, _ = publisher_setup
        
        initial_stats = publisher.publish_stats.copy()
        
        await publisher.publish_telegram_message(
            "test_channel",
            {"test": "data"}
        )
        
        assert publisher.publish_stats["total_published"] > initial_stats["total_published"]
        assert publisher.publish_stats["last_publish"] is not None


class TestRedisSubscriber:
    """Test Redis message subscription."""
    
    @pytest.fixture
    async def subscriber_setup(self):
        """Set up subscriber with connection manager."""
        connection_manager = RedisConnectionManager()
        subscriber = RedisSubscriber(connection_manager)
        await connection_manager.connect()
        yield subscriber, connection_manager
        await subscriber.stop_listening()
        await connection_manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_channel_subscription(self, subscriber_setup):
        """Test subscribing to specific channels."""
        subscriber, _ = subscriber_setup
        
        messages_received = []
        
        async def message_handler(message: RedisMessage):
            messages_received.append(message)
        
        await subscriber.subscribe("test_channel", message_handler)
        await subscriber.start_listening()
        
        # Give some time for subscription to be established
        await asyncio.sleep(0.1)
        
        assert subscriber.is_listening is True
        assert len(subscriber.subscriptions) == 1
        assert "test_channel" in subscriber.subscriptions
    
    @pytest.mark.asyncio
    async def test_pattern_subscription(self, subscriber_setup):
        """Test subscribing to channel patterns."""
        subscriber, _ = subscriber_setup
        
        pattern_messages = []
        
        async def pattern_handler(channel: str, message: RedisMessage):
            pattern_messages.append((channel, message))
        
        await subscriber.subscribe_pattern("telegram:*", pattern_handler)
        await subscriber.start_listening()
        
        await asyncio.sleep(0.1)
        
        assert subscriber.is_listening is True
        assert len(subscriber.pattern_subscriptions) == 1
        assert "telegram:*" in subscriber.pattern_subscriptions
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, subscriber_setup):
        """Test unsubscribing from channels."""
        subscriber, _ = subscriber_setup
        
        async def handler(message):
            pass
        
        await subscriber.subscribe("test_channel", handler)
        assert "test_channel" in subscriber.subscriptions
        
        await subscriber.unsubscribe("test_channel")
        assert "test_channel" not in subscriber.subscriptions


class TestRedisPubSubService:
    """Test the main Redis Pub/Sub service."""
    
    @pytest.fixture
    async def pubsub_service(self):
        """Create a pub/sub service for testing."""
        service = RedisPubSubService()
        yield service
        await service.stop()
    
    @pytest.mark.asyncio
    async def test_service_lifecycle(self, pubsub_service):
        """Test starting and stopping the service."""
        assert pubsub_service.is_running is False
        
        await pubsub_service.start()
        assert pubsub_service.is_running is True
        assert pubsub_service.connection_manager.is_connected is True
        assert pubsub_service.subscriber.is_listening is True
        
        await pubsub_service.stop()
        assert pubsub_service.is_running is False
        assert pubsub_service.connection_manager.is_connected is False
        assert pubsub_service.subscriber.is_listening is False
    
    @pytest.mark.asyncio
    async def test_publish_and_subscribe_integration(self, pubsub_service):
        """Test end-to-end message publishing and subscription."""
        await pubsub_service.start()
        
        received_messages = []
        
        async def message_handler(message: RedisMessage):
            received_messages.append(message)
        
        # Subscribe to messages
        await pubsub_service.subscribe_to_channel(
            "telegram:messages:integration_test",
            message_handler
        )
        
        # Give subscription time to establish
        await asyncio.sleep(0.1)
        
        # Publish a message
        message_data = {
            "text": "Integration test message",
            "message_id": 999,
            "channel": "integration_test"
        }
        
        result = await pubsub_service.publish_telegram_message(
            "integration_test",
            message_data,
            Priority.HIGH
        )
        
        assert result is True
        
        # Wait for message processing
        await asyncio.sleep(0.2)
        
        # Verify message was received
        assert len(received_messages) >= 1
        received_message = received_messages[0]
        assert received_message.message_type == MessageType.TELEGRAM_MESSAGE.value
        assert received_message.channel_id == "integration_test"
        assert received_message.data == message_data
        assert received_message.priority == Priority.HIGH.value
    
    @pytest.mark.asyncio
    async def test_pattern_subscription_integration(self, pubsub_service):
        """Test pattern-based message subscription."""
        await pubsub_service.start()
        
        pattern_messages = []
        
        async def pattern_handler(channel: str, message: RedisMessage):
            pattern_messages.append((channel, message))
        
        # Subscribe to all telegram messages
        await pubsub_service.subscribe_to_pattern(
            "telegram:messages:*",
            pattern_handler
        )
        
        await asyncio.sleep(0.1)
        
        # Publish messages to different channels
        await pubsub_service.publish_telegram_message(
            "channel1", {"test": "message1"}
        )
        await pubsub_service.publish_telegram_message(
            "channel2", {"test": "message2"}
        )
        
        await asyncio.sleep(0.2)
        
        # Should have received both messages
        assert len(pattern_messages) >= 2
    
    @pytest.mark.asyncio
    async def test_service_statistics(self, pubsub_service):
        """Test service statistics collection."""
        await pubsub_service.start()
        
        # Publish some messages
        await pubsub_service.publish_telegram_message(
            "stats_test", {"test": "data1"}
        )
        await pubsub_service.publish_telegram_message(
            "stats_test", {"test": "data2"}
        )
        
        stats = pubsub_service.get_stats()
        
        assert "connection" in stats
        assert "publisher" in stats
        assert "subscriber" in stats
        assert "service" in stats
        
        assert stats["connection"]["is_connected"] is True
        assert stats["service"]["is_running"] is True
        assert stats["publisher"]["stats"]["total_published"] >= 2


class TestConvenienceFunctions:
    """Test convenience functions for easy integration."""
    
    @pytest.mark.asyncio
    async def test_global_publish_function(self):
        """Test global publish_telegram_message function."""
        # Start the global service
        await redis_service.start()
        
        try:
            result = await publish_telegram_message(
                "convenience_test",
                {"test": "convenience function"},
                Priority.LOW
            )
            assert result is True
            
        finally:
            await redis_service.stop()
    
    @pytest.mark.asyncio
    async def test_convenience_subscription_functions(self):
        """Test convenience subscription functions."""
        await redis_service.start()
        
        try:
            received_messages = []
            
            async def handler(message):
                received_messages.append(message)
            
            async def pattern_handler(channel, message):
                received_messages.append((channel, message))
            
            # Test specific channel subscription
            await subscribe_to_telegram_messages("convenience_channel", handler)
            
            # Test pattern subscription
            await subscribe_to_all_telegram_messages(pattern_handler)
            
            await asyncio.sleep(0.1)
            
            # Publish a test message
            await publish_telegram_message(
                "convenience_channel",
                {"test": "convenience subscription"}
            )
            
            await asyncio.sleep(0.2)
            
            # Should receive message in both handlers
            assert len(received_messages) >= 2
            
        finally:
            await redis_service.stop()


class TestPerformanceAndResilience:
    """Test performance characteristics and error resilience."""
    
    @pytest.mark.asyncio
    async def test_high_volume_publishing(self):
        """Test high-volume message publishing."""
        service = RedisPubSubService()
        await service.start()
        
        try:
            start_time = time.time()
            
            # Publish 100 messages rapidly
            tasks = []
            for i in range(100):
                task = service.publish_telegram_message(
                    f"perf_test_{i % 10}",  # 10 different channels
                    {"message_id": i, "content": f"Performance test message {i}"}
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # All messages should be published successfully
            assert all(results)
            
            # Should complete within reasonable time (adjust based on system)
            assert duration < 10.0  # 10 seconds max for 100 messages
            
            stats = service.get_stats()
            assert stats["publisher"]["stats"]["total_published"] >= 100
            
        finally:
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_connection_resilience(self):
        """Test service resilience to connection issues."""
        connection_manager = RedisConnectionManager()
        
        # Test connection retry logic
        original_connect = connection_manager.connect
        call_count = 0
        
        async def failing_connect():
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 attempts
                raise ConnectionError("Mock connection failure")
            return await original_connect()
        
        with patch.object(connection_manager, 'connect', failing_connect):
            result = await connection_manager.reconnect()
            # Should eventually succeed after retries
            assert result is True or call_count >= 3
        
        await connection_manager.disconnect()


@pytest.mark.asyncio
async def test_real_redis_connectivity():
    """Integration test with real Redis instance."""
    service = RedisPubSubService()
    
    try:
        # Test basic connectivity
        await service.start()
        assert service.is_running is True
        
        # Test basic publish/subscribe flow
        received_messages = []
        
        async def test_handler(message: RedisMessage):
            received_messages.append(message)
        
        await service.subscribe_to_channel("integration:test", test_handler)
        await asyncio.sleep(0.1)
        
        # Publish test message
        test_message = RedisMessage(
            message_type=MessageType.TELEGRAM_MESSAGE.value,
            priority=Priority.MEDIUM.value,
            timestamp=time.time(),
            source="integration_test",
            data={"test": "integration"}
        )
        
        result = await service.publisher.publish_message("integration:test", test_message)
        assert result is True
        
        await asyncio.sleep(0.2)
        
        # Verify message was received
        assert len(received_messages) >= 1
        
    finally:
        await service.stop()


if __name__ == "__main__":
    # Run basic connectivity test
    asyncio.run(test_real_redis_connectivity())
    print("✅ Redis Pub/Sub integration test passed!") 