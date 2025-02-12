"""Configuration settings for GeopolMonitor."""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "src/web/static"
TEMPLATES_DIR = BASE_DIR / "src/web/templates"

# Database
DB_PATH = BASE_DIR / "news_monitor.db"

# API Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash-thinking-exp-01-21"

# Telegram Settings
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Rate Limiting
RPM_LIMIT = 15  # Requests per minute
RPD_LIMIT = 1500  # Requests per day
MINUTE_WINDOW = 60  # Time window in seconds for RPM
DAY_WINDOW = 86400  # Time window in seconds for RPD

# Web Server
WEB_HOST = "0.0.0.0"
WEB_PORT = 8000

# Feed Processing
MAX_CONCURRENT_FEEDS = 10
FEED_POLL_INTERVAL = (30, 60)  # Random interval between these values in seconds
ERROR_BACKOFF_DELAY = 60  # Seconds to wait after an error