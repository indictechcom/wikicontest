"""
Wiki editing utilities for WikiEval Application.

Provides helpers for MediaWiki OAuth-based editing operations:
fetching CSRF tokens, prepending templates, and appending categories.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests
from urllib.parse import urlparse

from app.services.mediawiki import MediaWikiClient
from app.utils.mediawiki_helpers import (
    extract_page_title_from_url,
    validate_wiki_url,
    get_mediawiki_headers,
)

__all__ = [
    "get_csrf_token",
    "prepend_template_to_article",
    "append_categories_to_article",
]


def get_csrf_token(
    api_url: str,
    oauth_token: str,
    oauth_token_secret: str,
    consumer_key: str,
    consumer_secret: str
) -> Optional[str]:
    """
    Retrieve a MediaWiki CSRF token using OAuth1 authentication.
    
    Parameters:
        api_url (str): MediaWiki API endpoint.
        oauth_token (str): OAuth resource owner token.
        oauth_token_secret (str): OAuth resource owner token secret.
        consumer_key (str): OAuth consumer key.
        consumer_secret (str): OAuth consumer secret.
    
    Returns:
        Optional[str]: The CSRF token, or None if the request or response is unsuccessful.
    """
    try:
        from requests_oauthlib import OAuth1
    except ImportError:
        return None

    auth = OAuth1(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
        signature_type='auth_header'
    )

    params = {
        "action": "query",
        "meta": "tokens",
        "type": "csrf",
        "format": "json",
        "formatversion": "2"
    }

    client = MediaWikiClient()

    try:
        data = client.post(api_url, data=params, auth=auth, timeout=15)
    except requests.RequestException as error:
        import logging
        logging.error("CSRF token request failed: %s", str(error))
        return None

    if data is None:
        import logging
        logging.error("CSRF token HTTP error or invalid response from %s", api_url)
        return None

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


def prepend_template_to_article(
    article_url: str,
    template_name: str,
    oauth_token: str,
    oauth_token_secret: str,
    consumer_key: str,
    consumer_secret: str,
    edit_summary: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prepend a MediaWiki template invocation to an article.
    
    Parameters:
        article_url (str): URL of the article to edit.
        template_name (str): Name of the template to prepend.
        edit_summary (Optional[str]): Edit summary for the change. A default
            WikiEval summary is used when omitted.
    
    Returns:
        Dict[str, Any]: Result containing success status, error information,
            the new revision ID, and the raw API response.
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

    page_title = extract_page_title_from_url(article_url)
    if not page_title:
        result['error'] = 'Could not extract page title from URL'
        return result

    base_url, error = validate_wiki_url(article_url)
    if error:
        result['error'] = error[0].get_json()['error']
        return result
    api_url = f"{base_url}/w/api.php"

    auth = OAuth1(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
        signature_type='auth_header'
    )

    csrf_token = get_csrf_token(
        api_url, oauth_token, oauth_token_secret, consumer_key, consumer_secret
    )
    if not csrf_token:
        result['error'] = 'Failed to obtain CSRF token. Check OAuth permissions.'
        return result

    template_text = f"{{{{{template_name}}}}}\n\n"

    if not edit_summary:
        edit_summary = f"Adding {{{{{template_name}}}}} contest template (via WikiEval)"

    edit_params = {
        "action": "edit",
        "title": page_title,
        "prependtext": template_text,
        "summary": edit_summary,
        "token": csrf_token,
        "bot": "1",
        "format": "json",
        "formatversion": "2"
    }

    headers = get_mediawiki_headers()

    client = MediaWikiClient()

    try:
        data = client.post(api_url, data=edit_params, auth=auth, timeout=30)
    except requests.RequestException as error:
        result['error'] = f'Network error during edit: {str(error)}'
        return result

    if data is None:
        result['error'] = 'HTTP error during edit or invalid response'
        import logging
        logging.error("Edit API HTTP error for %s", api_url)
        return result

    result['response'] = data

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


def append_categories_to_article(
    article_url: str,
    category_names: list,
    oauth_token: str,
    oauth_token_secret: str,
    consumer_key: str,
    consumer_secret: str,
    edit_summary: Optional[str] = None
) -> Dict[str, Any]:
    """
    Append categories to a wiki article while skipping categories already present.
    
    Parameters:
    	article_url (str): URL of the article to edit.
    	category_names (list): Category names to append.
    	oauth_token (str): OAuth resource owner token.
    	oauth_token_secret (str): OAuth resource owner token secret.
    	consumer_key (str): OAuth consumer key.
    	consumer_secret (str): OAuth consumer secret.
    	edit_summary (Optional[str]): Edit summary to use; a default is generated when omitted.
    
    Returns:
    	Dict[str, Any]: Result containing the edit status, error information, added and skipped categories, new revision ID, and API response.
    """
    result = {
        'success': False,
        'error': None,
        'categories_added': [],
        'categories_skipped': [],
        'new_revid': None,
        'response': None,
    }

    if not category_names:
        result['error'] = 'No categories provided'
        return result

    try:
        from requests_oauthlib import OAuth1
    except ImportError:
        result['error'] = 'OAuth library not installed (requests-oauthlib required)'
        return result

    page_title = extract_page_title_from_url(article_url)
    if not page_title:
        result['error'] = 'Could not extract page title from URL'
        return result

    base_url, error = validate_wiki_url(article_url)
    if error:
        result['error'] = error[0].get_json()['error']
        return result
    api_url = f"{base_url}/w/api.php"

    from app.utils.wiki_categories import check_article_has_category

    categories_to_add = []
    for category_name in category_names:
        category_check = check_article_has_category(article_url, category_name)
        if category_check.get('error'):
            categories_to_add.append(category_name)
        elif not category_check.get('has_category'):
            categories_to_add.append(category_name)
        else:
            result['categories_skipped'].append(category_name)

    if not categories_to_add:
        result['success'] = True
        return result

    auth = OAuth1(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
        signature_type='auth_header'
    )

    csrf_token = get_csrf_token(
        api_url, oauth_token, oauth_token_secret, consumer_key, consumer_secret
    )
    if not csrf_token:
        result['error'] = 'Failed to obtain CSRF token. Check OAuth permissions.'
        return result

    category_lines = []
    for category_name in categories_to_add:
        category_lines.append(f"[[Category:{category_name}]]")
    category_text = "\n" + "\n".join(category_lines) + "\n"

    if not edit_summary:
        if len(categories_to_add) == 1:
            edit_summary = f"Adding [[Category:{categories_to_add[0]}]] contest category (via WikiEval submission)"
        else:
            category_list = ", ".join([f"[[Category:{name}]]" for name in categories_to_add])
            edit_summary = f"Adding contest categories: {category_list} (via WikiEval submission)"

    edit_params = {
        "action": "edit",
        "title": page_title,
        "appendtext": category_text,
        "summary": edit_summary,
        "token": csrf_token,
        "bot": "1",
        "format": "json",
        "formatversion": "2"
    }

    client = MediaWikiClient()

    try:
        data = client.post(api_url, data=edit_params, auth=auth, timeout=30)
    except requests.RequestException as error:
        result['error'] = f'Network error during edit: {str(error)}'
        return result

    if data is None:
        result['error'] = 'HTTP error during edit or invalid response'
        import logging
        logging.error("Category edit API HTTP error for %s", api_url)
        return result

    result['response'] = data

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
