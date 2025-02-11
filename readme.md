# Telegram Bot Setup Guide

This guide will help you set up and run the `telegram_bot.py` script.

## Prerequisites

Make sure you have the following installed:
- Python 3.x
- pip (Python package installer)

## Installation Steps

1. **Clone the Repository**

    ```bash
    git clone https://github.com/yourusername/yourrepository.git
    cd yourrepository
    ```

2. **Install Required Packages**

    Install the necessary Python packages using pip:

    ```bash
    pip install -r requirements.txt
    ```

3. **Rename Configuration File**

    Rename the `.env.example` file to `.env`:

    ```bash
    mv .env.example .env
    ```

4. **Configure Environment Variables**

    Open the `.env` file and enter your Telegram Bot API key and Channel ID:

    ```env
    TELEGRAM_BOT_API_KEY=your_telegram_bot_api_key
    TELEGRAM_CHANNEL_ID=your_telegram_channel_id
    ```

5. **populate feeds.txt with the RSS feeds of your choice**

    it's as simple as pasting in the links one after the other on in the file, and once you've done, you can run `clean_feed.py` to verify if they can be read and detected, as well as deleting all invalid links

    sample:
    ```
    https://www.middleeastmonitor.com/rss/
    https://www.alaraby.co.uk/rss
    https://www.al-monitor.com/rss
    ...
    ```

## Running the Bot

To run the `telegram_bot.py` script, use the following command:

```bash
python telegram_bot.py
```

Your Telegram bot should now be up and running!

## Troubleshooting

If you encounter any issues, please check the following:
- Ensure all required packages are installed.
- Verify that the `.env` file contains the correct API key and Channel ID.
- Check for any error messages in the terminal and resolve them accordingly.

For further assistance, refer to the documentation or open an issue on the repository.
