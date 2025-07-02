# Telegram Client Setup Instructions

## Required Environment Variables

Add these to your `.env` file in the project root:

```bash
# NEW: Telegram Client Configuration (for monitoring channels)
# Get these from https://my.telegram.org/auth
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash
TELEGRAM_SESSION_NAME=geopol_monitor
TELEGRAM_RATE_LIMIT_DELAY=2.0

# Redis Configuration (for message buffering)
# Install Redis locally or use Redis Cloud
REDIS_URL=redis://localhost:6379/0
```

## Setup Steps

### 1. Get Telegram API Credentials
1. Go to https://my.telegram.org/auth
2. Log in with your phone number
3. Go to "API Development Tools"
4. Create a new application
5. Copy the `api_id` and `api_hash`

### 2. Install Redis
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt update
sudo apt install redis-server
sudo systemctl start redis

# Windows
# Download from https://redis.io/download
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Test the Setup
```python
from src.telegram.telegram_client import telegram_monitor
import asyncio

async def test():
    success = await telegram_monitor.initialize()
    print(f"Telegram client initialized: {success}")

asyncio.run(test())
```

## Channel Management

### Adding Channels to Monitor
```python
# Add a channel by username
await telegram_monitor.add_channel("@channel_username", credibility_tier="verified", region="europe")

# Add a channel by invite link
await telegram_monitor.add_channel("https://t.me/channel_name", credibility_tier="established", region="global")
```

### Credibility Tiers
- `verified`: Official government or verified news channels
- `established`: Well-known journalist or news organization channels  
- `emerging`: Citizen journalists with good track record
- `unverified`: New or unvetted sources (use with caution)

### Regions
- `global`: Worldwide coverage
- `europe`: European geopolitics
- `asia`: Asian geopolitics
- `americas`: North/South American geopolitics
- `africa`: African geopolitics
- `middle-east`: Middle Eastern geopolitics
- `oceania`: Oceania geopolitics 