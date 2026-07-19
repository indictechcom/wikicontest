"""
Article metrics functions for WikiContest Application.

Provides helpers for counting references, images, infoboxes, and links
in MediaWiki articles, plus parallel metric fetching for submissions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.services.mediawiki import MediaWikiClient
from app.utils.mediawiki_helpers import (
    extract_page_title_from_url,
    validate_wiki_url,
    get_article_wikitext,
    _log_warning,
)

__all__ = [
    "get_article_reference_count",
    "get_detailed_reference_counts",
    "get_article_image_count",
    "get_article_infobox_count",
    "get_article_incoming_links",
    "get_article_outgoing_links",
    "fetch_article_metrics",
]


def _count_footnotes_from_content(article_content: str) -> int:
    if not article_content:
        return 0
    ref_pattern = r'<ref\b'
    ref_matches = re.findall(ref_pattern, article_content, re.IGNORECASE)
    return len(ref_matches)


def _extract_article_content_from_revision(latest_rev: dict) -> str:
    slots = latest_rev.get("slots", {})
    if slots:
        main_slot = slots.get("main", {})
        article_content = main_slot.get("*", "") or main_slot.get("content", "")
        if article_content:
            return article_content

    return latest_rev.get("*", "") or latest_rev.get("content", "")


def _fetch_footnotes_count(api_url: str, page_title: str) -> int:
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

        client = MediaWikiClient()
        rev_data = client.get(api_url, params=rev_params, timeout=10)
        if rev_data is None:
            return 0

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

    except Exception:
        return 0


def get_detailed_reference_counts(article_url: str, wikitext=None) -> Dict[str, int]:
    if wikitext is None:
        wikitext = get_article_wikitext(article_url)
    if not wikitext:
        return {"new": 0, "reused": 0}

    try:
        import mwparserfromhell

        parsed = mwparserfromhell.parse(wikitext)

        new_refs = 0
        reused_refs = 0

        for tag in parsed.filter_tags():
            if str(tag.tag).strip().lower() != "ref":
                continue
            if tag.self_closing:
                reused_refs += 1
            else:
                new_refs += 1

        return {"new": new_refs, "reused": reused_refs}

    except ImportError:
        import logging
        logging.warning(
            "mwparserfromhell is not installed — falling back to regex for "
            "reference counting. Install it with: pip install mwparserfromhell"
        )

        text = re.sub(r"<!--.*?-->", "", wikitext, flags=re.DOTALL)

        reused_refs = len(re.findall(r"<ref\b[^>]*?/>", text, flags=re.IGNORECASE))
        new_refs = len(re.findall(
            r"<ref\b[^/][^>]*>(?:[^<]|<(?!/ref>))*</ref>",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        ))
        return {"new": new_refs, "reused": reused_refs}


def get_article_image_count(article_url: str, wikitext=None) -> Optional[int]:
    try:
        if wikitext is None:
            wikitext = get_article_wikitext(article_url)
        if wikitext is None:
            return None

        matches = re.findall(r'\[\[(?:File|Image):', wikitext, flags=re.IGNORECASE)
        return len(matches)

    except Exception as error:
        _log_warning("Failed to fetch image count", error)
        return None


def get_article_infobox_count(article_url: str, wikitext=None) -> Optional[int]:
    try:
        if wikitext is None:
            wikitext = get_article_wikitext(article_url)
        if wikitext is None:
            return None

        matches = re.findall(r"\{\{\s*infobox\b", wikitext, flags=re.IGNORECASE)
        return len(matches)

    except Exception as error:
        _log_warning("Failed to fetch infobox count", error)
        return None


def get_article_reference_count(article_url: str) -> Optional[int]:
    try:
        page_title = extract_page_title_from_url(article_url)
        if not page_title:
            return None

        base_url, error = validate_wiki_url(article_url)
        if error:
            return None
        api_url = f"{base_url}/w/api.php"

        footnotes_count = _fetch_footnotes_count(api_url, page_title)

        external_links_count = 0
        elcontinue = None
        client = MediaWikiClient()

        while True:
            api_params = {
                "action": "query",
                "titles": page_title,
                "format": "json",
                "formatversion": "2",
                "prop": "extlinks",
                "ellimit": "500",
                "redirects": "true",
                "converttitles": "true",
            }

            if elcontinue:
                api_params["elcontinue"] = elcontinue

            api_data = client.get(api_url, params=api_params)
            if api_data is None:
                return None

            if "error" in api_data:
                return None

            pages = api_data.get("query", {}).get("pages", [])
            if not pages or len(pages) == 0:
                return None

            page_data = pages[0]

            if page_data.get("missing", False):
                return None

            extlinks = page_data.get("extlinks", [])
            external_links_count += len(extlinks)

            continue_info = api_data.get("continue", {})
            elcontinue = continue_info.get("elcontinue")

            if not elcontinue:
                break

        total_count = footnotes_count + external_links_count
        return total_count

    except Exception as error:
        try:
            from flask import current_app
            current_app.logger.warning(
                f"Failed to fetch reference count: {str(error)}"
            )
        except Exception:
            pass
        return None


def get_article_incoming_links(article_url: str) -> Optional[int]:
    try:
        page_title = extract_page_title_from_url(article_url)
        if not page_title:
            return None

        base_url, error = validate_wiki_url(article_url)
        if error:
            return None
        api_url = f"{base_url}/w/api.php"

        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "list": "backlinks",
            "bltitle": page_title,
            "blnamespace": "0",
            "bllimit": "500",
            "blfilterredir": "nonredirects",
            "redirects": "true",
            "converttitles": "true",
        }

        client = MediaWikiClient()

        data = client.get(api_url, params=params)
        if data is None:
            return None

        if "error" in data:
            return None

        backlinks = data.get("query", {}).get("backlinks", [])
        total_count = len(backlinks)

        continue_params = data.get("continue")
        while continue_params and total_count < 10000:
            params.update(continue_params)

            data = client.get(api_url, params=params)
            if data is None:
                break

            if "error" in data:
                break

            more_backlinks = data.get("query", {}).get("backlinks", [])
            total_count += len(more_backlinks)

            continue_params = data.get("continue")

        return total_count

    except Exception:
        return None


def get_article_outgoing_links(article_url: str) -> Optional[int]:
    try:
        page_title = extract_page_title_from_url(article_url)
        if not page_title:
            return None

        base_url, error = validate_wiki_url(article_url)
        if error:
            return None
        api_url = f"{base_url}/w/api.php"

        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "links",
            "titles": page_title,
            "plnamespace": "0",
            "pllimit": "500",
            "plfilterredir": "nonredirects",
            "redirects": "true",
            "converttitles": "true",
        }

        client = MediaWikiClient()

        data = client.get(api_url, params=params)
        if data is None:
            return None

        if "error" in data:
            return None

        pages = data.get("query", {}).get("pages", [])
        if not pages:
            return None

        page_data = pages[0]
        if page_data.get("missing", False):
            return None

        links = page_data.get("links", [])
        total_count = len(links)

        continue_params = data.get("continue")
        while continue_params and total_count < 10000:
            params.update(continue_params)

            data = client.get(api_url, params=params)
            if data is None:
                break

            if "error" in data:
                break

            pages = data.get("query", {}).get("pages", [])
            if pages:
                more_links = pages[0].get("links", [])
                total_count += len(more_links)

            continue_params = data.get("continue")

        return total_count

    except Exception:
        return None


def fetch_article_metrics(article_link, contest_start_date=None):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    try:
        from flask import copy_current_request_context
    except ImportError:
        def copy_current_request_context(fn):
            return fn

    from app.utils import (
        get_article_wikitext,
        get_article_reference_count,
        get_detailed_reference_counts,
        get_article_image_count,
        get_article_infobox_count,
        get_article_incoming_links,
        get_article_outgoing_links,
        get_article_size_at_timestamp,
        _log_warning,
    )

    wikitext = get_article_wikitext(article_link)

    def _fetch_references():
        return get_article_reference_count(article_link)

    def _fetch_detailed_refs():
        return get_detailed_reference_counts(article_link, wikitext=wikitext)

    def _fetch_images():
        return get_article_image_count(article_link, wikitext=wikitext)

    def _fetch_infoboxes():
        return get_article_infobox_count(article_link, wikitext=wikitext)

    def _fetch_incoming():
        return get_article_incoming_links(article_link)

    def _fetch_outgoing():
        return get_article_outgoing_links(article_link)

    def _fetch_size_at_start():
        return get_article_size_at_timestamp(article_link, contest_start_date)

    tasks = {
        "reference_count": _fetch_references,
        "new_ref_count": _fetch_detailed_refs,
        "image_count": _fetch_images,
        "infobox_count": _fetch_infoboxes,
        "incoming_links": _fetch_incoming,
        "outgoing_links": _fetch_outgoing,
    }
    if contest_start_date is not None:
        tasks["size_at_start"] = _fetch_size_at_start

    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        wrapped = {
            executor.submit(copy_current_request_context(fn)): key
            for key, fn in tasks.items()
        }
        for future in as_completed(wrapped):
            key = wrapped[future]
            try:
                results[key] = future.result(timeout=30)
            except Exception as exc:
                _log_warning(f"fetch_article_metrics: failed to fetch {key}", exc)
                results[key] = None

    detailed = results.pop("new_ref_count", None)
    if isinstance(detailed, dict):
        results["new_ref_count"] = detailed.get("new", 0) or 0
        results["reused_ref_count"] = detailed.get("reused", 0) or 0
    else:
        results["new_ref_count"] = 0
        results["reused_ref_count"] = 0

    return results
