"""Briefing API controller for GeopolMonitor.

This module provides API endpoints for accessing daily briefing data,
including the current briefing, flash alerts, and historical briefings.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query

from ...database.models.briefing_models import (
    get_current_briefing,
    get_briefing_by_date,
    get_briefing_by_id,
    get_flash_items,
    get_regional_summary,
    get_news_in_timespan
)

logger = logging.getLogger(__name__)

# Create router for briefing endpoints
router = APIRouter(prefix="/api/briefing", tags=["briefing"])

@router.get("/current")
async def get_latest_briefing():
    """Get the latest daily briefing.
    
    Returns:
        Complete briefing data structure with all tiers
    """
    try:
        briefing = get_current_briefing()
        
        if not briefing:
            return {
                "status": "empty",
                "message": "No briefing data available yet",
                "data": {
                    "metadata": {
                        "generated_at": None,
                        "total_articles": 0,
                        "regional_hotspots": []
                    },
                    "executive_summary": {
                        "text": "No briefing has been generated yet.",
                        "key_points": []
                    },
                    "flash": {"items": []},
                    "summary": {"items": [], "regions": []},
                    "context": {"items": [], "categories": []}
                }
            }
        
        return {
            "status": "success",
            "data": briefing
        }
    except Exception as e:
        logger.error(f"Error fetching current briefing: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching briefing data")

@router.get("/flash")
async def get_flash_alerts(count: int = Query(5, description="Number of flash alerts to return"), 
                         offset: int = Query(0, description="Pagination offset")):
    """Get critical flash alerts only.
    
    Args:
        count: Number of alerts to return (default 5)
        offset: Pagination offset (default 0)
        
    Returns:
        List of flash alerts with details
    """
    try:
        alerts = get_flash_items(count, offset)
        
        return {
            "status": "success",
            "count": len(alerts),
            "data": alerts
        }
    except Exception as e:
        logger.error(f"Error fetching flash alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching flash alert data")

@router.get("/regions/{region_id}")
async def get_region_briefing(region_id: str):
    """Get region-specific briefing information.
    
    Args:
        region_id: Region code/name to get briefing for
        
    Returns:
        Region-specific briefing data and trends
    """
    try:
        # Get the current briefing
        briefing = get_current_briefing()
        
        if not briefing:
            return {
                "status": "empty",
                "message": "No briefing data available yet"
            }
        
        # Find region-specific data in the briefing
        region_data = None
        for region in briefing.get("summary", {}).get("regions", []):
            if region.get("name", "").lower() == region_id.lower():
                region_data = region
                break
        
        # Get historical trend data
        trend_data = get_regional_summary(region_id)
        
        return {
            "status": "success",
            "current": region_data,
            "trends": trend_data
        }
    except Exception as e:
        logger.error(f"Error fetching region briefing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching region briefing data for {region_id}")

@router.get("/historical/{date}")
async def get_historical_briefing(date: str):
    """Access a previous briefing by date.
    
    Args:
        date: Date string (YYYY-MM-DD)
        
    Returns:
        Complete briefing for that date
    """
    try:
        briefing = get_briefing_by_date(date)
        
        if not briefing:
            return {
                "status": "not_found",
                "message": f"No briefing found for date {date}"
            }
        
        return {
            "status": "success",
            "data": briefing
        }
    except Exception as e:
        logger.error(f"Error fetching historical briefing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching historical briefing for {date}")

@router.get("/stats")
async def get_briefing_stats():
    """Get meta-statistics about briefing content.
    
    Returns:
        Statistics about briefing coverage, update frequency, etc.
    """
    try:
        # Get the current briefing
        current = get_current_briefing()
        
        if not current:
            return {
                "status": "empty",
                "message": "No briefing data available yet"
            }
        
        # Extract metadata
        metadata = current.get("metadata", {})
        generated_at = metadata.get("generated_at")
        refreshed_at = metadata.get("refreshed_at")
        
        # Convert string timestamps to datetime if needed
        if isinstance(generated_at, str):
            try:
                generated_at = datetime.fromisoformat(generated_at)
            except ValueError:
                generated_at = None
                
        if isinstance(refreshed_at, str):
            try:
                refreshed_at = datetime.fromisoformat(refreshed_at)
            except ValueError:
                refreshed_at = None
        
        # Calculate time since last update
        now = datetime.now(timezone.utc)
        
        time_since_generation = None
        if generated_at:
            if not generated_at.tzinfo:
                generated_at = generated_at.replace(tzinfo=timezone.utc)
            time_since_generation = (now - generated_at).total_seconds()
            
        time_since_refresh = None
        if refreshed_at:
            if not refreshed_at.tzinfo:
                refreshed_at = refreshed_at.replace(tzinfo=timezone.utc)
            time_since_refresh = (now - refreshed_at).total_seconds()
        
        # Count articles by tier
        flash_count = len(current.get("flash", {}).get("items", []))
        summary_count = len(current.get("summary", {}).get("items", []))
        context_count = len(current.get("context", {}).get("items", []))
        
        # Calculate coverage statistics
        total_news_count = metadata.get("total_articles", 0)
        coverage_stats = {
            "flash_percentage": (flash_count / total_news_count * 100) if total_news_count > 0 else 0,
            "summary_percentage": (summary_count / total_news_count * 100) if total_news_count > 0 else 0,
            "context_percentage": (context_count / total_news_count * 100) if total_news_count > 0 else 0
        }
        
        return {
            "status": "success",
            "data": {
                "total_news_count": total_news_count,
                "flash_count": flash_count,
                "summary_count": summary_count,
                "context_count": context_count,
                "coverage_stats": coverage_stats,
                "generated_at": generated_at.isoformat() if generated_at else None,
                "refreshed_at": refreshed_at.isoformat() if refreshed_at else None,
                "time_since_generation": time_since_generation,
                "time_since_refresh": time_since_refresh,
                "hotspots": metadata.get("regional_hotspots", [])
            }
        }
    except Exception as e:
        logger.error(f"Error fetching briefing stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching briefing statistics")

@router.get("/range")
async def get_news_range(start: str = Query(..., description="Start timestamp (ISO format)"),
                      end: str = Query(..., description="End timestamp (ISO format)")):
    """Get news articles within a specific time range.
    
    Args:
        start: Start timestamp in ISO format
        end: End timestamp in ISO format
        
    Returns:
        List of news articles in the specified time range
    """
    try:
        # Convert string timestamps to datetime
        try:
            start_time = datetime.fromisoformat(start)
            end_time = datetime.fromisoformat(end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO format (YYYY-MM-DDTHH:MM:SS+00:00)")
        
        # Get news articles
        articles = get_news_in_timespan(start_time, end_time)
        
        return {
            "status": "success",
            "count": len(articles),
            "start": start,
            "end": end,
            "data": articles
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching news in range: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching news articles for specified range")