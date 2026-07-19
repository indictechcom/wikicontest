"""
MediaWiki API Client for WikiEval Application.

Provides a centralized interface for all MediaWiki API interactions,
handling authentication, headers, timeouts, and error parsing consistently.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class MediaWikiClient:
    """Centralized client for MediaWiki API requests.

    Wraps common request/response patterns to reduce duplication across
    utility functions and provide a single point for mocking in tests.
    """

    def __init__(
        self,
        timeout: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        # Lazy import to avoid circular dependency: app.utils -> app.services.mediawiki -> app.utils
        from app.utils import get_mediawiki_headers, MEDIAWIKI_API_TIMEOUT
        self.timeout = timeout if timeout is not None else MEDIAWIKI_API_TIMEOUT
        self.headers = headers if headers is not None else get_mediawiki_headers()

    def get(
        self,
        api_url: str,
        params: Optional[Dict[str, Any]] = None,
        auth: Optional[Any] = None,
        timeout: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make a GET request to the MediaWiki API.

        Args:
            api_url: Full API endpoint URL.
            params: Query parameters for the request.
            auth: Optional OAuth1 auth object.
            timeout: Optional override for request timeout.

        Returns:
            Parsed JSON response dict, or None on failure.
        """
        try:
            response = requests.get(
                api_url,
                params=params,
                auth=auth,
                headers=self.headers,
                timeout=timeout or self.timeout,
            )
        except requests.RequestException as exc:
            logger.warning("MediaWiki GET failed: %s", exc)
            return None

        if response.status_code != 200:
            logger.warning(
                "MediaWiki GET HTTP %s for %s", response.status_code, api_url
            )
            return None

        try:
            data = response.json()
        except ValueError as exc:
            logger.warning("MediaWiki GET JSON parse error: %s", exc)
            return None

        if "error" in data:
            logger.warning(
                "MediaWiki GET API error: %s",
                data["error"].get("info", "Unknown error"),
            )
            return None

        return data

    def post(
        self,
        api_url: str,
        data: Optional[Dict[str, Any]] = None,
        auth: Optional[Any] = None,
        timeout: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make a POST request to the MediaWiki API.

        Args:
            api_url: Full API endpoint URL.
            data: Form data for the request body.
            auth: Optional OAuth1 auth object.
            timeout: Optional override for request timeout.

        Returns:
            Parsed JSON response dict, or None on failure.
        """
        try:
            response = requests.post(
                api_url,
                data=data,
                auth=auth,
                headers=self.headers,
                timeout=timeout or self.timeout,
            )
        except requests.RequestException as exc:
            logger.warning("MediaWiki POST failed: %s", exc)
            return None

        if response.status_code != 200:
            logger.warning(
                "MediaWiki POST HTTP %s for %s: %s",
                response.status_code,
                api_url,
                response.text[:500],
            )
            return None

        try:
            data = response.json()
        except ValueError as exc:
            logger.warning("MediaWiki POST JSON parse error: %s", exc)
            return None

        if "error" in data:
            logger.warning(
                "MediaWiki POST API error: %s",
                data["error"].get("info", "Unknown error"),
            )
            return None

        return data
