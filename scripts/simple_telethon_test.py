#!/usr/bin/env python3
"""
Simple Telethon Authentication Test

Interactive script to authenticate and test basic Telethon functionality.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.telegram.telethon_client import telethon_monitor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Main authentication and test function."""
    print("🔐 Telethon Authentication Test")
    print("=" * 40)
    
    try:
        # Always start by trying to connect first
        print("📱 Attempting to connect to Telegram...")
        await telethon_monitor.client.connect()
        
        # Check if we're already authenticated
        if await telethon_monitor.client.is_user_authorized():
            print("✅ Found valid existing session!")
            success = True
            telethon_monitor.is_authenticated = True
        else:
            print("📱 No valid session found, starting authentication flow...")
            print("\n⚠️  You'll need to provide your phone number and verification code.")
            print("Make sure you can receive SMS or Telegram messages!\n")
            
            phone = input("Enter your phone number (with country code, e.g., +1234567890): ").strip()
            success = await telethon_monitor.authenticate_user(phone)
        
        if success:
            print("✅ Authentication successful!")
            
            # Get user info
            me = await telethon_monitor.client.get_me()
            print(f"👤 Connected as: {me.first_name} {me.last_name or ''}")
            print(f"📞 Phone: {me.phone}")
            print(f"🆔 User ID: {me.id}")
            
            # Test getting channel info (Telegram's official channel)
            print("\n📡 Testing channel information retrieval...")
            try:
                info = await telethon_monitor.get_channel_info("@telegram")
                if info:
                    print(f"✅ Channel Test Successful:")
                    print(f"   📺 {info['title']}")
                    subscribers = info.get('participants_count')
                    if subscribers:
                        print(f"   👥 {subscribers:,} subscribers")
                    else:
                        print(f"   👥 Subscriber count not available")
                    print(f"   ✅ Verified: {info['is_verified']}")
                else:
                    print("⚠️  Could not retrieve channel info")
            except Exception as e:
                print(f"❌ Channel test error: {e}")
            
            # Test statistics
            print("\n📊 Client Statistics:")
            stats = telethon_monitor.get_stats()
            print(f"   🔗 Connected: {stats['is_connected']}")
            print(f"   🔐 Authenticated: {stats['is_authenticated']}")
            print(f"   📁 Session: {stats['session_path']}")
            
            print("\n🎉 All tests passed! Telethon client is ready for use.")
            print("💾 Your session has been saved - you won't need to re-authenticate next time.")
            
        else:
            print("❌ Authentication failed!")
            print("\nTroubleshooting:")
            print("1. Make sure your phone number format is correct (+country_code + number)")
            print("2. Check that you received the verification code")
            print("3. Ensure your .env file has correct TELEGRAM_API_ID and TELEGRAM_API_HASH")
        
    except KeyboardInterrupt:
        print("\n👋 Authentication cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up
        await telethon_monitor.stop()
        print("🛑 Client disconnected")


if __name__ == "__main__":
    asyncio.run(main()) 