"""Shared error-handling utilities for WikiEval routes.

Provides a single helper for returning sanitized JSON error responses
while logging full exception details server-side. This prevents accidental
leakage of internal error information (SQL errors, tracebacks, etc.) to
clients in production.
"""

from flask import jsonify, current_app
import traceback


def safe_error_response(message, exc=None, status=500):
    """
    Create a sanitized JSON error response while recording exception details server-side.
    
    Parameters:
        message: User-facing error message without internal details.
        exc: Optional exception to include in server-side logging.
        status: HTTP status code for the response.
    
    Returns:
        A tuple containing the JSON error response and HTTP status code.
    """
    if exc is not None:
        try:
            current_app.logger.error(
                "%s: %s\n%s", message, str(exc), traceback.format_exc()
            )
        except Exception:  # pylint: disable=broad-exception-caught
            pass
    return jsonify({"error": message}), status
