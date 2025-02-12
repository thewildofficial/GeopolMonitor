"""AI processing utilities using Google's Gemini API."""
import os
import re
import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional
from google import genai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiting configuration
RPM_LIMIT = 15  # Requests per minute
RPD_LIMIT = 1500  # Requests per day
MINUTE_WINDOW = 60  # Time window in seconds for RPM
DAY_WINDOW = 86400  # Time window in seconds for RPD

# Rate limiting state
last_request_time = 0
requests_this_minute = 0
requests_today = 0
day_start_time = time.time()

async def wait_for_rate_limit():
    """Implements rate limiting according to free tier limits."""
    global last_request_time, requests_this_minute, requests_today, day_start_time
    current_time = time.time()
    
    # Reset daily counter if needed
    if current_time - day_start_time >= DAY_WINDOW:
        requests_today = 0
        day_start_time = current_time
    
    # Handle daily limit
    if requests_today >= RPD_LIMIT:
        wait_time = day_start_time + DAY_WINDOW - current_time
        logger.warning(f"Daily rate limit reached. Waiting {wait_time:.2f} seconds...")
        await asyncio.sleep(wait_time)
        requests_today = 0
        day_start_time = time.time()
        current_time = time.time()
    
    # Reset minute counter if needed
    time_since_last = current_time - last_request_time
    if time_since_last >= MINUTE_WINDOW:
        requests_this_minute = 0
        last_request_time = current_time
    
    # Handle minute limit
    if requests_this_minute >= RPM_LIMIT:
        wait_time = MINUTE_WINDOW - time_since_last + 1
        logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
        await asyncio.sleep(wait_time)
        requests_this_minute = 0
        last_request_time = time.time()
    
    # Update counters
    requests_this_minute += 1
    requests_today += 1
    last_request_time = current_time

class ContentProcessor:
    """Handles content processing with Gemini API."""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be set in environment variables")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.0-flash-thinking-exp-01-21"
    
    async def process_content(self, text: str, is_title: bool = False) -> Tuple[str, str]:
        """Process content with Gemini API."""
        try:
            await wait_for_rate_limit()
            
            prompt = f"""Analyze this text and provide three things:
1. If the text is not in English, translate it to natural English. If it's already in English, improve its clarity if needed.

2. You MUST provide TWO highly specific emoji that best represent the context. Generic emojis are not allowed. Follow these rules in order:

   a) For EMOJI_1, use flag emoji if ANY of these are mentioned (even indirectly):
      - Countries or their adjective forms (e.g., "French" → 🇫🇷)
      - Capital cities (e.g., "Tokyo" → 🇯🇵)
      - Major cities (e.g., "Shanghai" → 🇨🇳)
      - Political leaders (e.g., "Macron" → 🇫🇷)
      - Government bodies (e.g., "Parliament" → use country's flag)
      - Regional organizations (e.g., "NATO" → 🇪🇺)

   b) For EMOJI_2, use the MOST SPECIFIC topic emoji possible:
      Economy & Finance:
      - Banking/Markets: 🏦
      - Currency/Money: 💵
      - Stocks/Trading: 📈
      - Business/Profit: 💰
      - Credit/Debt: 💳
      - Economic decline: 📉
      
      Politics & Law:
      - Elections: 🗳️
      - Legislation: ⚖️
      - Government: 🏛️
      - Diplomacy: 🤝
      
      Current Affairs:
      - Military: ⚔️
      - Protests: ✊
      - Disasters: 🚨
      - Crime: 🚔
      
      Social Issues:
      - Healthcare: 🏥
      - Education: 🎓
      - Housing: 🏘️
      - Employment: 💼
      
      Industry & Tech:
      - Manufacturing: 🏭
      - Technology: 💻
      - Agriculture: 🌾
      - Energy: ⚡
      - Transport: 🚢
      
      Environment:
      - Climate: 🌡️
      - Pollution: 🏭 
      - Conservation: 🌳
      - Weather: ⛈️

3. {'Keep the text concise but preserve its meaning.' if is_title else 'Provide a concise 2-3 sentence summary.'}

Text: {text}

Example responses for different scenarios:
"French elections show tight race" → 🇫🇷🗳️
"Sydney house prices soar" → 🇦🇺🏘️
"Chinese tech stocks plummet" → 🇨🇳📉
"US Senate passes new bill" → 🇺🇸⚖️
"Tokyo markets open higher" → 🇯🇵📈
"Indian farmers protest" → 🇮🇳✊
"German industrial output" → 🇩🇪🏭
"Brazilian rainforest data" → 🇧🇷🌳
"Russian military exercise" → 🇷🇺⚔️

Respond exactly in this format:
EMOJI_1: [first specific emoji]
EMOJI_2: [second specific emoji]
TEXT: [processed text]"""

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            # Parse response
            result = response.text.strip().split('\n')
            emoji1 = None
            emoji2 = None
            processed_text = text  # Default to original text
            
            for line in result:
                line = line.strip()
                if line.startswith('EMOJI_1:'):
                    emoji1 = line.split('EMOJI_1:')[1].strip()
                elif line.startswith('EMOJI_2:'):
                    emoji2 = line.split('EMOJI_2:')[1].strip()
                elif line.startswith('TEXT:'):
                    processed_text = line.split('TEXT:')[1].strip()
            
            # Return combined emoji string and processed text
            emoji_str = f"{emoji1 or '🌎'}{emoji2 or '📰'}"
            return emoji_str, processed_text

        except Exception as e:
            error_msg = str(e)
            if "RESOURCE_EXHAUSTED" in error_msg:
                logger.warning("Rate limit exceeded, taking extended break")
                await asyncio.sleep(60)  # Take a minute break
                return "⏳💤", text
            elif "INVALID_ARGUMENT" in error_msg:
                logger.error(f"Invalid input: {error_msg}")
                return "⚠️❌", text
            else:
                logger.error(f"Unexpected Gemini API error: {error_msg}")
                return "🔄❌", text

# Create singleton instance
content_processor = ContentProcessor()
process_with_gemini = content_processor.process_content