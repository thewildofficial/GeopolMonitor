"""
SQLAlchemy models for Telegram data.

This module contains the database models for storing Telegram channel monitoring data.
Uses SQLAlchemy 2.0 with async support for better performance and scalability.
"""

from sqlalchemy import (
    Column, BigInteger, String, Text, Numeric, Boolean, 
    DateTime, JSON, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.types import TypeDecorator, Text as SQLText
import json
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List, Dict, Any

# Custom type for storing list data in SQLite-compatible way
class JSONList(TypeDecorator):
    """A type for storing Python lists as JSON strings in the database."""
    impl = SQLText
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


# Create the base class for all Telegram models
TelegramBase = declarative_base()


class TelegramChannel(TelegramBase):
    """Model for Telegram channels being monitored."""
    __tablename__ = 'telegram_channels'

    # Primary key - using Telegram's channel ID
    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    
    # Channel identification
    username: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Channel metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    invite_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    member_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Geographic and categorization
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default='en')
    
    # Content categorization  
    category: Mapped[str] = mapped_column(String(100), nullable=False, default='general')
    tags: Mapped[Optional[List[str]]] = mapped_column(JSONList, nullable=True)
    
    # Channel quality and reliability metrics
    credibility_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=5.0)
    reliability_weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=1.0)
    
    # Monitoring configuration
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority_level: Mapped[int] = mapped_column(BigInteger, nullable=False, default=5)  # 1-10 scale
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Platform metadata
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False, default='channel')  # channel, group, supergroup
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_scam: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_fake: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Relationships
    messages: Mapped[List["TelegramMessage"]] = relationship("TelegramMessage", back_populates="channel", cascade="all, delete-orphan")
    metrics: Mapped[List["ChannelMetric"]] = relationship("ChannelMetric", back_populates="channel", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('idx_telegram_channels_username', 'username'),
        Index('idx_telegram_channels_region_country', 'region', 'country'),
        Index('idx_telegram_channels_active_priority', 'is_active', 'priority_level'),
        Index('idx_telegram_channels_category', 'category'),
        Index('idx_telegram_channels_last_checked', 'last_checked'),
    )

    def __repr__(self):
        return f"<TelegramChannel(id={self.channel_id}, username={self.username}, title={self.title[:50]})>"


class TelegramMessage(TelegramBase):
    """Model for individual Telegram messages."""
    __tablename__ = 'telegram_messages'

    # Primary key - using Telegram's message ID combined with channel
    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('telegram_channels.channel_id'), primary_key=True)
    
    # Message content
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Unprocessed text
    
    # Message metadata
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    edit_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Author information
    from_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    from_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_signature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Message types and media
    message_type: Mapped[str] = mapped_column(String(50), nullable=False, default='text')  # text, photo, video, document, etc.
    has_media: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    media_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Message interaction metrics
    views: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    forwards: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    replies: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Processing and analysis
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # AI-generated content analysis
    sentiment_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    urgency_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Content categorization
    detected_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    translated_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    categories: Mapped[Optional[List[str]]] = mapped_column(JSONList, nullable=True)
    entities: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Extracted entities (locations, people, etc.)
    
    # Geographic and temporal context
    detected_locations: Mapped[Optional[List[str]]] = mapped_column(JSONList, nullable=True)
    detected_events: Mapped[Optional[List[str]]] = mapped_column(JSONList, nullable=True)
    time_sensitivity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # breaking, urgent, normal, archived
    
    # Message threading and replies
    reply_to_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    forward_from_channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    forward_from_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # System metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Raw message data for debugging/analysis
    raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    channel: Mapped["TelegramChannel"] = relationship("TelegramChannel", back_populates="messages")

    # Indexes for performance
    __table_args__ = (
        Index('idx_telegram_messages_date', 'date'),
        Index('idx_telegram_messages_channel_date', 'channel_id', 'date'),
        Index('idx_telegram_messages_processed', 'ai_processed', 'processed_at'),
        Index('idx_telegram_messages_urgency', 'urgency_score'),
        Index('idx_telegram_messages_sentiment', 'sentiment_score'),
        Index('idx_telegram_messages_time_sensitivity', 'time_sensitivity'),
        Index('idx_telegram_messages_categories', 'categories'),
        Index('idx_telegram_messages_locations', 'detected_locations'),
        UniqueConstraint('message_id', 'channel_id', name='uq_message_channel'),
    )

    def __repr__(self):
        return f"<TelegramMessage(id={self.message_id}, channel={self.channel_id}, date={self.date})>"


class ChannelMetric(TelegramBase):
    """Model for tracking channel performance and health metrics."""
    __tablename__ = 'channel_metrics'

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('telegram_channels.channel_id'), nullable=False)
    
    # Temporal scope
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    measurement_period: Mapped[str] = mapped_column(String(50), nullable=False, default='daily')  # hourly, daily, weekly, monthly
    
    # Message volume metrics
    total_messages: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    messages_per_hour: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    peak_activity_hour: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # 0-23
    
    # Engagement metrics
    avg_views: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    avg_forwards: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    avg_replies: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    engagement_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)  # 0-1 ratio
    
    # Content quality metrics
    avg_sentiment: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    avg_urgency: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    avg_relevance: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Channel health indicators
    activity_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)  # 0-10 scale
    consistency_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)  # 0-10 scale
    reliability_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)  # 0-10 scale
    
    # Member and growth metrics
    member_count_start: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    member_count_end: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    member_growth_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    
    # Content distribution
    message_types: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)  # text: 50, photo: 10, etc.
    language_distribution: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)
    top_categories: Mapped[Optional[List[str]]] = mapped_column(JSONList, nullable=True)
    
    # Performance indicators
    processing_lag: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)  # seconds
    error_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)  # 0-1 ratio
    uptime_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100
    
    # System metrics
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    channel: Mapped["TelegramChannel"] = relationship("TelegramChannel", back_populates="metrics")

    # Indexes for performance
    __table_args__ = (
        Index('idx_channel_metrics_channel_recorded', 'channel_id', 'recorded_at'),
        Index('idx_channel_metrics_period', 'measurement_period'),
        Index('idx_channel_metrics_activity', 'activity_score'),
        Index('idx_channel_metrics_recorded_at', 'recorded_at'),
        UniqueConstraint('channel_id', 'recorded_at', 'measurement_period', name='uq_channel_period_time'),
    )

    def __repr__(self):
        return f"<ChannelMetric(channel={self.channel_id}, period={self.measurement_period}, recorded={self.recorded_at})>"


# Async database engine and session configuration will be added in a separate configuration file
# This keeps the models clean and allows for flexible database setup 