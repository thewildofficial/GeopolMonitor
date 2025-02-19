"""AI processing utilities using Google's Gemini API."""
import os
import re
import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from google import genai
from config.settings import GEMINI_API_KEYS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiting constants
RPM_LIMIT = 60  # Requests per minute
RPD_LIMIT = 1500  # Requests per day
MINUTE_WINDOW = 60  # Window size in seconds
DAY_WINDOW = 86400  # 24 hours in seconds

# Initialize rate limiting variables
last_request_time = time.time()
requests_this_minute = 0
requests_today = 0
day_start_time = time.time()

class APIKeyManager:
    """Manages multiple API keys with rate limiting."""
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.key_states = [{
            'last_request_time': 0,
            'requests_this_minute': 0,
            'requests_today': 0,
            'day_start_time': time.time(),
            'backoff_until': 0
        } for _ in api_keys]
        self._lock = asyncio.Lock()
        
    def get_current_key(self) -> str:
        """Get current API key."""
        return self.api_keys[self.current_key_index]
    
    async def rotate_key(self):
        """Rotate to next available API key."""
        async with self._lock:
            original_index = self.current_key_index
            while True:
                self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                if self.key_states[self.current_key_index]['backoff_until'] <= time.time():
                    break
                if self.current_key_index == original_index:
                    # All keys are in backoff, wait for the one with shortest backoff
                    min_backoff = min(state['backoff_until'] for state in self.key_states)
                    wait_time = min_backoff - time.time()
                    if wait_time > 0:
                        logger.warning(f"All API keys are rate limited. Waiting {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)
                    break
            return self.get_current_key()
    
    async def wait_for_rate_limit(self) -> bool:
        """Check and wait for rate limits. Returns True if key rotation needed."""
        current_time = time.time()
        state = self.key_states[self.current_key_index]
        
        # Reset daily counter if needed
        if current_time - state['day_start_time'] >= 86400:  # 24 hours
            state['requests_today'] = 0
            state['day_start_time'] = current_time
        
        # Handle daily limit
        if state['requests_today'] >= 1500:  # Daily limit
            state['backoff_until'] = state['day_start_time'] + 86400
            return True
        
        # Reset minute counter if needed
        time_since_last = current_time - state['last_request_time']
        if time_since_last >= 60:
            state['requests_this_minute'] = 0
            state['last_request_time'] = current_time
        
        # Handle minute limit
        if state['requests_this_minute'] >= 15:  # Per-minute limit
            state['backoff_until'] = current_time + (60 - time_since_last)
            return True
        
        # Update counters
        state['requests_this_minute'] += 1
        state['requests_today'] += 1
        state['last_request_time'] = current_time
        return False

class ContentProcessor:
    """Handles content processing with Gemini API."""
    
    def __init__(self):
        self.key_manager = APIKeyManager(GEMINI_API_KEYS)
        self._init_client()
        self.model = "gemini-2.0-flash-thinking-exp-01-21"
    
    def _init_client(self):
        """Initialize or reinitialize the Gemini client with current API key."""
        self.client = genai.Client(api_key=self.key_manager.get_current_key())
    
    async def process_content(self, text: str, is_title: bool = False, instruction: Optional[str] = None) -> Tuple[str, str]:
        """Process content with Gemini API."""
        try:
            rotate_needed = await self.key_manager.wait_for_rate_limit()
            if rotate_needed:
                await self.key_manager.rotate_key()
                self._init_client()

            await wait_for_rate_limit()
            
            prompt = f"""Analyze this text and provide three things:

1. TRANSLATION & FORMATTING:
   - ALWAYS translate non-English text to clear, natural English
   - If already in English, improve clarity while preserving meaning
   - Remove any unnecessarily repetitive content
   - {'Format as a clear, concise title' if is_title else 'Format as exactly THREE short paragraphs that summarize the key points'}
   - Keep the tone professional and factual

2. EMOJI SELECTION:
   You MUST provide TWO highly specific emoji that best represent the context. Generic emojis are not allowed.

   a) For EMOJI_1, use flag emoji if ANY of these are mentioned (even indirectly):
      - Countries or their adjective forms (e.g., "French" → 🇫🇷)
      - Capital cities (e.g., "Tokyo" → 🇯🇵)
      - Major cities (e.g., "Shanghai" → 🇨🇳)
      - Political leaders (e.g., "Macron" → 🇫🇷)
      - Government bodies (e.g., "Parliament" → use country's flag)
      - Regional organizations (e.g., "EU" → 🇪🇺)

  b) For EMOJI_2, use the MOST SPECIFIC topic emoji:
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

3. TEXT PROCESSING:
   {instruction if instruction else 'Keep the text concise but preserve its meaning.' if is_title else 'Provide exactly three short paragraphs summarizing the key points. Each paragraph should be 1-3 sentences.'}

Text to process: {text}

Example responses for different scenarios:
"French elections show tight race" → 
EMOJI_1: 🇫🇷
EMOJI_2: 🗳️
TEXT: French Presidential Election Enters Final Phase as Polls Show Close Contest

"Long article about climate change" →
EMOJI_1: 🌎
EMOJI_2: 🌡️
TEXT: Global temperatures have reached unprecedented levels in 2024, with multiple regions experiencing record-breaking heat waves and extreme weather events.

The impact on agriculture and food security has become increasingly apparent, with crop yields declining in major farming regions and food prices rising globally.

Scientists warn that without immediate action to reduce greenhouse gas emissions, these trends will continue to worsen, potentially leading to catastrophic environmental and economic consequences.

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

    async def process_content_with_tags(self, text: str, is_title: bool = False, instruction: Optional[str] = None) -> Tuple[str, str, list[str], list[str], list[str]]:
        """Process content and generate tags with Gemini API."""
        emoji_str, processed_text = await self.process_content(text, is_title, instruction)
        topics, geography, events = await generate_tags(text)
        return emoji_str, processed_text, topics, geography, events

    async def analyze_sentiment_and_bias(self, text: str) -> Tuple[float, str, float]:
        """Analyze sentiment and bias of content using Gemini API."""
        try:
            rotate_needed = await self.key_manager.wait_for_rate_limit()
            if rotate_needed:
                await self.key_manager.rotate_key()
                self._init_client()

            prompt = f"""Analyze this text and provide three metrics:

1. SENTIMENT SCORE:
   - Score from -1.0 (extremely negative) to 1.0 (extremely positive)
   - Consider tone, language, and context
   - Be objective and consistent

2. BIAS CATEGORY:
   Choose the most evident geopolitical perspective:
   - western
   - russian
   - chinese
   - israeli
   - turkish
   - arab
   - indian
   - african
   - (any other geopolitical perspective detected)
   - neutral

3. BIAS SCORE:
   - Score from 0.0 (neutral/balanced) to 1.0 (strongly biased)
   - Consider language, sources quoted, and narrative framing

Text to analyze: {text}

Respond exactly in this format:
SENTIMENT: [score]
BIAS_CATEGORY: [category]
BIAS_SCORE: [score]"""

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            result = response.text.strip().split('\n')
            sentiment_score = 0.0
            bias_category = 'neutral'
            bias_score = 0.0

            for line in result:
                line = line.strip()
                if line.startswith('SENTIMENT:'):
                    try:
                        sentiment_score = float(line.split('SENTIMENT:')[1].strip())
                        sentiment_score = max(-1.0, min(1.0, sentiment_score))  # Clamp between -1 and 1
                    except ValueError:
                        pass
                elif line.startswith('BIAS_CATEGORY:'):
                    bias_category = line.split('BIAS_CATEGORY:')[1].strip().lower()
                elif line.startswith('BIAS_SCORE:'):
                    try:
                        bias_score = float(line.split('BIAS_SCORE:')[1].strip())
                        bias_score = max(0.0, min(1.0, bias_score))  # Clamp between 0 and 1
                    except ValueError:
                        pass

            return sentiment_score, bias_category, bias_score

        except Exception as e:
            logger.error(f"Error analyzing sentiment and bias: {e}")
            return 0.0, 'neutral', 0.0

    async def process_content_with_analysis(self, text: str, is_title: bool = False) -> Tuple[str, str, float, str, float]:
        """Process content and perform sentiment and bias analysis."""
        emoji_str, processed_text = await self.process_content(text, is_title)
        sentiment_score, bias_category, bias_score = await self.analyze_sentiment_and_bias(processed_text)
        return emoji_str, processed_text, sentiment_score, bias_category, bias_score

# Create singleton instance
content_processor = ContentProcessor()

# Update singleton instance methods
process_with_analysis = content_processor.process_content_with_analysis

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

async def generate_tags(text: str) -> Tuple[list[str], list[str], list[str]]:
    """Generate tags for an article using Gemini API."""
    try:
        await wait_for_rate_limit()
        
        prompt = """Analyze this text and generate three sets of tags:

1. TOPICS (e.g., Politics, Economy, Technology, etc.)
2. GEOGRAPHY (Countries, Regions, Cities mentioned)
3. EVENT TYPES (e.g., Election, Conflict, Treaty, Summit, etc.)

Rules for tag generation:
- Each tag should be a single word or hyphenated phrase
- Convert multi-word concepts into hyphenated form (e.g., "artificial intelligence" → "artificial-intelligence")
- Use lowercase for all tags
- Include only tags that are explicitly or strongly implied in the text
- Maximum 5 tags per category
- For geography, prefer country names over city names unless the city is the main focus

Example response format:
TOPICS: economy, technology, cybersecurity
GEOGRAPHY: united-states, china, european-union
EVENTS: trade-agreement, diplomatic-summit

Text to analyze: {text}

Respond exactly in this format:
TOPICS: [comma-separated tags]
GEOGRAPHY: [comma-separated tags]
EVENTS: [comma-separated tags]"""

        response = content_processor.client.models.generate_content(
            model=content_processor.model,
            contents=prompt.format(text=text)
        )

        # Parse response
        result = response.text.strip().split('\n')
        topics = []
        geography = []
        events = []
        
        for line in result:
            line = line.strip()
            if line.startswith('TOPICS:'):
                topics = [t.strip() for t in line.split('TOPICS:')[1].strip().split(',')]
            elif line.startswith('GEOGRAPHY:'):
                geography = [t.strip() for t in line.split('GEOGRAPHY:')[1].strip().split(',')]
            elif line.startswith('EVENTS:'):
                events = [t.strip() for t in line.split('EVENTS:')[1].strip().split(',')]
        
        return topics, geography, events

    except Exception as e:
        logger.error(f"Error generating tags: {e}")
        return [], [], []