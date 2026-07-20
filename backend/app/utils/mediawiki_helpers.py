"""
MediaWiki API helper functions for WikiEval Application.

Provides shared helpers for building MediaWiki API requests, parsing responses,
and fetching article metadata (size, author, creation date, etc.).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse, unquote, parse_qs

import requests
from flask import jsonify, current_app

from app.services.mediawiki import MediaWikiClient
from app.utils.url_validation import validate_wiki_url

__all__ = [
    "extract_page_title_from_url",
    "build_mediawiki_revisions_api_params",
    "get_mediawiki_headers",
    "get_latest_revision_author",
    "get_article_size_at_timestamp",
    "get_article_wikitext",
    "get_mediawiki_user_edit_count",
    "MEDIAWIKI_API_TIMEOUT",
]

MEDIAWIKI_API_TIMEOUT = 30


def extract_page_title_from_url(article_url: str) -> Optional[str]:
    """
    Extract a MediaWiki page title from an article URL.
    
    Parameters:
    	article_url (str): URL containing the article title.
    
    Returns:
    	Optional[str]: The URL-decoded page title, or `None` if no title can be derived.
    """
    if not article_url:
        return None

    url_obj = urlparse(article_url)

    if "/wiki/" in url_obj.path:
        return unquote(url_obj.path.split("/wiki/")[1])

    if "title=" in url_obj.query:
        query_params = parse_qs(url_obj.query)
        return unquote(query_params.get("title", [""])[0])

    parts = [p for p in url_obj.path.split("/") if p]
    if parts:
        return unquote(parts[-1])

    return None


def build_mediawiki_revisions_api_params(page_title: str) -> Dict[str, Any]:
    """
    Builds query parameters for retrieving a page's metadata and revisions from the MediaWiki API.
    
    Parameters:
    	page_title (str): Title of the page to query.
    
    Returns:
    	Dict[str, Any]: MediaWiki API query parameters for up to two revisions and page information.
    """
    return {
        "action": "query",
        "titles": page_title,
        "format": "json",
        "formatversion": "2",
        "prop": "info|revisions",
        "rvprop": "timestamp|user|userid|comment|size",
        "rvlimit": "2",
        "rvdir": "older",
        "redirects": "true",
        "converttitles": "true",
    }


def get_mediawiki_headers() -> Dict[str, str]:
    """
    Build the HTTP headers used for MediaWiki API requests.
    
    Returns:
        Dict[str, str]: A headers dictionary containing a WikiEval User-Agent value.
    """
    return {
        "User-Agent": (
            "WikiEval/1.0 (" + os.environ.get('FRONTEND_URL', 'https://wikieval.toolforge.org') + "; "
            "contact@wikieval.org) Python/requests"
        )
    }


def get_latest_revision_author(revisions: Iterable[Dict[str, Any]]) -> Optional[str]:
    """
    Determine the author of the latest revision.
    
    Parameters:
        revisions (Iterable[Dict[str, Any]]): Revision records ordered with the latest first.
    
    Returns:
        Optional[str]: The username, a formatted user ID, or None when no author information is available.
    """
    revisions_list: List[Dict[str, Any]] = list(revisions or [])
    if not revisions_list:
        return None

    latest = revisions_list[0]

    user_name = latest.get("user")
    if user_name:
        return user_name

    user_id = latest.get("userid")
    if user_id:
        return f"User ID: {user_id}"

    return None


def get_article_size_at_timestamp(article_url: str, when: datetime) -> Optional[int]:
    """
    Get an article's size at a specified timestamp.
    
    Parameters:
        article_url (str): URL of the article.
        when (datetime): Timestamp at which to retrieve the article size.
    
    Returns:
        Optional[int]: The article size in bytes, or `None` if the page, revision, or size is unavailable.
    """
    page_title = extract_page_title_from_url(article_url)
    if not page_title:
        return None

    base_url, error = validate_wiki_url(article_url)
    if error:
        return None
    api_url = f"{base_url}/w/api.php"

    when_iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")

    params: Dict[str, Any] = {
        "action": "query",
        "titles": page_title,
        "format": "json",
        "formatversion": "2",
        "prop": "revisions",
        "rvprop": "timestamp|size",
        "rvlimit": "1",
        "rvdir": "older",
        "rvstart": when_iso,
        "redirects": "true",
        "converttitles": "true",
    }

    client = MediaWikiClient()
    data = client.get(api_url, params=params)
    if data is None:
        return None

    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None

    page_data = pages[0]
    revisions = page_data.get("revisions", [])
    if not revisions:
        return None

    rev = revisions[0]
    return rev.get("size")


def get_article_wikitext(article_url: str) -> Optional[str]:
    """
    Retrieve the current wikitext content for an article URL.
    
    Parameters:
        article_url (str): URL of the MediaWiki article.
    
    Returns:
        str: The article's wikitext, or `None` if the article cannot be resolved or has no content.
    """
    if not article_url:
        return None

    page_title = extract_page_title_from_url(article_url)
    if not page_title:
        return None

    base_url, error = validate_wiki_url(article_url)
    if error:
        return None
    api_url = f"{base_url}/w/api.php"

    params = {
        "action": "query",
        "titles": page_title,
        "format": "json",
        "formatversion": "2",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "rvlimit": "1",
        "redirects": "true",
    }

    client = MediaWikiClient()
    data = client.get(api_url, params=params, timeout=15)
    if data is None:
        return None

    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None

    page_data = pages[0]
    if page_data.get("missing", False):
        return None

    revisions = page_data.get("revisions", [])
    if not revisions:
        return None

    slots = revisions[0].get("slots", {})
    main_slot = slots.get("main", {})
    content = main_slot.get("content")

    return content


def get_mediawiki_user_edit_count(
    username: str, mw_uri: str = "https://meta.wikimedia.org/w/index.php"
) -> Optional[int]:
    """
    Retrieve a user's MediaWiki edit count.
    
    Parameters:
        username (str): The MediaWiki username.
        mw_uri (str): The MediaWiki URI used to construct the API endpoint.
    
    Returns:
        Optional[int]: The user's edit count, or `None` if it cannot be retrieved.
    """
    try:
        if mw_uri.endswith('/index.php'):
            api_url = mw_uri[: -len('/index.php')] + '/api.php'
        elif mw_uri.endswith('/'):
            api_url = f"{mw_uri}w/api.php"
        else:
            api_url = f"{mw_uri}/w/api.php"

        api_params = {
            'action': 'query',
            'meta': 'globaluserinfo',
            'guiuser': username,
            'guiprop': 'editcount',
            'format': 'json',
            'formatversion': '2'
        }

        client = MediaWikiClient()
        data = client.get(api_url, params=api_params)
        if data is None:
            return None

        global_info = data.get('query', {}).get('globaluserinfo', {})
        if not global_info.get('missing'):
            edit_count = global_info.get('editcount')
            if edit_count is not None:
                return int(edit_count)

        api_params = {
            'action': 'query',
            'list': 'users',
            'ususers': username,
            'usprop': 'editcount',
            'format': 'json',
            'formatversion': '2'
        }

        data = client.get(api_url, params=api_params)
        if data is None:
            return None

        if 'error' in data:
            return None

        users = data.get('query', {}).get('users', [])
        if not users:
            return None

        user_data = users[0]

        if user_data.get('missing'):
            return None

        edit_count = user_data.get('editcount')
        if edit_count is None:
            return None

        return int(edit_count)

    except Exception as error:
        try:
            from flask import current_app
            current_app.logger.warning(
                f"Failed to fetch edit count for user {username}: {str(error)}"
            )
        except Exception:
            pass
        return None


def _log_warning(message: str, error: Exception) -> None:
    """
    Logs a warning message with the associated exception when logging is available.
    
    Parameters:
    	message (str): The warning message.
    	error (Exception): The exception associated with the warning.
    """
    try:
        from flask import current_app
        current_app.logger.warning("%s: %s", message, str(error))
    except Exception:
        pass
