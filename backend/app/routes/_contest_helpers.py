"""
Shared helpers for contest route blueprints.

Contains date-parsing utilities used across contest CRUD, submission, and
request routes. Extracted from the original monolithic contest_routes.py so
the split blueprint modules can share them without duplication.
"""

from datetime import datetime


def validate_date_string(date_str):
    """
    Validate date string format (YYYY-MM-DD)

    Args:
        date_str: Date string to validate

    Returns:
        date: Parsed date object or None if invalid
    """
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_date_or_none(date_str):
    """
    Parse a date string with multiple format fallbacks

    Tries YYYY-MM-DD format first, then ISO format

    Args:
        date_str: Date string to parse

    Returns:
        date: Parsed date object or None if invalid
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        try:
            return datetime.fromisoformat(date_str).date()
        except ValueError:
            return None
