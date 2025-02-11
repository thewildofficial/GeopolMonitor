from google import genai
import html
import re
import urllib.parse
import datetime
import os
import sqlite3
from contextlib import contextmanager
import time
import asyncio

# Initialize Gemini API client
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("API key must be set when using the Google AI API.")

# Rate limiting configuration
RPM_LIMIT = 15  # Requests per minute
RPD_LIMIT = 1500  # Requests per day
MINUTE_WINDOW = 60  # Time window in seconds for RPM
DAY_WINDOW = 86400  # Time window in seconds for RPD (24 hours)

# Rate limiting state
last_request_time = 0
requests_this_minute = 0
requests_today = 0
day_start_time = time.time()

async def wait_for_rate_limit():
    """Implements rate limiting for Gemini API according to free tier limits"""
    global last_request_time, requests_this_minute, requests_today, day_start_time
    current_time = time.time()
    
    # Reset daily counter if a new day has started
    if current_time - day_start_time >= DAY_WINDOW:
        requests_today = 0
        day_start_time = current_time
    
    # Check daily limit
    if requests_today >= RPD_LIMIT:
        wait_time = day_start_time + DAY_WINDOW - current_time
        print(f"Daily rate limit reached. Waiting {wait_time:.2f} seconds...")
        await asyncio.sleep(wait_time)
        requests_today = 0
        day_start_time = time.time()
        current_time = time.time()
    
    # Reset minute counter if a minute has passed
    time_since_last = current_time - last_request_time
    if time_since_last >= MINUTE_WINDOW:
        requests_this_minute = 0
        last_request_time = current_time
    
    # Check minute limit
    if requests_this_minute >= RPM_LIMIT:
        wait_time = MINUTE_WINDOW - time_since_last
        print(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
        await asyncio.sleep(wait_time)
        requests_this_minute = 0
        last_request_time = time.time()
    
    # Update counters
    requests_this_minute += 1
    requests_today += 1
    last_request_time = current_time

client = genai.Client(api_key=api_key)
MODEL = "gemini-2.0-flash-thinking-exp-01-21"

# Database setup
DB_PATH = 'news_monitor.db'
_connection = None

def init_db(connection=None):
    """Initialize SQLite database with required tables."""
    conn = connection if connection else sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS feed_cache (
            url TEXT PRIMARY KEY,
            last_check TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS news_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT UNIQUE,
            timestamp TIMESTAMP,
            feed_url TEXT,
            title TEXT,
            description TEXT,
            link TEXT
        )
    ''')
    conn.commit()
    if not connection:
        conn.close()

@contextmanager
def get_db():
    """Context manager for database connections."""
    global _connection
    
    if DB_PATH == ':memory:':
        if _connection is None:
            _connection = sqlite3.connect(DB_PATH)
            init_db(_connection)
        yield _connection
    else:
        conn = sqlite3.connect(DB_PATH)
        try:
            yield conn
        finally:
            conn.close()

def load_feed_cache():
    """Load feed cache from database."""
    with get_db() as conn:
        cursor = conn.execute('SELECT url, last_check FROM feed_cache')
        return {row[0]: datetime.datetime.fromisoformat(row[1]) for row in cursor}

def update_feed_cache(url, timestamp):
    """Update last check time for a feed."""
    with get_db() as conn:
        conn.execute('''
            INSERT OR REPLACE INTO feed_cache (url, last_check)
            VALUES (?, ?)
        ''', (url, timestamp.isoformat()))
        conn.commit()

def load_logged_entries():
    """Load existing news entries from database."""
    with get_db() as conn:
        cursor = conn.execute('SELECT message FROM news_entries')
        return {row[0] for row in cursor}

def append_to_log(message, logged_entries, feed_url=None, title=None, description=None, link=None):
    """Add a news entry to the database if not already present."""
    if message not in logged_entries:
        timestamp = datetime.datetime.now().isoformat()
        with get_db() as conn:
            conn.execute('''
                INSERT OR IGNORE INTO news_entries 
                (message, timestamp, feed_url, title, description, link)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (message, timestamp, feed_url, title, description, link))
            conn.commit()
        logged_entries.add(message)

# Initialize database on module import
init_db()

def clean_html(text):
    """Clean HTML while preserving certain entities"""
    # Special case for encoded script tags
    if text.startswith('&lt;script') and text.endswith('&lt;/script&gt;'):
        return html.unescape(text)
    # For other cases, first unescape all HTML entities
    text = html.unescape(text)
    # Then remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    return text

def extract_images(entry):
    image_urls = []
    if hasattr(entry, 'description') and entry.description:
        image_urls += re.findall(r'(https?://[^\s]+(?:jpg|jpeg|png|gif|bmp|svg|webp))', entry.description)
    if hasattr(entry, 'media_content'):
        image_urls += [m['url'] for m in entry.media_content if 'url' in m and m['url'].lower().endswith(('.jpg', '.png', '.jpeg', '.gif', '.bmp', '.svg', '.webp'))]
    if hasattr(entry, 'enclosures'):
        image_urls += [e['href'] for e in entry.enclosures if e.get('href', '').lower().endswith(('.jpg', '.png', '.jpeg', '.gif', '.bmp', '.svg', '.webp'))]
    return list(set(image_urls))

async def process_with_gemini(text, is_title=False):
    """Process text with Gemini API for translation, summarization and context extraction"""
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

IMPORTANT: Never resort to generic emojis. The text ALWAYS has some specific context that can be represented by specific emojis.

3. {'Keep the text as is but improve clarity if needed.' if is_title else 'Provide a concise summary in 2-3 sentences while preserving key information.'}

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

You must respond in exactly this format (each on a new line):
EMOJI_1: [first specific emoji]
EMOJI_2: [second specific emoji]
TEXT: [processed text]"""

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        
        # Parse response more safely
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
        
        # Enhanced location and context matching with word boundaries
        if not emoji1 or len(emoji1) > 4:
            locations = {
                r'\b(us|usa|america|american|washington)\b': '🇺🇸',
                r'\b(uk|britain|british|london|england|english)\b': '🇬🇧',
                r'\b(china|chinese|beijing|shanghai)\b': '🇨🇳',
                r'\b(russia|russian|moscow|putin)\b': '🇷🇺',
                r'\b(eu|europe|european|brussels)\b': '🇪🇺',
                r'\b(australia|australian|sydney|melbourne|canberra)\b': '🇦🇺',
                r'\b(india|indian|delhi|mumbai|modi)\b': '🇮🇳',
                r'\b(japan|japanese|tokyo|osaka)\b': '🇯🇵',
                r'\b(france|french|paris|macron)\b': '🇫🇷',
                r'\b(germany|german|berlin|scholz)\b': '🇩🇪',
                r'\b(canada|canadian|ottawa|toronto)\b': '🇨🇦',
                r'\b(italy|italian|rome|milan)\b': '🇮🇹',
                r'\b(spain|spanish|madrid|barcelona)\b': '🇪🇸',
                r'\b(brazil|brazilian|brasilia|sao paulo)\b': '🇧🇷',
                r'\b(korea|korean|seoul)\b': '🇰🇷',
                r'\b(mexico|mexican|mexico city)\b': '🇲🇽',
                r'\b(turkey|turkish|ankara|istanbul)\b': '🇹🇷',
                r'\b(israel|israeli|jerusalem|tel aviv)\b': '🇮🇱',
                r'\b(iran|iranian|tehran)\b': '🇮🇷',
                r'\b(saudi|riyadh|jeddah)\b': '🇸🇦',
            }
            text_lower = text.lower()
            for pattern, flag in locations.items():
                if re.search(pattern, text_lower):
                    emoji1 = flag
                    break
            if not emoji1:
                emoji1 = '🌎'  # Last resort: Earth instead of globe
                
        if not emoji2 or len(emoji2) > 4:
            # Enhanced topic matching with word boundaries
            topics = {
                r'\b(bank|banking|profit|loan|finance|stock|market)\b': '🏦',
                r'\b(money|cash|currency|dollar|euro|pound)\b': '💵',
                r'\b(economy|economic|gdp|growth|trade)\b': '📊',
                r'\b(debt|credit|mortgage|loan)\b': '💳',
                r'\b(election|vote|ballot|poll|campaign)\b': '🗳️',
                r'\b(law|legal|court|justice|judge)\b': '⚖️',
                r'\b(military|war|army|navy|defense|weapon)\b': '⚔️',
                r'\b(tech|technology|digital|software|cyber|ai)\b': '💻',
                r'\b(health|hospital|medical|doctor|patient|covid)\b': '🏥',
                r'\b(school|education|student|university|college)\b': '🎓',
                r'\b(climate|weather|storm|temperature)\b': '🌡️',
                r'\b(sport|sports|game|match|tournament)\b': '⚽',
                r'\b(art|museum|gallery|culture|artist)\b': '🎨',
                r'\b(house|housing|property|real estate|rent)\b': '🏘️',
                r'\b(factory|industry|manufacturing|production)\b': '🏭',
                r'\b(farm|farming|agriculture|crop|harvest)\b': '🌾',
                r'\b(protest|demonstration|riot|strike)\b': '✊',
                r'\b(crime|police|security|arrest)\b': '🚔',
                r'\b(energy|power|electricity|oil|gas)\b': '⚡',
                r'\b(transport|train|airport|shipping)\b': '🚢',
            }
            for pattern, topic_emoji in topics.items():
                if re.search(pattern, text_lower):
                    emoji2 = topic_emoji
                    break
            if not emoji2:
                emoji2 = '📰'  # Last resort: News emoji
            
        return f"{emoji1}{emoji2}", processed_text
    except Exception as e:
        error_msg = str(e)
        if "RESOURCE_EXHAUSTED" in error_msg:
            print(f"Rate limit exceeded. Taking a longer break...")
            await asyncio.sleep(60)
            return "⏳💤", text
        elif "INVALID_ARGUMENT" in error_msg:
            print(f"Invalid input: {error_msg}")
            return "⚠️❌", text
        else:
            print(f"Unexpected Gemini API error: {error_msg}")
            return "🔄❌", text

def clean_text(text):
    """Deep clean and normalize text for Telegram."""
    text = html.unescape(text).strip()
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\\', ' ', text)  # Replace backslash with space
    text = re.sub(r'\n', ' ', text)  # Replace newlines with space
    text = re.sub(r'[\u200b\u200c\u200d]+', ' ', text)  # Replace zero-width chars with space
    text = re.sub(r'\s+', ' ', text).strip()
    # Handle sentence truncation
    if '.' in text:
        parts = text.split('.')
        return parts[0].strip() + '.'
    return text

def clean_url(url):
    """Clean URL while removing authentication and keeping only scheme and netloc"""
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc
    if '@' in netloc:
        netloc = netloc.split('@')[1]
    return f"{parsed.scheme}://{netloc}"

def escape_markdown(text):
    """Escape characters that have special meanings in Telegram Markdown"""
    escape_chars = '_[]()~`>#{}%'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

async def process_article(entry):
    """Process an article by extracting information and formatting it for Telegram"""
    images = extract_images(entry)
    
    # Initial cleaning
    title_cleaned = clean_text(entry.title)
    description_cleaned = clean_text(entry.description or "")
    
    # Process with Gemini
    flags_emoji, title_processed = await process_with_gemini(title_cleaned, is_title=True)
    _, description_processed = await process_with_gemini(description_cleaned, is_title=False)

    # Escape Markdown (excluding URL)
    escaped_title = escape_markdown(title_processed)
    escaped_description = escape_markdown(description_processed)
    link = clean_url(entry.link)

    # Create combined message
    combined = f"{flags_emoji}: **{escaped_title}** \n\n{escaped_description}\n\n[Link]({link})"
    
    return {
        'flags_str': flags_emoji,
        'title': title_processed,
        'description': description_processed,
        'link': link,
        'images': images,
        'combined': combined
    }