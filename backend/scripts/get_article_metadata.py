"""
Script to fetch article metadata from MediaWiki pages.

This script uses the same MediaWiki API logic as the submission route
to fetch comprehensive metadata about any MediaWiki article, including:
- Article title and display title
- Author (creator)
- Creation date
- Last revision date
- Word count
- Page ID

This script calls the MediaWiki API directly (same logic as when users submit articles),
so it doesn't require the Flask server to be running.

Usage:
    # Method 1: Pass URL as command line argument
    python get_article_metadata.py "https://en.wikipedia.org/wiki/Python_(programming_language)"
    
    # Method 2: Change the URL variable in this script and run
    python get_article_metadata.py
    
    # Method 3: Run without arguments to be prompted for URL
    python get_article_metadata.py
"""

import sys
import json
import requests
from typing import Optional
from urllib.parse import urlparse, unquote, parse_qs

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default article URL (change this to fetch metadata for a different article)
# Leave empty to be prompted or pass as command line argument
DEFAULT_ARTICLE_URL = ""

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def get_article_metadata(article_url: str) -> Optional[dict]:
    """
    Fetch article metadata directly from MediaWiki API.
    
    This function uses the same logic as the submission route in contest_routes.py
    to fetch comprehensive article information from MediaWiki API.
    
    Args:
        article_url (str): Full URL of the MediaWiki article
        
    Returns:
        Optional[dict]: Article metadata dictionary if successful, None if error
    """
    try:
        # Parse the article URL to extract base URL and page title
        # This is the same logic used in the submission route
        url_obj = urlparse(article_url)
        base_url = f"{url_obj.scheme}://{url_obj.netloc}"
        
        # Extract page title from URL
        # Same extraction logic as submission route
        page_title = ''
        if '/wiki/' in url_obj.path:
            # Standard MediaWiki URL format: /wiki/Page_Title
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
            print("[X] Error: Could not extract page title from URL")
            return None
        
        print(f"[*] Fetching metadata from: {article_url}")
        print(f"[*] Extracted page title: {page_title}")
        print(f"[*] Base URL: {base_url}")
        print()
        
        # Build MediaWiki API URL
        api_url = f"{base_url}/w/api.php"
        
        # Fetch article information using the same parameters as submission route
        # Use formatversion=2 for better JSON structure
        # Request revisions with user info to get author and latest word count
        # Note: converttitles=true is important for handling special characters
        # Get 2 revisions: newest (for latest word count) and oldest (for author/creation date)
        api_params = {
            'action': 'query',
            'titles': page_title,
            'format': 'json',
            'formatversion': '2',  # Use formatversion=2 for cleaner JSON structure
            'prop': 'info|revisions',
            'rvprop': 'timestamp|user|userid|comment|size',  # Include userid as fallback
            'rvlimit': '2',  # Get 2 revisions: newest and oldest
            'rvdir': 'older',  # Start from newest (default), get newest first
            'inprop': 'url|displaytitle',
            'redirects': 'true',  # Follow redirects automatically
            'converttitles': 'true'  # Convert titles to canonical form (IMPORTANT!)
        }
        
        # Make request to MediaWiki API
        # MediaWiki API requires a User-Agent header to identify the application
        headers = {
            'User-Agent': (
                'WikiContest/1.0 (https://wikicontest.toolforge.org; '
                'contact@wikicontest.org) Python/requests'
            )
        }
        
        print(f"[>] Calling MediaWiki API: {api_url}")
        print()
        
        response = requests.get(api_url, params=api_params, headers=headers, timeout=10)
        
        # Check if request was successful
        if response.status_code != 200:
            print(f"[X] Error: MediaWiki API returned status code {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
        
        # Parse JSON response
        api_data = response.json()
        
        # Check for API errors
        if 'error' in api_data:
            error_info = api_data['error'].get('info', 'Unknown MediaWiki API error')
            error_code = api_data['error'].get('code', 'unknown')
            print(f"[X] Error: {error_info} (code: {error_code})")
            return None
        
        # Handle formatversion=2 (array) or formatversion=1 (object)
        pages = api_data.get('query', {}).get('pages', [])
        if not pages:
            print("[X] Error: No page data found in API response")
            return None
        
        # Handle both array (formatversion=2) and object (formatversion=1) formats
        if isinstance(pages, list):
            # formatversion=2: pages is an array
            if len(pages) == 0:
                print("[X] Error: Article not found")
                return None
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
        
        if not page_data or not has_valid_pageid or is_missing:
            print("[X] Error: Article not found")
            return None
        
        # Extract article information
        article_title = page_data.get('title', page_title)
        display_title = page_data.get('displaytitle', article_title)
        page_url = page_data.get('fullurl', article_url)
        
        # Get revision information
        # With formatversion=2, revisions is an array
        # With rvdir='older', revisions[0] is the newest (latest) revision
        revisions = page_data.get('revisions', [])
        author = None
        article_created_at = None
        last_revision_date = None
        word_count = None
        
        if revisions and len(revisions) > 0:
            # Get latest revision (newest) for word count and last revision date
            # With rvdir='older', the first revision is the newest
            latest_revision = revisions[0]
            
            # Get word count from latest revision (most current size)
            word_count = latest_revision.get('size', 0)
            last_revision_date = latest_revision.get('timestamp', '')
            
            # Get oldest revision (creation) for author and creation date
            # If we have multiple revisions, the last one in the array is the oldest
            # If we only have one revision, it's both the newest and oldest
            if len(revisions) > 1:
                # We have both newest and oldest revisions
                oldest_revision = revisions[-1]
            else:
                # Only one revision exists, so it's both newest and oldest
                oldest_revision = revisions[0]
            
            # Extract author from oldest revision (creation revision)
            # Try 'user' field first, then 'userid' as fallback
            author = oldest_revision.get('user')
            if not author:
                # If user field is missing, try userid (though this is numeric)
                userid = oldest_revision.get('userid')
                if userid:
                    author = f'User ID: {userid}'
                else:
                    author = 'Unknown'
            
            # Get creation date from oldest revision
            article_created_at = oldest_revision.get('timestamp', '')
        
        # Return comprehensive article information
        return {
            'article_title': article_title,
            'display_title': display_title,
            'article_url': page_url,
            'author': author,
            'article_created_at': article_created_at,
            'last_revision_date': last_revision_date,
            'word_count': word_count,
            'page_id': page_id,
            'base_url': base_url
        }
        
    except requests.exceptions.Timeout:
        print("[X] Error: Request to MediaWiki API timed out.")
        print("   The server may be slow or unavailable.")
        return None
    except requests.exceptions.RequestException as error:
        print(f"[X] Error: Failed to connect to MediaWiki API: {str(error)}")
        return None
    except ValueError as error:
        # JSON parsing error
        print(f"[X] Error: Invalid JSON response from MediaWiki API: {str(error)}")
        return None
    except (KeyError, TypeError, AttributeError) as error:
        # Catch data structure errors
        print(f"[X] Error: Unexpected error while fetching article information: {str(error)}")
        return None


def display_metadata(metadata: dict) -> None:
    """
    Display article metadata in a readable format.
    
    Args:
        metadata (dict): Article metadata dictionary from API
    """
    print("=" * 70)
    print("ARTICLE METADATA")
    print("=" * 70)
    print()
    
    # Display title information
    if 'display_title' in metadata:
        print(f"Display Title: {metadata['display_title']}")
    if 'article_title' in metadata:
        print(f"Article Title: {metadata['article_title']}")
    
    print()
    
    # Display URL
    if 'article_url' in metadata:
        print(f"URL: {metadata['article_url']}")
    
    print()
    
    # Display author information
    if 'author' in metadata and metadata['author']:
        print(f"Author: {metadata['author']}")
    else:
        print("Author: Unknown")
    
    print()
    
    # Display dates
    if 'article_created_at' in metadata and metadata['article_created_at']:
        print(f"Created: {metadata['article_created_at']}")
    
    if 'last_revision_date' in metadata and metadata['last_revision_date']:
        print(f"Last Revised: {metadata['last_revision_date']}")
    
    print()
    
    # Display statistics
    if 'word_count' in metadata and metadata['word_count']:
        # Format word count with thousands separator
        word_count = metadata['word_count']
        formatted_count = f"{word_count:,}" if isinstance(word_count, int) else str(word_count)
        print(f"Word Count: {formatted_count}")
    
    if 'page_id' in metadata and metadata['page_id']:
        print(f"Page ID: {metadata['page_id']}")
    
    if 'base_url' in metadata:
        print(f"Base URL: {metadata['base_url']}")
    
    print()
    print("=" * 70)
    
    # Also display raw JSON for debugging
    print()
    print("Raw JSON Response:")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


def main():
    """
    Main function to run the script.
    
    Handles command line arguments and prompts for URL if needed.
    """
    # Get article URL from command line argument, default variable, or prompt
    article_url = None
    
    # Method 1: Check command line arguments
    if len(sys.argv) > 1:
        article_url = sys.argv[1]
    
    # Method 2: Use default URL from script
    elif DEFAULT_ARTICLE_URL:
        article_url = DEFAULT_ARTICLE_URL
    
    # Method 3: Prompt user for URL
    else:
        print("Enter the MediaWiki article URL:")
        print("(Example: https://en.wikipedia.org/wiki/Python_(programming_language))")
        article_url = input("URL: ").strip()
    
    # Validate URL
    if not article_url:
        print("[X] Error: No article URL provided")
        print()
        print("Usage:")
        print("  python get_article_metadata.py <article_url>")
        print("  or change DEFAULT_ARTICLE_URL in the script")
        sys.exit(1)
    
    # Check if URL looks valid
    if not article_url.startswith(('http://', 'https://')):
        print(f"[!] Warning: URL doesn't start with http:// or https://")
        print(f"   Using as-is: {article_url}")
        print()
    
    # Fetch metadata
    metadata = get_article_metadata(article_url)
    
    # Display results
    if metadata:
        display_metadata(metadata)
    else:
        print()
        print("[X] Failed to fetch article metadata")
        sys.exit(1)


# Run the script if executed directly
if __name__ == '__main__':
    main()
