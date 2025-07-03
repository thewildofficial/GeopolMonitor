"""
Simple Redis Pub/Sub test script for debugging.
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.services.redis_pubsub import (
    RedisPubSubService, 
    RedisMessage, 
    Priority, 
    MessageType
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_basic_connectivity():
    """Test basic Redis connectivity."""
    service = RedisPubSubService()
    
    try:
        logger.info("🔌 Testing Redis connectivity...")
        await service.start()
        
        logger.info("✅ Redis connection established!")
        
        # Test basic publish without subscription first
        result = await service.publish_telegram_message(
            "test_channel",
            {"test": "basic connectivity"},
            Priority.MEDIUM
        )
        
        logger.info(f"📤 Publish result: {result}")
        
        stats = service.get_stats()
        logger.info(f"📊 Service stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Redis connectivity test failed: {e}")
        return False
    finally:
        await service.stop()
        logger.info("🔌 Redis connection closed")

async def test_pubsub_flow():
    """Test complete publish/subscribe flow."""
    service = RedisPubSubService()
    received_messages = []
    
    try:
        logger.info("🔄 Testing full Pub/Sub flow...")
        
        # Start service
        await service.start()
        logger.info("✅ Service started")
        
        # Define message handler
        async def message_handler(message: RedisMessage):
            logger.info(f"📨 Received message: {message.data}")
            received_messages.append(message)
        
        # Subscribe to channel BEFORE publishing
        channel_name = "telegram:messages:test_flow"
        await service.subscribe_to_channel(channel_name, message_handler)
        logger.info(f"👂 Subscribed to {channel_name}")
        
        # Give subscription time to establish
        await asyncio.sleep(0.5)
        
        # Publish message
        message_data = {"text": "Test flow message", "id": 123}
        result = await service.publish_telegram_message(
            "test_flow",
            message_data,
            Priority.HIGH
        )
        
        logger.info(f"📤 Published message, result: {result}")
        
        # Wait for message processing
        await asyncio.sleep(1.0)
        
        # Check results
        logger.info(f"📊 Messages received: {len(received_messages)}")
        
        if received_messages:
            msg = received_messages[0]
            logger.info(f"📥 First message details:")
            logger.info(f"   Type: {msg.message_type}")
            logger.info(f"   Channel: {msg.channel_id}")
            logger.info(f"   Data: {msg.data}")
            logger.info(f"   Priority: {msg.priority}")
        
        stats = service.get_stats()
        logger.info(f"📊 Final stats:")
        logger.info(f"   Published: {stats['publisher']['stats']['total_published']}")
        logger.info(f"   Received: {stats['subscriber']['stats']['total_received']}")
        logger.info(f"   Processed: {stats['subscriber']['stats']['messages_processed']}")
        
        return len(received_messages) > 0
        
    except Exception as e:
        logger.error(f"❌ Pub/Sub flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await service.stop()
        logger.info("🔌 Service stopped")

async def test_pattern_subscription():
    """Test pattern-based subscription."""
    service = RedisPubSubService()
    pattern_messages = []
    
    try:
        logger.info("🔍 Testing pattern subscription...")
        
        await service.start()
        
        async def pattern_handler(channel: str, message: RedisMessage):
            logger.info(f"🎯 Pattern matched - Channel: {channel}, Message: {message.data}")
            pattern_messages.append((channel, message))
        
        # Subscribe to pattern
        await service.subscribe_to_pattern("telegram:messages:*", pattern_handler)
        logger.info("👂 Subscribed to pattern: telegram:messages:*")
        
        await asyncio.sleep(0.5)
        
        # Publish to multiple channels
        channels = ["pattern_test_1", "pattern_test_2"]
        for i, channel in enumerate(channels):
            result = await service.publish_telegram_message(
                channel,
                {"test": f"pattern message {i+1}", "channel": channel}
            )
            logger.info(f"📤 Published to {channel}: {result}")
        
        await asyncio.sleep(1.0)
        
        logger.info(f"📊 Pattern messages received: {len(pattern_messages)}")
        
        for channel, message in pattern_messages:
            logger.info(f"   {channel}: {message.data}")
        
        return len(pattern_messages) >= 2
        
    except Exception as e:
        logger.error(f"❌ Pattern subscription test failed: {e}")
        return False
    finally:
        await service.stop()

async def main():
    """Run all tests."""
    logger.info("🚀 Starting Redis Pub/Sub tests...")
    
    tests = [
        ("Basic Connectivity", test_basic_connectivity),
        ("Pub/Sub Flow", test_pubsub_flow),
        ("Pattern Subscription", test_pattern_subscription)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 Running: {test_name}")
        logger.info('='*50)
        
        try:
            result = await test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"🏁 {test_name}: {status}")
        except Exception as e:
            logger.error(f"💥 {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("📋 TEST SUMMARY")
    logger.info('='*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status} {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\n🏆 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        logger.info("🎉 All tests passed! Redis Pub/Sub is working correctly.")
    else:
        logger.warning("⚠️  Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    asyncio.run(main()) 