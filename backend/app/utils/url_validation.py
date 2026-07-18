"""
URL validation for WikiContest Application.

Provides SSRF protection for all outbound MediaWiki API requests.
All functions that accept a user-supplied URL MUST call validate_wiki_url()
before constructing an outbound HTTP request.
"""

import os
import re
from urllib.parse import urlparse

from flask import jsonify

# Default allowlist of Wikimedia Foundation wiki domains.
# Covers all major Wikimedia projects: Wikipedia, Wikidata, Commons, etc.
_DEFAULT_ALLOWED_DOMAINS = [
    # Wikipedia language editions
    r"(?:[a-z0-9-]+\.)?wikipedia\.org",
    # Other Wikimedia projects
    r"(?:[a-z0-9-]+\.)?wikimedia\.org",
    r"(?:[a-z0-9-]+\.)?wikidata\.org",
    r"(?:[a-z0-9-]+\.)?mediawiki\.org",
    r"(?:[a-z0-9-]+\.)?wikisource\.org",
    r"(?:[a-z0-9-]+\.)?wikiquote\.org",
    r"(?:[a-z0-9-]+\.)?wikivoyage\.org",
    r"(?:[a-z0-9-]+\.)?wiktionary\.org",
    r"(?:[a-z0-9-]+\.)?wikibooks\.org",
    r"(?:[a-z0-9-]+\.)?wikinews\.org",
    r"(?:[a-z0-9-]+\.)?wikiversity\.org",
    # Wikimedia internal infrastructure (needed for staging/test)
    r"(?:[a-z0-9-]+\.)?wikimedia\.cloud",
]

# Compile the combined regex pattern (case-insensitive).
# Subdomains are allowed (e.g., en.wikipedia.org, hi.wikipedia.org).
_ALLOWED_PATTERN = re.compile(
    r"^(?:[a-z0-9-]+\.)?(?:"
    + "|".join(_DEFAULT_ALLOWED_DOMAINS)
    + r")$",
    re.IGNORECASE,
)


def _get_allowed_domains():
    """
    Return the list of allowed domain patterns.

    Operators can extend the default allowlist via the ALLOWED_WIKI_HOSTS
    environment variable (comma-separated regex patterns).
    """
    env_override = os.environ.get("ALLOWED_WIKI_HOSTS", "").strip()
    if env_override:
        extra = [p.strip() for p in env_override.split(",") if p.strip()]
        return _DEFAULT_ALLOWED_DOMAINS + extra
    return _DEFAULT_ALLOWED_DOMAINS


def validate_wiki_url(article_url):
    """
    Validate that a URL points to an allowed Wikimedia wiki domain.

    This is the SSRF protection entry-point. Every function that accepts a
    user-supplied URL and makes an outbound HTTP request MUST call this
    function before constructing the request.

    Args:
        article_url: The full URL supplied by the user (e.g., from request
            args or JSON body).

    Returns:
        tuple: (base_url, error_response_or_None)
            - base_url (str): The scheme + netloc portion (e.g.,
              "https://en.wikipedia.org") when validation passes.
            - error_response_or_None: None on success, or a
              (jsonify_response, status_code) tuple on failure.
    """
    if not article_url or not isinstance(article_url, str):
        return None, (jsonify({"error": "A valid article URL is required"}), 400)

    article_url = article_url.strip()

    if not article_url:
        return None, (jsonify({"error": "A valid article URL is required"}), 400)

    # Only allow http:// and https:// schemes.
    if not article_url.startswith("http://") and not article_url.startswith("https://"):
        return None, (jsonify({"error": "URL must start with http:// or https://"}), 400)

    try:
        url_obj = urlparse(article_url)
    except Exception:
        return None, (jsonify({"error": "Invalid URL format"}), 400)

    if not url_obj.scheme or not url_obj.netloc:
        return None, (jsonify({"error": "Invalid URL format"}), 400)

    # Reject URLs with userinfo (user:pass@host) to prevent auth-header injection.
    if url_obj.username or url_obj.password:
        return None, (jsonify({"error": "URL must not contain credentials"}), 400)

    # Reject URLs with ports (prevents bypass via alternative ports).
    if url_obj.port is not None and url_obj.port not in (80, 443):
        return None, (jsonify({"error": "URL must use standard ports (80 or 443)"}), 400)

    # Build the compiled pattern with any env-var overrides.
    allowed_domains = _get_allowed_domains()
    allowed_pattern = re.compile(
        r"^(?:[a-z0-9-]+\.)?(?:"
        + "|".join(allowed_domains)
        + r")$",
        re.IGNORECASE,
    )

    if not allowed_pattern.match(url_obj.netloc):
        return None, (
            jsonify({
                "error": (
                    "URL domain is not allowed. Only Wikimedia Foundation wiki "
                    "domains are supported."
                )
            }),
            400,
        )

    base_url = f"{url_obj.scheme}://{url_obj.netloc}"
    return base_url, None
