"""SQLAlchemy ORM models for news entries, tags, article_tags, and feed_cache."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class NewsBase(DeclarativeBase):
    pass


class FeedCache(NewsBase):
    __tablename__ = "feed_cache"

    url: Mapped[str] = mapped_column(String(1024), primary_key=True)
    last_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    etag: Mapped[Optional[str]] = mapped_column(String(255))
    last_modified: Mapped[Optional[str]] = mapped_column(String(255))
    update_frequency: Mapped[int] = mapped_column(Integer, default=3600)
    last_success_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    source_priority: Mapped[int] = mapped_column(Integer, default=100, index=True)


class NewsEntry(NewsBase):
    __tablename__ = "news_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    content: Mapped[Optional[str]] = mapped_column(Text)
    link: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    guid: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    pub_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    processed_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    feed_url: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    emoji1: Mapped[Optional[str]] = mapped_column(String(8))
    emoji2: Mapped[Optional[str]] = mapped_column(String(8))
    image_url: Mapped[Optional[str]] = mapped_column(String(1024))
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    bias_category: Mapped[str] = mapped_column(String(64), default="neutral")
    bias_score: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[Optional[str]] = mapped_column(Text)
    message: Mapped[Optional[str]] = mapped_column(Text)

    tags: Mapped[list[Tag]] = relationship(
        secondary=lambda: ArticleTag.__table__, back_populates="articles"
    )

    __table_args__ = (
        Index("ix_news_pub_date_feed", "pub_date", "feed_url"),
    )


class Tag(NewsBase):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    articles: Mapped[list[NewsEntry]] = relationship(
        secondary=lambda: ArticleTag.__table__, back_populates="tags"
    )

    __table_args__ = (
        UniqueConstraint("name", "category", name="uq_tag_name_category"),
    )


class ArticleTag(NewsBase):
    __tablename__ = "article_tags"

    article_id: Mapped[int] = mapped_column(
        ForeignKey("news_entries.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (
        Index("ix_article_tags_article_id", "article_id"),
    )


