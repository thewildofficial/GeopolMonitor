"""
Simple WebSocket Test for Basic Connectivity.
"""

import asyncio
import json
import sys
import os
import websockets

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.services.redis_pubsub import publish_telegram_message, Priority, redis_service

print("🧪 Simple WebSocket Test")
print("=" * 40)

async def test_basic_connection():
    """Test basic WebSocket connection and welcome message."""
    print("1. Testing basic WebSocket connection...")
    
    try:
        # Connect to WebSocket
        async with websockets.connect("ws://localhost:8000/ws") as websocket:
            print("✅ Connected to WebSocket")
            
            # Wait for welcome message
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            
            if data.get('type') == 'system_status':
                print(f"✅ Received welcome message: {data['data']['status']}")
                return True
            else:
                print(f"❌ Unexpected message type: {data.get('type')}")
                return False
                
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for welcome message")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def test_redis_message():
    """Test Redis message broadcasting through WebSocket."""
    print("2. Testing Redis message broadcast...")
    
    try:
        # Start Redis service
        await redis_service.start()
        print("✅ Redis service started")
        
        # Connect to WebSocket
        async with websockets.connect("ws://localhost:8000/ws") as websocket:
            print("✅ Connected to WebSocket")
            
            # Wait for and discard welcome message
            await websocket.recv()
            
            # Publish test message
            test_data = {
                "message_id": 12345,
                "channel_id": -1001234567890,
                "channel_username": "test_channel",
                "text": "Hello from Redis test!",
                "author": "Test User"
            }
            
            print("📡 Publishing test message to Redis...")
            await publish_telegram_message(
                channel_id="test_channel",
                message_data=test_data,
                priority=Priority.MEDIUM
            )
            
            # Wait for message to come back through WebSocket
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(message)
                
                if data.get('type') == 'telegram_message':
                    print("✅ Received Telegram message via WebSocket!")
                    print(f"   - Text: {data['data']['text']}")
                    print(f"   - Channel: {data['data']['channel_username']}")
                    return True
                else:
                    print(f"❌ Unexpected message type: {data.get('type')}")
                    return False
                    
            except asyncio.TimeoutError:
                print("❌ Timeout waiting for Redis message")
                return False
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("Starting simple WebSocket tests...\n")
    
    # Test 1: Basic connection
    result1 = await test_basic_connection()
    print()
    
    # Test 2: Redis integration
    result2 = await test_redis_message()
    print()
    
    # Summary
    print("=" * 40)
    print("📊 RESULTS:")
    print(f"   Basic Connection: {'✅ PASS' if result1 else '❌ FAIL'}")
    print(f"   Redis Integration: {'✅ PASS' if result2 else '❌ FAIL'}")
    
    if result1 and result2:
        print("\n🎉 All tests passed! WebSocket integration is working!")
    else:
        print("\n🔧 Some issues detected.")
    
    return result1 and result2

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        sys.exit(1) 