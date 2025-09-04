"""Utility functions for handling dates and timezone conversions."""
import logging
from datetime import datetime, timezone, timedelta
import dateparser

logger = logging.getLogger(__name__)

def is_tz_aware(dt: datetime) -> bool:
    """
    Check if a datetime object is timezone-aware.
    
    Args:
        dt (datetime): The datetime object to check
        
    Returns:
        bool: True if the datetime has timezone info, False otherwise
    """
    if not isinstance(dt, datetime):
        return False
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

def ensure_utc(dt: datetime) -> datetime:
    """
    Convert a datetime object to UTC timezone.
    If the datetime is naive (no timezone), it's assumed to be UTC.
    
    Args:
        dt (datetime): The datetime object to convert
        
    Returns:
        datetime: A timezone-aware datetime in UTC
    """
    if not isinstance(dt, datetime):
        return None
        
    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        logger.debug(f"Converting naive datetime to UTC: {dt}")
        return dt.replace(tzinfo=timezone.utc)
        
    # If datetime already has timezone info, convert to UTC
    if dt.tzinfo != timezone.utc:
        logger.debug(f"Converting from {dt.tzinfo} to UTC: {dt}")
        return dt.astimezone(timezone.utc)
    
    # Already in UTC
    return dt

def safe_parse_date(date_str, default_timezone='UTC') -> datetime:
    """
    Safely parse a date string to a UTC datetime object.
    Rejects dates that are:
    - In the future
    - Older than 50 years
    
    Args:
        date_str: The date string to parse
        default_timezone: Default timezone to use if none specified
        
    Returns:
        datetime: A timezone-aware datetime in UTC or None if parsing fails
    """
    if not date_str:
        return None
    
    try:
        # Configure dateparser to handle timezone information correctly
        settings = {
            'TIMEZONE': default_timezone,
            'RETURN_AS_TIMEZONE_AWARE': True,
        }
        
        dt = dateparser.parse(date_str, settings=settings)
        if not dt:
            logger.warning(f"Failed to parse date string: {date_str}")
            return None
            
        # Convert to UTC first
        dt = ensure_utc(dt)
        
        # Check if date is in the future
        now = datetime.now(timezone.utc)
        if dt > now:
            logger.warning(f"Rejecting future date: {dt}")
            return None
            
        # Check if date is too old (older than 50 years)
        max_age = now - timedelta(days=365 * 50)
        if dt < max_age:
            logger.warning(f"Rejecting very old date: {dt}")
            return None
            
        return dt
        
    except Exception as e:
        logger.warning(f"Error parsing date string '{date_str}': {e}")
        return None

def format_datetime_for_display(dt: datetime, format_str="%Y-%m-%d %H:%M:%S %Z") -> str:
    """
    Format a datetime object for display, ensuring it is timezone-aware.
    
    Args:
        dt (datetime): The datetime to format
        format_str (str): The format string to use
        
    Returns:
        str: Formatted datetime string with timezone indicator
    """
    if not dt:
        return ""
        
    # Ensure datetime is timezone aware
    dt = ensure_utc(dt) if not is_tz_aware(dt) else dt
    
    try:
        return dt.strftime(format_str)
    except Exception as e:
        logger.error(f"Error formatting datetime {dt}: {e}")
        return str(dt)

def format_iso_date(dt: datetime) -> str:
    """
    Format a datetime as ISO 8601 string with UTC timezone (for APIs and database).
    
    Args:
        dt (datetime): The datetime to format
        
    Returns:
        str: ISO formatted datetime string with Z timezone indicator
    """
    dt = ensure_utc(dt)
    return dt.isoformat().replace('+00:00', 'Z')

def datetime_to_utc_timestamp(dt: datetime) -> float:
    """
    Convert a datetime to UTC timestamp (seconds since epoch).
    
    Args:
        dt (datetime): The datetime to convert
        
    Returns:
        float: UTC timestamp in seconds
    """
    dt = ensure_utc(dt)
    return dt.timestamp()

def format_relative_time(dt: datetime) -> str:
    """
    Format a datetime as a relative time string (e.g., "2 hours ago").
    
    Args:
        dt (datetime): The datetime to convert
        
    Returns:
        str: Human-readable relative time
    """
    if not dt:
        return ""
        
    # Ensure datetime is timezone aware in UTC
    dt = ensure_utc(dt) if dt else None
    if not dt:
        return ""
        
    now = datetime.now(timezone.utc)
    diff = now - dt
    
    # Handle future dates
    if diff.total_seconds() < 0:
        diff = abs(diff)
        if diff.days > 0:
            return f"in {diff.days} day{'s' if diff.days > 1 else ''}"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"in {hours} hour{'s' if hours > 1 else ''}"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"in {minutes} minute{'s' if minutes > 1 else ''}"
        else:
            return "just now"
    
    # Handle past dates
    if diff.days > 0:
        if diff.days >= 30:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"

def utc_to_local_datetime(dt: datetime, local_tz=None) -> datetime:
    """
    Convert a UTC datetime to the local timezone.
    
    Args:
        dt (datetime): The UTC datetime to convert
        local_tz: The local timezone to convert to (defaults to system timezone)
        
    Returns:
        datetime: Local datetime with timezone info
    """
    import tzlocal
    
    # Ensure datetime is timezone aware in UTC
    dt = ensure_utc(dt) if dt else None
    if not dt:
        return None
        
    # Get local timezone if not provided
    if not local_tz:
        local_tz = tzlocal.get_localzone()
        
    # Convert to local timezone
    return dt.astimezone(local_tz)

def format_date_for_browser(dt: datetime) -> str:
    """
    Format a datetime for browser compatibility (ISO format).
    Used for datetime-local inputs and date sorting.
    
    Args:
        dt (datetime): The datetime to format
        
    Returns:
        str: ISO formatted date string without timezone info
    """
    if not dt:
        return ""
        
    # Ensure datetime is timezone aware
    dt = ensure_utc(dt) if not is_tz_aware(dt) else dt
    
    # Format for HTML datetime-local input
    return dt.strftime("%Y-%m-%dT%H:%M:%S")