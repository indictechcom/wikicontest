"""
Utility Functions for WikiContest Application.

This module contains shared helpers that are used by the Flask routes,
Alembic‑backed models, and maintenance scripts.

The focus here is small, well‑documented functions:
- Permission and access control helpers.
- MediaWiki API helpers.
- Simple parsing helpers.

All functions are intentionally simple and safe.
They catch network / parsing errors and return `None` instead of crashing.
"""
# pylint: disable=too-many-lines

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse, unquote, parse_qs

import requests
from flask import jsonify


__all__ = [
    "validate_contest_submission_access",
    "get_article_size_at_timestamp",
    "extract_page_title_from_url",
    "get_latest_revision_author",
    "build_mediawiki_revisions_api_params",
    "get_mediawiki_headers",
    "MEDIAWIKI_API_TIMEOUT",
    "validate_template_link",
    "extract_template_name_from_url",
    "check_article_has_template",
    "get_article_wikitext",
    "prepend_template_to_article",
    "get_csrf_token",
    "extract_category_name_from_url",
    "check_article_has_category",
    "append_categories_to_article",
    "get_article_reference_count",
    "get_detailed_reference_counts",
    "get_mediawiki_user_edit_count",
    "get_article_image_count",
    "get_article_infobox_count",
    "get_article_incoming_links",
    "get_article_outgoing_links",
    "crawl_category_articles",
]


# ---------------------------------------------------------------------------
# MediaWiki API Configuration
# ---------------------------------------------------------------------------

# Timeout for MediaWiki API requests (in seconds)
# Increased from 10 to 30 seconds to handle slow API responses
# MediaWiki API can sometimes be slow, especially for large articles or during high traffic
MEDIAWIKI_API_TIMEOUT = 30


# ------------------------------------------------------------------------
# ACCESS CONTROL HELPERS
# ------------------------------------------------------------------------

def validate_contest_submission_access(contest_id, user, Contest):  # pylint: disable=invalid-name
    # pylint: disable=invalid-name
    """
    Check if a user is allowed to view or manage submissions for a contest.

    This is used by multiple routes and must stay very small and clear.

    Returns:
        (contest, error_response)
        - contest: Contest object when access is allowed, else None.
        - error_response: (Response, status_code) when access is denied, else None.
    """
    # Fetch contest from the database
    contest = Contest.query.get(contest_id)

    if not contest:
        # Contest does not exist
        return None, (jsonify({"error": "Contest not found"}), 404)

    # --- Permission Check: Admin ---
    # Admin users are always allowed
    # Our User model exposes this as a method (see app.models.user.User)
    if hasattr(user, "is_admin") and callable(getattr(user, "is_admin")):
        if user.is_admin():
            return contest, None

    # --- Permission Check: Contest Creator ---
    # Contest creator is allowed
    # created_by stores the creator's username
    if getattr(user, "username", None) == getattr(contest, "created_by", None):
        return contest, None

    # --- Permission Check: Jury Member ---
    # Jury members are allowed
    # Contest keeps jury members as a comma‑separated string of usernames
    try:
        from app.models.user import User  # local import to avoid circular deps
    except Exception:  # pylint: disable=broad-exception-caught
        User = None  # type: ignore  # pylint: disable=invalid-name

    if User is not None and hasattr(user, "is_jury_member"):
        try:
            # Prefer the dedicated helper on the User model
            if user.is_jury_member(contest):
                return contest, None
        except Exception:  # pylint: disable=broad-exception-caught
            # Fall back to manual parsing if something goes wrong
            pass

    # Manual fallback: parse jury_members as usernames list
    jury_members_raw = getattr(contest, "jury_members", "") or ""
    jury_usernames = [u.strip() for u in jury_members_raw.split(",") if u.strip()]
    if getattr(user, "username", None) in jury_usernames:
        return contest, None

    # No matching permission rule → deny access
    return None, (jsonify({"error": "Permission denied"}), 403)


# ------------------------------------------------------------------------
# MEDIAWIKI API HELPERS
# ------------------------------------------------------------------------

def extract_page_title_from_url(article_url: str) -> Optional[str]:
    """
    Extract a MediaWiki page title from a full article URL.

    This mirrors the logic used in the maintenance scripts.
    It supports:
    - `/wiki/Page_Title` style URLs.
    - `/w/index.php?title=Page_Title` style URLs.
    - Fallback to the last path segment.

    Returns:
        The decoded page title string, or None when it cannot be extracted.
    """
    if not article_url:
        return None

    url_obj = urlparse(article_url)

    # Standard `/wiki/Page_Title` format (most common)
    if "/wiki/" in url_obj.path:
        return unquote(url_obj.path.split("/wiki/")[1])

    # Old style `/w/index.php?title=Page_Title` format
    if "title=" in url_obj.query:
        query_params = parse_qs(url_obj.query)
        return unquote(query_params.get("title", [""])[0])

    # Fallback: last non‑empty path segment
    parts = [p for p in url_obj.path.split("/") if p]
    if parts:
        return unquote(parts[-1])

    return None




def build_mediawiki_revisions_api_params(page_title: str) -> Dict[str, Any]:  # pylint: disable=invalid-name
    """
    Build a standard parameter set for MediaWiki `revisions` queries.

    This is shared by the routes and scripts so that any change to the
    API contract is done in a single place.
    """
    return {
        "action": "query",
        "titles": page_title,
        "format": "json",
        "formatversion": "2",  # Use modern API format (array-based pages)
        "prop": "info|revisions",
        # We request timestamp, user, userid, and size so that callers can
        # compute authorship and word/byte counts
        "rvprop": "timestamp|user|userid|comment|size",
        # Get both newest and oldest revisions in a tiny window
        "rvlimit": "2",
        # With rvdir='older', the first revision in the list is the newest
        "rvdir": "older",
        # Follow redirects to get the actual page
        "redirects": "true",
        # Convert titles to the preferred variant
        "converttitles": "true",
    }


def get_mediawiki_headers() -> Dict[str, str]:
    """
    Return a standard set of HTTP headers for MediaWiki API calls.

    MediaWiki requires a descriptive User‑Agent.
    Using one shared helper keeps this string consistent.
    """
    return {
        "User-Agent": (
            "WikiContest/1.0 (https://wikicontest.toolforge.org; "
            "contact@wikicontest.org) Python/requests"
        )
    }


def get_latest_revision_author(revisions: Iterable[Dict[str, Any]]) -> Optional[str]:
    """
    Get the author of the latest revision from a revisions list.

    The calling code usually passes the list returned by the MediaWiki API.
    With `rvdir='older'`, the first element is the newest revision.

    Returns:
        Username string when available, a simple "User ID: <id>" fallback,
        or None when no author information is present.
    """
    revisions_list: List[Dict[str, Any]] = list(revisions or [])
    if not revisions_list:
        return None

    # First element is the newest revision (with rvdir='older')
    latest = revisions_list[0]

    # Prefer the human‑readable username when available
    user_name = latest.get("user")
    if user_name:
        return user_name

    # Fallback to numeric user id when username is missing
    # This can happen for deleted/suppressed users
    user_id = latest.get("userid")
    if user_id:
        return f"User ID: {user_id}"

    return None


def extract_template_name_from_url(template_url: str) -> Optional[str]:
    """
    Extract the template name from a Wiki template URL.

    Supports URLs like:
    - https://en.wikipedia.org/wiki/Template:Editathon2025
    - https://en.wikipedia.org/w/index.php?title=Template:Editathon2025

    Args:
        template_url: Full URL to a Wiki template page.

    Returns:
        Template name without 'Template:' prefix (e.g., 'Editathon2025'),
        or None if extraction fails.
    """
    page_title = extract_page_title_from_url(template_url)
    if not page_title:
        return None

    # Check if it's in the Template namespace
    # Handle different language prefixes (Template:, Vorlage:, Plantilla:, etc.)
    # For simplicity, we check for common patterns
    template_prefixes = [
        "Template:", "template:",
        "Vorlage:",  # German
        "Plantilla:",  # Spanish
        "Modèle:",  # French
        "Szablon:",  # Polish
        "Шаблон:",  # Russian
        "模板:",  # Chinese
    ]

    for prefix in template_prefixes:
        if page_title.startswith(prefix):
            return page_title[len(prefix):]

    # If no prefix found, return None (not a template page)
    return None


def validate_template_link(template_url: str) -> Dict[str, Any]:  # pylint: disable=too-many-return-statements
    """
    Validate a template link by checking:
    1. URL is valid and well-formed
    2. Page exists on the wiki
    3. Page is in the Template namespace

    Args:
        template_url: Full URL to a Wiki template page.

    Returns:
        Dict with:
        - 'valid': bool indicating if template is valid
        - 'error': error message if invalid, None if valid
        - 'template_name': extracted template name if valid
        - 'page_exists': whether the page exists
        - 'is_template': whether it's in Template namespace
    """
    result = {
        'valid': False,
        'error': None,
        'template_name': None,
        'page_exists': False,
        'is_template': False,
    }

    # Check URL format
    if not template_url:
        result['error'] = 'Template link is required'
        return result

    if not (template_url.startswith('http://') or template_url.startswith('https://')):
        result['error'] = 'Template link must be a valid HTTP/HTTPS URL'
        return result

    # Extract page title
    page_title = extract_page_title_from_url(template_url)
    if not page_title:
        result['error'] = 'Could not extract page title from URL'
        return result

    # Check if it's a template page
    template_name = extract_template_name_from_url(template_url)
    if template_name:
        result['is_template'] = True
        result['template_name'] = template_name
    else:
        result['error'] = 'URL must point to a Template namespace page (e.g., Template:YourTemplate)'
        return result

    # Verify page exists via MediaWiki API
    url_obj = urlparse(template_url)
    base_url = f"{url_obj.scheme}://{url_obj.netloc}"
    api_url = f"{base_url}/w/api.php"

    params = {
        "action": "query",
        "titles": page_title,
        "format": "json",
        "formatversion": "2",
        "prop": "info",
        "redirects": "true",
    }

    try:
        response = requests.get(api_url, params=params, headers=get_mediawiki_headers(), timeout=MEDIAWIKI_API_TIMEOUT)
    except requests.RequestException as error:
        result['error'] = f'Failed to verify template: network error ({str(error)})'
        return result

    if response.status_code != 200:
        result['error'] = f'Failed to verify template: HTTP {response.status_code}'
        return result

    try:
        data = response.json()
    except ValueError:
        result['error'] = 'Failed to parse API response'
        return result

    if 'error' in data:
        result['error'] = f"API error: {data['error'].get('info', 'Unknown error')}"
        return result

    pages = data.get('query', {}).get('pages', [])
    if not pages:
        result['error'] = 'Template page not found'
        return result

    page_data = pages[0]
    is_missing = page_data.get('missing', False)

    if is_missing:
        result['error'] = 'Template page does not exist'
        return result

    result['page_exists'] = True
    result['valid'] = True
    return result


def get_article_wikitext(article_url: str) -> Optional[str]:  # pylint: disable=too-many-return-statements
    """
    Fetch the wikitext content of an article.

    Args:
        article_url: Full URL to the wiki article.

    Returns:
        Wikitext content as string, or None if fetch fails.
    """
    if not article_url:
        return None

    page_title = extract_page_title_from_url(article_url)
    if not page_title:
        return None

    url_obj = urlparse(article_url)
    base_url = f"{url_obj.scheme}://{url_obj.netloc}"
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

    try:
        response = requests.get(api_url, params=params, headers=get_mediawiki_headers(), timeout=15)
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    if 'error' in data:
        return None

    pages = data.get('query', {}).get('pages', [])
    if not pages:
        return None

    page_data = pages[0]
    if page_data.get('missing', False):
        return None

    revisions = page_data.get('revisions', [])
    if not revisions:
        return None

    # Get content from main slot
    slots = revisions[0].get('slots', {})
    main_slot = slots.get('main', {})
    content = main_slot.get('content')

    return content


def get_detailed_reference_counts(article_url: str) -> Dict[str, int]:
    """Parses wikitext to distinguish between New (defined) and Reused (self-closing) references."""
    wikitext = get_article_wikitext(article_url)
    if not wikitext:
        return {"new": 0, "reused": 0}

    text = re.sub(r"<!--.*?-->", "", wikitext, flags=re.DOTALL)

    new_refs_pattern = r"<ref\b[^>]*?>.*?</ref>"
    new_refs = len(re.findall(new_refs_pattern, text, flags=re.IGNORECASE | re.DOTALL))

    reused_refs_pattern = r"<ref\b[^>]*?/>"
    reused_refs = len(re.findall(reused_refs_pattern, text, flags=re.IGNORECASE))

    return {"new": new_refs, "reused": reused_refs}


def check_article_has_template(article_url: str, template_name: str) -> Dict[str, Any]:
    """
    Check if an article begins with the specified template.

    This normalizes whitespace, handles HTML comments, noinclude tags,
    and other formatting differences that might appear before the template.

    Args:
        article_url: Full URL to the wiki article.
        template_name: Template name without 'Template:' prefix.

    Returns:
        Dict with:
        - 'has_template': bool indicating if template is present at beginning
        - 'error': error message if check failed, None otherwise
        - 'article_content': first 500 chars of article for debugging
    """
    result = {
        'has_template': False,
        'error': None,
        'article_content': None,
    }

    wikitext = get_article_wikitext(article_url)
    if wikitext is None:
        result['error'] = 'Failed to fetch article content'
        return result

    result['article_content'] = wikitext[:500] if len(wikitext) > 500 else wikitext

    # Normalize the content for comparison
    # Strip leading whitespace and normalize line breaks
    normalized_content = wikitext.lstrip()

    # Remove HTML comments that might appear before the template
    # Pattern: <!-- ... --> (can span multiple lines)
    # Note: re is already imported at module level
    # Remove single-line and multi-line HTML comments
    normalized_content = re.sub(r'<!--.*?-->', '', normalized_content, flags=re.DOTALL)
    # Strip whitespace again after removing comments
    normalized_content = normalized_content.lstrip()

    # Remove <noinclude> tags that might wrap the template
    # Pattern: <noinclude>...</noinclude> (can contain the template)
    # We'll check both inside and outside noinclude tags
    content_without_noinclude = re.sub(r'<noinclude>.*?</noinclude>', '', normalized_content, flags=re.DOTALL)
    content_without_noinclude = content_without_noinclude.lstrip()

    # Build possible template invocations to check
    # Handle variations: {{TemplateName}}, {{Template_Name}}, {{ TemplateName }}
    template_variations = [
        f"{{{{{template_name}}}}}",
        f"{{{{{template_name.replace(' ', '_')}}}}}",
        f"{{{{{template_name.replace('_', ' ')}}}}}",
    ]

    # Helper function to check if content starts with template
    def check_template_at_start(content: str) -> bool:
        """Check if content starts with any variation of the template"""
        # Check exact template matches (no parameters)
        for variation in template_variations:
            if content.startswith(variation):
                return True

        # Check for template with parameters (starts with {{TemplateName| or {{TemplateName\n)
        template_start_patterns = [
            f"{{{{{template_name}|",
            f"{{{{{template_name}\n",
            f"{{{{{template_name}\r",
            f"{{{{{template_name.replace(' ', '_')}|",
            f"{{{{{template_name.replace('_', ' ')}|",
        ]

        for pattern in template_start_patterns:
            if content.startswith(pattern):
                return True

        # Also handle case-insensitive matching for the template name
        lower_content = content.lower()
        lower_template = template_name.lower()

        if lower_content.startswith(f"{{{{{lower_template}}}}}") or \
           lower_content.startswith(f"{{{{{lower_template}|"):
            return True

        return False

    # Check both with and without noinclude tags removed
    # (template might be inside or outside noinclude tags)
    if check_template_at_start(normalized_content) or check_template_at_start(content_without_noinclude):
        result['has_template'] = True
        return result

    return result


def get_article_size_at_timestamp(article_url: str, when: datetime) -> Optional[int]:
    """
    Get the article size (bytes) at or before a specific timestamp.

    This is used to compute expansion bytes for contests.
    It keeps the logic small by doing a single `revisions` API call and
    returning the size of the newest revision that is not newer than `when`.

    Args:
        article_url: Full article URL.
        when: UTC datetime to look back from.

    Returns:
        Integer byte size if available, otherwise None.
    """
    # Extract page title from URL
    page_title = extract_page_title_from_url(article_url)
    if not page_title:
        return None

    # Build API endpoint URL
    url_obj = urlparse(article_url)
    base_url = f"{url_obj.scheme}://{url_obj.netloc}"
    api_url = f"{base_url}/w/api.php"

    # ISO timestamp in the format expected by MediaWiki
    when_iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build API parameters for historical size query
    params: Dict[str, Any] = {
        "action": "query",
        "titles": page_title,
        "format": "json",
        "formatversion": "2",
        "prop": "revisions",
        "rvprop": "timestamp|size",
        # We want the newest revision at or before `when`
        "rvlimit": "1",
        "rvdir": "older",  # Start from newest and go back in time
        "rvstart": when_iso,  # Start at this timestamp
        "redirects": "true",
        "converttitles": "true",
    }

    try:
        response = requests.get(api_url, params=params, headers=get_mediawiki_headers(), timeout=MEDIAWIKI_API_TIMEOUT)
    except requests.RequestException:
        # Network error. Caller will handle `None` gracefully
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except ValueError:
        # Invalid JSON response
        return None

    if "error" in data:
        # API returned an error
        return None

    # Extract page data from response
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None

    page_data = pages[0]
    revisions = page_data.get("revisions", [])
    if not revisions:
        # No revisions found at or before the timestamp
        return None

    # Single revision because we requested `rvlimit=1`
    rev = revisions[0]
    return rev.get("size")


# ---------------------------------------------------------------------------
# OAuth-based Wiki editing utilities
# ---------------------------------------------------------------------------

def get_csrf_token(
    api_url: str,
    oauth_token: str,
    oauth_token_secret: str,
    consumer_key: str,
    consumer_secret: str
) -> Optional[str]:
    """
    Fetch a CSRF token from MediaWiki API using OAuth1 authentication.

    This token is required for any write operations (edits, moves, etc.).

    Args:
        api_url: MediaWiki API URL (e.g., 'https://en.wikipedia.org/w/api.php')
        oauth_token: User's OAuth access token
        oauth_token_secret: User's OAuth access token secret
        consumer_key: Application's OAuth consumer key
        consumer_secret: Application's OAuth consumer secret

    Returns:
        CSRF token string, or None if fetch fails.
    """
    try:
        from requests_oauthlib import OAuth1
    except ImportError:
        # requests-oauthlib not installed
        return None

    # Create OAuth1 signature helper
    # signature_type='auth_header' puts OAuth credentials in Authorization header (required)
    auth = OAuth1(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
        signature_type='auth_header'  # Use Authorization header for OAuth
    )

    params = {
        "action": "query",
        "meta": "tokens",
        "type": "csrf",
        "format": "json",
        "formatversion": "2"  # Use modern format version
    }

    headers = get_mediawiki_headers()

    try:
        response = requests.get(api_url, params=params, auth=auth, headers=headers, timeout=15)
    except requests.RequestException as error:
        # Log the error for debugging
        import logging
        logging.error("CSRF token request failed: %s", str(error))
        return None

    if response.status_code != 200:
        # Log the status code and response for debugging
        import logging
        logging.error("CSRF token HTTP %s: %s", response.status_code, response.text[:500])
        return None

    try:
        data = response.json()
    except ValueError as error:
        import logging
        logging.error("CSRF token JSON parse error: %s, response: %s", str(error), response.text[:500])
        return None

    # Check for API errors
    if 'error' in data:
        import logging
        error_info = data['error']
        logging.error(
            "CSRF token API error: %s - %s",
            error_info.get('code', 'unknown'),
            error_info.get('info', 'Unknown error')
        )
        return None

    try:
        return data['query']['tokens']['csrftoken']
    except KeyError as error:
        import logging
        logging.error("CSRF token not found in response: %s, data: %s", str(error), data)
        return None


def prepend_template_to_article(  # pylint: disable=too-many-return-statements
    article_url: str,
    template_name: str,
    oauth_token: str,
    oauth_token_secret: str,
    consumer_key: str,
    consumer_secret: str,
    edit_summary: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prepend a template to the beginning of a Wikipedia article.

    Uses the MediaWiki API's 'prependtext' parameter to safely add content
    at the beginning of the page without risking edit conflicts.
    The edit is marked as a bot edit if the user has bot rights.

    Args:
        article_url: Full URL to the wiki article
        template_name: Template name without 'Template:' prefix
        oauth_token: User's OAuth access token
        oauth_token_secret: User's OAuth access token secret
        consumer_key: Application's OAuth consumer key
        consumer_secret: Application's OAuth consumer secret
        edit_summary: Optional edit summary (defaults to auto-generated)

    Returns:
        Dict with:
        - 'success': bool indicating if edit succeeded
        - 'error': error message if failed, None if succeeded
        - 'new_revid': new revision ID if succeeded
        - 'response': raw API response for debugging

    Note:
        The edit is marked as a bot edit using the 'bot' parameter.
        This requires the user account to have the 'bot' user right on the wiki.
        If the user doesn't have bot rights, the API will ignore the bot parameter
        and the edit will be made as a regular edit.
    """
    result = {
        'success': False,
        'error': None,
        'new_revid': None,
        'response': None,
    }

    try:
        from requests_oauthlib import OAuth1
    except ImportError:
        result['error'] = 'OAuth library not installed (requests-oauthlib required)'
        return result

    # Extract page title and build API URL
    page_title = extract_page_title_from_url(article_url)
    if not page_title:
        result['error'] = 'Could not extract page title from URL'
        return result

    url_obj = urlparse(article_url)
    base_url = f"{url_obj.scheme}://{url_obj.netloc}"
    api_url = f"{base_url}/w/api.php"

    # Create OAuth1 auth object
    # signature_type='auth_header' ensures OAuth signature is in Authorization header
    auth = OAuth1(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
        signature_type='auth_header'  # Use Authorization header for OAuth
    )

    # Get CSRF token
    csrf_token = get_csrf_token(
        api_url, oauth_token, oauth_token_secret, consumer_key, consumer_secret
    )
    if not csrf_token:
        result['error'] = 'Failed to obtain CSRF token. Check OAuth permissions.'
        return result

    # Build the template invocation
    # Format: {{TemplateName}}\n (with newline for proper spacing)
    template_text = f"{{{{{template_name}}}}}\n\n"

    # Prepare edit summary
    if not edit_summary:
        edit_summary = f"Adding {{{{{template_name}}}}} contest template (via WikiContest)"

    # Prepare the edit request
    # Note: The 'bot' parameter marks the edit as a bot edit
    # This requires the user account to have the 'bot' user right on the wiki
    # If the user doesn't have bot rights, the API will ignore this parameter
    edit_params = {
        "action": "edit",
        "title": page_title,
        "prependtext": template_text,  # Add to beginning of page
        "summary": edit_summary,
        "token": csrf_token,
        "bot": "1",  # Mark edit as bot edit (requires bot user right)
        "format": "json",
        "formatversion": "2"  # Use modern format version
    }

    headers = get_mediawiki_headers()

    try:
        response = requests.post(api_url, data=edit_params, auth=auth, headers=headers, timeout=30)
    except requests.RequestException as error:
        result['error'] = f'Network error during edit: {str(error)}'
        return result

    if response.status_code != 200:
        result['error'] = f'HTTP error during edit: {response.status_code}'
        # Log response for debugging
        import logging
        logging.error("Edit API HTTP %s: %s", response.status_code, response.text[:500])
        return result

    try:
        data = response.json()
    except ValueError:
        result['error'] = 'Failed to parse API response'
        return result

    result['response'] = data

    # Check for success
    if 'edit' in data:
        edit_result = data['edit'].get('result', '')
        if edit_result == 'Success':
            result['success'] = True
            result['new_revid'] = data['edit'].get('newrevid')
            return result
        result['error'] = f"Edit failed: {edit_result}"
        return result
    if 'error' in data:
        error_info = data['error']
        result['error'] = f"API error: {error_info.get('code', 'unknown')} - {error_info.get('info', 'Unknown error')}"
        return result
    result['error'] = 'Unknown API response format'
    return result


def _count_footnotes_from_content(article_content: str) -> int:
    """
    Count footnote references (<ref> tags) in article content.

    Args:
        article_content: Raw article content from MediaWiki API

    Returns:
        Integer count of <ref> tags found
    """
    if not article_content:
        return 0
    ref_pattern = r'<ref\b'
    ref_matches = re.findall(ref_pattern, article_content, re.IGNORECASE)
    return len(ref_matches)


def _extract_article_content_from_revision(latest_rev: dict) -> str:  # pylint: disable=invalid-name
    """
    Extract article content from MediaWiki revision data.

    Args:
        latest_rev: Revision data from MediaWiki API

    Returns:
        Article content string, or empty string if not found
    """
    # Try to get content from slots.main.*
    slots = latest_rev.get("slots", {})
    if slots:
        main_slot = slots.get("main", {})
        article_content = main_slot.get("*", "") or main_slot.get("content", "")
        if article_content:
            return article_content

    # Fallback to direct content access
    return latest_rev.get("*", "") or latest_rev.get("content", "")


def _fetch_footnotes_count(api_url: str, page_title: str, headers: dict) -> int:
    """
    Fetch and count footnotes from article content.

    Args:
        api_url: MediaWiki API URL
        page_title: Article page title
        headers: HTTP headers for API request

    Returns:
        Integer count of footnotes, or 0 if fetch fails
    """
    try:
        rev_params = {
            "action": "query",
            "titles": page_title,
            "format": "json",
            "formatversion": "2",
            "prop": "revisions",
            "rvprop": "ids|content",
            "rvlimit": "1",
            "rvdir": "older",
            "redirects": "true",
            "converttitles": "true",
            "rvslots": "*",
        }

        rev_response = requests.get(
            api_url, params=rev_params, headers=headers, timeout=10
        )

        if rev_response.status_code != 200:
            return 0

        rev_data = rev_response.json()
        if "error" in rev_data:
            return 0

        pages = rev_data.get("query", {}).get("pages", [])
        if not pages:
            return 0

        page_data = pages[0]
        if page_data.get("missing", False):
            return 0

        revisions = page_data.get("revisions", [])
        if not revisions:
            return 0

        latest_rev = revisions[0]
        article_content = _extract_article_content_from_revision(latest_rev)
        return _count_footnotes_from_content(article_content)

    except Exception:  # pylint: disable=broad-exception-caught
        # If footnote counting fails, continue with external links only
        # This ensures we still return a count even if content fetch fails
        return 0


def _log_warning(message: str, error: Exception) -> None:
    """Best-effort logging helper that uses Flask current_app when available.

    This keeps network helpers free from hard Flask dependencies while still
    providing useful diagnostics in a running application.
    """
    try:
        from flask import current_app

        current_app.logger.warning("%s: %s", message, str(error))
    except Exception:  # pylint: disable=broad-exception-caught
        # Logging must never break core logic, so ignore any logging failures
        pass


def get_article_image_count(article_url: str) -> Optional[int]:
    """
    The count is approximate and based purely on wikitext patterns; it does
    not guarantee that every match results in a rendered image, but it
    generally tracks user-added content images.
    """
    try:
        wikitext = get_article_wikitext(article_url)
        if wikitext is None:
            return None

        # Match explicit file/image links like [[File:Example.jpg|...]] or
        # [[Image:Example.png|...]] in a case-insensitive way.
        matches = re.findall(r'\[\[(?:File|Image):', wikitext, flags=re.IGNORECASE)
        return len(matches)

    except Exception as error:  # pylint: disable=broad-exception-caught
        _log_warning("Failed to fetch image count", error)
        return None


def get_article_infobox_count(article_url: str) -> Optional[int]:
    """Count approximate number of infobox templates in article wikitext.

    Detection is done via a simple regex scan for ``{{infobox ...}}`` in the
    raw wikitext. This is an approximation and may over-count or under-count
    in edge cases (e.g. nested templates, unusual formatting), but is
    sufficient for high-level richness metrics.
    """
    try:
        wikitext = get_article_wikitext(article_url)
        if wikitext is None:
            return None

        matches = re.findall(r"\{\{\s*infobox\b", wikitext, flags=re.IGNORECASE)
        return len(matches)

    except Exception as error:  # pylint: disable=broad-exception-caught
        _log_warning("Failed to fetch infobox count", error)
        return None


def get_article_reference_count(article_url: str) -> Optional[int]:
    """
    Get the total number of references in a MediaWiki article.

    Counts both:
    1. Footnotes (<ref> tags) - by parsing article content
    2. External links (URLs) - using MediaWiki extlinks API

    Uses the latest revision to ensure accuracy. Handles pagination
    automatically for articles with >500 external links.

    Args:
        article_url: Full URL to the article

    Returns:
        Integer count of total references (footnotes + external links) if successful,
        None if fetch fails.
    """
    try:
        # Extract page title from URL using shared utility
        page_title = extract_page_title_from_url(article_url)
        if not page_title:
            return None

        # Parse URL to get base URL
        url_obj = urlparse(article_url)
        base_url = f"{url_obj.scheme}://{url_obj.netloc}"
        api_url = f"{base_url}/w/api.php"
        headers = get_mediawiki_headers()

        # Step 1: Get article content to count footnotes (<ref> tags)
        footnotes_count = _fetch_footnotes_count(api_url, page_title, headers)

        # Step 2: Count external links using extlinks API
        external_links_count = 0
        elcontinue = None

        # Loop to handle pagination (MediaWiki API returns max 500 links per request)
        while True:
            # Build API parameters for external links query
            # Use prop=extlinks to get all external URLs (not interwikis)
            api_params = {
                "action": "query",
                "titles": page_title,
                "format": "json",
                "formatversion": "2",
                "prop": "extlinks",
                "ellimit": "500",  # Maximum allowed per request
                "redirects": "true",
                "converttitles": "true",
            }

            # Add continuation token if we're paginating
            if elcontinue:
                api_params["elcontinue"] = elcontinue

            # Make API request using shared headers
            response = requests.get(
                api_url, params=api_params, headers=headers, timeout=10
            )

            if response.status_code != 200:
                # Request failed, return None
                return None

            api_data = response.json()

            # Check for API errors
            if "error" in api_data:
                return None

            # Extract pages from response
            pages = api_data.get("query", {}).get("pages", [])
            if not pages or len(pages) == 0:
                return None

            page_data = pages[0]

            # Check if page exists (not a missing/deleted page)
            if page_data.get("missing", False):
                return None

            # Count external links in this batch
            extlinks = page_data.get("extlinks", [])
            external_links_count += len(extlinks)

            # Check if there are more links to fetch (pagination)
            continue_info = api_data.get("continue", {})
            elcontinue = continue_info.get("elcontinue")

            # If no continuation token, we've fetched all links
            if not elcontinue:
                break

        # Return total count: footnotes + external links
        total_count = footnotes_count + external_links_count
        return total_count

    except Exception as error:  # pylint: disable=broad-exception-caught
        # Log error but don't fail
        # This ensures the application continues even if reference counting fails
        try:
            from flask import current_app
            current_app.logger.warning(
                f"Failed to fetch reference count: {str(error)}"
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # Logging itself failed, silently continue
            pass
        return None


# ---------------------------------------------------------------------------
# MediaWiki User Information Utilities
# ---------------------------------------------------------------------------

def get_mediawiki_user_edit_count(
    username: str, mw_uri: str = "https://meta.wikimedia.org/w/index.php"
) -> Optional[int]:
    """
    Get the edit count for a MediaWiki user.

    Fetches user information from MediaWiki API and returns their edit count.
    This is used to check if a user meets the minimum edit count requirement
    for automatic trusted member status (>= 300 edits).

    Args:
        username: MediaWiki username to check
        mw_uri: MediaWiki base URI (defaults to meta.wikimedia.org)

    Returns:
        Integer edit count if successful, None if fetch fails or user not found.
    """
    try:
        # Build API URL from MediaWiki URI
        # Convert from index.php format to api.php format
        if mw_uri.endswith('/index.php'):
            api_url = mw_uri.replace('/index.php', '/w/api.php')
        elif mw_uri.endswith('/'):
            api_url = f"{mw_uri}w/api.php"
        else:
            api_url = f"{mw_uri}/w/api.php"

        # Build API parameters to get user info
        # Use users query to get edit count
        api_params = {
            'action': 'query',
            'list': 'users',
            'ususers': username,
            'usprop': 'editcount',  # Get edit count
            'format': 'json',
            'formatversion': '2'
        }

        headers = get_mediawiki_headers()

        # Make request to MediaWiki API
        response = requests.get(
            api_url,
            params=api_params,
            headers=headers,
            timeout=MEDIAWIKI_API_TIMEOUT
        )

        if response.status_code != 200:
            return None

        data = response.json()

        # Check for API errors
        if 'error' in data:
            return None

        # Extract edit count from response
        users = data.get('query', {}).get('users', [])
        if not users or len(users) == 0:
            return None

        user_data = users[0]

        # Check if user was found (missing field indicates user doesn't exist)
        if user_data.get('missing'):
            return None

        # Get edit count
        edit_count = user_data.get('editcount')
        if edit_count is None:
            return None

        return int(edit_count)

    except Exception as error:  # pylint: disable=broad-exception-caught
        # Log error but don't fail
        # This ensures the application continues even if edit count fetch fails
        try:
            from flask import current_app
            current_app.logger.warning(
                f"Failed to fetch edit count for user {username}: {str(error)}"
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # Logging itself failed, silently continue
            pass
        return None


# ---------------------------------------------------------------------------
# Category utilities for article category attachment
# ---------------------------------------------------------------------------

def extract_category_name_from_url(category_url: str) -> Optional[str]:
    """
    Extract the category name from a Wiki category URL.

    Supports URLs like:
    - https://en.wikipedia.org/wiki/Category:Contest2025
    - https://en.wikipedia.org/w/index.php?title=Category:Contest2025

    Args:
        category_url: Full URL to a Wiki category page.

    Returns:
        Category name without 'Category:' prefix (e.g., 'Contest2025'),
        or None if extraction fails.
    """
    page_title = extract_page_title_from_url(category_url)
    if not page_title:
        return None

    # Check if it's in the Category namespace
    # Handle different language prefixes (Category:, Kategorie:, Categoría:, etc.)
    category_prefixes = [
        "Category:", "category:",
        "Kategorie:",  # German
        "Categoría:",  # Spanish
        "Catégorie:",  # French
        "Kategoria:",  # Polish
        "Категория:",  # Russian
        "分类:",  # Chinese
    ]

    for prefix in category_prefixes:
        if page_title.startswith(prefix):
            return page_title[len(prefix):]

    # If no prefix found, return None (not a category page)
    return None


def check_article_has_category(article_url: str, category_name: str) -> Dict[str, Any]:
    """
    Check if an article has the specified category.

    Searches the article wikitext for [[Category:CategoryName]] pattern.
    Handles variations in spacing and formatting.

    Args:
        article_url: Full URL to the wiki article.
        category_name: Category name without 'Category:' prefix.

    Returns:
        Dict with:
        - 'has_category': bool indicating if category is present
        - 'error': error message if check failed, None otherwise
    """
    result = {
        'has_category': False,
        'error': None,
    }

    # Fetch article wikitext
    wikitext = get_article_wikitext(article_url)
    if wikitext is None:
        result['error'] = 'Failed to fetch article content'
        return result

    # Normalize category name for comparison
    # Handle spaces vs underscores
    category_variations = [
        category_name,
        category_name.replace(' ', '_'),
        category_name.replace('_', ' '),
    ]

    # Build category patterns to search for
    # Categories can appear as [[Category:Name]] or [[Category:Name|sortkey]]
    category_patterns = []
    for variation in category_variations:
        # Exact match: [[Category:Name]]
        category_patterns.append(f"[[Category:{variation}]]")
        # With sortkey: [[Category:Name|...]]
        category_patterns.append(f"[[Category:{variation}|")
        # Case-insensitive variations
        category_patterns.append(f"[[category:{variation.lower()}]]")
        category_patterns.append(f"[[category:{variation.lower()}|")

    # Search for any of the patterns in the wikitext
    for pattern in category_patterns:
        if pattern in wikitext:
            result['has_category'] = True
            return result

    # Category not found
    return result


def append_categories_to_article(  # pylint: disable=too-many-return-statements
    article_url: str,
    category_names: List[str],
    oauth_token: str,
    oauth_token_secret: str,
    consumer_key: str,
    consumer_secret: str,
    edit_summary: Optional[str] = None
) -> Dict[str, Any]:
    """
    Append categories to the end of a Wikipedia article.

    Uses the MediaWiki API's 'appendtext' parameter to safely add categories
    at the end of the page without risking edit conflicts.
    The edit is marked as a bot edit if the user has bot rights.

    Args:
        article_url: Full URL to the wiki article
        category_names: List of category names without 'Category:' prefix
        oauth_token: User's OAuth access token
        oauth_token_secret: User's OAuth access token secret
        consumer_key: Application's OAuth consumer key
        consumer_secret: Application's OAuth consumer secret
        edit_summary: Optional edit summary (defaults to auto-generated)

    Returns:
        Dict with:
        - 'success': bool indicating if edit succeeded
        - 'error': error message if failed, None if succeeded
        - 'categories_added': list of category names that were added
        - 'categories_skipped': list of category names that already existed
        - 'new_revid': new revision ID if succeeded
        - 'response': raw API response for debugging

    Note:
        The edit is marked as a bot edit using the 'bot' parameter.
        This requires the user account to have the 'bot' user right on the wiki.
        If the user doesn't have bot rights, the API will ignore the bot parameter
        and the edit will be made as a regular edit.
    """
    result = {
        'success': False,
        'error': None,
        'categories_added': [],
        'categories_skipped': [],
        'new_revid': None,
        'response': None,
    }

    # Validate input
    if not category_names:
        result['error'] = 'No categories provided'
        return result

    try:
        from requests_oauthlib import OAuth1
    except ImportError:
        result['error'] = 'OAuth library not installed (requests-oauthlib required)'
        return result

    # Extract page title and build API URL
    page_title = extract_page_title_from_url(article_url)
    if not page_title:
        result['error'] = 'Could not extract page title from URL'
        return result

    url_obj = urlparse(article_url)
    base_url = f"{url_obj.scheme}://{url_obj.netloc}"
    api_url = f"{base_url}/w/api.php"

    # Check which categories already exist
    categories_to_add = []
    for category_name in category_names:
        category_check = check_article_has_category(article_url, category_name)
        if category_check.get('error'):
            # If check failed, we'll try to add it anyway (better to try than skip)
            categories_to_add.append(category_name)
        elif not category_check.get('has_category'):
            # Category doesn't exist, add it
            categories_to_add.append(category_name)
        else:
            # Category already exists, skip it
            result['categories_skipped'].append(category_name)

    # If all categories already exist, return success with skipped list
    if not categories_to_add:
        result['success'] = True
        return result

    # Create OAuth1 auth object
    # signature_type='auth_header' ensures OAuth signature is in Authorization header
    auth = OAuth1(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
        signature_type='auth_header'  # Use Authorization header for OAuth
    )

    # Get CSRF token
    csrf_token = get_csrf_token(
        api_url, oauth_token, oauth_token_secret, consumer_key, consumer_secret
    )
    if not csrf_token:
        result['error'] = 'Failed to obtain CSRF token. Check OAuth permissions.'
        return result

    # Build the category text to append
    # Format: \n[[Category:Name1]]\n[[Category:Name2]]\n
    # Each category on its own line at the end of the article
    category_lines = []
    for category_name in categories_to_add:
        category_lines.append(f"[[Category:{category_name}]]")
    category_text = "\n" + "\n".join(category_lines) + "\n"

    # Prepare edit summary
    if not edit_summary:
        if len(categories_to_add) == 1:
            edit_summary = f"Adding [[Category:{categories_to_add[0]}]] contest category (via WikiContest submission)"
        else:
            category_list = ", ".join([f"[[Category:{name}]]" for name in categories_to_add])
            edit_summary = f"Adding contest categories: {category_list} (via WikiContest submission)"

    # Prepare the edit request
    # Note: The 'bot' parameter marks the edit as a bot edit
    # This requires the user account to have the 'bot' user right on the wiki
    # If the user doesn't have bot rights, the API will ignore this parameter
    edit_params = {
        "action": "edit",
        "title": page_title,
        "appendtext": category_text,  # Add to end of page
        "summary": edit_summary,
        "token": csrf_token,
        "bot": "1",  # Mark edit as bot edit (requires bot user right)
        "format": "json",
        "formatversion": "2"  # Use modern format version
    }

    headers = get_mediawiki_headers()

    try:
        response = requests.post(api_url, data=edit_params, auth=auth, headers=headers, timeout=30)
    except requests.RequestException as error:
        result['error'] = f'Network error during edit: {str(error)}'
        return result

    if response.status_code != 200:
        result['error'] = f'HTTP error during edit: {response.status_code}'
        # Log response for debugging
        import logging
        logging.error("Category edit API HTTP %s: %s", response.status_code, response.text[:500])
        return result

    try:
        data = response.json()
    except ValueError:
        result['error'] = 'Failed to parse API response'
        return result

    result['response'] = data

    # Check for success
    if 'edit' in data:
        edit_result = data['edit'].get('result', '')
        if edit_result == 'Success':
            result['success'] = True
            result['new_revid'] = data['edit'].get('newrevid')
            result['categories_added'] = categories_to_add
            return result
        result['error'] = f"Edit failed: {edit_result}"
        return result
    if 'error' in data:
        error_info = data['error']
        result['error'] = f"API error: {error_info.get('code', 'unknown')} - {error_info.get('info', 'Unknown error')}"
        return result
    result['error'] = 'Unknown API response format'
    return result


def get_article_incoming_links(article_url: str) -> Optional[int]:
    """
    Count the number of mainspace articles that link to the given article.
    
    This uses the MediaWiki API's "backlinks" query to count incoming links
    from other articles in the main namespace (namespace 0).
    
    Args:
        article_url: Full URL to the wiki article
        
    Returns:
        Integer count of incoming links from mainspace articles, or None if fetch fails
    """
    try:
        # Extract page title from URL
        page_title = extract_page_title_from_url(article_url)
        if not page_title:
            return None
            
        # Parse the article URL to extract base URL
        url_obj = urlparse(article_url)
        base_url = f"{url_obj.scheme}://{url_obj.netloc}"
        api_url = f"{base_url}/w/api.php"
        
        # Build API parameters for backlinks query
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "list": "backlinks",
            "bltitle": page_title,
            "blnamespace": "0",  # Only count links from mainspace (namespace 0)
            "bllimit": "500",  # Maximum allowed by API
            "blfilterredir": "nonredirects",  # Exclude redirects
            "redirects": "true",  # Follow redirects to get actual page
            "converttitles": "true",
        }
        
        headers = get_mediawiki_headers()
        
        # Make initial request
        response = requests.get(api_url, params=params, headers=headers, timeout=MEDIAWIKI_API_TIMEOUT)
        if response.status_code != 200:
            return None
            
        data = response.json()
        if "error" in data:
            return None
            
        # Count backlinks from response
        backlinks = data.get("query", {}).get("backlinks", [])
        total_count = len(backlinks)
        
        # Check if there are more results (continuation)
        continue_params = data.get("continue")
        while continue_params and total_count < 10000:  # Safety limit to prevent infinite loops
            # Update params with continuation token
            params.update(continue_params)
            
            response = requests.get(api_url, params=params, headers=headers, timeout=MEDIAWIKI_API_TIMEOUT)
            if response.status_code != 200:
                break
                
            data = response.json()
            if "error" in data:
                break
                
            # Add more backlinks to count
            more_backlinks = data.get("query", {}).get("backlinks", [])
            total_count += len(more_backlinks)
            
            # Get next continuation token
            continue_params = data.get("continue")
            
        return total_count
        
    except Exception:  # pylint: disable=broad-exception-caught
        # If link counting fails, return None to indicate failure
        # This ensures submission process continues even if link counting fails
        return None


def get_article_outgoing_links(article_url: str) -> Optional[int]:
    """
    Count the number of mainspace articles that the given article links to.
    
    This uses the MediaWiki API's "links" query to count outgoing links
    to other articles in the main namespace (namespace 0).
    
    Args:
        article_url: Full URL to the wiki article
        
    Returns:
        Integer count of outgoing links to mainspace articles, or None if fetch fails
    """
    try:
        # Extract page title from URL
        page_title = extract_page_title_from_url(article_url)
        if not page_title:
            return None
            
        # Parse the article URL to extract base URL
        url_obj = urlparse(article_url)
        base_url = f"{url_obj.scheme}://{url_obj.netloc}"
        api_url = f"{base_url}/w/api.php"
        
        # Build API parameters for links query
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "links",
            "titles": page_title,
            "plnamespace": "0",  # Only count links to mainspace (namespace 0)
            "pllimit": "500",  # Maximum allowed by API
            "plfilterredir": "nonredirects",  # Exclude redirects
            "redirects": "true",  # Follow redirects to get actual page
            "converttitles": "true",
        }
        
        headers = get_mediawiki_headers()
        
        # Make initial request
        response = requests.get(api_url, params=params, headers=headers, timeout=MEDIAWIKI_API_TIMEOUT)
        if response.status_code != 200:
            return None
            
        data = response.json()
        if "error" in data:
            return None
            
        # Extract links from response
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            return None
            
        page_data = pages[0]
        if page_data.get("missing", False):
            return None
            
        links = page_data.get("links", [])
        total_count = len(links)
        
        # Check if there are more results (continuation)
        continue_params = data.get("continue")
        while continue_params and total_count < 10000:  # Safety limit to prevent infinite loops
            # Update params with continuation token
            params.update(continue_params)
            
            response = requests.get(api_url, params=params, headers=headers, timeout=MEDIAWIKI_API_TIMEOUT)
            if response.status_code != 200:
                break
                
            data = response.json()
            if "error" in data:
                break
                
            # Add more links to count
            pages = data.get("query", {}).get("pages", [])
            if pages:
                more_links = pages[0].get("links", [])
                total_count += len(more_links)
            
            # Get next continuation token
            continue_params = data.get("continue")
            
        return total_count
        
    except Exception:  # pylint: disable=broad-exception-caught
        # If link counting fails, return None to indicate failure
        # This ensures submission process continues even if link counting fails
        return None


# ---------------------------------------------------------------------------
# Category Crawler Utilities
# ---------------------------------------------------------------------------

def crawl_category_articles(
    category_url: str,
    limit: int = 5000,
    mw_uri: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Crawl articles from a Wikipedia category using the MediaWiki API.

    Uses the `list=categorymembers` API to fetch all pages in a category,
    handling pagination via `cmcontinue` tokens.

    Args:
        category_url: Full URL to a Wikipedia category page.
            Examples:
            - https://en.wikipedia.org/wiki/Category:Living_people
            - https://es.wikipedia.org/wiki/Categoría:Wikipedia
        limit: Maximum number of articles to fetch (default: 5000, max: 5000).
        mw_uri: Optional MediaWiki API base URI. If not provided, extracted from category_url.

    Returns:
        Dictionary with:
            - "articles": List of dicts with "title" and "url" keys
            - "total": Total number of articles fetched
            - "category": Category name extracted from URL
            - "wiki_base": Wiki base URL (e.g., "https://en.wikipedia.org")
        Or None if an error occurs.
    """
    try:
        # Enforce maximum limit
        limit = min(limit, 5000)

        # Extract category name from URL
        category_name = extract_category_name_from_url(category_url)
        if not category_name:
            return None

        # Parse wiki base URL from category URL
        parsed = urlparse(category_url)
        wiki_base = f"{parsed.scheme}://{parsed.netloc}"
        api_url = f"{wiki_base}/w/api.php"

        # Determine MediaWiki URI
        if mw_uri is None:
            mw_uri = api_url

        headers = get_mediawiki_headers()

        # Build API params for category members
        # cmtitle requires the full title with namespace prefix (e.g., "Category:Living_people")
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category_name}",
            "cmtype": "page",  # Only get actual pages, not subcategories or files
            "cmlimit": "max",  # Max per request (usually 500)
            "cmnamespace": "0",  # Only mainspace articles
            "format": "json",
        }

        articles = []
        continue_token = None

        while len(articles) < limit:
            # Add continue token if we have one
            if continue_token:
                params["cmcontinue"] = continue_token

            response = requests.get(
                mw_uri,
                params=params,
                headers=headers,
                timeout=MEDIAWIKI_API_TIMEOUT
            )

            if response.status_code != 200:
                break

            data = response.json()

            if "error" in data:
                break

            # Extract category members
            members = data.get("query", {}).get("categorymembers", [])

            for member in members:
                if len(articles) >= limit:
                    break

                title = member.get("title")
                page_id = member.get("pageid")

                if title:
                    # Build article URL
                    # Use /wiki/ format for cleaner URLs
                    encoded_title = title.replace(" ", "_")
                    article_url = f"{wiki_base}/wiki/{encoded_title}"

                    articles.append({
                        "title": title,
                        "url": article_url,
                        "page_id": page_id,
                    })

            # Check for continuation
            continue_data = data.get("continue")
            if continue_data and "cmcontinue" in continue_data:
                continue_token = continue_data["cmcontinue"]
            else:
                break

        return {
            "articles": articles,
            "total": len(articles),
            "category": category_name,
            "wiki_base": wiki_base,
        }

    except Exception as e:  # pylint: disable=broad-exception-caught
        # If crawling fails, return None to indicate failure
        # Log the error for debugging
        import logging
        logging.error(f"crawl_category_articles failed: {str(e)}")
        return None
