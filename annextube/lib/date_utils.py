"""Date parsing utilities for update windows."""

import re
from datetime import datetime, timedelta
from typing import Optional


def parse_duration(duration_str: str) -> timedelta:
    """Parse duration string like '1 week', '2 days', '3 months'.

    Args:
        duration_str: Duration string (e.g., "1 week", "2 days", "3 months")

    Returns:
        timedelta object

    Raises:
        ValueError: If duration string is invalid

    Examples:
        >>> parse_duration("1 week")
        timedelta(days=7)
        >>> parse_duration("2 days")
        timedelta(days=2)
        >>> parse_duration("3 months")
        timedelta(days=90)
    """
    # Match patterns like "1 week", "2 days", "3 months"
    match = re.match(r'^(\d+)\s+(hour|hours|day|days|week|weeks|month|months|year|years)$', duration_str.strip())

    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}. Expected format: 'N unit' (e.g., '1 week', '2 days')")

    amount = int(match.group(1))
    unit = match.group(2)

    # Normalize to singular
    if unit.endswith('s'):
        unit = unit[:-1]

    # Convert to timedelta
    if unit == 'hour':
        return timedelta(hours=amount)
    elif unit == 'day':
        return timedelta(days=amount)
    elif unit == 'week':
        return timedelta(weeks=amount)
    elif unit == 'month':
        # Approximate: 30 days per month
        return timedelta(days=amount * 30)
    elif unit == 'year':
        # Approximate: 365 days per year
        return timedelta(days=amount * 365)
    else:
        raise ValueError(f"Unknown time unit: {unit}")


def parse_date(date_str: str, reference_date: Optional[datetime] = None) -> datetime:
    """Parse date string with support for relative dates and ISO format.

    Args:
        date_str: Date string (ISO format or relative like "1 week ago")
        reference_date: Reference date for relative parsing (default: now)

    Returns:
        datetime object

    Raises:
        ValueError: If date string is invalid

    Examples:
        >>> parse_date("2024-01-15")
        datetime(2024, 1, 15, 0, 0)
        >>> parse_date("1 week")  # Relative to now
        datetime(...)
    """
    if reference_date is None:
        reference_date = datetime.now()

    date_str = date_str.strip()

    # Try ISO format first
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        pass

    # Try relative duration (e.g., "1 week", "2 days")
    try:
        duration = parse_duration(date_str)
        return reference_date - duration
    except ValueError:
        pass

    # Try with "ago" suffix
    if date_str.endswith(' ago'):
        duration_part = date_str[:-4]
        try:
            duration = parse_duration(duration_part)
            return reference_date - duration
        except ValueError:
            pass

    raise ValueError(f"Invalid date format: {date_str}. Expected ISO format (YYYY-MM-DD) or duration (e.g., '1 week', '2 days')")
