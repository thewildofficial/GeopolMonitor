"""
LEGACY CODE: FOR TESTING, NOT FOR RUNNING
Headless GeopolMonitor Module.
This script monitors RSS feeds without sending Telegram messages.
It uses helper functions from helper.py for text processing, image extraction, and caching.
"""
import feedparser
import argparse
import time
import asyncio
import random
import datetime
import json
import os
# Import helper functions to avoid redundancy
import helper as h

# Cache management (unchanged here)

def load_cache():
    """Load cache with timezone-aware datetimes from 'feed_cache.json'."""
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
    """Save cache with timezone-aware datetimes to 'feed_cache.json'."""
    cache_data = {}
    for url, ts in cache.items():
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        cache_data[url] = ts.isoformat()
    with open('feed_cache.json', 'w') as f:
        json.dump(cache_data, f, indent=2)

async def process_entry(entry, entry_time, logged_entries):
    """
    Process a single entry using helper.process_article.
    Append the processed message to the log if not a duplicate.
    """
    async with asyncio.Semaphore(10):
        try:
            result = await asyncio.wait_for(h.process_article(entry), timeout=100)
            if result:
                formatted_result = result['combined'].strip()
                print(formatted_result)
                h.append_to_log(formatted_result, logged_entries)
            return entry_time
        except Exception as e:
            print(f"Error processing entry: {e}")
            return entry_time

async def process_entries(feed, cache, feed_url, logged_entries):
    """
    Process new feed entries and update the cache timestamp.
    Only process an entry if its published time is later than the cached time.
    """
    try:
        last_check_time = cache.get(feed_url, datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
    except AttributeError:
        last_check_time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

    new_entries = []
    entry_times = []
    for entry in feed.entries[:1]:
        try:
            year, month, day, hour, minute, second = entry.published_parsed[:6]
            entry_time = datetime.datetime(year, month, day, hour, minute, second, tzinfo=datetime.timezone.utc)
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
        cache[feed_url] = max(new_entry_times)

async def cache_saver(cache, interval):
    """Periodically save the cache every 'interval' seconds."""
    while True:
        save_cache(cache)
        await asyncio.sleep(interval)

async def monitor_feed(feed_url, cache, check_interval, logged_entries):
    """
    Continuously monitor a specified feed URL and process its entries.
    Uses helper functions and sleeps randomly between checks.
    """
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
    """
    Main function to start headless feed monitoring.
    Reads feed URLs, creates asyncio tasks for each feed, and runs them.
    """
    with open(feed_file) as f:
        feeds = f.read().splitlines()    
    cache = load_cache()
    logged_entries = h.load_logged_entries()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = []
    for feed_url in feeds:
        tasks.append(loop.create_task(monitor_feed(feed_url, cache, interval, logged_entries)))
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