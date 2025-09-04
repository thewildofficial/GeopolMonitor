"""
Async database configuration and helpers for News/Tags/FeedCache using SQLAlchemy 2.0.
"""
from __future__ import annotations

import os
import logging
from typing import Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import select, func

from .models.news_models import NewsBase, NewsEntry, Tag, ArticleTag, FeedCache

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _get_async_url() -> str:
    url = os.getenv("POSTGRES_URL")
    if not url:
        raise RuntimeError("POSTGRES_URL is not set in environment")
    return url.replace("postgresql://", "postgresql+asyncpg://")


async def init_news_db(echo: bool = False) -> AsyncEngine:
    global _engine, _session_factory
    if _engine is not None:
        return _engine

    url = _get_async_url()
    _engine = create_async_engine(url, echo=echo, pool_pre_ping=True, pool_recycle=3600)
    _session_factory = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)

    # Ensure tables exist (alembic should manage, but safe to verify in dev)
    async with _engine.begin() as conn:
        await conn.run_sync(NewsBase.metadata.create_all)

    logger.info("News database initialized")
    return _engine


def get_news_session() -> AsyncSession:
    if _session_factory is None:
        raise RuntimeError("News DB not initialized. Call init_news_db() first.")
    return _session_factory()


async def get_news_paginated(
    page: int,
    page_size: int,
    tag_names: Optional[list[str]] = None,
):
    async with get_news_session() as session:
        where_clause = []
        if tag_names:
            # Join through the association table for tag filter
            tag_subq = (
                select(ArticleTag.article_id)
                .join(Tag, Tag.id == ArticleTag.tag_id)
                .where(Tag.name.in_(tag_names))
                .group_by(ArticleTag.article_id)
                .subquery()
            )

            total_stmt = select(func.count()).select_from(tag_subq)
            total_count = (await session.execute(total_stmt)).scalar_one()

            items_stmt = (
                select(NewsEntry)
                .join(tag_subq, tag_subq.c.article_id == NewsEntry.id)
                .order_by(NewsEntry.pub_date.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
        else:
            total_stmt = select(func.count()).select_from(NewsEntry)
            total_count = (await session.execute(total_stmt)).scalar_one()
            items_stmt = (
                select(NewsEntry)
                .order_by(NewsEntry.pub_date.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )

        rows = (await session.execute(items_stmt)).scalars().all()
        return total_count, rows


