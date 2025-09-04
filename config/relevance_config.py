"""
Configuration settings for AI-powered relevance filtering in GeopolMonitor.
"""

# AI Analysis Configuration
AI_FILTERING_ENABLED = True
RELEVANCE_THRESHOLD = 0.3  # Messages must score >= this to be considered relevant

# Fallback Configuration
MIN_MESSAGE_LENGTH = 10  # Minimum characters for processing
KEYWORD_FALLBACK_ENABLED = True

# Analysis Thresholds (for categorization)
RELEVANCE_CATEGORIES = {
    "high": 0.7,      # 0.7-1.0: Direct government actions, conflicts, major policy
    "medium": 0.4,    # 0.4-0.69: Economic policies, regional tensions, diplomatic news
    "low": 0.2,       # 0.2-0.39: Local politics with broader implications
    "none": 0.0       # 0.0-0.19: Personal messages, spam, irrelevant content
}

# Enhanced keyword categories for fallback analysis
GEOPOLITICAL_KEYWORDS = {
    "conflicts": [
        "war", "conflict", "battle", "invasion", "attack", "military", 
        "combat", "strike", "offensive", "defense", "ceasefire", "armistice",
        "bombing", "artillery", "missile", "airstrike", "siege"
    ],
    "diplomacy": [
        "treaty", "agreement", "summit", "negotiation", "ambassador", 
        "diplomatic", "talks", "accord", "pact", "alliance", "coalition",
        "envoy", "delegation", "mediation", "arbitration", "protocol"
    ],
    "economics": [
        "sanctions", "trade", "tariff", "economy", "gdp", "inflation", 
        "economic", "financial", "embargo", "blockade", "export", "import",
        "currency", "market", "investment", "recession", "growth"
    ],
    "regions": [
        "ukraine", "russia", "china", "usa", "united states", "middle east", 
        "nato", "eu", "europe", "asia", "africa", "americas", "pacific",
        "taiwan", "syria", "israel", "palestine", "iran", "north korea"
    ],
    "security": [
        "terrorism", "cyber", "intelligence", "security", "threat", 
        "espionage", "surveillance", "hacking", "breach", "defense",
        "counterterrorism", "homeland", "border", "immigration"
    ],
    "politics": [
        "government", "election", "policy", "parliament", "congress", 
        "minister", "president", "prime minister", "chancellor", "senate",
        "referendum", "vote", "legislature", "cabinet", "opposition"
    ],
    "international": [
        "un", "united nations", "g7", "g20", "imf", "world bank", 
        "international", "global", "multilateral", "bilateral", "wto"
    ]
}

# Priority keywords for message prioritization
PRIORITY_KEYWORDS = [
    "breaking", "urgent", "alert", "developing", "confirmed",
    "exclusive", "first", "just in", "now", "live", "emergency",
    "critical", "immediate", "bulletin", "flash", "update"
]

# Performance Configuration
BATCH_SIZE = 10  # Messages processed in parallel
RATE_LIMIT_DELAY = 0.5  # Seconds between batches
MAX_RETRIES = 3  # API failure retries

# Logging Configuration
LOG_RELEVANCE_ANALYSIS = True
LOG_FILTERED_MESSAGES = False  # Set True for debugging
DETAILED_STATS = True

# Testing Configuration
TEST_MODE = False  # Enable for testing without actual Telegram/Redis
TEST_CHANNELS = ["test_channel"]

def get_filtering_config():
    """Get complete filtering configuration."""
    return {
        "ai_enabled": AI_FILTERING_ENABLED,
        "threshold": RELEVANCE_THRESHOLD,
        "min_length": MIN_MESSAGE_LENGTH,
        "categories": RELEVANCE_CATEGORIES,
        "keywords": GEOPOLITICAL_KEYWORDS,
        "priority_keywords": PRIORITY_KEYWORDS,
        "performance": {
            "batch_size": BATCH_SIZE,
            "rate_limit_delay": RATE_LIMIT_DELAY,
            "max_retries": MAX_RETRIES
        },
        "logging": {
            "log_analysis": LOG_RELEVANCE_ANALYSIS,
            "log_filtered": LOG_FILTERED_MESSAGES,
            "detailed_stats": DETAILED_STATS
        },
        "testing": {
            "test_mode": TEST_MODE,
            "test_channels": TEST_CHANNELS
        }
    }

def validate_config():
    """Validate configuration values."""
    assert 0.0 <= RELEVANCE_THRESHOLD <= 1.0, "Relevance threshold must be between 0.0 and 1.0"
    assert MIN_MESSAGE_LENGTH > 0, "Minimum message length must be positive"
    assert BATCH_SIZE > 0, "Batch size must be positive"
    assert RATE_LIMIT_DELAY >= 0, "Rate limit delay must be non-negative"
    assert MAX_RETRIES >= 0, "Max retries must be non-negative"
    
    # Validate category thresholds are in order
    cats = RELEVANCE_CATEGORIES
    assert cats["none"] <= cats["low"] <= cats["medium"] <= cats["high"], "Category thresholds must be in ascending order"
    
    return True

# Validate on import
if __name__ != "__main__":
    validate_config() 