"""
MediaWiki API proxy routes for WikiContest Application.

Backend-side proxies to the MediaWiki API that solve browser CORS issues by
making requests from the server. Moved here from the direct routes previously
defined on the Flask app in app/__init__.py.

The blueprint has no URL prefix so endpoint URLs and methods are unchanged.
"""

import os
from urllib.parse import urlparse, parse_qs, unquote

from flask import Blueprint, request, jsonify

from app.utils import (
    extract_page_title_from_url,
    build_mediawiki_revisions_api_params,
    get_latest_revision_author,
    get_article_reference_count,
)
from app.services.mediawiki import MediaWikiClient
from app.utils.url_validation import validate_wiki_url

# Create blueprint (no url_prefix — endpoints keep their original paths)
mediawiki_proxy_bp = Blueprint('mediawiki_proxy', __name__)


@mediawiki_proxy_bp.route('/api/mediawiki/article-info', methods=['GET'])
def mediawiki_article_info():  # pylint: disable=too-many-return-statements
    """
    Fetch comprehensive article information from MediaWiki API.

    This endpoint fetches detailed information about a MediaWiki article including:
    - Article title
    - Author (creator) of the article
    - Creation date
    - Last revision date
    - Page ID
    - Word count
    - And other metadata useful for judging

    Query Parameters:
        url (str): The full MediaWiki article URL

    Returns:
        JSON: Article information including title, author, dates, etc.

    Example:
        GET /api/mediawiki/article-info?url=https://en.wikipedia.org/wiki/Article_Title
    """
    # Get the article URL from query parameters
    article_url = request.args.get('url', '')

    if not article_url:
        return jsonify({'error': 'Article URL is required'}), 400

    try:
        # Extract page title from URL using shared utility function
        # This ensures consistency with the submission route
        page_title = extract_page_title_from_url(article_url)

        if not page_title:
            return jsonify({'error': 'Could not extract page title from URL'}), 400

        # Parse the article URL to extract base URL
        base_url, error = validate_wiki_url(article_url)
        if error:
            return error

        # Build MediaWiki API URL
        api_url = f"{base_url}/w/api.php"

        # Build API parameters using shared utility function
        # This ensures we use the same logic as the submission route
        # With rvdir='older', we get the newest revision first, then oldest
        # This matches how the submission route fetches byte count
        api_params = build_mediawiki_revisions_api_params(page_title)
        # Add additional parameters for this endpoint
        api_params['inprop'] = 'url|displaytitle'

        # Make request to MediaWiki API using the centralized client
        client = MediaWikiClient()
        data = client.get(api_url, params=api_params)

        if data is None:
            return jsonify({
                'error': 'Failed to fetch article information from MediaWiki API',
                'api_url': api_url,
                'page_title': page_title
            }), 502

        # Check for API errors
        if 'error' in data:
            error_info = data['error'].get('info', 'Unknown MediaWiki API error')
            error_code = data['error'].get('code', 'unknown')
            return jsonify({
                'error': error_info,
                'code': error_code
            }), 400

        # Get page data
        # With formatversion=2, pages is an array; otherwise it's an object
        pages = data.get('query', {}).get('pages', [])
        if not pages:
            return jsonify({'error': 'No page data found in API response'}), 404

        # Handle formatversion=2 (array) or formatversion=1 (object)
        if isinstance(pages, list):
            # formatversion=2: pages is an array
            if len(pages) == 0:
                return jsonify({'error': 'Article not found'}), 404
            page_data = pages[0]
            page_id = str(page_data.get('pageid', ''))
        else:
            # formatversion=1: pages is an object with page IDs as keys
            page_id = list(pages.keys())[0]
            page_data = pages[page_id]

        # Check if page exists
        # In formatversion=2, missing pages have 'missing': True
        # In formatversion=1, missing pages have pageid: -1
        is_missing = page_data.get('missing', False) if page_data else True
        has_valid_pageid = page_id and page_id != '-1' and page_id != ''

        if not has_valid_pageid or is_missing:
            return jsonify({'error': 'Article not found'}), 404

        # Extract article information
        article_title = page_data.get('title', page_title)
        display_title = page_data.get('displaytitle', article_title)
        page_url = page_data.get('fullurl', article_url)

        # Get revision information
        # With rvdir='older' and rvlimit=2, we get:
        # - revisions[0] = newest (latest) revision - use for byte count
        # - revisions[-1] = oldest (first) revision - use for creation date/author
        revisions = page_data.get('revisions', [])
        author = None
        article_created_at = None
        last_revision_date = None
        word_count = None

        if revisions and len(revisions) > 0:
            # Get latest revision (newest) for byte count
            # This matches the submission route logic - we validate against current size
            # With rvdir='older', the first revision is the newest (latest)
            latest_revision = revisions[0]
            word_count = latest_revision.get('size', 0)

            # Get latest revision author using shared utility function
            # This gets the author who made the most recent edit
            author = get_latest_revision_author(revisions)
            if not author:
                author = 'Unknown'

            # Get oldest revision for creation date
            # If we have multiple revisions, the last one is the oldest
            # If we only have one revision, it's both the newest and oldest
            if len(revisions) > 1:
                oldest_revision = revisions[-1]
            else:
                oldest_revision = revisions[0]

            article_created_at = oldest_revision.get('timestamp', '')
            last_revision_date = latest_revision.get('timestamp', '')
        else:
            # Page exists but has no revisions - this is unusual but possible
            # Set defaults and log a warning
            word_count = 0
            author = 'Unknown'
            article_created_at = None
            last_revision_date = None

        # Fetch reference count using shared utility function
        # This counts both footnotes (<ref> tags) and external links (URLs)
        # Uses the latest revision to ensure accuracy
        reference_count = get_article_reference_count(article_url)

        # Return comprehensive article information
        return jsonify({
            'article_title': article_title,
            'display_title': display_title,
            'article_url': page_url,
            'author': author,
            'article_created_at': article_created_at,
            'last_revision_date': last_revision_date,
            'word_count': word_count,
            'reference_count': reference_count,  # Total references: footnotes + external links
            'page_id': page_id,
            'base_url': base_url
        }), 200

    except ValueError as error:
        # JSON parsing or data conversion error
        return jsonify({
            'error': f'Invalid response from MediaWiki API: {str(error)}'
        }), 502
    except (KeyError, TypeError, AttributeError) as error:
        # Catch data structure errors (missing keys, wrong types, missing attributes)
        return jsonify({
            'error': f'Unexpected error while fetching article information: {str(error)}'
        }), 500


@mediawiki_proxy_bp.route('/api/mediawiki/preview', methods=['GET'])
def mediawiki_preview():  # pylint: disable=too-many-return-statements
    """
    Proxy endpoint for MediaWiki API article preview requests.

    This endpoint acts as a proxy to fetch MediaWiki article content
    from external MediaWiki sites. It solves CORS issues by making
    the request from the backend server instead of the browser.

    Query Parameters:
        url (str): The full MediaWiki article URL to fetch preview for
        page (str, optional): The page title (if URL parsing fails)

    Returns:
        JSON: MediaWiki API response with parsed article content

    Example:
        GET /api/mediawiki/preview?url=https://en.wikipedia.org/wiki/Userpage
    """
    # Get the article URL from query parameters
    article_url = request.args.get('url', '')
    page_title = request.args.get('page', '')

    if not article_url:
        return jsonify({'error': 'Article URL is required'}), 400

    try:
        # Parse the article URL to extract base URL and page title
        url_obj = urlparse(article_url)
        base_url, error = validate_wiki_url(article_url)
        if error:
            return error

        # Extract page title from URL if not provided as parameter
        if not page_title:
            if '/wiki/' in url_obj.path:
                # Standard MediaWiki URL format: /wiki/Page_Title
                # Decode URL-encoded characters (e.g., %20 -> space, %2F -> /)
                page_title = unquote(url_obj.path.split('/wiki/')[1])
            elif 'title=' in url_obj.query:
                # Old-style URL: /w/index.php?title=Page_Title
                query_params = parse_qs(url_obj.query)
                page_title = unquote(query_params.get('title', [''])[0])
            else:
                # Try to extract from pathname
                parts = url_obj.path.split('/')
                page_title = unquote(parts[-1]) if parts else ''

        if not page_title:
            return jsonify({'error': 'Could not extract page title from URL'}), 400

        # Build MediaWiki API URL
        # Use action=parse to get rendered HTML content
        api_url = f"{base_url}/w/api.php"

        # MediaWiki API request with formatversion=2 for better JSON structure
        # This matches the recommended API format
        api_params = {
            'action': 'parse',
            'page': page_title,  # MediaWiki API handles URL encoding internally
            'format': 'json',
            'formatversion': '2',  # Use formatversion=2 for cleaner JSON structure
            'prop': 'text|displaytitle',
            'redirects': 'true'  # Follow redirects
        }

        # Make request to MediaWiki API with timeout
        # Backend-to-backend requests don't have CORS restrictions
        # MediaWiki API requires a User-Agent header to identify the application
        headers = {
            'User-Agent': (
                'WikiContest/1.0 (' + os.environ.get('FRONTEND_URL', 'https://wikicontest.toolforge.org') + '; '
                'contact@wikicontest.org) Python/requests'
            )
        }

        client = MediaWikiClient()
        data = client.get(api_url, params=api_params)

        if data is None:
            return jsonify({
                'error': 'Failed to fetch article content from MediaWiki API',
                'api_url': api_url,
                'page_title': page_title
            }), 502

        # Check for API errors
        if 'error' in data:
            error_info = data['error'].get('info', 'Unknown MediaWiki API error')
            error_code = data['error'].get('code', 'unknown')
            return jsonify({
                'error': error_info,
                'code': error_code,
                'page_title': page_title
            }), 400

        # Check if we have parsed content
        if 'parse' not in data:
            return jsonify({
                'error': 'No parse data found in MediaWiki API response',
                'page_title': page_title,
                'response_keys': (
                    list(data.keys()) if isinstance(data, dict) else 'not a dict'
                )
            }), 404

        # Check if text field exists (can be dict or string depending on formatversion)
        parse_data = data.get('parse', {})
        if 'text' not in parse_data:
            return jsonify({
                'error': 'No text content found in MediaWiki API response',
                'page_title': page_title,
                'parse_keys': (
                    list(parse_data.keys()) if isinstance(parse_data, dict) else 'not a dict'
                )
            }), 404

        # Get the HTML content
        # Handle both formatversion=1 (dict with '*') and formatversion=2
        # MediaWiki API parse action returns text as a dict with '*' key
        text_data = parse_data.get('text', {})

        if isinstance(text_data, dict):
            # Standard format: text is a dict with '*' key containing the HTML
            html_content = text_data.get('*', '')
        elif isinstance(text_data, str):
            # Fallback: if text is directly a string (shouldn't happen but handle it)
            html_content = text_data
        else:
            # No text data available
            html_content = ''

        # Get the actual page title (may differ from URL due to redirects)
        # Use safe access to avoid errors
        actual_page_title = parse_data.get('displaytitle') or parse_data.get('title', page_title)

        # Make links absolute (convert relative links to absolute)
        # This ensures images and links work correctly in the preview
        html_content = html_content.replace('href="/wiki/', f'href="{base_url}/wiki/')
        html_content = html_content.replace('href="/w/', f'href="{base_url}/w/')
        html_content = html_content.replace('src="/wiki/', f'src="{base_url}/wiki/')
        html_content = html_content.replace('src="/w/', f'src="{base_url}/w/')

# Return the parsed content
        response = jsonify({
            'htmlContent': html_content,
            'actualPageTitle': actual_page_title,
            'pageTitle': page_title,
            'baseUrl': base_url
        })
        response.headers['Cache-Control'] = 'public, max-age=30'
        return response, 200

    except ValueError as error:
        # JSON parsing error
        return jsonify({
            'error': f'Invalid response from MediaWiki API: {str(error)}'
        }), 502
    except (KeyError, TypeError, AttributeError) as error:
        # Catch data structure errors (missing keys, wrong types, missing attributes)
        return jsonify({
            'error': f'Unexpected error while fetching article preview: {str(error)}'
        }), 500
