"""
Article metrics functions for WikiEval Application.

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
    """
    Count reference tags in article wikitext.
    
    Parameters:
    	article_content (str): Article wikitext to inspect.
    
    Returns:
    	int: Number of opening `<ref` tag occurrences, or 0 when the content is empty.
    """
    if not article_content:
        return 0
    ref_pattern = r'<ref\b'
    ref_matches = re.findall(ref_pattern, article_content, re.IGNORECASE)
    return len(ref_matches)


def _extract_article_content_from_revision(latest_rev: dict) -> str:
    """
    Extract article wikitext from a revision response.
    
    Parameters:
    	latest_rev (dict): Revision data containing article content directly or in its main slot.
    
    Returns:
    	str: The extracted article content, or an empty string when no content is available.
    """
    slots = latest_rev.get("slots", {})
    if slots:
        main_slot = slots.get("main", {})
        article_content = main_slot.get("*", "") or main_slot.get("content", "")
        if article_content:
            return article_content

    return latest_rev.get("*", "") or latest_rev.get("content", "")


def _fetch_footnotes_count(api_url: str, page_title: str) -> int:
    """
    Count `<ref>` tags in the latest available revision of an article.
    
    Parameters:
    	api_url (str): MediaWiki API endpoint URL.
    	page_title (str): Article title to query.
    
    Returns:
    	int: Number of `<ref>` tags, or `0` if the article data cannot be retrieved.
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
    """
    Count new and reused references in an article's wikitext.
    
    Parameters:
    	article_url (str): URL of the article used to retrieve wikitext when `wikitext` is not provided.
    	wikitext: Optional article wikitext to analyze.
    
    Returns:
    	Dict[str, int]: Counts keyed by `"new"` for paired references and `"reused"` for self-closing references.
    """
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
    """
    Count file and image inclusions in an article's wikitext.
    
    Parameters:
        article_url (str): URL of the article.
        wikitext (str, optional): Article wikitext to analyze. If omitted, it is fetched from the article URL.
    
    Returns:
        int or None: Number of file and image inclusions, or None if the wikitext is unavailable or an error occurs.
    """
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
    """
    Count infobox templates in an article's wikitext.
    
    Parameters:
    	article_url (str): URL of the article whose wikitext is analyzed.
    	wikitext: Optional wikitext to analyze instead of fetching the article content.
    
    Returns:
    	int: Number of infobox template occurrences, or `None` if the wikitext cannot be obtained or an error occurs.
    """
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
    """Count an article's footnotes and external links.
    
    Parameters:
        article_url (str): URL of the article to measure.
    
    Returns:
        Optional[int]: Combined footnote and external link count, or `None` if the article cannot be queried.
    """
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

            # Safety cap: stop pagination if we reach 10,000 items
            if external_links_count >= 10000:
                break

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
    """
    Count non-redirecting incoming links to a wiki article.
    
    Parameters:
    	article_url (str): URL of the article whose incoming links are counted.
    
    Returns:
    	int: Number of incoming links, up to 10,000; `None` if the URL is invalid or the data cannot be retrieved.
    """
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
    """
    Count non-redirecting outgoing article links.
    
    Parameters:
    	article_url (str): URL of the wiki article.
    
    Returns:
    	int: Number of outgoing links, up to 10,000; `None` if the URL is invalid, the article is unavailable, or a request fails.
    """
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
    """
    Collect article reference, media, infobox, link, and optional historical size metrics.
    
    Parameters:
        article_link: URL identifying the article.
        contest_start_date: Date for the optional historical size metric.
    
    Returns:
        Dictionary of metric names to values. Reference details are returned as
        ``new_ref_count`` and ``reused_ref_count``; unavailable metrics have a
        value of ``None``.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    try:
        from flask import copy_current_request_context
    except ImportError:
        def copy_current_request_context(fn):
            """
            Pass a callable through unchanged when request-context copying is unavailable.
            
            Parameters:
                fn (callable): The callable to preserve.
            
            Returns:
                callable: The original callable.
            """
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
        """
        Fetch the article's total reference count.
        
        Returns:
        	int or None: The number of references, or None if the count cannot be retrieved.
        """
        return get_article_reference_count(article_link)

    def _fetch_detailed_refs():
        """
        Fetch detailed counts of new and reused references for the article.
        
        Returns:
        	dict[str, int]: Counts grouped by ``"new"`` and ``"reused"`` references.
        """
        return get_detailed_reference_counts(article_link, wikitext=wikitext)

    def _fetch_images():
        """
        Count file and image inclusions for the article.
        
        Returns:
            Optional[int]: The number of file and image inclusions, or None if unavailable.
        """
        return get_article_image_count(article_link, wikitext=wikitext)

    def _fetch_infoboxes():
        """
        Fetch the number of infobox templates in the article.
        
        Returns:
        	int or None: The infobox count, or None if the count cannot be determined.
        """
        return get_article_infobox_count(article_link, wikitext=wikitext)

    def _fetch_incoming():
        """
        Fetch the number of incoming links for the article.
        
        Returns:
        	int or None: The incoming-link count, or None if it cannot be fetched.
        """
        return get_article_incoming_links(article_link)

    def _fetch_outgoing():
        """Fetches the number of outgoing links for the article.
        
        Returns:
            Optional[int]: The number of outgoing links, or ``None`` if unavailable.
        """
        return get_article_outgoing_links(article_link)

    def _fetch_size_at_start():
        """
        Fetch the article size at the contest start date.
        
        Returns:
            The article size at `contest_start_date`.
        """
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
