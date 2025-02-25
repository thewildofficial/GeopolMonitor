"""Settings configuration."""
import os
from pathlib import Path
from typing import Tuple, List

# Load environment variables if .env file exists
from dotenv import load_dotenv
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "src/web/static"
TEMPLATES_DIR = BASE_DIR / "src/web/templates"

# Database
DB_PATH = BASE_DIR / "news_monitor.db"

def get_api_keys() -> List[str]:
    """Get list of API keys from environment variables."""
    keys = []
    i = 0
    while True:
        key = os.getenv(f"GEMINI_API_KEY_{i}") if i > 0 else os.getenv("GEMINI_API_KEY")
        if not key:
            break
        keys.append(key)
        i += 1
    return keys if keys else [os.getenv("GEMINI_API_KEY")]  # Fallback to single key

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# API Configuration
GEMINI_API_KEYS = get_api_keys()

# Rate Limiting
RPM_LIMIT = 15  # Requests per minute
RPD_LIMIT = 1500  # Requests per day
MINUTE_WINDOW = 60  # Time window in seconds for RPM
DAY_WINDOW = 86400  # Time window in seconds for RPD

# Web Server
WEB_HOST = "0.0.0.0"
WEB_PORT = 8000

# Feed Processing
MAX_CONCURRENT_FEEDS = 5  # Reduced from 10 to prevent overwhelming the API
FEED_POLL_INTERVAL: Tuple[int, int] = (60, 120)  # Increased interval to reduce API pressure
ERROR_BACKOFF_DELAY: int = 120  # Increased backoff time for error recovery
BATCH_SIZE: int = 3  # Reduced batch size for more manageable processing
MAX_ENTRIES_PER_FEED: int = 10  # Reduced max entries to process per feed
API_CALLS_PER_MINUTE: int = 15 # Adjusted to stay well within Gemini API limits
API_CALLS_PER_DAY: int = 1500  # Conservative daily limit to ensure stability