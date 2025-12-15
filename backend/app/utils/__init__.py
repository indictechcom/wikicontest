"""
Utility Functions for WikiContest Application

This module contains common utility functions that are used across
different parts of the application. These functions help maintain
DRY (Don't Repeat Yourself) principles and provide reusable functionality.

This file implements a small, focused set of helpers that are used by
the contest and submission routes to talk to the MediaWiki API and to
check contest permissions.

The goal is to keep the helpers:
- Simple
- Well documented
- Easy to change later if we need more advanced behaviour
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse, parse_qs, unquote

import requests
from flask import jsonify, current_app


# Re-exported helpers – other modules import these from app.utils
__all__ = [
    "validate_contest_submission_access",
    "get_article_size_at_timestamp",
    "extract_page_title_from_url",
    "get_latest_revision_author",
    "build_mediawiki_revisions_api_params",
    "get_mediawiki_headers",
]


# ============================================================================
# Permission / Access helpers
# ============================================================================

def validate_contest_submission_access(contest_id: int, user, Contest):
    """
    Validate that the given user is allowed to access submissions for a contest.

    Rules:
    - If contest does not exist → 404
    - Admins can always access
    - Contest creator (by username) can access
    - Jury members listed on the contest can access

    Returns:
        (contest, None) on success
        (None, (json_response, status_code)) on failure
    """
    contest = Contest.query.get(contest_id)

    if not contest:
        return None, (jsonify({"error": "Contest not found"}), 404)

    try:
        # Admins
        if hasattr(user, "is_admin") and callable(user.is_admin) and user.is_admin():
            return contest, None

        # Contest creator – creator is stored as username
        if getattr(user, "username", None) and user.username == contest.created_by:
            return contest, None

        # Jury members – check via helper on User model
        if hasattr(user, "is_jury_member") and user.is_jury_member(contest):
            return contest, None

    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Safety net – on unexpected errors we deny access but also log details.
        try:
            current_app.logger.error(
                "validate_contest_submission_access failed for contest %s: %s",
                contest_id,
                str(exc),
            )
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        return None, (jsonify({"error": "Permission check failed"}), 500)

    # If none of the rules matched, deny access
    return None, (jsonify({"error": "Permission denied"}), 403)


# ============================================================================
# MediaWiki URL / revision helpers
# ============================================================================

def extract_page_title_from_url(article_url: str) -> Optional[str]:
    """
    Extract the page title from a MediaWiki-style article URL.

    Supports common URL formats:
    - https://example.org/wiki/Page_Title
    - https://example.org/w/index.php?title=Page_Title
    - Fallback: last non-empty segment of the path

    Returns:
        Page title (URL-decoded, without leading/trailing slashes) or None.
    """
    if not article_url:
        return None

    try:
        url_obj = urlparse(article_url)

        # /wiki/Page_Title
        if "/wiki/" in url_obj.path:
            return unquote(url_obj.path.split("/wiki/", 1)[1])

        # /w/index.php?title=Page_Title
        if "title=" in url_obj.query:
            query_params = parse_qs(url_obj.query)
            title = query_params.get("title", [""])[0]
            return unquote(title) or None

        # Fallback: last path segment
        parts = [p for p in url_obj.path.split("/") if p]
        if parts:
            return unquote(parts[-1])
    except Exception:  # pylint: disable=broad-exception-caught
        # On any parsing error just return None – callers have fallbacks
        return None

    return None


def build_mediawiki_revisions_api_params(page_title: str) -> Dict[str, Any]:
    """
    Build a standard set of parameters for MediaWiki `action=query&prop=revisions`.

    The params are tuned for our use cases:
    - formatversion=2 → cleaner JSON
    - rvprop includes timestamp, user, userid and size so callers can compute
      authorship and byte counts
    - rvlimit kept small (10) to avoid heavy responses
    - rvdir='older' so the first revision in the list is the newest / latest
    """
    return {
        "action": "query",
        "titles": page_title,
        "format": "json",
        "formatversion": "2",
        "prop": "revisions",
        "rvprop": "timestamp|user|userid|size",
        "rvlimit": "10",
        "rvdir": "older",  # newest first
        "redirects": "true",
    }


def get_latest_revision_author(revisions: Iterable[Dict[str, Any]]) -> Optional[str]:
    """
    Get the author name of the latest revision from a revisions list.

    Assumes revisions are ordered with the *newest first*, which matches
    the way we call the MediaWiki API (rvdir='older').
    """
    if not revisions:
        return None

    try:
        rev_list = list(revisions)
        if not rev_list:
            return None

        latest = rev_list[0]
        username = latest.get("user")
        if username:
            return username

        user_id = latest.get("userid")
        if user_id:
            return f"User ID: {user_id}"

    except Exception:  # pylint: disable=broad-exception-caught
        return None

    return None


def get_mediawiki_headers() -> Dict[str, str]:
    """
    Return a standard User-Agent header for all MediaWiki API requests.

    Using a clear User-Agent is required by Wikimedia's API policy.
    """
    return {
        "User-Agent": (
            "WikiContest/1.0 (https://wikicontest.toolforge.org; "
            "contact@wikicontest.toolforge.org) Python/requests"
        )
    }


def get_article_size_at_timestamp(article_link: str, timestamp: datetime) -> Optional[int]:
    """
    Get the size (in bytes) of an article at or just before a given UTC timestamp.

    Implementation notes:
    - We ask the API for the latest revision at or before the timestamp
      (using rvstart + rvdir=older + rvlimit=1).
    - On any error we return None instead of raising – callers treat this
      as "unknown size" and fall back gracefully.
    """
    if not article_link or not timestamp:
        return None

    try:
        page_title = extract_page_title_from_url(article_link)
        if not page_title:
            return None

        url_obj = urlparse(article_link)
        base_url = f"{url_obj.scheme}://{url_obj.netloc}"
        api_url = f"{base_url}/w/api.php"

        # ISO 8601 with Z suffix – MediaWiki expects UTC timestamps
        ts_iso = timestamp.replace(microsecond=0).isoformat() + "Z"

        params = {
            "action": "query",
            "titles": page_title,
            "format": "json",
            "formatversion": "2",
            "prop": "revisions",
            "rvprop": "timestamp|size",
            "rvlimit": "1",
            "rvdir": "older",  # newest first, starting at rvstart
            "rvstart": ts_iso,
            "redirects": "true",
        }

        headers = get_mediawiki_headers()
        response = requests.get(api_url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            return None

        page = pages[0]
        revisions = page.get("revisions", [])
        if not revisions:
            return None

        size = revisions[0].get("size")
        return int(size) if size is not None else None

    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Log but do not break submission flow
        try:
            current_app.logger.warning(
                "Failed to get article size at timestamp for %s: %s",
                article_link,
                str(exc),
            )
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        return None
