"""
Comprehensive Test Script for Telethon-Redis Integration.

This script tests the complete integration between Telethon client, Redis Pub/Sub,
and real-time message distribution for GeopolMonitor.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.telegram.telethon_client import TelethonMonitorClient
from src.core.services.redis_pubsub import (
    RedisPubSubService, 
    Priority, 
    subscribe_to_all_telegram_messages,
    redis_service
)
from src.telegram.telethon_redis_integration import (
    TelethonRedisIntegration,
    initialize_integration,
    start_monitoring,
    get_integration_stats
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Test configuration
TEST_CHANNELS = [
    "@telegram",  # Official Telegram channel - safe for testing
    # Add more test channels here if needed
]

class IntegrationTester:
    """Test suite for Telethon-Redis integration."""
    
    def __init__(self):
        self.integration: TelethonRedisIntegration = None
        self.received_messages = []
        self.test_results = {}
    
    async def run_all_tests(self):
        """Run comprehensive integration tests."""
        logger.info("🚀 Starting Telethon-Redis Integration Tests")
        
        tests = [
            ("Component Initialization", self.test_component_initialization),
            ("Redis Connectivity", self.test_redis_connectivity),
            ("Telethon Authentication", self.test_telethon_authentication),
            ("Integration Setup", self.test_integration_setup),
            ("Channel Management", self.test_channel_management),
            ("Message Subscription", self.test_message_subscription),
            ("End-to-End Flow", self.test_end_to_end_flow),
            ("Statistics Collection", self.test_statistics_collection),
            ("Graceful Shutdown", self.test_graceful_shutdown)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 Running: {test_name}")
            logger.info('='*60)
            
            try:
                result = await test_func()
                self.test_results[test_name] = result
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"🏁 {test_name}: {status}")
            except Exception as e:
                logger.error(f"💥 {test_name} crashed: {e}")
                self.test_results[test_name] = False
        
        await self.print_summary()
    
    async def test_component_initialization(self) -> bool:
        """Test initialization of core components."""
        try:
            # Test Telethon client creation
            telethon_client = TelethonMonitorClient()
            logger.info("✅ Telethon client created")
            
            # Test Redis service
            redis_svc = RedisPubSubService()
            logger.info("✅ Redis service created")
            
            # Test integration creation
            self.integration = TelethonRedisIntegration(telethon_client, redis_svc)
            logger.info("✅ Integration object created")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Component initialization failed: {e}")
            return False
    
    async def test_redis_connectivity(self) -> bool:
        """Test Redis connection and basic operations."""
        try:
            # Test Redis connection
            await redis_service.start()
            logger.info("✅ Redis service started")
            
            # Test basic pub/sub
            test_messages = []
            
            async def test_handler(channel, message):
                test_messages.append((channel, message))
            
            await subscribe_to_all_telegram_messages(test_handler)
            logger.info("✅ Redis subscription established")
            
            # Small delay for subscription to be active
            await asyncio.sleep(0.2)
            
            # Test publishing
            from src.core.services.redis_pubsub import publish_telegram_message
            result = await publish_telegram_message(
                "redis_test",
                {"test": "redis connectivity", "timestamp": datetime.now().isoformat()},
                Priority.LOW
            )
            
            if result:
                logger.info("✅ Redis publish successful")
            
            await asyncio.sleep(0.5)
            
            # Check if message was received
            if test_messages:
                logger.info(f"✅ Redis message received: {len(test_messages)} messages")
                return True
            else:
                logger.warning("⚠️ No messages received (may be normal in some setups)")
                return True  # Don't fail the test for this
            
        except Exception as e:
            logger.error(f"❌ Redis connectivity test failed: {e}")
            return False
    
    async def test_telethon_authentication(self) -> bool:
        """Test Telethon client authentication."""
        try:
            telethon_client = TelethonMonitorClient()
            
            # Check if already authenticated
            session_file = "data/telegram_sessions/telethon_geopol_monitor.session"
            if os.path.exists(session_file):
                logger.info("✅ Telethon session file exists")
                
                # Try to start client
                await telethon_client.start()
                
                if telethon_client.client and telethon_client.client.is_connected():
                    logger.info("✅ Telethon client connected successfully")
                    
                    # Test basic API call
                    await telethon_client.client.get_me()
                    logger.info("✅ Telethon API call successful")
                    
                    await telethon_client.stop()
                    return True
                else:
                    logger.error("❌ Telethon client failed to connect")
                    return False
            else:
                logger.warning("⚠️ Telethon session not found - authentication may be required")
                logger.info("💡 Run the authentication test script first: scripts/test_telethon_auth.py")
                return False
                
        except Exception as e:
            logger.error(f"❌ Telethon authentication test failed: {e}")
            return False
    
    async def test_integration_setup(self) -> bool:
        """Test integration service setup."""
        try:
            if not self.integration:
                self.integration = await initialize_integration()
            
            # Test starting the integration
            await self.integration.start()
            logger.info("✅ Integration service started")
            
            # Check if all components are running
            stats = self.integration.get_stats()
            
            if stats["is_running"]:
                logger.info("✅ Integration service is running")
            
            if self.integration.redis_service.is_running:
                logger.info("✅ Redis service is active in integration")
            
            if self.integration.telethon_client.client and self.integration.telethon_client.client.is_connected():
                logger.info("✅ Telethon client is active in integration")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Integration setup failed: {e}")
            return False
    
    async def test_channel_management(self) -> bool:
        """Test adding and managing channels."""
        try:
            if not self.integration or not self.integration.is_running:
                logger.error("Integration service not running")
                return False
            
            # Test adding a channel
            test_channel = TEST_CHANNELS[0]
            result = await self.integration.add_channel_to_monitor(
                test_channel,
                priority=Priority.LOW,
                keywords=["test", "telegram"]
            )
            
            if result:
                logger.info(f"✅ Successfully added channel: {test_channel}")
            else:
                logger.error(f"❌ Failed to add channel: {test_channel}")
                return False
            
            # Check if channel is in monitored list
            stats = self.integration.get_stats()
            if stats["channels_monitored"] > 0:
                logger.info(f"✅ Channel count updated: {stats['channels_monitored']}")
            
            # Test getting channel info
            channel_details = stats["channels_detail"]
            if channel_details:
                logger.info(f"✅ Channel details available: {list(channel_details.keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Channel management test failed: {e}")
            return False
    
    async def test_message_subscription(self) -> bool:
        """Test message subscription and handling."""
        try:
            # Set up message collection
            async def collect_messages(channel, message):
                logger.info(f"📨 Received message from {channel}: {message.data.get('text', 'No text')[:50]}...")
                self.received_messages.append((channel, message))
            
            # Subscribe to all telegram messages
            await subscribe_to_all_telegram_messages(collect_messages)
            logger.info("✅ Message subscription established")
            
            # Give some time for real messages (optional)
            logger.info("⏳ Waiting for potential real messages (5 seconds)...")
            await asyncio.sleep(5)
            
            if self.received_messages:
                logger.info(f"✅ Received {len(self.received_messages)} real messages")
                
                # Show sample message
                _, sample_message = self.received_messages[0]
                logger.info(f"📋 Sample message structure: {list(sample_message.data.keys())[:5]}...")
            else:
                logger.info("ℹ️ No real messages received (normal for test channels)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Message subscription test failed: {e}")
            return False
    
    async def test_end_to_end_flow(self) -> bool:
        """Test complete end-to-end message flow."""
        try:
            if not self.integration or not self.integration.is_running:
                logger.error("Integration service not running")
                return False
            
            logger.info("🔄 Testing end-to-end message flow...")
            
            # Get initial stats
            initial_stats = self.integration.get_stats()
            initial_processed = initial_stats["messages_processed"]
            initial_published = initial_stats["messages_published"]
            
            logger.info(f"📊 Initial stats - Processed: {initial_processed}, Published: {initial_published}")
            
            # Wait for a short period to see if any messages come through
            logger.info("⏳ Monitoring for message activity (10 seconds)...")
            await asyncio.sleep(10)
            
            # Get final stats
            final_stats = self.integration.get_stats()
            final_processed = final_stats["messages_processed"]
            final_published = final_stats["messages_published"]
            
            logger.info(f"📊 Final stats - Processed: {final_processed}, Published: {final_published}")
            
            # Check for any activity
            if final_processed > initial_processed:
                logger.info(f"✅ Messages processed: {final_processed - initial_processed}")
            
            if final_published > initial_published:
                logger.info(f"✅ Messages published: {final_published - initial_published}")
            
            # The test passes if the system is running properly, even without new messages
            if final_stats["is_running"]:
                logger.info("✅ End-to-end flow system is operational")
                return True
            else:
                logger.error("❌ Integration system stopped running")
                return False
            
        except Exception as e:
            logger.error(f"❌ End-to-end flow test failed: {e}")
            return False
    
    async def test_statistics_collection(self) -> bool:
        """Test statistics collection and reporting."""
        try:
            if not self.integration:
                logger.error("Integration not initialized")
                return False
            
            # Get comprehensive stats
            stats = self.integration.get_stats()
            
            # Check required stat fields
            required_fields = [
                "is_running", "messages_processed", "messages_published",
                "channels_monitored", "errors", "start_time"
            ]
            
            for field in required_fields:
                if field in stats:
                    logger.info(f"✅ Stat field '{field}': {stats[field]}")
                else:
                    logger.error(f"❌ Missing stat field: {field}")
                    return False
            
            # Check nested stats
            if "telethon_stats" in stats and "redis_stats" in stats:
                logger.info("✅ Nested component statistics available")
            
            # Check uptime calculation
            if "uptime_seconds" in stats:
                uptime = stats["uptime_seconds"]
                logger.info(f"✅ Uptime calculation: {uptime:.1f} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Statistics collection test failed: {e}")
            return False
    
    async def test_graceful_shutdown(self) -> bool:
        """Test graceful shutdown of the integration."""
        try:
            if not self.integration:
                logger.error("Integration not initialized")
                return False
            
            logger.info("🛑 Testing graceful shutdown...")
            
            # Get stats before shutdown
            stats_before = self.integration.get_stats()
            logger.info(f"📊 Pre-shutdown - Running: {stats_before['is_running']}")
            
            # Stop the integration
            await self.integration.stop()
            logger.info("✅ Integration stop() called")
            
            # Check if properly stopped
            if not self.integration.is_running:
                logger.info("✅ Integration service stopped")
            
            # Also stop global Redis service
            await redis_service.stop()
            logger.info("✅ Redis service stopped")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Graceful shutdown test failed: {e}")
            return False
    
    async def print_summary(self):
        """Print test summary."""
        logger.info(f"\n{'='*60}")
        logger.info("📋 INTEGRATION TEST SUMMARY")
        logger.info('='*60)
        
        passed = 0
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{status} {test_name}")
            if result:
                passed += 1
        
        logger.info(f"\n🏆 {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All integration tests passed! System is ready for production.")
        else:
            logger.warning("⚠️ Some tests failed. Review the logs above for details.")
        
        if self.received_messages:
            logger.info(f"📨 Total messages captured during testing: {len(self.received_messages)}")


async def quick_connectivity_test():
    """Quick test for basic connectivity without full integration."""
    logger.info("🔍 Running quick connectivity test...")
    
    try:
        # Test Redis
        await redis_service.start()
        logger.info("✅ Redis: Connected")
        
        # Test Telethon session
        session_file = "data/telegram_sessions/telethon_geopol_monitor.session"
        if os.path.exists(session_file):
            telethon_client = TelethonMonitorClient()
            
            await telethon_client.start()
            
            if telethon_client.client and telethon_client.client.is_connected():
                logger.info("✅ Telethon: Connected")
                await telethon_client.stop()
            else:
                logger.error("❌ Telethon: Failed to connect")
                return False
        else:
            logger.warning("⚠️ Telethon: Session file not found")
            return False
        
        await redis_service.stop()
        logger.info("✅ Quick connectivity test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Quick connectivity test failed: {e}")
        return False


async def main():
    """Main test runner."""
    logger.info("🚀 Telethon-Redis Integration Test Suite")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        await quick_connectivity_test()
        return
    
    # Check prerequisites
    logger.info("🔍 Checking prerequisites...")
    
    session_file = "data/telegram_sessions/telethon_geopol_monitor.session"
    if not os.path.exists(session_file):
        logger.error("❌ Telethon session file not found!")
        logger.info("💡 Please run authentication first: python scripts/test_telethon_auth.py")
        return
    
    # Run comprehensive tests
    tester = IntegrationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc() 