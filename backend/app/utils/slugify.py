"""
Slug generation utility for WikiEval Application.
Converts contest names to URL-safe slugs.
"""

import re


def generate_slug(text):
    """
    Convert a contest name into a URL-safe slug.

    Mirrors the legacy frontend slugify utility so that backfills and
    newly generated slugs are consistent with existing frontend behaviour.

    Parameters:
        text (str): Contest name to slugify.

    Returns:
        str: URL-safe slug (lowercase, hyphens, alphanumeric + hyphens only).
    """
    if not text:
        return ''
    slug = text.lower().strip()
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'[^\w\-]+', '', slug)
    slug = re.sub(r'\-\-+', '-', slug)
    return slug.strip('-')
