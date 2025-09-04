import unittest
from datetime import datetime, timezone, timedelta
import pytz
from src.utils.date_utils import (
    is_tz_aware, 
    ensure_utc, 
    safe_parse_date,
    format_datetime_for_display,
    format_iso_date, 
    format_relative_time
)

class TestDateUtils(unittest.TestCase):
    """Test suite for date_utils.py functionality."""
    
    def test_is_tz_aware(self):
        """Test is_tz_aware correctly identifies timezone-aware and naive datetimes."""
        # Naive datetime
        naive_dt = datetime(2023, 5, 1, 12, 0, 0)
        self.assertFalse(is_tz_aware(naive_dt))
        
        # Timezone-aware datetime
        aware_dt = datetime(2023, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(is_tz_aware(aware_dt))
        
        # Non-datetime object
        self.assertFalse(is_tz_aware("not a datetime"))
    
    def test_ensure_utc(self):
        """Test ensure_utc correctly converts dates to UTC timezone."""
        # Convert naive to UTC
        naive_dt = datetime(2023, 5, 1, 12, 0, 0)
        utc_dt = ensure_utc(naive_dt)
        self.assertEqual(utc_dt.tzinfo, timezone.utc)
        self.assertEqual(utc_dt.hour, 12)  # Time should remain the same
        
        # Convert non-UTC timezone to UTC
        est = timezone(timedelta(hours=-5))
        est_dt = datetime(2023, 5, 1, 12, 0, 0, tzinfo=est)
        utc_dt = ensure_utc(est_dt)
        self.assertEqual(utc_dt.tzinfo, timezone.utc)
        self.assertEqual(utc_dt.hour, 17)  # 12 EST = 17 UTC
        
        # Already UTC
        utc_already = datetime(2023, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = ensure_utc(utc_already)
        self.assertEqual(result, utc_already)
        
        # Handle non-datetime
        self.assertIsNone(ensure_utc("not a datetime"))
    
    def test_safe_parse_date(self):
        """Test safe_parse_date correctly parses various date formats."""
        # ISO format
        iso_date = "2023-05-01T12:00:00Z"
        parsed = safe_parse_date(iso_date)
        self.assertTrue(is_tz_aware(parsed))
        self.assertEqual(parsed.year, 2023)
        self.assertEqual(parsed.month, 5)
        self.assertEqual(parsed.day, 1)
        self.assertEqual(parsed.hour, 12)
        self.assertEqual(parsed.tzinfo, timezone.utc)
        
        # ISO format with timezone
        iso_tz = "2023-05-01T12:00:00+02:00"
        parsed = safe_parse_date(iso_tz)
        self.assertTrue(is_tz_aware(parsed))
        self.assertEqual(parsed.hour, 10)  # Converted to UTC (12 CEST = 10 UTC)
        self.assertEqual(parsed.tzinfo, timezone.utc)
        
        # Human readable
        human = "May 1, 2023 12:00 PM"
        parsed = safe_parse_date(human)
        self.assertTrue(is_tz_aware(parsed))
        self.assertEqual(parsed.year, 2023)
        self.assertEqual(parsed.month, 5)
        self.assertEqual(parsed.day, 1)
        self.assertEqual(parsed.tzinfo, timezone.utc)
        
        # Invalid input
        self.assertIsNone(safe_parse_date("not a date"))
        self.assertIsNone(safe_parse_date(""))
        self.assertIsNone(safe_parse_date(None))
    
    def test_format_datetime_for_display(self):
        """Test format_datetime_for_display formats dates correctly."""
        dt = datetime(2023, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Default format
        formatted = format_datetime_for_display(dt)
        self.assertIn("2023", formatted)  # Year
        self.assertIn("05-01", formatted)  # Month and day in standard format
        self.assertIn("12:00:00", formatted)  # Time
        self.assertIn("UTC", formatted)  # Timezone
        
        # Custom format
        custom = format_datetime_for_display(dt, "%Y-%m-%d %H:%M")
        self.assertEqual(custom, "2023-05-01 12:00")
        
        # Handle None
        self.assertEqual(format_datetime_for_display(None), "")
    
    def test_format_iso_date(self):
        """Test format_iso_date produces correct ISO 8601 format."""
        dt = datetime(2023, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
        iso = format_iso_date(dt)
        self.assertEqual(iso, "2023-05-01T12:00:00Z")
        
        # Convert non-UTC to UTC then format
        est = timezone(timedelta(hours=-5))
        est_dt = datetime(2023, 5, 1, 12, 0, 0, tzinfo=est)
        iso = format_iso_date(est_dt)
        self.assertEqual(iso, "2023-05-01T17:00:00Z")  # 12 EST = 17 UTC
    
    def test_format_relative_time(self):
        """Test format_relative_time calculates relative time correctly."""
        now = datetime.now(timezone.utc)
        
        # Just now
        recent = now - timedelta(seconds=30)
        self.assertEqual(format_relative_time(recent), "just now")
        
        # Minutes ago
        minutes_ago = now - timedelta(minutes=5)
        self.assertEqual(format_relative_time(minutes_ago), "5 minutes ago")
        
        # 1 minute ago (singular)
        one_minute = now - timedelta(minutes=1)
        self.assertEqual(format_relative_time(one_minute), "1 minute ago")
        
        # Hours ago
        hours_ago = now - timedelta(hours=3)
        self.assertEqual(format_relative_time(hours_ago), "3 hours ago")
        
        # Days ago
        days_ago = now - timedelta(days=2)
        self.assertEqual(format_relative_time(days_ago), "2 days ago")
        
        # Handle None
        self.assertEqual(format_relative_time(None), "")

if __name__ == "__main__":
    unittest.main()