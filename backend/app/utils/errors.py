"""Shared error-handling utilities for WikiContest routes.

Provides a single helper for returning sanitized JSON error responses
while logging full exception details server-side. This prevents accidental
leakage of internal error information (SQL errors, tracebacks, etc.) to
clients in production.
"""

from flask import jsonify, current_app
import traceback


def safe_error_response(message, exc=None, status=500):
    """Return a sanitized JSON error response.

    Logs the full exception details server-side but sends only the generic
    message to the client.

    Args:
        message: User-facing error message (no internal details).
        exc: Optional exception instance for server-side logging.
        status: HTTP status code (default 500).

    Returns:
        Flask JSON response tuple: (jsonify({"error": message}), status)
    """
    if exc is not None:
        try:
            current_app.logger.error(
                "%s: %s\n%s", message, str(exc), traceback.format_exc()
            )
        except Exception:  # pylint: disable=broad-exception-caught
            pass
    return jsonify({"error": message}), status
