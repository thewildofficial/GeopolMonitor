#!/usr/bin/env python3
"""
Test script for Telegram client infrastructure

This script tests the basic functionality of the Telegram monitoring client
including connection, authentication, and basic message handling.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from telegram.telegram_client import telegram_monitor, TelegramMessage


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_message_handler(message: TelegramMessage):
    """Test message handler for processing incoming messages"""
    logger.info(f"Received message from {message.channel_username}: {message.text[:100]}...")
    
    # Example processing logic
    if any(keyword in message.text.lower() for keyword in ['breaking', 'urgent', 'alert']):
        message.urgency_level = "breaking"
        logger.warning(f"BREAKING NEWS detected in {message.channel_username}")
    
    # Geographic tagging example
    if any(region in message.text.lower() for region in ['ukraine', 'russia', 'europe']):
        message.geographic_tags = ['europe']
    elif any(region in message.text.lower() for region in ['china', 'taiwan', 'korea', 'japan']):
        message.geographic_tags = ['asia']
    

async def test_client_initialization():
    """Test basic client initialization"""
    logger.info("Testing Telegram client initialization...")
    
    try:
        success = await telegram_monitor.initialize()
        if success:
            logger.info("✅ Telegram client initialized successfully")
            return True
        else:
            logger.error("❌ Failed to initialize Telegram client")
            return False
    except Exception as e:
        logger.error(f"❌ Error during initialization: {e}")
        return False


async def test_add_test_channel():
    """Test adding a test channel (you can change this to a channel you have access to)"""
    logger.info("Testing channel addition...")
    
    # Replace with a channel you have access to for testing
    test_channel = "@test_channel_username"  # Change this!
    
    try:
        success = await telegram_monitor.add_channel(
            test_channel, 
            credibility_tier="emerging", 
            region="global"
        )
        
        if success:
            logger.info(f"✅ Successfully added test channel: {test_channel}")
        else:
            logger.warning(f"⚠️  Could not add test channel: {test_channel}")
            logger.info("This is normal if you don't have access to the test channel")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error adding test channel: {e}")
        return False


async def test_stats_and_monitoring():
    """Test statistics and monitoring info"""
    logger.info("Testing statistics and monitoring info...")
    
    try:
        stats = telegram_monitor.get_stats()
        logger.info(f"📊 Client statistics: {stats}")
        
        channels = telegram_monitor.get_monitored_channels()
        logger.info(f"📡 Monitored channels: {len(channels)}")
        
        for channel in channels:
            logger.info(f"  - {channel.username} ({channel.title}) - {channel.credibility_tier}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")
        return False


async def test_redis_connection():
    """Test Redis connection for message buffering"""
    logger.info("Testing Redis connection...")
    
    try:
        import redis
        from config.settings import REDIS_URL
        
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        
        logger.info("✅ Redis connection successful")
        
        # Test basic operations
        redis_client.set("test_key", "test_value", ex=60)
        value = redis_client.get("test_key")
        
        if value == "test_value":
            logger.info("✅ Redis read/write operations working")
            redis_client.delete("test_key")
            return True
        else:
            logger.error("❌ Redis read/write test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        logger.info("Make sure Redis is installed and running:")
        logger.info("  macOS: brew install redis && brew services start redis")
        logger.info("  Ubuntu: sudo apt install redis-server && sudo systemctl start redis")
        return False


async def main():
    """Main test function"""
    logger.info("🚀 Starting Telegram Client Infrastructure Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Client Initialization", test_client_initialization),
        ("Statistics and Monitoring", test_stats_and_monitoring),
        ("Add Test Channel", test_add_test_channel),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running test: {test_name}")
        try:
            result = await test_func()
            results[test_name] = result
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.warning(f"⚠️  {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📋 TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Your Telegram client infrastructure is ready.")
    else:
        logger.warning("⚠️  Some tests failed. Check the logs above for details.")
        logger.info("\nCommon issues:")
        logger.info("1. Missing environment variables in .env file")
        logger.info("2. Redis not installed or running")
        logger.info("3. Invalid Telegram API credentials")
        logger.info("4. Network connectivity issues")
    
    # Add message handler for future testing
    telegram_monitor.add_message_handler(test_message_handler)
    logger.info("\n💡 Message handler added for future message processing tests")
    
    # Cleanup
    try:
        await telegram_monitor.stop()
    except:
        pass


if __name__ == "__main__":
    # Check for required environment variables
    from config.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH, REDIS_URL
    
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        logger.error("❌ Missing required environment variables!")
        logger.error("Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in your .env file")
        logger.error("See telegram_env_setup.md for instructions")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1) 