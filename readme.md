# GeopolMonitor 🌍

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-modern_web-009688.svg)](https://fastapi.tiangolo.com)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot_API-blue.svg)](https://core.telegram.org/bots/api)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI_Powered-orange.svg)](https://deepmind.google/technologies/gemini/)

A real-time geopolitical news monitoring system with AI-powered context inference, Telegram integration, and a modern web interface.

## Table of Contents 📑
- [Features](#features-)
- [Prerequisites](#prerequisites-)
- [Setup Guide](#setup-guide-)
- [Usage](#usage-)
- [Rate Limits](#rate-limits-)
- [Testing](#testing-)
- [Emoji Classification](#emoji-classification-)
- [Database Management](#database-management-)
- [Troubleshooting](#troubleshooting-)
- [Contributing](#contributing-)
- [License](#license-)

## Project Structure 📁

```
GeopolMonitor/
├── src/                    # Main source code
│   ├── core/              # Core functionality
│   │   ├── processor.py   # News processing logic
│   │   └── feed_watcher.py# Feed monitoring
│   ├── database/          # Database operations
│   │   └── models.py      # Database models
│   ├── utils/             # Utility functions
│   │   ├── text.py       # Text processing
│   │   └── ai.py         # AI integration
│   ├── telegram/          # Telegram integration
│   │   └── bot.py        # Bot functionality
│   └── web/              # Web interface
│       └── main.py       # FastAPI app
├── config/                # Configuration
│   └── settings.py       # Settings
├── web/                  # Web assets
│   ├── static/           # Static files
│   └── templates/        # HTML templates
├── tests/                # Test files
├── bot.py               # Bot entry point
└── web_server.py        # Web server entry point
```

## Features ✨

- Real-time RSS feed monitoring
- WebSocket-based live updates
- Responsive grid/list view toggle
- Theme switching (light/dark mode)
- AI-powered context inference with Gemini
- Automatic emoji tagging for locations and topics
- Telegram channel integration
- Modern web interface with search and time filtering
- Image extraction and handling
- Rate-limited API management
- SQLite database for caching

## Prerequisites 📋

- Python 3.9+
- A Telegram Bot Token
- A Telegram Channel
- Google Gemini API Key

## Setup Guide 🚀

1. **Clone and Setup Environment**
   ```bash
   git clone <repository-url>
   cd GeopolMonitor
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Create a `.env` file:
   ```
   TELEGRAM_TOKEN=your_bot_token
   TELEGRAM_CHANNEL_ID=your_channel_id
   GEMINI_API_KEY=your_gemini_api_key
   ```

3. **Initialize Database**
   ```python
   python -c "from src.database.models import init_db; init_db()"
   ```

4. **Configure Feeds**
   Add RSS feed URLs to `feeds.txt`

## Installation

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage 💡

### Run the Bot
```bash
python bot.py
```

### Run the Web Interface
```bash
python web_server.py
```

The web interface will be available at `http://localhost:8000` with features including:
- Real-time updates via WebSocket
- Grid/List view toggle
- Dark/Light theme switch
- Search functionality
- Time-based filtering (1h, 24h, 7d, all)
- Responsive design for mobile/desktop

## Technical Details 🔧
### WebSocket Integration
The system uses WebSocket connections for real-time updates:
- Automatic reconnection handling
- Server-side event broadcasting
- Real-time news delivery
- Efficient JSON message format

### Web Interface Features
- Grid/List view with FLIP animations
- Dark/Light theme with system preference detection
- Debounced search with real-time filtering
- Time-based content filtering
- Responsive image handling
- Mobile-first design
- Error state management

## Database Management 🗄️

The system uses SQLite for:
- Feed cache management
- Message deduplication
- Entry history tracking

The database (`news_monitor.db`) is automatically created in the project root. To reset the database:
```bash
rm news_monitor.db
python -c "from src.database.models import init_db; init_db()"
```

## Rate Limits ⚠️

The system respects Gemini API's free tier limits:
- 15 requests per minute (RPM)
- 1.5K requests per day (RPD)
- Automatic rate limiting and backoff

## Testing 🧪

Run the test suite:
```bash
pytest test_helper.py
```

## Emoji Classification 🎯

The system automatically classifies news using:
1. **Location Emojis** (First Position)
   - Country flags (e.g., 🇺🇸, 🇬🇧, 🇨🇳)
   - Regional indicators (e.g., 🌎 for global news)

2. **Topic Emojis** (Second Position)
   - Economy & Finance (🏦, 💵, 📈, 💰)
   - Politics & Law (🗳️, ⚖️, 🏛️)
   - Current Affairs (⚔️, ✊, 🚨)
   - Social Issues (🏥, 🎓, 🏘️)
   - Industry & Tech (🏭, 💻, 🌾)
   - Environment (🌡️, 🌳, ⛈️)

## Troubleshooting 🔧

### Common Issues
1. **Rate Limit Errors**
   - The bot will automatically handle rate limits
   - Check `GEMINI_API_KEY` if you see persistent errors

2. **Feed Errors**
   - Run `clean_feed.py` to validate feeds
   - Check feed URLs are accessible
   - Verify RSS format is valid

3. **Database Issues**
   - Delete `news_monitor.db` and restart to reset
   - Check write permissions in project directory

4. **Telegram Errors**
   - Verify bot has admin rights in channel
   - Check `TELEGRAM_TOKEN` and `TELEGRAM_CHANNEL_ID`
   - Ensure bot can post messages and media

## Contributing 🤝

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
