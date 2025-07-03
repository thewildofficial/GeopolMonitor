#!/usr/bin/env python3
"""
LIVE MESSAGE CAPTURE PROOF - GeopolMonitor

This script provides concrete proof that the system can capture real messages
from Telegram channels by:
1. Connecting to actual Telegram channels
2. Displaying recent messages with timestamps, content, and metadata
3. Monitoring for new messages in real-time
4. Showing message processing pipeline in action
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.telegram.telethon_client import TelethonMonitorClient
from config.channels import get_test_channels
from telethon import events

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class MessageCaptureProof:
    """Provides concrete proof of message capture capabilities."""
    
    def __init__(self):
        self.captured_messages = []
        self.telethon_client = None
        
    async def demonstrate_message_capture(self):
        """Demonstrate actual message capture from real channels."""
        logger.info("🔍 LIVE MESSAGE CAPTURE PROOF")
        logger.info("=" * 60)
        
        try:
            # Step 1: Initialize Telethon client
            await self._initialize_client()
            
            # Step 2: Show recent messages from channels (PROOF)
            await self._show_recent_messages()
            
            # Step 3: Set up real-time monitoring (PROOF)
            await self._setup_realtime_monitoring()
            
            # Step 4: Monitor for new messages (PROOF)
            await self._monitor_for_new_messages()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Proof demonstration failed: {e}")
            return False
        finally:
            await self._cleanup()
    
    async def _initialize_client(self):
        """Initialize and connect the Telethon client."""
        logger.info("\n🔧 Step 1: Initializing Telegram Client")
        logger.info("-" * 40)
        
        self.telethon_client = TelethonMonitorClient()
        
        # Start the client
        success = await self.telethon_client.start_with_monitoring()
        if not success:
            raise RuntimeError("Failed to connect to Telegram")
        
        logger.info("✅ Connected to Telegram successfully")
        logger.info(f"📱 Session: {self.telethon_client.get_stats()['session_path']}")
        logger.info(f"🔐 Authenticated: {self.telethon_client.get_stats()['is_authenticated']}")
    
    async def _show_recent_messages(self):
        """Show recent actual messages from channels as proof."""
        logger.info("\n📋 Step 2: Recent Messages from Channels (PROOF)")
        logger.info("-" * 40)
        
        test_channels = get_test_channels()
        
        for channel_config in test_channels:
            channel_id = channel_config['identifier']
            channel_title = channel_config['title']
            
            try:
                logger.info(f"\n📺 Channel: {channel_title} ({channel_id})")
                
                # Get recent messages
                messages = await self.telethon_client.get_recent_messages(channel_id, limit=3)
                
                if messages:
                    logger.info(f"   ✅ Found {len(messages)} recent messages:")
                    
                    for i, msg in enumerate(messages, 1):
                        # Format message info - handle both dict and object formats
                        if hasattr(msg, 'date'):
                            # Telethon Message object
                            msg_time = msg.date.isoformat() if msg.date else 'Unknown'
                            msg_content = msg.text or '[Media/Non-text content]'
                            msg_id = msg.id
                            sender_id = msg.sender_id
                        else:
                            # Dict format
                            msg_time = msg.get('date', 'Unknown')
                            msg_content = msg.get('message') or msg.get('text') or '[Media/Non-text content]'
                            msg_id = msg.get('id', 'Unknown')
                            sender_id = msg.get('sender_id', 'Unknown')
                        
                        # Truncate long messages
                        if len(str(msg_content)) > 100:
                            msg_content = str(msg_content)[:100] + "..."
                        
                        logger.info(f"   {i}. ID: {msg_id}")
                        logger.info(f"      Time: {msg_time}")
                        logger.info(f"      Content: {msg_content}")
                        logger.info(f"      Sender: {sender_id}")
                        
                        # Add to captured messages for proof
                        self.captured_messages.append({
                            'channel': channel_title,
                            'channel_id': channel_id,
                            'message_id': msg_id,
                            'content': str(msg_content),
                            'timestamp': str(msg_time),
                            'proof_type': 'historical'
                        })
                else:
                    logger.warning(f"   ⚠️  No recent messages found in {channel_title}")
                    
            except Exception as e:
                logger.error(f"   ❌ Failed to get messages from {channel_title}: {e}")
    
    async def _setup_realtime_monitoring(self):
        """Set up real-time message monitoring."""
        logger.info("\n📡 Step 3: Setting Up Real-time Monitoring")
        logger.info("-" * 40)
        
        # Create message handler for proof
        async def proof_message_handler(event):
            """Handle new messages and capture them as proof."""
            try:
                message = event.message
                chat = await event.get_chat()
                
                # Extract message data
                msg_data = {
                    'channel': getattr(chat, 'title', 'Unknown Channel'),
                    'channel_id': str(chat.id),
                    'message_id': message.id,
                    'content': message.text or '[Media/Non-text content]',
                    'timestamp': message.date.isoformat() if message.date else 'Unknown',
                    'sender_id': message.sender_id,
                    'proof_type': 'realtime'
                }
                
                # Add to captured messages
                self.captured_messages.append(msg_data)
                
                # Log the captured message
                logger.info(f"🎯 LIVE MESSAGE CAPTURED!")
                logger.info(f"   Channel: {msg_data['channel']}")
                logger.info(f"   Time: {msg_data['timestamp']}")
                logger.info(f"   Content: {msg_data['content'][:100]}...")
                logger.info(f"   Message ID: {msg_data['message_id']}")
                
            except Exception as e:
                logger.error(f"Error in proof message handler: {e}")
        
        # Add event handler to client
        self.telethon_client.client.add_event_handler(
            proof_message_handler,
            events.NewMessage()
        )
        
        logger.info("✅ Real-time message handler installed")
        logger.info("🔍 Now monitoring for new messages...")
    
    async def _monitor_for_new_messages(self):
        """Monitor for new messages for a short period."""
        logger.info("\n⏱️  Step 4: Monitoring for New Messages (15 seconds)")
        logger.info("-" * 40)
        logger.info("💡 Send a message to @telegram or @durov to see live capture!")
        
        initial_count = len(self.captured_messages)
        
        # Monitor for 15 seconds
        for i in range(15):
            await asyncio.sleep(1)
            
            current_count = len(self.captured_messages)
            new_messages = current_count - initial_count
            
            # Show progress every 5 seconds
            if (i + 1) % 5 == 0:
                logger.info(f"⏰ {15 - i - 1} seconds remaining... ({new_messages} new messages captured)")
        
        final_count = len(self.captured_messages)
        new_messages = final_count - initial_count
        
        logger.info(f"\n📊 Monitoring Complete:")
        logger.info(f"   📥 New messages captured: {new_messages}")
        logger.info(f"   📋 Total messages in proof: {final_count}")
    
    async def _cleanup(self):
        """Clean up resources."""
        logger.info("\n🧹 Cleaning up...")
        
        if self.telethon_client:
            await self.telethon_client.stop()
            logger.info("✅ Telethon client disconnected")
    
    def display_proof_summary(self):
        """Display comprehensive proof of message capture."""
        logger.info("\n" + "=" * 60)
        logger.info("🏆 MESSAGE CAPTURE PROOF SUMMARY")
        logger.info("=" * 60)
        
        if not self.captured_messages:
            logger.warning("⚠️  No messages captured during proof")
            return
        
        # Group messages by type
        historical_msgs = [m for m in self.captured_messages if m['proof_type'] == 'historical']
        realtime_msgs = [m for m in self.captured_messages if m['proof_type'] == 'realtime']
        
        logger.info(f"📊 PROOF STATISTICS:")
        logger.info(f"   💾 Historical messages: {len(historical_msgs)}")
        logger.info(f"   ⚡ Real-time messages: {len(realtime_msgs)}")
        logger.info(f"   🎯 Total captured: {len(self.captured_messages)}")
        
        # Show detailed proof
        logger.info(f"\n📋 DETAILED MESSAGE PROOF:")
        
        for i, msg in enumerate(self.captured_messages, 1):
            logger.info(f"\n{i}. {msg['proof_type'].upper()} MESSAGE:")
            logger.info(f"   📺 Channel: {msg['channel']}")
            logger.info(f"   🆔 Message ID: {msg['message_id']}")
            logger.info(f"   ⏰ Timestamp: {msg['timestamp']}")
            logger.info(f"   📝 Content: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")
        
        # Save proof to file
        proof_file = f"message_capture_proof_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(proof_file, 'w') as f:
                json.dump(self.captured_messages, f, indent=2, default=str)
            logger.info(f"\n💾 Proof saved to: {proof_file}")
        except Exception as e:
            logger.error(f"Failed to save proof file: {e}")
        
        if len(self.captured_messages) > 0:
            logger.info(f"\n✅ PROOF CONFIRMED: System successfully captured {len(self.captured_messages)} real messages!")
        else:
            logger.info(f"\n⚠️  PROOF INCOMPLETE: No messages captured (channels may be inactive)")


async def main():
    """Main proof demonstration."""
    logger.info("🌟 GeopolMonitor Message Capture Proof")
    logger.info("   Demonstrating REAL message capture from Telegram channels")
    logger.info("=" * 60)
    
    proof = MessageCaptureProof()
    
    try:
        success = await proof.demonstrate_message_capture()
        
        # Display proof summary
        proof.display_proof_summary()
        
        if success:
            logger.info("\n🎉 MESSAGE CAPTURE PROOF COMPLETED!")
            logger.info("✅ System demonstrated real Telegram message capture")
        else:
            logger.info("\n⚠️  PROOF DEMONSTRATION HAD ISSUES")
            logger.info("🔧 Check logs for details")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Proof interrupted by user")
        return False
    except Exception as e:
        logger.error(f"\n❌ Proof failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 