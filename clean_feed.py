"""
Feed Cleaning Module for GeopolMonitor.
This script reads a list of RSS feed URLs from 'feeds.txt', validates each one,
and writes back only valid feeds.
Functions:
  - is_valid_rss: Check if a URL properly returns a valid RSS feed.
  - clean_feeds: Validate and clean the feed list file.
"""
import feedparser
import requests

def is_valid_rss(url, timeout=3):
    """
    Check if the URL returns a valid RSS feed.
    Returns True if valid (bozo flag equals 0), else False.
    """
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        return feed.bozo == 0
    except:
        return False

def clean_feeds(file_path):
    """
    Read feeds from file_path, check each for validity,
    and write back only the valid feeds.
    Also prints summary information for valid and invalid feeds.
    """
    with open(file_path, 'r') as file:
        feeds = file.readlines()
        # reverse feeds to go from bottom to top
        feeds.reverse() 

    valid_feeds = []
    total_feeds = len(feeds)
    valid_count = 0
    invalid_count = 0

    for feed in feeds:
        feed = feed.strip()
        if is_valid_rss(feed):
            valid_feeds.append(feed + '\n')
            print(f"✅ Valid feed: {feed}")
            valid_count += 1
        else:
            print(f"❌ Invalid feed: {feed}")
            invalid_count += 1

    with open(file_path, 'w') as file:
        file.writelines(valid_feeds)

    print("\nSummary:")
    print(f"Total feeds: {total_feeds}")
    print(f"Valid feeds: {valid_count}")
    print(f"Invalid feeds: {invalid_count}")

if __name__ == "__main__":
    clean_feeds('feeds.txt')





