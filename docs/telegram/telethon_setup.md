# Telethon Client Setup and Usage

## Overview

The Telethon client provides an alternative Telegram monitoring solution optimized for large-scale channel monitoring. It runs alongside the existing Pyrogram client and offers better performance for monitoring many channels simultaneously.

## Features

- **User Account Authentication**: Uses your personal Telegram account for monitoring
- **Event-Driven Architecture**: Real-time message processing as they arrive
- **Session Management**: Persistent authentication sessions (no re-login required)
- **Channel Management**: Easy addition and removal of monitored channels
- **Rate Limiting**: Built-in rate limiting and error handling
- **Statistics Tracking**: Monitor client performance and message processing

## Quick Setup

### 1. Prerequisites

Ensure you have the required environment variables in your `.env` file:

```bash
# Telegram API Configuration (same as Pyrogram)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
```

### 2. Initial Authentication

Run the authentication test script:

```bash
source venv/bin/activate
python scripts/test_telethon_auth.py
```

This will:
- Prompt for your phone number (if not already authenticated)
- Send you a verification code via Telegram
- Handle two-factor authentication if enabled
- Save a persistent session for future use

### 3. Verify Setup

After authentication, the script will test:
- ✅ Connection to Telegram servers
- ✅ Channel information retrieval
- ✅ Recent message fetching
- ✅ Channel monitoring capabilities
- ✅ Client statistics

## Usage Examples

### Basic Client Usage

```python
import asyncio
from src.telegram.telethon_client import telethon_monitor

async def main():
    # Start the client (uses saved session)
    success = await telethon_monitor.start()
    
    if success:
        print("Connected to Telegram!")
        
        # Get user info
        me = await telethon_monitor.client.get_me()
        print(f"Connected as: {me.first_name}")
        
        # Stop when done
        await telethon_monitor.stop()

asyncio.run(main())
```

### Adding Channels for Monitoring

```python
# Add a channel
success = await telethon_monitor.add_channel(
    "@channelname",
    credibility_tier="verified",
    region="europe"
)

# Get channel information
info = await telethon_monitor.get_channel_info("@channelname")
print(f"Channel: {info['title']} - {info['participants_count']} members")

# Get recent messages
messages = await telethon_monitor.get_recent_messages("@channelname", limit=10)
for msg in messages:
    print(f"[{msg['date']}] {msg['text'][:100]}...")
```

### Message Event Handling

```python
async def handle_message(message_data):
    """Custom message handler function."""
    print(f"New message from {message_data['channel_username']}: {message_data['text'][:50]}...")
    
    # Your custom processing logic here
    if "breaking" in message_data['text'].lower():
        print("🚨 Breaking news detected!")

# Register the handler
telethon_monitor.add_message_handler(handle_message)

# Start monitoring (runs until disconnected)
await telethon_monitor.start()
await telethon_monitor.run_until_disconnected()
```

## Session Management

### Session Files

- **Location**: `data/telegram_sessions/telethon_geopol_monitor.session`
- **Security**: Sessions are stored locally and contain authentication tokens
- **Persistence**: Once authenticated, you won't need to re-enter codes
- **Separation**: Uses different session from Pyrogram client (no conflicts)

### Re-authentication

If you need to re-authenticate:

```bash
# Remove the session file
rm data/telegram_sessions/telethon_geopol_monitor.session

# Run authentication script again
python scripts/test_telethon_auth.py
```

## API Integration

The Telethon client integrates with your existing GeopolMonitor infrastructure:

### Database Integration

```python
from src.database.telegram_db import get_telegram_session
from src.database.models.telegram_models import TelegramMessage

async def save_message(message_data):
    """Save message to database."""
    async with get_telegram_session() as session:
        db_message = TelegramMessage(
            message_id=message_data['message_id'],
            channel_id=message_data['channel_id'],
            text=message_data['text'],
            date=message_data['date'],
            # ... other fields
        )
        session.add(db_message)
        await session.commit()

# Register database handler
telethon_monitor.add_message_handler(save_message)
```

### AI Processing Integration

```python
from src.utils.ai import process_text_with_ai

async def ai_message_handler(message_data):
    """Process messages with AI."""
    if len(message_data['text']) > 50:  # Only process substantial messages
        ai_result = await process_text_with_ai(message_data['text'])
        print(f"AI Sentiment: {ai_result.get('sentiment', 'neutral')}")

telethon_monitor.add_message_handler(ai_message_handler)
```

## Performance and Monitoring

### Client Statistics

```python
stats = telethon_monitor.get_stats()
print(f"Messages processed: {stats['messages_received']}")
print(f"Uptime: {stats.get('uptime_seconds', 0):.1f} seconds")
print(f"Monitored channels: {stats['monitored_channels_count']}")
```

### Rate Limiting

The client includes built-in rate limiting to comply with Telegram's API limits:
- Conservative default limits
- Automatic backoff on rate limit errors
- Error handling and recovery

### Error Handling

- **Connection Issues**: Automatic reconnection with exponential backoff
- **Authentication Errors**: Clear error messages and recovery guidance
- **API Limits**: Built-in rate limiting and flood wait handling
- **Session Issues**: Automatic session validation and renewal

## Comparison with Pyrogram Client

| Feature | Telethon | Pyrogram |
|---------|----------|----------|
| **Performance** | Optimized for large-scale monitoring | Good for general use |
| **Memory Usage** | Lower memory footprint | Standard |
| **Event System** | Native event-driven architecture | Decorator-based handlers |
| **Session Format** | SQLite-based sessions | Different format |
| **API Coverage** | Comprehensive Telegram API access | Good coverage |
| **Documentation** | Extensive | Good |

## Troubleshooting

### Common Issues

1. **"no such column: version" Error**
   - This happens when trying to use a Pyrogram session with Telethon
   - Solution: Different session names are used automatically

2. **Authentication Failed**
   - Check API ID and API Hash in `.env` file
   - Ensure phone number format is correct (+1234567890)
   - Verify you received and entered the correct code

3. **Rate Limiting**
   - The client handles this automatically
   - Wait for the specified time before retrying

4. **Connection Issues**
   - Check internet connectivity
   - Verify firewall settings allow Telegram connections
   - Try again after a few minutes

### Support

For additional help:
1. Check the test script output for specific error messages
2. Review the client logs for detailed error information
3. Ensure all environment variables are correctly set
4. Verify Redis is running if using message buffering features

## Next Steps

After successful setup:
1. **Task 5**: Implement real-time channel monitoring
2. **Task 6**: Add AI processing for message analysis
3. **Task 7**: Create WebSocket integration for live updates
4. **Task 8**: Develop channel management interface 