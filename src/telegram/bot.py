"""Telegram message formatting and sending utilities."""
import os
import re
import json
import asyncio
import aiohttp
from typing import List, Optional

# Load Telegram credentials from environment
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

def escape_markdown_v2(text: str, exclude_urls: bool = False) -> str:
    """Escape characters that have special meanings in Telegram MarkdownV2 format"""
    if not text:
        return ""
    
    escape_chars = '_*[]()~`>#+-=|{}.!'
    
    if exclude_urls:
        url_pattern = r'https?://[^\s<>]+'
        urls = re.findall(url_pattern, text)
        
        placeholder_map = {}
        for i, url in enumerate(urls):
            placeholder = f"URL_PLACEHOLDER_{i}"
            placeholder_map[placeholder] = url
            text = text.replace(url, placeholder)
    
    escaped_text = ''.join(['\\' + char if char in escape_chars else char for char in text])
    
    if exclude_urls:
        for placeholder, url in placeholder_map.items():
            escaped_text = escaped_text.replace(placeholder, url)
    
    return escaped_text

async def make_telegram_request(session: aiohttp.ClientSession, endpoint: str, data: dict, retry_count: int = 0) -> bool:
    """Make a request to Telegram API with retry and rate limit handling"""
    try:
        async with session.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{endpoint}",
            data=data
        ) as response:
            response_json = await response.json()
            
            if not response_json.get('ok'):
                print(f"Telegram API error in {endpoint}: {response_json}")
                if "can't parse entities" in str(response_json.get('description', '')):
                    print(f"Text that failed parsing: {data.get('text', '')}")
            
            if response.status == 429:  # Rate limit hit
                retry_after = response_json.get('parameters', {}).get('retry_after', 3)
                print(f"Rate limited. Waiting {retry_after} seconds...")
                await asyncio.sleep(retry_after)
                if retry_count < 3:
                    return await make_telegram_request(session, endpoint, data, retry_count + 1)
                return False
            
            return response.status == 200
    except Exception as e:
        print(f"Error in {endpoint}: {e}")
        return False

async def send_message(text: str, image_urls: Optional[List[str]] = None) -> None:
    """Send a message to Telegram with optional images"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHANNEL_ID:
        print("Telegram credentials not configured.")
        return

    # Escape the message text, but keep URLs unescaped
    escaped_text = escape_markdown_v2(text, exclude_urls=True)
    
    max_caption_length = 1024
    max_text_length = 4096
    truncated_text = escaped_text[:max_text_length]
    
    async with aiohttp.ClientSession() as session:
        if image_urls and image_urls[0]:
            # Send first image with caption
            first_image = image_urls[0]
            caption = truncated_text[:max_caption_length]
            data_photo = {
                'chat_id': TELEGRAM_CHANNEL_ID,
                'photo': first_image,
                'caption': caption,
                'parse_mode': 'MarkdownV2',
                'disable_web_page_preview': True
            }
            
            success = await make_telegram_request(session, "sendPhoto", data_photo)
            
            if not success:
                print("Failed to send photo, falling back to text-only message")
                data_text = {
                    'chat_id': TELEGRAM_CHANNEL_ID,
                    'text': truncated_text,
                    'parse_mode': 'MarkdownV2',
                    'disable_web_page_preview': False
                }
                await make_telegram_request(session, "sendMessage", data_text)
            else:
                # Send remaining images if any
                remaining_images = image_urls[1:]
                if remaining_images:
                    media = [{'type': 'photo', 'media': img} for img in remaining_images[:9]]
                    media_group_data = {
                        'chat_id': TELEGRAM_CHANNEL_ID,
                        'media': json.dumps(media),
                        'disable_notification': True
                    }
                    await make_telegram_request(session, "sendMediaGroup", media_group_data)
        else:
            # Text-only message
            data_text = {
                'chat_id': TELEGRAM_CHANNEL_ID,
                'text': truncated_text,
                'parse_mode': 'MarkdownV2',
                'disable_web_page_preview': False
            }
            await make_telegram_request(session, "sendMessage", data_text)
        # Add delay between messages
        await asyncio.sleep(2)