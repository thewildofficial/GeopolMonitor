"""
High-Priority Telegram Channels Configuration for GeopolMonitor.

This module contains the curated list of 20-30 high-priority Telegram channels
for real-time geopolitical monitoring, organized by region and credibility tier.
"""

from typing import List, Dict, Any
from enum import Enum

from src.core.services.redis_pubsub import Priority


class CredibilityTier(Enum):
    """Channel credibility tiers for source reliability assessment."""
    VERIFIED = "verified"           # Official government/verified news
    ESTABLISHED = "established"     # Well-known journalists/organizations
    EMERGING = "emerging"          # Citizen journalists with track record
    UNVERIFIED = "unverified"      # New or unvetted sources


class GeographicRegion(Enum):
    """Geographic regions for channel categorization."""
    GLOBAL = "global"
    EUROPE = "europe"
    MIDDLE_EAST = "middle_east"
    ASIA_PACIFIC = "asia_pacific"
    AFRICA = "africa"
    AMERICAS = "americas"
    RUSSIA_CIS = "russia_cis"


# High-Priority Channel Configuration
# These channels are selected for their consistent, reliable geopolitical coverage
HIGH_PRIORITY_CHANNELS = [
    # TIER 1: VERIFIED SOURCES (Official/Verified News)
    {
        "identifier": "@rtnews",
        "title": "RT News",
        "region": GeographicRegion.RUSSIA_CIS,
        "credibility_tier": CredibilityTier.VERIFIED,
        "priority": Priority.HIGH,
        "languages": ["en", "ru"],
        "categories": ["breaking_news", "global_politics", "military"],
        "keywords": ["breaking", "urgent", "putin", "russia", "ukraine", "nato"]
    },
    {
        "identifier": "@bbcbreaking",
        "title": "BBC Breaking News",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.VERIFIED,
        "priority": Priority.HIGH,
        "languages": ["en"],
        "categories": ["breaking_news", "international"],
        "keywords": ["breaking", "urgent", "developing"]
    },
    {
        "identifier": "@cnnbrk",
        "title": "CNN Breaking News",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.VERIFIED,
        "priority": Priority.HIGH,
        "languages": ["en"],
        "categories": ["breaking_news", "us_politics", "international"],
        "keywords": ["breaking", "urgent", "biden", "congress", "nato"]
    },
    {
        "identifier": "@reutersagency",
        "title": "Reuters",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.VERIFIED,
        "priority": Priority.HIGH,
        "languages": ["en"],
        "categories": ["breaking_news", "finance", "politics"],
        "keywords": ["reuters", "exclusive", "breaking"]
    },
    {
        "identifier": "@dw_english",
        "title": "DW News",
        "region": GeographicRegion.EUROPE,
        "credibility_tier": CredibilityTier.VERIFIED,
        "priority": Priority.HIGH,
        "languages": ["en", "de"],
        "categories": ["european_politics", "germany"],
        "keywords": ["germany", "eu", "europe", "merkel", "scholz"]
    },

    # TIER 2: ESTABLISHED SOURCES (Reputable Journalists/Organizations)
    {
        "identifier": "@intelcrab",
        "title": "Intel Crab",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.ESTABLISHED,
        "priority": Priority.HIGH,
        "languages": ["en"],
        "categories": ["osint", "military", "conflicts"],
        "keywords": ["ukraine", "russia", "osint", "military", "conflict"]
    },
    {
        "identifier": "@war_monitor",
        "title": "War Monitor",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.ESTABLISHED,
        "priority": Priority.HIGH,
        "languages": ["en"],
        "categories": ["conflicts", "military", "syria", "ukraine"],
        "keywords": ["war", "conflict", "syria", "ukraine", "military"]
    },
    {
        "identifier": "@miladvisor",
        "title": "Military Advisor",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.ESTABLISHED,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["military", "defense", "strategy"],
        "keywords": ["military", "defense", "strategy", "weapons"]
    },
    {
        "identifier": "@energypolitics",
        "title": "Energy Politics",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.ESTABLISHED,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["energy", "sanctions", "economics"],
        "keywords": ["oil", "gas", "energy", "sanctions", "pipeline"]
    },

    # TIER 3: REGIONAL SPECIALISTS
    {
        "identifier": "@middle_east_spectator",
        "title": "Middle East Spectator",
        "region": GeographicRegion.MIDDLE_EAST,
        "credibility_tier": CredibilityTier.ESTABLISHED,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["middle_east", "iran", "israel", "saudi"],
        "keywords": ["iran", "israel", "saudi", "middle east", "palestine"]
    },
    {
        "identifier": "@chinaobservers",
        "title": "China Observers",
        "region": GeographicRegion.ASIA_PACIFIC,
        "credibility_tier": CredibilityTier.ESTABLISHED,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["china", "asia", "economics", "geopolitics"],
        "keywords": ["china", "xi jinping", "taiwan", "south china sea"]
    },
    {
        "identifier": "@europeelects",
        "title": "Europe Elects",
        "region": GeographicRegion.EUROPE,
        "credibility_tier": CredibilityTier.ESTABLISHED,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["elections", "europe", "politics"],
        "keywords": ["election", "poll", "vote", "parliament", "eu"]
    },
    {
        "identifier": "@africaintel",
        "title": "Africa Intelligence",
        "region": GeographicRegion.AFRICA,
        "credibility_tier": CredibilityTier.ESTABLISHED,
        "priority": Priority.MEDIUM,
        "languages": ["en", "fr"],
        "categories": ["africa", "coups", "elections"],
        "keywords": ["africa", "coup", "election", "sahel", "sudan"]
    },

    # TIER 4: EMERGING/OSINT SOURCES
    {
        "identifier": "@geostrategic",
        "title": "Geostrategic Analysis",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.EMERGING,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["analysis", "strategy", "geopolitics"],
        "keywords": ["geopolitics", "strategy", "analysis", "geostrategy"]
    },
    {
        "identifier": "@osintdefender",
        "title": "OSINT Defender",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.EMERGING,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["osint", "military", "ukraine"],
        "keywords": ["osint", "ukraine", "russia", "military", "himars"]
    },
    {
        "identifier": "@ukrainewarroom",
        "title": "Ukraine War Room",
        "region": GeographicRegion.EUROPE,
        "credibility_tier": CredibilityTier.EMERGING,
        "priority": Priority.HIGH,
        "languages": ["en"],
        "categories": ["ukraine", "war", "osint"],
        "keywords": ["ukraine", "russia", "war", "putin", "zelensky"]
    },
    {
        "identifier": "@politicsforall",
        "title": "Politics For All",
        "region": GeographicRegion.EUROPE,
        "credibility_tier": CredibilityTier.EMERGING,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["uk_politics", "elections"],
        "keywords": ["uk", "brexit", "parliament", "conservative", "labour"]
    },

    # SPECIALIZED INTELLIGENCE & SECURITY
    {
        "identifier": "@intelligencefusion",
        "title": "Intelligence Fusion",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.ESTABLISHED,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["intelligence", "security", "terrorism"],
        "keywords": ["intelligence", "security", "terrorism", "cyber"]
    },
    {
        "identifier": "@cybersecuritynews",
        "title": "Cybersecurity News",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.ESTABLISHED,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["cybersecurity", "hacking", "geopolitics"],
        "keywords": ["cyber", "hack", "ransomware", "russia", "china"]
    },

    # ECONOMIC & FINANCE FOCUS
    {
        "identifier": "@economicwar",
        "title": "Economic War",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.EMERGING,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["economics", "sanctions", "trade"],
        "keywords": ["sanctions", "trade", "economy", "swift", "dollar"]
    },
    {
        "identifier": "@globaltimes_opinion",
        "title": "Global Times Opinion",
        "region": GeographicRegion.ASIA_PACIFIC,
        "credibility_tier": CredibilityTier.VERIFIED,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["china", "opinion", "geopolitics"],
        "keywords": ["china", "belt and road", "taiwan", "us-china"]
    },

    # CONFLICT MONITORING
    {
        "identifier": "@conflictmonitor",
        "title": "Conflict Monitor",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.EMERGING,
        "priority": Priority.MEDIUM,
        "languages": ["en"],
        "categories": ["conflicts", "monitoring", "crises"],
        "keywords": ["conflict", "crisis", "civil war", "refugees"]
    },
    {
        "identifier": "@syrianews",
        "title": "Syria News",
        "region": GeographicRegion.MIDDLE_EAST,
        "credibility_tier": CredibilityTier.EMERGING,
        "priority": Priority.MEDIUM,
        "languages": ["en", "ar"],
        "categories": ["syria", "middle_east", "conflict"],
        "keywords": ["syria", "assad", "turkey", "kurds", "idlib"]
    },

    # ALTERNATIVE PERSPECTIVES
    {
        "identifier": "@southfront",
        "title": "South Front",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.EMERGING,
        "priority": Priority.LOW,
        "languages": ["en"],
        "categories": ["military", "analysis"],
        "keywords": ["military", "geopolitics", "russia", "syria"]
    },
    {
        "identifier": "@aljazeera_world",
        "title": "Al Jazeera World",
        "region": GeographicRegion.MIDDLE_EAST,
        "credibility_tier": CredibilityTier.VERIFIED,
        "priority": Priority.MEDIUM,
        "languages": ["en", "ar"],
        "categories": ["middle_east", "global", "news"],
        "keywords": ["qatar", "middle east", "palestine", "iran"]
    },

    # TEST CHANNELS (Safe for development)
    {
        "identifier": "@telegram",
        "title": "Telegram Official",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.VERIFIED,
        "priority": Priority.LOW,
        "languages": ["en"],
        "categories": ["tech", "announcements"],
        "keywords": ["telegram", "update", "feature"],
        "test_channel": True  # Mark as safe test channel
    },
    {
        "identifier": "@durov",
        "title": "Pavel Durov",
        "region": GeographicRegion.GLOBAL,
        "credibility_tier": CredibilityTier.VERIFIED,
        "priority": Priority.LOW,
        "languages": ["en"],
        "categories": ["tech", "telegram"],
        "keywords": ["durov", "telegram", "privacy"],
        "test_channel": True  # Mark as safe test channel
    }
]


def get_channels_by_priority(priority: Priority) -> List[Dict[str, Any]]:
    """Get channels filtered by priority level."""
    return [
        channel for channel in HIGH_PRIORITY_CHANNELS
        if channel.get("priority") == priority
    ]


def get_channels_by_region(region: GeographicRegion) -> List[Dict[str, Any]]:
    """Get channels filtered by geographic region."""
    return [
        channel for channel in HIGH_PRIORITY_CHANNELS
        if channel.get("region") == region
    ]


def get_channels_by_credibility(tier: CredibilityTier) -> List[Dict[str, Any]]:
    """Get channels filtered by credibility tier."""
    return [
        channel for channel in HIGH_PRIORITY_CHANNELS
        if channel.get("credibility_tier") == tier
    ]


def get_test_channels() -> List[Dict[str, Any]]:
    """Get channels marked as safe for testing."""
    return [
        channel for channel in HIGH_PRIORITY_CHANNELS
        if channel.get("test_channel", False)
    ]


def get_production_channels() -> List[Dict[str, Any]]:
    """Get all production channels (excluding test channels)."""
    return [
        channel for channel in HIGH_PRIORITY_CHANNELS
        if not channel.get("test_channel", False)
    ]


def get_channels_by_keywords(keywords: List[str]) -> List[Dict[str, Any]]:
    """Get channels that monitor specific keywords."""
    matching_channels = []
    for channel in HIGH_PRIORITY_CHANNELS:
        channel_keywords = channel.get("keywords", [])
        if any(keyword.lower() in [k.lower() for k in channel_keywords] for keyword in keywords):
            matching_channels.append(channel)
    return matching_channels


def get_all_channels() -> List[Dict[str, Any]]:
    """Get all configured channels."""
    return HIGH_PRIORITY_CHANNELS.copy()


def get_channel_count() -> int:
    """Get total number of configured channels."""
    return len(HIGH_PRIORITY_CHANNELS)


# Configuration summary
CHANNEL_SUMMARY = {
    "total_channels": len(HIGH_PRIORITY_CHANNELS),
    "by_priority": {
        "high": len(get_channels_by_priority(Priority.HIGH)),
        "medium": len(get_channels_by_priority(Priority.MEDIUM)),
        "low": len(get_channels_by_priority(Priority.LOW))
    },
    "by_credibility": {
        "verified": len(get_channels_by_credibility(CredibilityTier.VERIFIED)),
        "established": len(get_channels_by_credibility(CredibilityTier.ESTABLISHED)),
        "emerging": len(get_channels_by_credibility(CredibilityTier.EMERGING)),
        "unverified": len(get_channels_by_credibility(CredibilityTier.UNVERIFIED))
    },
    "by_region": {
        "global": len(get_channels_by_region(GeographicRegion.GLOBAL)),
        "europe": len(get_channels_by_region(GeographicRegion.EUROPE)),
        "middle_east": len(get_channels_by_region(GeographicRegion.MIDDLE_EAST)),
        "asia_pacific": len(get_channels_by_region(GeographicRegion.ASIA_PACIFIC)),
        "africa": len(get_channels_by_region(GeographicRegion.AFRICA)),
        "americas": len(get_channels_by_region(GeographicRegion.AMERICAS)),
        "russia_cis": len(get_channels_by_region(GeographicRegion.RUSSIA_CIS))
    },
    "test_channels": len(get_test_channels()),
    "production_channels": len(get_production_channels())
} 