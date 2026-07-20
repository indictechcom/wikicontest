"""
Wiki template utilities for WikiEval Application.

Provides helpers for validating, checking, and extracting wiki template names.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.mediawiki import MediaWikiClient
from app.utils.mediawiki_helpers import extract_page_title_from_url
from app.utils.url_validation import validate_wiki_url

__all__ = [
    "extract_template_name_from_url",
    "validate_template_link",
    "check_article_has_template",
]


def extract_template_name_from_url(template_url: str) -> Optional[str]:
    """
    Extract a template name from a wiki template URL.
    
    Parameters:
    	template_url (str): URL of the wiki template page.
    
    Returns:
    	Optional[str]: The template name without its namespace prefix, or `None` if the URL does not identify a supported template namespace.
    """
    page_title = extract_page_title_from_url(template_url)
    if not page_title:
        return None

    template_prefixes = [
        "Template:", "template:",
        "Vorlage:",
        "Plantilla:",
        "Modèle:",
        "Szablon:",
        "Шаблон:",
        "模板:",
    ]

    for prefix in template_prefixes:
        if page_title.startswith(prefix):
            return page_title[len(prefix):]

    return None


def validate_template_link(template_url: str) -> Dict[str, Any]:
    """
    Validate a template URL and confirm that the corresponding wiki page exists.
    
    Parameters:
    	template_url (str): HTTP or HTTPS URL for a page in a supported Template namespace.
    
    Returns:
    	Dict[str, Any]: Validation result containing validity, template name, page existence, template status, and an error message when validation fails.
    """
    result = {
        'valid': False,
        'error': None,
        'template_name': None,
        'page_exists': False,
        'is_template': False,
    }

    if not template_url:
        result['error'] = 'Template link is required'
        return result

    if not (template_url.startswith('http://') or template_url.startswith('https://')):
        result['error'] = 'Template link must be a valid HTTP/HTTPS URL'
        return result

    page_title = extract_page_title_from_url(template_url)
    if not page_title:
        result['error'] = 'Could not extract page title from URL'
        return result

    template_name = extract_template_name_from_url(template_url)
    if template_name:
        result['is_template'] = True
        result['template_name'] = template_name
    else:
        result['error'] = 'URL must point to a Template namespace page (e.g., Template:YourTemplate)'
        return result

    base_url, error = validate_wiki_url(template_url)
    if error:
        result['error'] = error[0].get_json()['error']
        return result
    api_url = f"{base_url}/w/api.php"

    params = {
        "action": "query",
        "titles": page_title,
        "format": "json",
        "formatversion": "2",
        "prop": "info",
        "redirects": "true",
    }

    client = MediaWikiClient()
    data = client.get(api_url, params=params)
    if data is None:
        result['error'] = 'Failed to verify template: network or API error'
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


def check_article_has_template(article_url: str, template_name: str) -> Dict[str, Any]:
    """
    Determine whether an article begins with the specified template.
    
    Parameters:
    	article_url (str): URL of the article whose wikitext is checked.
    	template_name (str): Name of the template to locate at the start of the article.
    
    Returns:
    	Dict[str, Any]: Result containing whether the template was found, a truncated article-content preview, and an error message when fetching fails.
    """
    result = {
        'has_template': False,
        'error': None,
        'article_content': None,
    }

    from app.utils.mediawiki_helpers import get_article_wikitext

    wikitext = get_article_wikitext(article_url)
    if wikitext is None:
        result['error'] = 'Failed to fetch article content'
        return result

    result['article_content'] = wikitext[:500] if len(wikitext) > 500 else wikitext

    normalized_content = wikitext.lstrip()
    normalized_content = __import__('re').sub(r'<!--.*?-->', '', normalized_content, flags=__import__('re').DOTALL)
    normalized_content = normalized_content.lstrip()
    content_without_noinclude = __import__('re').sub(r'<noinclude>.*?</noinclude>', '', normalized_content, flags=__import__('re').DOTALL)
    content_without_noinclude = content_without_noinclude.lstrip()

    template_variations = [
        f"{{{{{template_name}}}}}",
        f"{{{{{template_name.replace(' ', '_')}}}}}",
        f"{{{{{template_name.replace('_', ' ')}}}}}",
    ]

    def check_template_at_start(content: str) -> bool:
        """
        Determine whether the content begins with an invocation of the specified template.
        
        Parameters:
            content (str): Wikitext content to inspect.
        
        Returns:
            bool: `True` if the content begins with a recognized template invocation, `False` otherwise.
        """
        for variation in template_variations:
            if content.startswith(variation):
                return True

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

        lower_content = content.lower()
        lower_template = template_name.lower()

        if lower_content.startswith(f"{{{{{lower_template}}}}}") or \
           lower_content.startswith(f"{{{{{lower_template}|"):
            return True

        return False

    if check_template_at_start(normalized_content) or check_template_at_start(content_without_noinclude):
        result['has_template'] = True
        return result

    return result
