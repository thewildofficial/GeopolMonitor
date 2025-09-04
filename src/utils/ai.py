"""AI processing utilities using Google's Gemini API."""
import os
import re
import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from google import genai
from config.settings import GEMINI_API_KEYS, RPM_LIMIT, RPD_LIMIT, MINUTE_WINDOW, DAY_WINDOW

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Changed from INFO to WARNING to filter out AFC messages
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiting constants (centralized in config.settings)

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
    
    async def process_content(self, text: str, url: str, is_title: bool = False, instruction: Optional[str] = None) -> Tuple[str, str]:
        """Process content with Gemini API."""
        try:
            rotate_needed = await self.key_manager.wait_for_rate_limit()
            if rotate_needed:
                await self.key_manager.rotate_key()
                self._init_client()

            # Validate URL parameter
            if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
                logger.error(f"Invalid URL provided: {url}")
                raise ValueError(f"Invalid URL format: {url}")

            # Only scrape article content if text is too short
            if len(text.strip()) < 100:
                from .scraper import scrape_article
                logger.info(f"Content too short, attempting to scrape article from: {url}")
                article_data = await scrape_article(url)
                if (article_data and article_data.get('text')):
                    logger.info(f"Successfully scraped article content from: {url}")
                    text = f"{article_data.get('title', '')}\n\n{article_data['text']}"

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

    async def process_content_with_tags(self, text: str, url: str, is_title: bool = False, instruction: Optional[str] = None) -> Tuple[str, str, list[str], list[str], list[str]]:
        """Process content and generate tags with Gemini API."""
        try:
            # First get emojis and processed text
            emoji_str, processed_text = await self.process_content(text, url, is_title, instruction)
            
            # Then get tags from the full text for better context
            if not is_title and len(text.strip()) < 100:
                from .scraper import scrape_article
                article_data = await scrape_article(url)
                if article_data and article_data.get('text'):
                    text = f"{article_data.get('title', '')}\n\n{article_data['text']}"
            
            # Generate and clean tags
            topics, geography, events = await generate_tags(text)
            
            # Ensure unique tags per category
            topics = list(dict.fromkeys(topics))
            geography = list(dict.fromkeys(geography))
            events = list(dict.fromkeys(events))
            
            return emoji_str, processed_text, topics, geography, events
        except Exception as e:
            logger.error(f"Error in process_content_with_tags: {str(e)}")
            return emoji_str, processed_text, [], [], []

    async def analyze_sentiment_and_bias(self, text: str) -> Tuple[float, str, float]:
        """Analyze sentiment and bias of content using Gemini API."""
        try:
            rotate_needed = await self.key_manager.wait_for_rate_limit()
            if rotate_needed:
                await self.key_manager.rotate_key()
                self._init_client()

            prompt = f"""Analyze this text and provide a detailed sentiment and bias analysis:

1. SENTIMENT SCORE (-1.0 to 1.0):
   Consider these aspects:
   - Overall emotional tone (negative/positive/neutral)
   - Language intensity and emotional charge
   - Impact on reader (concerning/reassuring/neutral)
   - Presence of crisis/conflict vs cooperation/progress
   - Economic implications (decline/growth/stable)
   - Social implications (division/unity/neutral)
   - Environmental impact (harmful/beneficial/neutral)
   
   Scoring guide:
   -1.0 to -0.7: Highly negative (crisis, conflict, severe problems)
   -0.6 to -0.3: Moderately negative (challenges, concerns, difficulties)
   -0.2 to 0.2: Neutral (balanced, factual, objective)
   0.3 to 0.6: Moderately positive (progress, improvement, cooperation)
   0.7 to 1.0: Highly positive (breakthrough, success, strong growth)

2. BIAS PERSPECTIVE:
   Provide 2-3 thoughtful, neutral sentences that highlight specific framing choices or perspective biases in the text. Your analysis should:
   - Identify specific examples of language, quotes, or narrative structures that reveal potential bias
   - Point to particular sentences or word choices that may subtly direct readers toward a viewpoint
   - Use strictly neutral language that does not favor any political position
   - Avoid making judgment calls about whether the bias is "good" or "bad"
   - Frame observations as helpful context for critical reading, not accusations
   
   Consider these aspects:
   - Dominant geopolitical perspectives (Western, Eastern, Regional)
   - Source diversity and representation of different viewpoints
   - Use of emotionally charged language or persuasive techniques
   - Selective presentation of facts or absence of key context
   - Historical or cultural framing choices
   - Economic or political perspectives that may influence the narrative
   - Which viewpoints benefit from the framing and which may be minimized
   
   Example analyses:
   - "This text frames economic policies using terms like 'reckless spending' rather than neutral alternatives like 'increased expenditure,' potentially directing readers toward a specific fiscal perspective. The article primarily quotes business leaders while government officials' perspectives appear briefly in the final paragraph."
   - "The reporting presents regional tensions primarily through a Western security framework, using terms like 'aggression' for one side while describing similar actions by allied nations as 'defensive positioning.' Consider how this framing might influence interpretation of the events described."
   - "While covering the diplomatic negotiations, the article dedicates significantly more space to one party's concerns (8 paragraphs) compared to the other's perspective (2 paragraphs). This structural choice, though subtle, may shape how readers understand the relative importance of each position."

3. BIAS SCORE (0.0 to 1.0):
   Evaluate these factors:
   - Source diversity (single vs multiple perspectives)
   - Language patterns (loaded terms, emotional manipulation)
   - Fact presentation (selective vs comprehensive)
   - Quote selection (balanced vs one-sided)
   - Context provision (complete vs partial)
   - Historical framing (balanced vs skewed)
   - Economic framing (fair vs biased)
   - Cultural sensitivity (present vs absent)
   
   Scoring guide:
   0.0 to 0.2: Minimal bias (multiple perspectives, balanced reporting)
   0.3 to 0.5: Moderate bias (slight favor to one perspective)
   0.6 to 0.8: Significant bias (clear favoritism, selective reporting)
   0.9 to 1.0: Strong bias (propaganda-like, heavily one-sided)

Text to analyze: {text}

Respond exactly in this format:
SENTIMENT: [score]
BIAS_CATEGORY: [2-3 sentence analysis of specific bias elements in the text, using neutral language]
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

    async def process_content_with_analysis(self, text: str, url: str, is_title: bool = False) -> Tuple[str, str, float, str, float]:
        """Process content and perform sentiment and bias analysis."""
        # First get the full article content
        from .scraper import scrape_article
        article_data = await scrape_article(url)
        full_article_text = f"{article_data.get('title', '')}\n\n{article_data['text']}" if article_data and article_data.get('text') else text
        
        # Get emoji and processed text (summary)
        emoji_str, processed_text = await self.process_content(text, url, is_title)
        
        # Use full article text for sentiment and bias analysis
        sentiment_score, bias_category, bias_score = await self.analyze_sentiment_and_bias(full_article_text)
        return emoji_str, processed_text, sentiment_score, bias_category, bias_score

    async def process_telegram_message(
        self, 
        message_text: str, 
        analysis_type: str = "relevance",
        channel_context: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Process raw Telegram message content for geopolitical analysis.
        
        Args:
            message_text: Raw text content from Telegram message
            analysis_type: Type of analysis ("relevance", "entities", "summary", "full")
            channel_context: Optional context about the channel source
            metadata: Optional metadata about the message (timestamp, author, etc.)
            
        Returns:
            Dict containing analysis results based on analysis_type
        """
        try:
            # Input validation
            if not message_text or not isinstance(message_text, str):
                raise ValueError("message_text must be a non-empty string")
            
            if analysis_type not in ["relevance", "entities", "summary", "full"]:
                raise ValueError("analysis_type must be one of: relevance, entities, summary, full")
            
            # Handle rate limiting and key rotation
            rotate_needed = await self.key_manager.wait_for_rate_limit()
            if rotate_needed:
                await self.key_manager.rotate_key()
                self._init_client()
            
            # Clean and prepare message text
            cleaned_text = self._clean_telegram_text(message_text)
            
            # Select appropriate analysis based on type
            if analysis_type == "relevance":
                return await self._analyze_geopolitical_relevance(cleaned_text, channel_context, metadata)
            elif analysis_type == "entities":
                return await self._extract_entities(cleaned_text, channel_context, metadata)
            elif analysis_type == "summary":
                return await self._generate_summary(cleaned_text, channel_context, metadata)
            elif analysis_type == "full":
                return await self._full_analysis(cleaned_text, channel_context, metadata)
                
        except Exception as e:
            logger.error(f"Error processing Telegram message: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis_type": analysis_type,
                "message_length": len(message_text) if message_text else 0
            }
    
    def _clean_telegram_text(self, text: str) -> str:
        """Clean and normalize Telegram message text."""
        # Remove excessive whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove Telegram-specific formatting (but preserve links)
        text = re.sub(r'@(\w+)', r'@\1', text)  # Keep username mentions
        text = re.sub(r'#(\w+)', r'#\1', text)  # Keep hashtags
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        return text
    
    async def process_telegram_batch(
        self, 
        messages: List[Dict[str, any]], 
        analysis_type: str = "relevance",
        batch_size: int = 10
    ) -> List[Dict[str, any]]:
        """
        Process multiple Telegram messages in batches with load balancing.
        
        Args:
            messages: List of message dictionaries with 'text' field required
            analysis_type: Type of analysis to perform on each message
            batch_size: Number of messages to process in parallel
            
        Returns:
            List of analysis results in same order as input
        """
        results = []
        
        # Process messages in batches to respect rate limits
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            
            # Create async tasks for batch processing
            tasks = []
            for msg in batch:
                if isinstance(msg, dict) and 'text' in msg:
                    task = self.process_telegram_message(
                        message_text=msg['text'],
                        analysis_type=analysis_type,
                        channel_context=msg.get('channel_context'),
                        metadata=msg.get('metadata')
                    )
                    tasks.append(task)
                else:
                    # Handle invalid message format
                    error_result = {
                        "success": False,
                        "error": "Invalid message format - 'text' field required",
                        "analysis_type": analysis_type
                    }
                    tasks.append(asyncio.create_task(self._return_async_result(error_result)))
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions in batch results
            for result in batch_results:
                if isinstance(result, Exception):
                    results.append({
                        "success": False,
                        "error": str(result),
                        "analysis_type": analysis_type
                    })
                else:
                    results.append(result)
            
            # Small delay between batches to be respectful of rate limits
            if i + batch_size < len(messages):
                await asyncio.sleep(0.5)
        
        return results
    
    async def _return_async_result(self, result):
        """Helper method to return a result asynchronously."""
        return result

    async def _analyze_geopolitical_relevance(self, text: str, channel_context: Optional[str], metadata: Optional[Dict]) -> Dict:
        """Analyze message for geopolitical relevance."""
        context_info = f"Channel: {channel_context}" if channel_context else ""
        
        prompt = f"""Analyze this Telegram message for geopolitical relevance and provide a structured assessment.

{context_info}

Message text: {text}

Analyze the content and respond in this EXACT format:

RELEVANCE_SCORE: [0.0-1.0 numeric score where 1.0 is highly relevant to geopolitics]
RELEVANCE_CATEGORY: [high/medium/low/none]
CONFIDENCE: [0.0-1.0 confidence in the assessment]
PRIMARY_TOPICS: [comma-separated list of main geopolitical topics, max 3]
GEOGRAPHIC_FOCUS: [main countries/regions mentioned, comma-separated]
REASONING: [2-3 sentence explanation of the relevance assessment]

Guidelines for scoring:
- High (0.8-1.0): Direct government actions, international relations, conflicts, major policy changes
- Medium (0.5-0.79): Economic policies with geopolitical impact, regional tensions, diplomatic news
- Low (0.2-0.49): Local politics with broader implications, trade disputes, social movements
- None (0.0-0.19): Personal messages, spam, irrelevant content, pure entertainment"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            return self._parse_relevance_response(response.text.strip(), text)
            
        except Exception as e:
            logger.error(f"Error in geopolitical relevance analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_type": "relevance"
            }

    async def _extract_entities(self, text: str, channel_context: Optional[str], metadata: Optional[Dict]) -> Dict:
        """Extract entities from the message."""
        context_info = f"Channel: {channel_context}" if channel_context else ""
        
        prompt = f"""Extract key entities from this Telegram message and structure them appropriately.

{context_info}

Message text: {text}

Extract entities and respond in this EXACT format:

PEOPLE: [comma-separated list of people mentioned]
ORGANIZATIONS: [comma-separated list of organizations, governments, companies]
LOCATIONS: [comma-separated list of countries, cities, regions]
EVENTS: [comma-separated list of specific events or situations]
TOPICS: [comma-separated list of main subject areas]
DATES_TIMES: [any dates or times mentioned]
SUMMARY: [1-2 sentence summary of the message content]

Guidelines:
- Only include entities that are clearly mentioned or directly referenced
- Use full names where possible (e.g., "United States" not "US")
- For people, include titles if mentioned (e.g., "President Biden")
- Keep each category to max 5 items, prioritize the most important"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            return self._parse_entity_response(response.text.strip(), text)
            
        except Exception as e:
            logger.error(f"Error in entity extraction: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_type": "entities"
            }

    async def _generate_summary(self, text: str, channel_context: Optional[str], metadata: Optional[Dict]) -> Dict:
        """Generate summary of the message."""
        context_info = f"Channel: {channel_context}" if channel_context else ""
        
        prompt = f"""Summarize this Telegram message and assess its key characteristics.

{context_info}

Message text: {text}

Provide a summary in this EXACT format:

SUMMARY: [2-3 sentence summary of the main content]
KEY_POINTS: [comma-separated list of 2-4 key points]
TONE: [professional/informal/urgent/neutral/other]
LANGUAGE_QUALITY: [native/translated/poor/good/excellent]
MESSAGE_TYPE: [news/opinion/announcement/discussion/spam/other]
CREDIBILITY_INDICATORS: [factors that suggest reliability or lack thereof]

Guidelines:
- Keep summary concise but informative
- Focus on factual content over opinions
- Note if the message seems to be news, analysis, or personal commentary
- Consider source reliability indicators (official accounts, verification, etc.)"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            return self._parse_summary_response(response.text.strip(), text)
            
        except Exception as e:
            logger.error(f"Error in summary generation: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_type": "summary"
            }

    async def _full_analysis(self, text: str, channel_context: Optional[str], metadata: Optional[Dict]) -> Dict:
        """Perform comprehensive analysis combining all analysis types."""
        try:
            # Run all analyses concurrently
            relevance_task = self._analyze_geopolitical_relevance(text, channel_context, metadata)
            entities_task = self._extract_entities(text, channel_context, metadata)
            summary_task = self._generate_summary(text, channel_context, metadata)
            
            relevance_result, entities_result, summary_result = await asyncio.gather(
                relevance_task, entities_task, summary_task, return_exceptions=True
            )
            
            # Combine results
            full_result = {
                "success": True,
                "analysis_type": "full",
                "message_text": text[:100] + "..." if len(text) > 100 else text,
                "relevance": relevance_result if not isinstance(relevance_result, Exception) else {"error": str(relevance_result)},
                "entities": entities_result if not isinstance(entities_result, Exception) else {"error": str(entities_result)},
                "summary": summary_result if not isinstance(summary_result, Exception) else {"error": str(summary_result)},
                "channel_context": channel_context,
                "metadata": metadata
            }
            
            return full_result
            
        except Exception as e:
            logger.error(f"Error in full analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_type": "full"
            }

    def _parse_relevance_response(self, response_text: str, original_text: str) -> Dict:
        """Parse the geopolitical relevance analysis response."""
        result = {
            "success": True,
            "analysis_type": "relevance",
            "relevance_score": 0.0,
            "relevance_category": "none",
            "confidence": 0.0,
            "primary_topics": [],
            "geographic_focus": [],
            "reasoning": "",
            "message_text": original_text[:100] + "..." if len(original_text) > 100 else original_text
        }
        
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            try:
                if line.startswith('RELEVANCE_SCORE:'):
                    score = float(line.split('RELEVANCE_SCORE:')[1].strip())
                    result["relevance_score"] = max(0.0, min(1.0, score))
                elif line.startswith('RELEVANCE_CATEGORY:'):
                    result["relevance_category"] = line.split('RELEVANCE_CATEGORY:')[1].strip().lower()
                elif line.startswith('CONFIDENCE:'):
                    conf = float(line.split('CONFIDENCE:')[1].strip())
                    result["confidence"] = max(0.0, min(1.0, conf))
                elif line.startswith('PRIMARY_TOPICS:'):
                    topics = [t.strip() for t in line.split('PRIMARY_TOPICS:')[1].strip().split(',') if t.strip()]
                    result["primary_topics"] = topics[:3]  # Max 3 topics
                elif line.startswith('GEOGRAPHIC_FOCUS:'):
                    geo = [g.strip() for g in line.split('GEOGRAPHIC_FOCUS:')[1].strip().split(',') if g.strip()]
                    result["geographic_focus"] = geo[:5]  # Max 5 locations
                elif line.startswith('REASONING:'):
                    result["reasoning"] = line.split('REASONING:')[1].strip()
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parsing relevance response line '{line}': {e}")
                continue
        
        return result

    def _parse_entity_response(self, response_text: str, original_text: str) -> Dict:
        """Parse the entity extraction response."""
        result = {
            "success": True,
            "analysis_type": "entities",
            "people": [],
            "organizations": [],
            "locations": [],
            "events": [],
            "topics": [],
            "dates_times": [],
            "summary": "",
            "message_text": original_text[:100] + "..." if len(original_text) > 100 else original_text
        }
        
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            try:
                if line.startswith('PEOPLE:'):
                    people = [p.strip() for p in line.split('PEOPLE:')[1].strip().split(',') if p.strip()]
                    result["people"] = people[:5]
                elif line.startswith('ORGANIZATIONS:'):
                    orgs = [o.strip() for o in line.split('ORGANIZATIONS:')[1].strip().split(',') if o.strip()]
                    result["organizations"] = orgs[:5]
                elif line.startswith('LOCATIONS:'):
                    locs = [l.strip() for l in line.split('LOCATIONS:')[1].strip().split(',') if l.strip()]
                    result["locations"] = locs[:5]
                elif line.startswith('EVENTS:'):
                    events = [e.strip() for e in line.split('EVENTS:')[1].strip().split(',') if e.strip()]
                    result["events"] = events[:5]
                elif line.startswith('TOPICS:'):
                    topics = [t.strip() for t in line.split('TOPICS:')[1].strip().split(',') if t.strip()]
                    result["topics"] = topics[:5]
                elif line.startswith('DATES_TIMES:'):
                    dates = [d.strip() for d in line.split('DATES_TIMES:')[1].strip().split(',') if d.strip()]
                    result["dates_times"] = dates[:3]
                elif line.startswith('SUMMARY:'):
                    result["summary"] = line.split('SUMMARY:')[1].strip()
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parsing entity response line '{line}': {e}")
                continue
        
        return result

    def _parse_summary_response(self, response_text: str, original_text: str) -> Dict:
        """Parse the summary generation response."""
        result = {
            "success": True,
            "analysis_type": "summary",
            "summary": "",
            "key_points": [],
            "tone": "",
            "language_quality": "",
            "message_type": "",
            "credibility_indicators": "",
            "message_text": original_text[:100] + "..." if len(original_text) > 100 else original_text
        }
        
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            try:
                if line.startswith('SUMMARY:'):
                    result["summary"] = line.split('SUMMARY:')[1].strip()
                elif line.startswith('KEY_POINTS:'):
                    points = [p.strip() for p in line.split('KEY_POINTS:')[1].strip().split(',') if p.strip()]
                    result["key_points"] = points[:4]
                elif line.startswith('TONE:'):
                    result["tone"] = line.split('TONE:')[1].strip()
                elif line.startswith('LANGUAGE_QUALITY:'):
                    result["language_quality"] = line.split('LANGUAGE_QUALITY:')[1].strip()
                elif line.startswith('MESSAGE_TYPE:'):
                    result["message_type"] = line.split('MESSAGE_TYPE:')[1].strip()
                elif line.startswith('CREDIBILITY_INDICATORS:'):
                    result["credibility_indicators"] = line.split('CREDIBILITY_INDICATORS:')[1].strip()
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parsing summary response line '{line}': {e}")
                continue
        
        return result

# Create singleton instance
content_processor = ContentProcessor()

# Update singleton instance methods
process_with_analysis = content_processor.process_content_with_analysis
process_telegram_message = content_processor.process_telegram_message
process_telegram_batch = content_processor.process_telegram_batch

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
        
        # Clean and shorten text if needed
        text = text[:4000] if len(text) > 4000 else text
        
        prompt = """Analyze this text and generate only relevant tags in three categories:

1. TOPICS: Generate 2-3 specific topic tags that represent the main subjects
2. GEOGRAPHY: List only countries, regions, or cities that are directly mentioned or central to the story
3. EVENTS: Create 1-2 specific event-type tags that describe what's happening

STRICT FORMAT RULES:
- Each tag must be lowercase, hyphenated if multiple words
- NO special characters or brackets
- NO generic terms like "news", "update", "development"
- Each tag must be directly relevant to the article content
- DO NOT repeat tags across categories
- Keep tags concise and specific
- Use ISO country names for geography tags
- Add country context for cities (e.g., "paris", "france" as seperate tags)
- Maximum 5 tags per category, fewer is better

Example of good tags:
TOPICS: economy,defense,trade,politics,technology 
GEOGRAPHY: united-states, south-korea
EVENTS: budget-cut, diplomatic-visit

Analyze this text: {text}

Respond EXACTLY in this format:
TOPICS: tag1, tag2
GEOGRAPHY: tag1, tag2
EVENTS: tag1, tag2"""

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
                topics = [t.strip() for t in line.split('TOPICS:')[1].strip().split(',') if t.strip()]
            elif line.startswith('GEOGRAPHY:'):
                geography = [t.strip() for t in line.split('GEOGRAPHY:')[1].strip().split(',') if t.strip()]
            elif line.startswith('EVENTS:'):
                events = [t.strip() for t in line.split('EVENTS:')[1].strip().split(',') if t.strip()]
        
        def clean_tag_list(tags):
            cleaned = []
            seen = set()  # Track seen tags to avoid duplicates
            
            for tag in tags:
                # Skip if empty or already seen
                if not tag or tag in seen:
                    continue
                
                # Normalize and clean the tag
                tag = tag.strip().lower()
                tag = tag.replace(' ', '-')  # Convert spaces to hyphens
                
                # Skip invalid tags
                if (len(tag) < 2 or len(tag) > 50 or
                    any(char in tag for char in '[]()<>"\',') or
                    any(term in tag for term in ['tag', 'etc', 'other', 'news', 'update'])):
                    continue
                
                seen.add(tag)
                cleaned.append(tag)
            
            # Limit number of tags per category
            return cleaned[:5]

        # Clean and deduplicate tags
        topics = clean_tag_list(topics)
        geography = clean_tag_list(geography)
        events = clean_tag_list(events)
        
        # Ensure no tag appears in multiple categories
        all_tags = set()
        for tag_list in [topics, geography, events]:
            new_tags = []
            for tag in tag_list:
                if tag not in all_tags:
                    all_tags.add(tag)
                    new_tags.append(tag)
            tag_list[:] = new_tags

        return topics, geography, events

    except Exception as e:
        logger.error(f"Error generating tags: {e}")
        return [], [], []
