"""
Shared helpers for user route blueprints.

Contains validation utilities used across auth, profile, and trusted-member
routes. Extracted from the original monolithic user_routes.py so the split
blueprint modules can share them without duplication.
"""

import re


def validate_email(email):
    """
    Validate email format

    Args:
        email: Email string to validate

    Returns:
        bool: True if valid email, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username):
    """
    Validate username format

    Args:
        username: Username string to validate

    Returns:
        bool: True if valid username, False otherwise
    """
    # Username should be 3-20 characters, alphanumeric and underscores only
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(pattern, username) is not None
