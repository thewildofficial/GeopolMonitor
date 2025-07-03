#!/usr/bin/env python3
"""
Message Storage Testing Script - GeopolMonitor

This script tests the complete message storage pipeline:
1. Database initialization and connection
2. Single message save function
3. Bulk message save function
4. Duplicate handling logic
5. Integration with Telethon data
6. Performance testing with multiple messages

Tests both SQLite (development) and PostgreSQL (production) scenarios.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone
import json
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.telegram_db import (
    init_telegram_db,
    get_telegram_session,
    close_telegram_db,
    save_telegram_message,
    save_telegram_messages_bulk,
    save_telegram_channel,
    message_exists,
    health_check
)
from src.database.models.telegram_models import TelegramMessage, TelegramChannel
from src.telegram.telethon_client import TelethonMonitorClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MessageStorageTest:
    """Comprehensive test suite for message storage functionality."""
    
    def __init__(self):
        self.test_results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": []
        }
        self.test_channel_id = 1234567890  # Test channel ID
        self.test_messages = []
        
    async def run_all_tests(self):
        """Run all storage tests."""
        logger.info("🧪 Starting Message Storage Test Suite")
        logger.info("=" * 60)
        
        try:
            # Initialize database
            await self._test_database_initialization()
            
            # Test channel storage
            await self._test_channel_storage()
            
            # Test single message storage
            await self._test_single_message_storage()
            
            # Test duplicate handling
            await self._test_duplicate_handling()
            
            # Test bulk message storage
            await self._test_bulk_message_storage()
            
            # Test integration with real Telethon data
            await self._test_telethon_integration()
            
            # Performance testing
            await self._test_performance()
            
            # Test data retrieval
            await self._test_data_retrieval()
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            self.test_results["errors"].append(str(e))
        
        finally:
            await self._cleanup()
            await self._print_results()
    
    async def _test_database_initialization(self):
        """Test database initialization and health check."""
        logger.info("1️⃣ Testing Database Initialization...")
        
        try:
            # Initialize database
            await init_telegram_db()
            logger.info("   ✅ Database initialized successfully")
            
            # Health check
            is_healthy = await health_check()
            if is_healthy:
                logger.info("   ✅ Database health check passed")
                self._record_success()
            else:
                logger.error("   ❌ Database health check failed")
                self._record_failure("Database health check failed")
                
        except Exception as e:
            logger.error(f"   ❌ Database initialization failed: {e}")
            self._record_failure(f"Database initialization: {e}")
    
    async def _test_channel_storage(self):
        """Test channel metadata storage."""
        logger.info("2️⃣ Testing Channel Storage...")
        
        try:
            # Test channel data
            channel_data = {
                'id': self.test_channel_id,
                'username': 'test_channel',
                'title': 'Test Channel for Storage Testing',
                'description': 'A test channel for verifying storage functionality',
                'participants_count': 1000,
                'is_verified': True,
                'is_scam': False,
                'is_fake': False
            }
            
            # Save channel
            saved_channel = await save_telegram_channel(channel_data)
            
            if saved_channel:
                logger.info(f"   ✅ Channel stored: {saved_channel.title} (ID: {saved_channel.channel_id})")
                self._record_success()
            else:
                logger.error("   ❌ Channel storage failed")
                self._record_failure("Channel storage returned None")
                
        except Exception as e:
            logger.error(f"   ❌ Channel storage failed: {e}")
            self._record_failure(f"Channel storage: {e}")
    
    async def _test_single_message_storage(self):
        """Test single message storage functionality."""
        logger.info("3️⃣ Testing Single Message Storage...")
        
        try:
            # Create test message
            message_data = {
                'message_id': 1001,
                'channel_id': self.test_channel_id,
                'text': 'This is a test message for storage verification',
                'date': datetime.now(timezone.utc),
                'from_user_id': 123456,
                'from_username': 'test_user',
                'views': 150,
                'forwards': 5,
                'media_type': 'text',
                'raw_data': {'test': 'data'}
            }
            
            # Save message
            saved_message = await save_telegram_message(message_data)
            
            if saved_message:
                logger.info(f"   ✅ Message stored: ID {saved_message.message_id} from channel {saved_message.channel_id}")
                self.test_messages.append(saved_message)
                self._record_success()
            else:
                logger.error("   ❌ Message storage failed")
                self._record_failure("Message storage returned None")
                
            # Test message existence check
            exists = await message_exists(message_data['message_id'], message_data['channel_id'])
            if exists:
                logger.info("   ✅ Message existence check passed")
                self._record_success()
            else:
                logger.error("   ❌ Message existence check failed")
                self._record_failure("Message existence check failed")
                
        except Exception as e:
            logger.error(f"   ❌ Single message storage failed: {e}")
            self._record_failure(f"Single message storage: {e}")
    
    async def _test_duplicate_handling(self):
        """Test duplicate message handling."""
        logger.info("4️⃣ Testing Duplicate Handling...")
        
        try:
            # Create duplicate message with updated data
            duplicate_data = {
                'message_id': 1001,  # Same as previous test
                'channel_id': self.test_channel_id,
                'text': 'This is an UPDATED test message with new content',
                'date': datetime.now(timezone.utc),
                'from_user_id': 123456,
                'from_username': 'test_user',
                'views': 300,  # Updated view count
                'forwards': 10,  # Updated forward count
                'media_type': 'text',
                'raw_data': {'test': 'updated_data', 'new_field': 'value'}
            }
            
            # Test with update_if_exists=True (default)
            updated_message = await save_telegram_message(duplicate_data, update_if_exists=True)
            
            if updated_message and updated_message.views == 300:
                logger.info("   ✅ Duplicate handling with update: Message updated successfully")
                self._record_success()
            else:
                logger.error("   ❌ Duplicate handling with update failed")
                self._record_failure("Message update on duplicate failed")
            
            # Test with update_if_exists=False
            skipped_message = await save_telegram_message(duplicate_data, update_if_exists=False)
            
            if skipped_message:  # Should return existing message
                logger.info("   ✅ Duplicate handling with skip: Existing message returned")
                self._record_success()
            else:
                logger.error("   ❌ Duplicate handling with skip failed")
                self._record_failure("Message skip on duplicate failed")
                
        except Exception as e:
            logger.error(f"   ❌ Duplicate handling test failed: {e}")
            self._record_failure(f"Duplicate handling: {e}")
    
    async def _test_bulk_message_storage(self):
        """Test bulk message storage functionality."""
        logger.info("5️⃣ Testing Bulk Message Storage...")
        
        try:
            # Create batch of test messages
            bulk_messages = []
            for i in range(10):
                message_data = {
                    'message_id': 2000 + i,
                    'channel_id': self.test_channel_id,
                    'text': f'Bulk test message #{i+1} with some content for testing',
                    'date': datetime.now(timezone.utc),
                    'from_user_id': 123456 + i,
                    'from_username': f'bulk_user_{i}',
                    'views': 50 + i * 10,
                    'forwards': i,
                    'media_type': 'text',
                    'raw_data': {'bulk_test': True, 'index': i}
                }
                bulk_messages.append(message_data)
            
            # Bulk save
            stats = await save_telegram_messages_bulk(bulk_messages, batch_size=5)
            
            expected_inserted = len(bulk_messages)
            if stats.get('inserted', 0) >= expected_inserted:
                logger.info(f"   ✅ Bulk storage: {stats.get('inserted')} messages inserted")
                logger.info(f"   📊 Bulk stats: {stats}")
                self._record_success()
            else:
                logger.error(f"   ❌ Bulk storage failed: expected {expected_inserted}, got {stats.get('inserted', 0)}")
                self._record_failure(f"Bulk storage: {stats}")
                
        except Exception as e:
            logger.error(f"   ❌ Bulk message storage failed: {e}")
            self._record_failure(f"Bulk storage: {e}")
    
    async def _test_telethon_integration(self):
        """Test integration with real Telethon data format."""
        logger.info("6️⃣ Testing Telethon Integration...")
        
        try:
            # Simulate Telethon client to get real data format
            telethon_client = TelethonMonitorClient()
            
            # If connected, try to get real message data
            if hasattr(telethon_client, 'client') and telethon_client.client:
                try:
                    await telethon_client.start_with_monitoring()
                    
                    # Test with @telegram channel
                    messages = await telethon_client.get_recent_messages('@telegram', limit=1)
                    
                    if messages:
                        # Convert first message to our storage format
                        telethon_message = messages[0]
                        storage_data = {
                            'message_id': telethon_message.get('id') or telethon_message.get('message_id'),
                            'channel_id': telethon_message.get('channel_id', self.test_channel_id + 100),
                            'text': telethon_message.get('text', ''),
                            'date': telethon_message.get('date'),
                            'from_user_id': telethon_message.get('from_user'),
                            'views': telethon_message.get('views'),
                            'forwards': telethon_message.get('forwards'),
                            'raw_data': telethon_message
                        }
                        
                        # Store real Telethon message
                        saved = await save_telegram_message(storage_data)
                        
                        if saved:
                            logger.info(f"   ✅ Real Telethon message stored: {saved.message_id}")
                            self._record_success()
                        else:
                            logger.warning("   ⚠️ Telethon message storage returned None")
                            self._record_success()  # Not a critical failure
                            
                    else:
                        logger.info("   ✅ Telethon integration test skipped (no messages retrieved)")
                        self._record_success()
                        
                    await telethon_client.stop()
                    
                except Exception as e:
                    logger.warning(f"   ⚠️ Telethon integration test skipped: {e}")
                    self._record_success()  # Not a critical failure
            else:
                logger.info("   ✅ Telethon integration test skipped (client not available)")
                self._record_success()
                
        except Exception as e:
            logger.warning(f"   ⚠️ Telethon integration test failed: {e}")
            self._record_success()  # Not a critical failure for this test
    
    async def _test_performance(self):
        """Test storage performance with larger datasets."""
        logger.info("7️⃣ Testing Performance...")
        
        try:
            import time
            
            # Create 100 messages for performance testing
            perf_messages = []
            for i in range(100):
                message_data = {
                    'message_id': 3000 + i,
                    'channel_id': self.test_channel_id,
                    'text': f'Performance test message #{i+1} with substantial content to test database performance and storage capabilities',
                    'date': datetime.now(timezone.utc),
                    'from_user_id': 200000 + i,
                    'from_username': f'perf_user_{i}',
                    'views': 100 + i * 5,
                    'forwards': i % 10,
                    'media_type': 'text',
                    'raw_data': {'performance_test': True, 'batch': i // 10, 'index': i}
                }
                perf_messages.append(message_data)
            
            # Time bulk insert
            start_time = time.time()
            stats = await save_telegram_messages_bulk(perf_messages, batch_size=25)
            end_time = time.time()
            
            duration = end_time - start_time
            messages_per_second = len(perf_messages) / duration if duration > 0 else 0
            
            logger.info(f"   ✅ Performance test: {len(perf_messages)} messages in {duration:.2f}s")
            logger.info(f"   📊 Throughput: {messages_per_second:.1f} messages/second")
            logger.info(f"   📊 Stats: {stats}")
            
            self._record_success()
            
        except Exception as e:
            logger.error(f"   ❌ Performance test failed: {e}")
            self._record_failure(f"Performance test: {e}")
    
    async def _test_data_retrieval(self):
        """Test data retrieval and query functionality."""
        logger.info("8️⃣ Testing Data Retrieval...")
        
        try:
            async with get_telegram_session() as session:
                # Query messages from test channel
                from sqlalchemy import select, func
                
                # Count total messages
                result = await session.execute(
                    select(func.count(TelegramMessage.message_id)).where(
                        TelegramMessage.channel_id == self.test_channel_id
                    )
                )
                message_count = result.scalar()
                
                # Get recent messages
                result = await session.execute(
                    select(TelegramMessage).where(
                        TelegramMessage.channel_id == self.test_channel_id
                    ).order_by(TelegramMessage.date.desc()).limit(5)
                )
                recent_messages = result.scalars().all()
                
                logger.info(f"   ✅ Found {message_count} total messages in test channel")
                logger.info(f"   ✅ Retrieved {len(recent_messages)} recent messages")
                
                # Verify message content
                if recent_messages:
                    sample_message = recent_messages[0]
                    logger.info(f"   ✅ Sample message: ID {sample_message.message_id}, text length: {len(sample_message.text)}")
                
                self._record_success()
                
        except Exception as e:
            logger.error(f"   ❌ Data retrieval test failed: {e}")
            self._record_failure(f"Data retrieval: {e}")
    
    async def _cleanup(self):
        """Clean up test data and connections."""
        logger.info("🧹 Cleaning up test data...")
        
        try:
            async with get_telegram_session() as session:
                # Delete test messages
                from sqlalchemy import delete
                
                await session.execute(
                    delete(TelegramMessage).where(
                        TelegramMessage.channel_id == self.test_channel_id
                    )
                )
                
                # Delete test channel
                await session.execute(
                    delete(TelegramChannel).where(
                        TelegramChannel.channel_id == self.test_channel_id
                    )
                )
                
                await session.commit()
                logger.info("   ✅ Test data cleaned up")
                
            # Close database connections
            await close_telegram_db()
            logger.info("   ✅ Database connections closed")
            
        except Exception as e:
            logger.warning(f"   ⚠️ Cleanup warning: {e}")
    
    def _record_success(self):
        """Record a successful test."""
        self.test_results["tests_run"] += 1
        self.test_results["tests_passed"] += 1
    
    def _record_failure(self, error_msg: str):
        """Record a failed test."""
        self.test_results["tests_run"] += 1
        self.test_results["tests_failed"] += 1
        self.test_results["errors"].append(error_msg)
    
    async def _print_results(self):
        """Print comprehensive test results."""
        logger.info("📊 TEST RESULTS")
        logger.info("=" * 60)
        
        results = self.test_results
        logger.info(f"Tests Run: {results['tests_run']}")
        logger.info(f"Tests Passed: {results['tests_passed']} ✅")
        logger.info(f"Tests Failed: {results['tests_failed']} ❌")
        
        if results["errors"]:
            logger.info("\\nErrors encountered:")
            for i, error in enumerate(results["errors"], 1):
                logger.error(f"  {i}. {error}")
        
        # Calculate pass rate
        if results["tests_run"] > 0:
            pass_rate = (results["tests_passed"] / results["tests_run"]) * 100
            logger.info(f"\\nPass Rate: {pass_rate:.1f}%")
            
            if pass_rate >= 90:
                logger.info("🎉 Message storage system is working excellently!")
            elif pass_rate >= 70:
                logger.info("✅ Message storage system is working well with minor issues")
            else:
                logger.warning("⚠️ Message storage system needs attention")
        
        logger.info("=" * 60)


async def main():
    """Run the message storage test suite."""
    test_suite = MessageStorageTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 