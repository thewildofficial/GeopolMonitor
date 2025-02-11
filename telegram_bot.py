import feedparser
import argparse
import asyncio
import random
import datetime
import os
import aiohttp
import time
import json
from urllib.parse import urlparse
import helper as h

# Global variables for Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# Async processing
semaphore = asyncio.Semaphore(10)

class FeedWatcher:
    def __init__(self):
        self.feeds = {}  # Store feed info and last modified/etag
        self.session = None
        self.logged_entries = set()
        
    async def init(self):
        """Initialize aiohttp session and logged entries"""
        self.session = aiohttp.ClientSession()
        self.logged_entries = h.load_logged_entries()
        
    async def close(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            
    async def check_feed_headers(self, feed_url):
        """Check feed headers for changes using conditional GET"""
        headers = {}
        feed_info = self.feeds.get(feed_url, {})
        
        # Add conditional GET headers if we have them
        if 'etag' in feed_info:
            headers['If-None-Match'] = feed_info['etag']
        if 'last_modified' in feed_info:
            headers['If-Modified-Since'] = feed_info['last_modified']
            
        try:
            async with self.session.get(feed_url, headers=headers) as response:
                if response.status == 304:  # Not modified
                    return False
                    
                # Update feed info with new headers
                self.feeds[feed_url] = {
                    'etag': response.headers.get('ETag'),
                    'last_modified': response.headers.get('Last-Modified'),
                    'content_type': response.headers.get('Content-Type', '')
                }
                
                content = await response.text()
                return content
        except Exception as e:
            print(f"Error checking feed {feed_url}: {e}")
            return False
            
    async def process_feed_content(self, feed_url, content):
        """Process feed content if it has changed"""
        if not content:
            return
            
        feed = feedparser.parse(content)
        if not feed.entries:
            return
            
        # Get last check time from cache
        cache = h.load_feed_cache()
        last_check = cache.get(feed_url, datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
        
        # Process new entries
        new_entries = []
        entry_times = []
        
        for entry in feed.entries:
            try:
                year, month, day, hour, minute, second = entry.published_parsed[:6]
                entry_time = datetime.datetime(
                    year, month, day, hour, minute, second,
                    tzinfo=datetime.timezone.utc
                )
                if entry_time > last_check:
                    new_entries.append(entry)
                    entry_times.append(entry_time)
            except (AttributeError, TypeError):
                continue
                
        if not new_entries:
            return
            
        # Process new entries in parallel
        tasks = [self.process_entry(e, t, feed_url) for e, t in zip(new_entries, entry_times)]
        results = await asyncio.gather(*tasks)
        
        # Update cache with latest entry time
        new_entry_times = [t for t in results if t is not None]
        if new_entry_times:
            h.update_feed_cache(feed_url, max(new_entry_times))
            
    async def process_entry(self, entry, entry_time, feed_url):
        """Process a single feed entry"""
        async with semaphore:
            try:
                result = await asyncio.wait_for(h.process_article(entry), timeout=100)
                if result:
                    message = result['combined']
                    if message not in self.logged_entries:
                        await send_telegram_message(message, result['images'])
                        h.append_to_log(message, self.logged_entries, feed_url,
                                    result['title'], result['description'], result['link'])
                    else:
                        print("Skipping duplicate message.")
                return entry_time
            except Exception as e:
                print(f"Error processing entry: {e}")
                return entry_time
                
    async def watch_feed(self, feed_url):
        """Watch a single feed for updates"""
        while True:
            try:
                content = await self.check_feed_headers(feed_url)
                if content:
                    print(f"🔄 Updates found in {feed_url}")
                    await self.process_feed_content(feed_url, content)
                await asyncio.sleep(random.randint(30, 60))  # Adaptive polling interval
            except Exception as e:
                print(f"Error watching feed {feed_url}: {e}")
                await asyncio.sleep(60)  # Back off on error

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

async def main(feed_file):
    """Main function to start feed watching"""
    with open(feed_file) as f:
        feeds = f.read().splitlines()
        
    watcher = FeedWatcher()
    await watcher.init()
    
    try:
        tasks = []
        for feed_url in feeds:
            tasks.append(asyncio.create_task(watcher.watch_feed(feed_url)))
            
        print("▶ Starting real-time feed monitoring...")
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")
    finally:
        for task in tasks:
            task.cancel()
        await watcher.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--feeds", default="feeds.txt", help="Path to RSS feeds file")
    args = parser.parse_args()
    
    asyncio.run(main(args.feeds))