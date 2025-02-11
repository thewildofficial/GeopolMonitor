from googletrans import Translator
import pycountry
import re
import asyncio
import spacy
import urllib.parse
import html
import datetime
import os

# Load models and libraries
nlp = spacy.load("en_core_web_sm")  # NLP for entity extraction
TRANSLATOR = Translator()
# Constants
COUNTRY_CODE_MAP = {'UK': 'GB', 'UK.': 'GB', 'GR': 'GR'}
REGION_ORG_EMOJIS = {
    'EU': {'keywords': ['EU', 'EUROPEAN UNION'], 'emoji': '🇪🇺'},
    'NATO': {'keywords': ['NATO'], 'emoji': '🌐'},
    'AFRICA': {'keywords': ['AFRICA'], 'emoji': '🌍'},
    'MIDDLE EAST': {'keywords': ['MIDDLE EAST'], 'emoji': '🌍'},
    'UN': {'keywords': ['UN', 'UNITED NATIONS'], 'emoji': '🇺🇳'},
}
LEADER_COUNTRY_MAP = {
    "trump": "United States",
    "putin": "Russia",
    "biden": "United States",
    "modi": "India",
    "macron": "France",
    "merkel": "Germany",
    "king charles": "United Kingdom"
}

# Helper functions
def get_flag_emoji(entity_text):
    try:
        if len(entity_text) == 2 and entity_text.isupper():
            return ''.join(chr(ord(c) + 127397) for c in entity_text)
        country = pycountry.countries.search_fuzzy(entity_text)[0]
        return ''.join(chr(ord(c) + 127397) for c in country.alpha_2)
    except:
        return None

def clean_html(text):
    text = html.unescape(text)
    return re.sub(r'<.*?>', '', text)

def extract_images(entry):
    image_urls = []
    if entry.get('description'):
        image_urls += re.findall(r'(https?://[^\s]+(?:jpg|jpeg|png|gif|bmp|svg|webp))', entry.description)
    if hasattr(entry, 'media_content'):
        image_urls += [m['url'] for m in entry.media_content if 'url' in m and m['url'].lower().endswith(('.jpg', '.png', '.jpeg', '.gif', '.bmp', '.svg', '.webp'))]
    if hasattr(entry, 'enclosures'):
        image_urls += [e['href'] for e in entry.enclosures if e.get('href', '').lower().endswith(('.jpg', '.png', '.jpeg', '.gif', '.bmp', '.svg', '.webp'))]
    return list(set(image_urls))

def extract_countries(text):
    doc = nlp(text)
    flags = set()
    
    for ent in doc.ents:
        if ent.label_ in ["GPE", "NORP"]:
            cleaned_text = re.sub(r"['’]s?$", "", ent.text).strip()
            flag = get_flag_emoji(cleaned_text)
            if flag:
                flags.add(flag)
            else:
                for country in pycountry.countries:
                    if cleaned_text.lower() in country.name.lower() or country.name.lower() in cleaned_text.lower():
                        flag = get_flag_emoji(country.name)
                        if flag:
                            flags.add(flag)
    
    for leader, country in LEADER_COUNTRY_MAP.items():
        if re.search(rf'\b{leader}\b', text.lower()):
            flags.add(get_flag_emoji(country))
    
    for region, emoji_info in REGION_ORG_EMOJIS.items():
        for keyword in emoji_info['keywords']:
            if re.search(rf'\b{keyword}\b', text.upper()):
                flags.add(emoji_info['emoji'])
    
    return list(flags)[:2]

async def translate(text):
    try:
        detected = await TRANSLATOR.detect(text)
        if detected.lang != 'en':
            translated = await TRANSLATOR.translate(text, dest='en')
            return translated.text

        return text
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def calculate_max_length(text):
    word_count = len(text.split())
    return min(300, max(20, int(word_count * 0.7)))

def clean_url(url):
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def load_logged_entries():
    """Load existing log messages into a set (without timestamps)."""
    logged_messages = set()
    if not os.path.exists('news_monitor.log'):
        return logged_messages
    with open('news_monitor.log', 'r') as f:
        for line in f:
            # Split timestamp and message
            parts = line.strip().split(' - ', 1)
            if len(parts) == 2:
                _, message = parts
                logged_messages.add(message)
    return logged_messages

def append_to_log(message, logged_entries):
    """Append a message to the log file if it's not already logged."""
    if message not in logged_entries:
        log_line = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"
        with open('news_monitor.log', 'a') as f:
            f.write(log_line)
        logged_entries.add(message)

def escape_markdown(text):
    """Escape characters that have special meanings in Telegram Markdown"""
    escape_chars = '_[]()~`>#{}'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

def clean_text(text):
    """Deep clean and normalize text for Telegram."""
    text = html.unescape(text).strip()
    text = re.sub(r'<[^>]+>', '', text)  # Remove all HTML tags
    text = re.sub(r'\\', '', text)  # Remove backslashes
    text = re.sub(r'[\u200b\u200c\u200d]+', '', text)  # Strip zero-width spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:text.rfind('.') + 1] if '.' in text else text  # Clean trailing content

async def process_article(entry):
    images = extract_images(entry)
    
    # Initial cleaning
    title_cleaned = clean_text(entry.title)
    description_cleaned = clean_text(entry.description or "")
    
    # Translate and re-clean
    title_translated = await translate(title_cleaned)
    title_translated = clean_text(title_translated)
    description_translated = await translate(description_cleaned)
    description_translated = clean_text(description_translated)

    # Escape Markdown (excluding URL)
    escaped_title = escape_markdown(title_translated)
    escaped_description = escape_markdown(description_translated)
    link = clean_url(entry.link)

    # Create combined message
    flags = extract_countries(f"{title_translated} {description_translated}")
    flags_str = ' '.join(flags) if flags else "🌐"
    combined = f"{flags_str}: **{escaped_title}** \n\n{escaped_description}\n\n[Link]({link})"  # Use hyperlink format
    
    return {
        'flags_str': flags_str,
        'title': title_translated,
        'description': description_translated,
        'link': link,
        'images': images,
        'combined': combined
    }