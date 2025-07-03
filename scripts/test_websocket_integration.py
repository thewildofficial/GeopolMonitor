"""
Comprehensive Test Script for WebSocket Integration.

This script tests the WebSocket endpoint integration with Redis Pub/Sub
for real-time Telegram message distribution.
"""

import asyncio
import json
import logging
import sys
import os
import websockets
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.services.redis_pubsub import (
    publish_telegram_message,
    Priority,
    redis_service
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class WebSocketTestClient:
    """Test client for WebSocket functionality."""
    
    def __init__(self, uri: str = "ws://localhost:8000/ws"):
        self.uri = uri
        self.websocket = None
        self.messages_received = []
        self.is_connected = False
        
    async def connect(self, filters: dict = None):
        """Connect to WebSocket with optional filters."""
        try:
            # Build URI with query parameters if filters provided
            uri = self.uri
            if filters:
                params = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        value = ",".join(value)
                    params.append(f"{key}={value}")
                if params:
                    uri += "?" + "&".join(params)
                    
            logger.info(f"Connecting to WebSocket: {uri}")
            self.websocket = await websockets.connect(uri)
            self.is_connected = True
            logger.info("✅ WebSocket connected successfully")
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to WebSocket: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket and self.is_connected:
            await self.websocket.close()
            self.is_connected = False
            logger.info("WebSocket disconnected")
            
    async def send_message(self, message: dict):
        """Send a message to the WebSocket."""
        if self.websocket and self.is_connected:
            await self.websocket.send(json.dumps(message))
            logger.info(f"Sent message: {message['type']}")
            
    async def wait_for_messages(self, timeout: int = 10, expected_count: int = 1):
        """Wait for messages to be received."""
        start_time = asyncio.get_event_loop().time()
        
        while len(self.messages_received) < expected_count:
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.warning(f"Timeout waiting for messages. Received {len(self.messages_received)}/{expected_count}")
                break
            await asyncio.sleep(0.1)
            
        return self.messages_received
        
    async def _listen_for_messages(self):
        """Listen for incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.messages_received.append(data)
                    logger.info(f"📩 Received {data.get('type', 'unknown')} message")
                    
                    # Log message details for debugging
                    if data.get('type') == 'telegram_message':
                        msg_data = data.get('data', {})
                        logger.info(f"   - Channel: {msg_data.get('channel_username')}")
                        logger.info(f"   - Text: {msg_data.get('text', '')[:100]}...")
                        logger.info(f"   - Priority: {msg_data.get('priority')}")
                        
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse message: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error listening for messages: {e}")
            self.is_connected = False


async def test_basic_websocket_connection():
    """Test basic WebSocket connection."""
    logger.info("🧪 Testing basic WebSocket connection...")
    
    client = WebSocketTestClient()
    
    try:
        # Connect to WebSocket
        success = await client.connect()
        if not success:
            return False
            
        # Wait for welcome message
        messages = await client.wait_for_messages(timeout=5, expected_count=1)
        
        if messages and messages[0].get('type') == 'system_status':
            logger.info("✅ Received welcome message")
            return True
        else:
            logger.error("❌ Did not receive expected welcome message")
            return False
            
    finally:
        await client.disconnect()


async def test_telegram_message_broadcast():
    """Test Telegram message broadcasting via Redis."""
    logger.info("🧪 Testing Telegram message broadcast...")
    
    client = WebSocketTestClient()
    
    try:
        # Connect to WebSocket
        success = await client.connect()
        if not success:
            return False
            
        # Wait for welcome message
        await client.wait_for_messages(timeout=3, expected_count=1)
        client.messages_received.clear()  # Clear welcome message
        
        # Start Redis service
        await redis_service.start()
        
        # Simulate publishing a Telegram message
        test_message_data = {
            "message_id": 12345,
            "channel_id": -1001234567890,
            "channel_username": "test_channel",
            "text": "This is a test message from Telegram integration test",
            "author": "Test User",
            "metadata": {
                "message_type": "text",
                "has_media": False
            },
            "ai_analysis": {
                "sentiment_score": 0.75,
                "urgency_score": 0.6
            },
            "geographical_relevance": ["United States", "Europe"]
        }
        
                          logger.info("📡 Publishing test Telegram message to Redis...")
         await publish_telegram_message(
             channel_id="test_channel",
             message_data=test_message_data,
             priority=Priority.MEDIUM
         )
        
        # Wait for message to be received via WebSocket
        messages = await client.wait_for_messages(timeout=10, expected_count=1)
        
        if messages:
            telegram_msg = next((m for m in messages if m.get('type') == 'telegram_message'), None)
            if telegram_msg:
                logger.info("✅ Received Telegram message via WebSocket")
                return True
            else:
                logger.error("❌ Did not receive Telegram message")
                return False
        else:
            logger.error("❌ No messages received")
            return False
            
    finally:
        await client.disconnect()


async def test_websocket_filtering():
    """Test WebSocket message filtering."""
    logger.info("🧪 Testing WebSocket filtering...")
    
    # Client with channel filter
    filtered_client = WebSocketTestClient()
    
    # Client without filter
    unfiltered_client = WebSocketTestClient()
    
    try:
        # Connect filtered client (only test_channel)
        filters = {"channels": ["test_channel"]}
        success1 = await filtered_client.connect(filters)
        
        # Connect unfiltered client
        success2 = await unfiltered_client.connect()
        
        if not (success1 and success2):
            return False
            
        # Wait for welcome messages
        await filtered_client.wait_for_messages(timeout=3, expected_count=1)
        await unfiltered_client.wait_for_messages(timeout=3, expected_count=1)
        
        # Clear welcome messages
        filtered_client.messages_received.clear()
        unfiltered_client.messages_received.clear()
        
        # Start Redis service
        await redis_service.start()
        
        # Publish message to filtered channel
        test_message_1 = {
            "message_id": 11111,
            "channel_id": -1001234567890,
            "channel_username": "test_channel",
            "text": "Message for test_channel",
            "author": "Test User",
            "metadata": {},
            "ai_analysis": {},
            "geographical_relevance": []
        }
        
        # Publish message to different channel
        test_message_2 = {
            "message_id": 22222,
            "channel_id": -1009876543210,
            "channel_username": "other_channel",
            "text": "Message for other_channel",
            "author": "Test User",
            "metadata": {},
            "ai_analysis": {},
            "geographical_relevance": []
        }
        
                 logger.info("📡 Publishing messages to both channels...")
         await publish_telegram_message(channel_id="test_channel", message_data=test_message_1, priority=Priority.MEDIUM)
         await publish_telegram_message(channel_id="other_channel", message_data=test_message_2, priority=Priority.MEDIUM)
        
        # Wait for messages
        await asyncio.sleep(2)
        
        # Check filtered client (should only receive test_channel message)
        filtered_messages = await filtered_client.wait_for_messages(timeout=5, expected_count=1)
        unfiltered_messages = await unfiltered_client.wait_for_messages(timeout=5, expected_count=2)
        
        # Verify filtering worked
        filtered_telegram_msgs = [m for m in filtered_messages if m.get('type') == 'telegram_message']
        unfiltered_telegram_msgs = [m for m in unfiltered_messages if m.get('type') == 'telegram_message']
        
        if len(filtered_telegram_msgs) == 1 and len(unfiltered_telegram_msgs) >= 1:
            # Check that filtered client only got test_channel message
            received_channel = filtered_telegram_msgs[0]['data']['channel_username']
            if received_channel == "test_channel":
                logger.info("✅ WebSocket filtering working correctly")
                return True
            else:
                logger.error(f"❌ Filtered client received wrong channel: {received_channel}")
                return False
        else:
            logger.error(f"❌ Filtering failed. Filtered: {len(filtered_telegram_msgs)}, Unfiltered: {len(unfiltered_telegram_msgs)}")
            return False
            
    finally:
        await filtered_client.disconnect()
        await unfiltered_client.disconnect()


async def test_websocket_stats_endpoint():
    """Test WebSocket statistics API endpoint."""
    logger.info("🧪 Testing WebSocket stats endpoint...")
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/websocket/stats") as response:
                if response.status == 200:
                    stats = await response.json()
                    logger.info("✅ WebSocket stats endpoint working")
                    logger.info(f"   - Active connections: {stats.get('active_connections', 0)}")
                    logger.info(f"   - Messages sent: {stats.get('messages_sent', 0)}")
                    logger.info(f"   - Redis connected: {stats.get('redis_connected', False)}")
                    return True
                else:
                    logger.error(f"❌ Stats endpoint returned {response.status}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Failed to test stats endpoint: {e}")
        return False


async def test_dynamic_filter_updates():
    """Test dynamic filter updates via WebSocket."""
    logger.info("🧪 Testing dynamic filter updates...")
    
    client = WebSocketTestClient()
    
    try:
        # Connect without filters
        success = await client.connect()
        if not success:
            return False
            
        # Wait for welcome message
        await client.wait_for_messages(timeout=3, expected_count=1)
        client.messages_received.clear()
        
        # Send filter update
        filter_update = {
            "type": "update_filters",
            "data": {
                "channels": ["test_channel"],
                "priority_level": "medium"
            }
        }
        
        await client.send_message(filter_update)
        
        # Wait for filter update confirmation
        messages = await client.wait_for_messages(timeout=5, expected_count=1)
        
        filter_msg = next((m for m in messages if m.get('type') == 'system_status' and m.get('data', {}).get('status') == 'filters_updated'), None)
        
        if filter_msg:
            logger.info("✅ Dynamic filter update working")
            return True
        else:
            logger.error("❌ Did not receive filter update confirmation")
            return False
            
    finally:
        await client.disconnect()


async def run_integration_tests():
    """Run comprehensive WebSocket integration tests."""
    logger.info("🚀 Starting WebSocket Integration Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Basic Connection", test_basic_websocket_connection),
        ("Message Broadcast", test_telegram_message_broadcast),
        ("Message Filtering", test_websocket_filtering),
        ("Stats Endpoint", test_websocket_stats_endpoint),
        ("Dynamic Filters", test_dynamic_filter_updates),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running {test_name} Test...")
        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name} Test: PASSED")
            else:
                logger.error(f"❌ {test_name} Test: FAILED")
        except Exception as e:
            logger.error(f"💥 {test_name} Test: ERROR - {e}")
            results.append((test_name, False))
            
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"   {test_name}: {status}")
    
    logger.info(f"\n🏆 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! WebSocket integration is working perfectly!")
        return True
    else:
        logger.error(f"🚨 {total - passed} tests failed. Please check the logs above.")
        return False


async def main():
    """Main function."""
    # Quick check - is the server running?
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/") as response:
                if response.status != 200:
                    logger.error("❌ FastAPI server not responding. Please start it with: python web_server.py")
                    return False
    except Exception:
        logger.error("❌ Cannot connect to FastAPI server. Please start it with: python web_server.py")
        return False
    
    logger.info("✅ FastAPI server is running")
    
    # Run tests
    success = await run_integration_tests()
    
    if success:
        logger.info("\n🎯 WebSocket integration is production-ready!")
    else:
        logger.info("\n🔧 Some issues detected. Please review and fix.")
    
    return success


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1) 