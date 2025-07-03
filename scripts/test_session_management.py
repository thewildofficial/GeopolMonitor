#!/usr/bin/env python3
"""
Telethon Session Management and Reconnection Test

Test script to verify robust session management, auto-reconnection,
and connection monitoring features.
"""

import asyncio
import logging
import sys
import signal
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.telegram.telethon_client import telethon_monitor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class SessionManagementTester:
    """Test suite for session management features."""
    
    def __init__(self):
        self.client = telethon_monitor
        self.test_results = {}
        self.is_running = True
    
    async def test_basic_connection(self) -> bool:
        """Test basic connection with existing session."""
        logger.info("🔗 Testing basic connection...")
        
        try:
            success = await self.client.start()
            if success and self.client.client.is_connected():
                logger.info("✅ Basic connection successful")
                return True
            else:
                logger.error("❌ Basic connection failed")
                return False
        except Exception as e:
            logger.error(f"❌ Basic connection error: {e}")
            return False
    
    async def test_monitored_connection(self) -> bool:
        """Test connection with monitoring enabled."""
        logger.info("📊 Testing monitored connection...")
        
        try:
            success = await self.client.start_with_monitoring()
            if success:
                logger.info("✅ Monitored connection started successfully")
                
                # Wait a bit to let monitoring tasks start
                await asyncio.sleep(5)
                
                # Check if monitoring tasks are running
                monitor_running = (self.client._connection_monitor_task and 
                                 not self.client._connection_monitor_task.done())
                heartbeat_running = (self.client._heartbeat_task and 
                                   not self.client._heartbeat_task.done())
                
                if monitor_running and heartbeat_running:
                    logger.info("✅ Background monitoring tasks running")
                    return True
                else:
                    logger.error("❌ Background monitoring tasks not running properly")
                    return False
            else:
                logger.error("❌ Monitored connection failed")
                return False
        except Exception as e:
            logger.error(f"❌ Monitored connection error: {e}")
            return False
    
    async def test_connection_statistics(self) -> bool:
        """Test connection statistics and monitoring data."""
        logger.info("📈 Testing connection statistics...")
        
        try:
            stats = self.client.get_stats()
            
            required_fields = [
                'is_connected', 'is_authenticated', 'is_running',
                'connection_config', 'reconnection_stats'
            ]
            
            missing_fields = [field for field in required_fields if field not in stats]
            
            if missing_fields:
                logger.error(f"❌ Missing statistics fields: {missing_fields}")
                return False
            
            logger.info("✅ Connection statistics complete")
            logger.info(f"   📊 Connected: {stats['is_connected']}")
            logger.info(f"   🔐 Authenticated: {stats['is_authenticated']}")
            logger.info(f"   🏃 Running: {stats['is_running']}")
            logger.info(f"   🔄 Total reconnections: {stats['reconnection_stats']['total_reconnections']}")
            logger.info(f"   ✅ Successful reconnections: {stats['reconnection_stats']['successful_reconnections']}")
            logger.info(f"   📡 Monitored channels: {stats['monitored_channels_count']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Statistics test error: {e}")
            return False
    
    async def test_robust_operations(self) -> bool:
        """Test robust operation wrapper."""
        logger.info("🛡️ Testing robust operations...")
        
        try:
            # Test channel info retrieval with robust wrapper
            info = await self.client.get_channel_info("@telegram")
            
            if info and 'title' in info:
                logger.info(f"✅ Robust operation successful: {info['title']}")
                return True
            else:
                logger.error("❌ Robust operation failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Robust operation error: {e}")
            return False
    
    async def test_connection_health_monitoring(self) -> bool:
        """Test connection health monitoring over time."""
        logger.info("💗 Testing connection health monitoring...")
        
        try:
            # Monitor for 30 seconds
            start_time = time.time()
            monitor_duration = 30
            
            logger.info(f"   Monitoring connection health for {monitor_duration} seconds...")
            
            while time.time() - start_time < monitor_duration:
                stats = self.client.get_stats()
                
                if not stats['is_connected'] or not stats['is_authenticated']:
                    logger.error("❌ Connection health check failed")
                    return False
                
                # Check last ping time
                if stats['last_ping']:
                    logger.debug(f"   Last ping: {stats['last_ping']}")
                
                await asyncio.sleep(5)  # Check every 5 seconds
            
            logger.info("✅ Connection health monitoring successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection health monitoring error: {e}")
            return False
    
    async def test_graceful_shutdown(self) -> bool:
        """Test graceful shutdown of monitoring tasks."""
        logger.info("🛑 Testing graceful shutdown...")
        
        try:
            await self.client.stop()
            
            # Check if tasks were properly cancelled
            if self.client._connection_monitor_task:
                if self.client._connection_monitor_task.done():
                    logger.info("✅ Connection monitor task properly stopped")
                else:
                    logger.error("❌ Connection monitor task not stopped")
                    return False
            
            if self.client._heartbeat_task:
                if self.client._heartbeat_task.done():
                    logger.info("✅ Heartbeat task properly stopped")
                else:
                    logger.error("❌ Heartbeat task not stopped")
                    return False
            
            logger.info("✅ Graceful shutdown successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Graceful shutdown error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all session management tests."""
        logger.info("🚀 Starting Session Management Tests")
        logger.info("=" * 60)
        
        tests = [
            ("Basic Connection", self.test_basic_connection),
            ("Monitored Connection", self.test_monitored_connection),
            ("Connection Statistics", self.test_connection_statistics),
            ("Robust Operations", self.test_robust_operations),
            ("Health Monitoring", self.test_connection_health_monitoring),
            ("Graceful Shutdown", self.test_graceful_shutdown)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n🧪 Running: {test_name}")
            logger.info("-" * 40)
            
            try:
                result = await test_func()
                self.test_results[test_name] = result
                
                if result:
                    passed += 1
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {e}")
                self.test_results[test_name] = False
        
        # Final results
        logger.info("\n" + "=" * 60)
        logger.info("📊 FINAL TEST RESULTS")
        logger.info("=" * 60)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {test_name}: {status}")
        
        logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED! Session management is robust.")
        else:
            logger.error("❌ Some tests failed. Check logs for details.")
        
        return passed == total


async def main():
    """Main test function."""
    tester = SessionManagementTester()
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info("🛑 Received shutdown signal, stopping tests...")
        tester.is_running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        success = await tester.run_all_tests()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("👋 Tests interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Test suite error: {e}")
        return 1
    finally:
        # Ensure client is stopped
        try:
            await telethon_monitor.stop()
        except:
            pass


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 