# GeopolMonitor Specifications

## 1. Project Overview

GeopolMonitor is a real-time geopolitical news monitoring system that leverages AI for context inference and provides updates via a Telegram bot and a web interface.

## 2. Key Components

### 2.1. Telegram Bot (`bot.py`)

The bot is responsible for:

*   Monitoring RSS feeds specified in `feeds.txt`.
*   Using `FeedWatcher` to asynchronously watch and process feeds.
*   Sending updates to a Telegram channel.

### 2.2. Core News Processor (`src/core/processor.py`)

This component handles:

*   Fetching and parsing articles from RSS feeds.
*   Extracting relevant information such as title, description, and images.
*   Cleaning HTML content.
*   Using Gemini AI to infer context and generate tags (topics, geography, events).
*   Generating messages with emojis for Telegram.

### 2.3. Web Interface (`src/web/main.py`)

The web interface is built with FastAPI and provides:

*   Real-time updates via WebSocket.
*   A modern web interface for browsing news articles.
*   Filtering by tags.
*   A map view for visualizing geopolitical data.
*   REST API endpoints for accessing news and tags.
*   Uses Jinja2 templates for rendering HTML.

## 3. Data Flow

1.  The `bot.py` reads RSS feed URLs from `feeds.txt`.
2.  `FeedWatcher` fetches and parses articles from the feeds.
3.  `ArticleProcessor` extracts and cleans the article content.
4.  Gemini AI is used to generate context and tags.
5.  The processed information is sent to the Telegram channel via the bot.
6.  The processed information is stored in an SQLite database.
7.  The web interface fetches news from the database and displays it to the user.

## 4. Technologies Used

*   Python 3.9+
*   FastAPI
*   Telegram Bot API
*   Gemini AI
*   SQLite
*   Jinja2
*   WebSocket

## 5. Configuration

The project is configured using environment variables defined in the `.env` file:

*   `TELEGRAM_TOKEN`: Telegram bot token.
*   `TELEGRAM_CHANNEL_ID`: Telegram channel ID.
*   `GEMINI_API_KEY`: Google Gemini API key.

## 6. Database

The project uses SQLite for data storage. The database schema includes tables for:

*   `news_entries`: Stores news articles.
*   `tags`: Stores tags (topics, geography, events).
*   `article_tags`: Stores the relationship between articles and tags.
