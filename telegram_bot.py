import feedparser
import argparse
import asyncio
import random
import datetime
import json
import os
import aiohttp

import helper as h


# Global variables for Telegram (get from dotenv)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# Cache management
def load_cache():
    """Load cache with timezone-aware datetimes."""
    try:
        with open('feed_cache.json', 'r') as f:
            cache_data = json.load(f)
            cache = {}
            for url, ts_str in cache_data.items():
                ts = datetime.datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=datetime.timezone.utc)
                cache[url] = ts
            return cache
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_cache(cache):
    """Save cache with timezone-aware datetimes."""
    cache_data = {}
    for url, ts in cache.items():
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        cache_data[url] = ts.isoformat()
    with open('feed_cache.json', 'w') as f:
        json.dump(cache_data, f, indent=2)

# Async processing
semaphore = asyncio.Semaphore(10)  # Adjust the number as needed

async def send_telegram_message(text, image_urls=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("Telegram credentials not configured.")
        return

    max_caption_length = 1024
    max_text_length = 4096
    truncated_text = text[:max_text_length]

    async with aiohttp.ClientSession() as session:
        if image_urls:
            first_image = image_urls[0]
            caption = truncated_text[:max_caption_length]
            data_photo = {
                'chat_id': TELEGRAM_CHANNEL_ID,
                'photo': first_image,
                'caption': caption,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            try:
                async with session.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                    data=data_photo
                ) as response:
                    if response.status != 200:
                        print(f"Failed to send photo: {await response.text()}")
                remaining_images = image_urls[1:]
                if remaining_images:
                    media = [{'type': 'photo', 'media': img} for img in remaining_images[:9]]
                    media_group_data = {
                        'chat_id': TELEGRAM_CHANNEL_ID,
                        'media': json.dumps(media),
                        'disable_notification': True
                    }
                    async with session.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMediaGroup",
                        data=media_group_data
                    ) as response:
                        if response.status != 200:
                            print(f"Failed to send media group: {await response.text()}")
                if len(truncated_text) > max_caption_length:
                    data_text = {
                        'chat_id': TELEGRAM_CHANNEL_ID,
                        'text': truncated_text[max_caption_length:max_text_length],
                        'parse_mode': 'MarkdownV2',
                        'disable_web_page_preview': True
                    }
                    async with session.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                        data=data_text
                                                                ) as response:
                        if response.status != 200:
                            print(f"Failed to send text: {await response.text()}")
            except Exception as e:
                print(f"Error sending to Telegram: {e}")
        else:
            data_text = {
                'chat_id': TELEGRAM_CHANNEL_ID,
                'text': truncated_text,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            try:
                async with session.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    data=data_text
                ) as response:
                    if response.status != 200:
                        print(f"Failed to send text: {await response.text()}")
            except Exception as e:
                print(f"Error sending message: {e}")

        await asyncio.sleep(1)
        
async def process_entry(entry, entry_time, logged_entries):
    """Process an article entry and return its timestamp regardless of success."""
    async with semaphore:
        try:
            result = await asyncio.wait_for(h.process_article(entry), timeout=100)
            if result:
                # Use the combined message from helper which is already formatted
                message = result['combined']

                if message not in logged_entries:
                    await send_telegram_message(message, result['images'])
                    h.append_to_log(message, logged_entries)
                else:
                    print("Skipping duplicate message.")
            return entry_time
        except Exception as e:
            print(f"Error processing entry: {e}")
            return entry_time

async def process_entries(feed, cache, feed_url, logged_entries):
    """Process new entries from a feed and update cache."""
    try:
        last_check_time = cache.get(feed_url, datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
    except AttributeError:
        last_check_time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

    new_entries = []
    entry_times = []

    for entry in feed.entries[:1]:  # Only take the first article
        try:
            year, month, day, hour, minute, second = entry.published_parsed[:6]
            entry_time = datetime.datetime(
                year, month, day, hour, minute, second,
                tzinfo=datetime.timezone.utc
            )
        except AttributeError:
            continue

        if entry_time > last_check_time:
            new_entries.append(entry)
            entry_times.append(entry_time)

    if not new_entries:
        return

    tasks = [process_entry(e, t, logged_entries) for e, t in zip(new_entries, entry_times)]
    results = await asyncio.gather(*tasks)
    new_entry_times = [t for t in results if t is not None]

    if new_entry_times:
        latest_entry_time = max(new_entry_times)
        cache[feed_url] = latest_entry_time

async def cache_saver(cache, interval):
    """Periodically save the cache to disk."""
    while True:
        save_cache(cache)
        await asyncio.sleep(interval)

async def monitor_feed(feed_url, cache, check_interval, process_entries, logged_entries):
    """Continuously monitor a single feed for updates."""
    while True:
        try:
            feed = feedparser.parse(feed_url)
            feed_title = feed.feed.get('title', 'Unknown Feed')
            print(f"\n🔍 Scanning {feed_title} ({feed_url})...")

            if feed.entries:
                await process_entries(feed, cache, feed_url, logged_entries)
            else:
                print("⚠ No new entries found")

            await asyncio.sleep(random.randint(0, 5))
        except Exception as e:
            print(f"⚠ Error processing feed {feed_url}: {e}")
        finally:
            await asyncio.sleep(check_interval)

def main(feed_file, interval):
    with open(feed_file) as f:
        feeds = f.read().splitlines()
    
    cache = load_cache()
    logged_entries = h.load_logged_entries()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    tasks = []
    for feed_url in feeds:
        tasks.append(loop.create_task(
            monitor_feed(feed_url, cache, interval, process_entries, logged_entries)
        ))

    tasks.append(loop.create_task(cache_saver(cache, 300)))

    try:
        print("▶ Starting parallel feed monitoring...")
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")
    finally:
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        save_cache(cache)
        loop.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--feeds", default="feeds.txt", help="Path to RSS feeds file")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds")
    args = parser.parse_args()

    main(args.feeds, args.interval)