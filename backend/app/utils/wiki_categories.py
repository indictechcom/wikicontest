"""
Wiki category utilities for WikiEval Application.

Provides helpers for validating, checking, and extracting wiki category names,
plus category crawling functionality for automated scoring contests.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from app.services.mediawiki import MediaWikiClient
from app.utils.mediawiki_helpers import (
    extract_page_title_from_url,
    get_article_wikitext,
)


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


def crawl_category_articles(
    category_url: str,
    limit: int = 5000,
    mw_uri: Optional[str] = None,
    continue_from: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Crawl articles from a Wikipedia category using the MediaWiki API.

    Uses the `list=categorymembers` API to fetch all pages in a category,
    handling pagination via `cmcontinue` tokens.

    Args:
        category_url:  Full URL to a Wikipedia category page.
        limit:         Maximum number of articles to fetch in this call.
        mw_uri:        Optional MediaWiki API base URI. Extracted from
                       category_url when omitted.
        continue_from: A ``cmcontinue`` token returned by a previous call.
                       When provided the crawl resumes from that position
                       instead of starting from the beginning of the category.
                       Pass the value of ``next_continue`` from the previous
                       response to implement "Import Next Batch" behaviour.

    Returns:
        Dictionary with:
            - "articles":      List of dicts with "title", "url", "page_id".
            - "total":         Number of articles fetched in this call.
            - "category":      Category name extracted from URL.
            - "wiki_base":     Wiki base URL (e.g., "https://en.wikipedia.org").
            - "has_more":      True if there are more articles beyond this batch.
            - "next_continue": cmcontinue token to pass as ``continue_from``
                               in the next call (None when has_more is False).
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

        # Build API params for category members
        # cmtitle requires the full title with namespace prefix (e.g., "Category:Living_people")
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category_name}",
            "cmtype": "page",      # Only get actual pages, not subcategories or files
            "cmlimit": "max",      # Max per request (usually 500)
            "cmnamespace": "0",    # Only mainspace articles
            "format": "json",
        }

        articles = []
        # Seed the continue token from caller so we resume mid-category
        continue_token: Optional[str] = continue_from
        # Track the token that will be returned for the *next* batch
        next_continue: Optional[str] = None
        client = MediaWikiClient()

        while len(articles) < limit:
            # Add continue token if we have one (either seeded or from prev page)
            if continue_token:
                params["cmcontinue"] = continue_token
            elif "cmcontinue" in params:
                # Remove stale key from a previous iteration that has now been cleared
                del params["cmcontinue"]

            data = client.get(mw_uri, params=params)
            if data is None:
                break

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
                    # Build article URL — use /wiki/ format for cleaner URLs
                    encoded_title = title.replace(" ", "_")
                    article_url = f"{wiki_base}/wiki/{encoded_title}"

                    articles.append({
                        "title": title,
                        "url": article_url,
                        "page_id": page_id,
                    })

            # Check for continuation token from MediaWiki
            continue_data = data.get("continue")
            if continue_data and "cmcontinue" in continue_data:
                next_continue = continue_data["cmcontinue"]
                continue_token = next_continue
            else:
                # No more pages in the category
                next_continue = None
                break

            # If we hit the limit mid-category the outer while loop exits here.
            # next_continue already holds the right token for resuming.

        # has_more is True when we stopped because we hit `limit` AND there are
        # still more articles beyond this batch (next_continue is not None).
        has_more = next_continue is not None and len(articles) >= limit

        return {
            "articles": articles,
            "total": len(articles),
            "category": category_name,
            "wiki_base": wiki_base,
            # Pagination fields for "Import Next Batch" support
            "has_more": has_more,
            "next_continue": next_continue if has_more else None,
        }

    except Exception as e:  # pylint: disable=broad-exception-caught
        # If crawling fails, return None to indicate failure
        # Log the error for debugging
        logging.error(f"crawl_category_articles failed: {str(e)}")
        return None
