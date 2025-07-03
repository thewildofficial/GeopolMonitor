#!/usr/bin/env python3
"""
Telethon Authentication Test Script

This script tests the Telethon client authentication flow and basic functionality.
Run this to verify your Telegram API credentials and complete the authentication.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.telegram.telethon_client import telethon_monitor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_authentication():
    """Test Telethon client authentication."""
    logger.info("🔐 Testing Telethon Authentication")
    logger.info("=" * 50)
    
    try:
        # Get phone number from user if needed
        phone_number = None
        
        # Check if already authenticated
        if telethon_monitor.session_path.exists():
            logger.info("Found existing session file, attempting to use it...")
            success = await telethon_monitor.start()
        else:
            logger.info("No existing session found, starting authentication flow...")
            phone_number = input("Enter your phone number (with country code, e.g., +1234567890): ").strip()
            success = await telethon_monitor.start(phone_number)
        
        if success:
            logger.info("✅ Authentication successful!")
            
            # Get user info
            me = await telethon_monitor.client.get_me()
            logger.info(f"📱 Connected as: {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'})")
            logger.info(f"📞 Phone: {me.phone}")
            
            return True
        else:
            logger.error("❌ Authentication failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Authentication error: {e}")
        return False


async def test_channel_info():
    """Test getting channel information."""
    logger.info("\n📡 Testing Channel Information Retrieval")
    logger.info("=" * 50)
    
    # Test with a public channel
    test_channels = [
        "@telegram",  # Telegram's official channel
        "@durov",     # Pavel Durov's channel
    ]
    
    for channel in test_channels:
        try:
            logger.info(f"Getting info for {channel}...")
            info = await telethon_monitor.get_channel_info(channel)
            
            if info:
                logger.info(f"✅ {channel}:")
                logger.info(f"   Title: {info['title']}")
                logger.info(f"   Username: @{info['username']}")
                logger.info(f"   ID: {info['id']}")
                logger.info(f"   Subscribers: {info['participants_count']:,}")
                logger.info(f"   Verified: {info['is_verified']}")
            else:
                logger.warning(f"⚠️  Could not get info for {channel}")
                
        except Exception as e:
            logger.error(f"❌ Error getting info for {channel}: {e}")


async def test_recent_messages():
    """Test getting recent messages from a channel."""
    logger.info("\n📨 Testing Recent Messages Retrieval")
    logger.info("=" * 50)
    
    test_channel = "@telegram"  # Telegram's official channel
    
    try:
        logger.info(f"Getting recent messages from {test_channel}...")
        messages = await telethon_monitor.get_recent_messages(test_channel, limit=5)
        
        if messages:
            logger.info(f"✅ Retrieved {len(messages)} recent messages:")
            for i, msg in enumerate(messages, 1):
                text_preview = msg['text'][:100] + "..." if len(msg['text']) > 100 else msg['text']
                logger.info(f"   {i}. [{msg['date']}] {text_preview}")
                logger.info(f"      Views: {msg['views']:,}" if msg['views'] else "      Views: N/A")
        else:
            logger.warning(f"⚠️  No recent messages found for {test_channel}")
            
    except Exception as e:
        logger.error(f"❌ Error getting messages from {test_channel}: {e}")


async def test_add_monitor_channel():
    """Test adding a channel to monitoring (without actually monitoring)."""
    logger.info("\n📡 Testing Channel Monitoring Setup")
    logger.info("=" * 50)
    
    test_channel = "@telegram"  # Telegram's official channel
    
    try:
        logger.info(f"Testing adding {test_channel} to monitoring...")
        success = await telethon_monitor.add_channel(
            test_channel,
            credibility_tier="verified",
            region="global",
            test_mode=True
        )
        
        if success:
            logger.info(f"✅ Successfully added {test_channel} to monitoring")
            
            # Show monitored channels
            channels = telethon_monitor.get_monitored_channels()
            logger.info(f"📊 Monitored channels: {len(channels)}")
            for channel in channels:
                logger.info(f"   - {channel['title']} (@{channel['username']})")
            
            # Remove the test channel
            await telethon_monitor.remove_channel(test_channel)
            logger.info(f"🧹 Removed {test_channel} from monitoring (test cleanup)")
        else:
            logger.warning(f"⚠️  Failed to add {test_channel} to monitoring")
            
    except Exception as e:
        logger.error(f"❌ Error testing channel monitoring: {e}")


async def test_client_stats():
    """Test getting client statistics."""
    logger.info("\n📊 Testing Client Statistics")
    logger.info("=" * 50)
    
    try:
        stats = telethon_monitor.get_stats()
        
        logger.info("✅ Client Statistics:")
        logger.info(f"   Authenticated: {stats['is_authenticated']}")
        logger.info(f"   Connected: {stats['is_connected']}")
        logger.info(f"   Session path: {stats['session_path']}")
        logger.info(f"   Messages received: {stats['messages_received']}")
        logger.info(f"   Errors handled: {stats['errors_handled']}")
        logger.info(f"   Monitored channels: {stats['monitored_channels_count']}")
        
        if stats.get('uptime_seconds'):
            logger.info(f"   Uptime: {stats['uptime_seconds']:.1f} seconds")
            
    except Exception as e:
        logger.error(f"❌ Error getting client statistics: {e}")


async def main():
    """Main test function."""
    logger.info("🚀 Starting Telethon Client Tests")
    logger.info("=" * 60)
    
    # Test authentication first
    auth_success = await test_authentication()
    
    if not auth_success:
        logger.error("❌ Authentication failed. Cannot proceed with other tests.")
        logger.info("\nCommon issues:")
        logger.info("1. Invalid API ID or API Hash in .env file")
        logger.info("2. Incorrect phone number format (use +1234567890)")
        logger.info("3. Invalid verification code")
        logger.info("4. Network connectivity issues")
        return
    
    # Run other tests
    await test_channel_info()
    await test_recent_messages()
    await test_add_monitor_channel()
    await test_client_stats()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("🎉 Telethon Client Tests Complete!")
    logger.info("=" * 60)
    logger.info("✅ Authentication: PASSED")
    logger.info("✅ Channel info retrieval: TESTED")
    logger.info("✅ Message retrieval: TESTED")
    logger.info("✅ Channel monitoring: TESTED")
    logger.info("✅ Statistics: TESTED")
    
    logger.info(f"\n💾 Session saved to: {telethon_monitor.session_path}")
    logger.info("🔄 You can now use this session for future connections without re-authentication")
    
    # Cleanup
    await telethon_monitor.stop()
    logger.info("🛑 Telethon client stopped")


if __name__ == "__main__":
    # Run the test
    asyncio.run(main()) 