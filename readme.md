# GeopolMonitor 🌍

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot_API-blue.svg)](https://core.telegram.org/bots/api)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI_Powered-orange.svg)](https://deepmind.google/technologies/gemini/)

A real-time geopolitical news monitoring system that processes RSS feeds and sends formatted updates to Telegram channels with smart context inference and emoji tagging.

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

## Features ✨

- Real-time RSS feed monitoring
- Smart context inference with Gemini AI
- Automatic emoji tagging based on location and topic
- Telegram channel integration
- Rate-limited API handling
- Feed validation and cleaning
- Image extraction and sharing
- Markdown formatting support
- SQLite database for caching and deduplication

## Prerequisites 📋

- Python 3.9+
- A Telegram Bot Token
- A Telegram Channel
- Google Gemini API Key
- SQLite3 (usually comes with Python)

## Setup Guide 🚀

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd GeopolMonitor
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv geopolenv
   ```

3. **Activate Virtual Environment**
   - On Windows:
     ```bash
     .\geopolenv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source geopolenv/bin/activate
     ```

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure Environment Variables**
   - Copy `.env.example` to `.env`
   ```bash
   cp .env.example .env
   ```
   - Edit `.env` and add your credentials:
     ```
     TELEGRAM_TOKEN=your_telegram_bot_token
     TELEGRAM_CHANNEL_ID=your_channel_id
     GEMINI_API_KEY=your_gemini_api_key
     ```

6. **Initialize Database**
   The database will be automatically initialized when you first run the bot, but you can also initialize it manually:
   ```python
   python -c "import helper; helper.init_db()"
   ```

7. **Configure RSS Feeds**
   - Add your RSS feed URLs to `feeds.txt`, one per line
   - Run the feed cleaner to validate feeds:
     ```bash
     python clean_feed.py
     ```

## Usage 💡

### Running the Bot
```bash
python telegram_bot.py
```

### Test Mode
To test without sending to Telegram:
```bash
python dry_run.py
```

### Headless Mode
For server deployment:
```bash
python headless_geomonitor.py
```

## Database Management 🗄️

The system uses SQLite for:
- Feed cache management
- Message deduplication
- Entry history tracking

The database (`news_monitor.db`) is automatically created in the project root. To reset the database:
```bash
rm news_monitor.db
python -c "import helper; helper.init_db()"
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
