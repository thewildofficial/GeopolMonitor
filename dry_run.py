"""
Dry-Run Module for GeopolMonitor.
This script performs a one-time processing of feed entries, printing out the formatted messages.
It uses helper functions from helper.py to process articles, thereby removing redundancy.
"""
import feedparser
import argparse
import os
import asyncio
import random
# Import helper for processing functions
import helper as h

# Configure cache directory for transformers, if needed
os.environ['HF_HOME'] = os.path.join(os.getcwd(), 'cache')
os.makedirs('cache', exist_ok=True)
from transformers import pipeline
# The summarizer pipeline is now defined here only if additional summarization is desired.
# In our refactoring, we rely on h.process_article for processing the article.
# If you still need custom summarization, integrate it inside h.process_article.

def print_processed_entries(feed):
    """Process and print entries in the given feed by invoking helper.process_article."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = []
    for entry in feed.entries[:5]:
        tasks.append(h.process_article(entry))
    results = loop.run_until_complete(asyncio.gather(*tasks))
    for result in results:
        if result:
            print(result['combined'] + "\n")
    loop.close()

def main(feed_file):
    """
    Main function for the dry run.
    Reads feed URLs, shuffles them, processes entries using helper functions, and prints the output.
    """
    with open(feed_file) as f:
        feeds = f.read().splitlines()
    
    print("🌐 Starting geopolitical monitor dry run...\n")
    while True:
        print("\n--------------------------------------------------")
        print("Checking news feeds... (Ctrl+C to exit)")
        print("--------------------------------------------------\n")
        random.shuffle(feeds)
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                feed_title = feed.feed.get('title', None)
                if feed_title:
                    print(f"🔍 Scanning {feed_title}...")
                else:
                    print(f"🔍 Scanning Unknown Feed ({feed_url})...")
                print_processed_entries(feed)
            except Exception as e:
                print(f"🚨 Failed to parse feed {feed_url}: {e}")
        input("\nPress Enter to refresh or Ctrl+C to quit...\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--feeds", default="feeds.txt", help="Path to RSS feeds file")
    args = parser.parse_args()
    try:
        main(args.feeds)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")
