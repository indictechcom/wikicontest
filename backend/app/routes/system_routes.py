"""
System & authentication routes for WikiEval Application.

Holds the application-level endpoints that are not part of a feature
blueprint (user/contest/submission): cookie/session checks, frontend
static serving, health checks, OAuth callback bridging, and OAuth config
diagnostics.

These were previously defined directly on the Flask app in app/__init__.py.
They are now exposed through a blueprint with no URL prefix so that all
endpoint URLs and methods remain identical.
"""

import os

from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt_identity,
    jwt_required,
)
from flask_jwt_extended.exceptions import JWTDecodeError, NoAuthorizationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text as sql_text

from app.database import db
from app.models.user import User

# Create blueprint (no url_prefix — endpoints keep their original paths)
system_bp = Blueprint('system', __name__)


# ---------------------------------------------------------------------------
# AUTHENTICATION ENDPOINTS
# ---------------------------------------------------------------------------

@system_bp.route('/api/cookie', methods=['GET'])
def check_cookie():
    """
    Check if user is authenticated via JWT cookie.

    This endpoint is used by the frontend to verify if a user is currently
    logged in. It reads the JWT token from the HTTP-only cookie and returns
    the user's basic information if the token is valid.

    Returns:
        JSON: User information if authenticated, error if not
    """
    try:
        # Verify the JWT token from the cookie
        # Use optional=False to ensure token MUST be present and valid
        verify_jwt_in_request(optional=False)
        user_id = get_jwt_identity()

        # Validate user_id exists and is valid
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401

        # Query User from Database
        # CRITICAL: Query directly from database using raw SQL to bypass ALL ORM caching
        # This ensures we get the absolute latest role from the database
        # Include is_trusted_member and trusted_member_request_status to check if user can create contests
        direct_query = db.session.execute(
            sql_text('SELECT id, username, email, role, is_trusted_member, trusted_member_request_status FROM users WHERE id = :user_id'),
            {'user_id': int(user_id)}
        ).fetchone()

        if not direct_query:
            return jsonify({'error': 'User not found'}), 401

        # Extract data from direct database query (most reliable - no ORM caching)
        db_user_id = direct_query[0]
        db_username = direct_query[1]
        db_email = direct_query[2]
        db_role = direct_query[3]
        db_is_trusted_member = direct_query[4] if len(direct_query) > 4 else False
        db_trusted_member_request_status = direct_query[5] if len(direct_query) > 5 else None

        # Normalize role: ensure it's a string, trimmed, and lowercase
        role_value = str(db_role).strip().lower() if db_role else 'user'

        # Build response using data directly from database (no ORM objects)
        # Include trusted member status for frontend permission checks
        # Superadmins are automatically trusted, so check both role and is_trusted_member
        is_trusted = bool(db_is_trusted_member) or role_value == 'superadmin'

        response_data = {
            'userId': db_user_id,
            'username': db_username,
            'email': db_email,
            # Use role directly from database query - most reliable source
            'role': role_value,
            # Include trusted member status so frontend can check if user can create contests
            'is_trusted_member': is_trusted,
            # Include trusted member request status for pending/rejected state tracking
            'trusted_member_request': db_trusted_member_request_status is not None,
            'trusted_member_request_status': db_trusted_member_request_status
        }

        return jsonify(response_data), 200, {'Cache-Control': 'private, no-store'}

    except (JWTDecodeError, NoAuthorizationError):
        # No token or invalid token - user is definitely not logged in
        return jsonify({'error': 'You are not logged in'}), 401
    except (SQLAlchemyError, RuntimeError, AttributeError, ValueError) as error:
        # Catch database errors, Flask context errors, or other specific errors
        # Log for debugging but don't expose error to client
        try:
            current_app.logger.debug(f'Cookie check failed: {str(error)}')
        except (AttributeError, RuntimeError):
            # Logger might not be available or Flask context missing
            pass
        return jsonify({'error': 'You are not logged in'}), 401


# ---------------------------------------------------------------------------
# FRONTEND SERVING ROUTES
# ---------------------------------------------------------------------------

@system_bp.route('/')
def index():
    """
    Serve the main frontend page.

    Serves the Vue.js application.
    In production, serves from frontend/dist directory (built Vue.js app).
    """
    # Calculate workspace root (backend/app/ -> backend/ -> workspace/)
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    dist_path = os.path.join(workspace_root, 'frontend', 'dist')

    if os.path.exists(dist_path):
        # Production - serve built Vue.js files
        return send_from_directory(dist_path, 'index.html')

    # Fallback - development mode
    frontend_path = os.path.join(workspace_root, 'frontend')
    return send_from_directory(frontend_path, 'index.html')


@system_bp.route('/<path:filename>')
def serve_static(filename):
    """
    Serve static files from frontend directory.

    In production, serves from frontend/dist directory (built Vue.js app).
    In development, serves from frontend directory (Vite dev server handles Vue.js).
    """
    # Skip API routes to avoid conflict with API endpoints
    if filename.startswith('api/') or filename.startswith('oauth/'):
        return jsonify({'error': 'Endpoint not found'}), 404

    # Calculate workspace root (backend/app/ -> backend/ -> workspace/)
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    dist_path = os.path.join(workspace_root, 'frontend', 'dist')

    if os.path.exists(dist_path):
        # Production - serve from dist
        try:
            return send_from_directory(dist_path, filename)
        except Exception:
            # If file not found in dist, serve index.html (for Vue Router)
            # This enables client-side routing in production
            if not filename.startswith('api/') and not filename.startswith('oauth/'):
                return send_from_directory(dist_path, 'index.html')
            raise
    # Development - serve from frontend directory
    frontend_path = os.path.join(workspace_root, 'frontend')
    return send_from_directory(frontend_path, filename)


# ---------------------------------------------------------------------------
# SYSTEM ENDPOINTS
# ---------------------------------------------------------------------------

@system_bp.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    This endpoint can be used by monitoring systems to check if the
    application is running and responding to requests.

    Returns:
        JSON: Application status information
    """
    try:
        db.session.execute(sql_text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'message': 'WikiEval API is running',
            'version': '1.0.0'
        }), 200
    except Exception:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'message': 'WikiEval API is running',
            'version': '1.0.0'
        }), 503


@system_bp.route('/oauth/callback', methods=['GET'])
def oauth_callback_redirect():
    """
    Redirect /oauth/callback to the blueprint handler at /api/user/oauth/callback.

    The Toolforge OAuth consumer is registered with callback URL
    https://wikieval.toolforge.org/oauth/callback, but the actual handler
    lives at /api/user/oauth/callback (the user_bp blueprint).
    This route bridges the two by forwarding all query parameters.
    """
    from flask import redirect
    query_string = request.query_string.decode('utf-8')
    target = '/api/user/oauth/callback'
    if query_string:
        target = f'{target}?{query_string}'
    return redirect(target, code=302)


@system_bp.route('/api/oauth/config', methods=['GET'])
@jwt_required()
def oauth_config_check():
    """
    Diagnostic endpoint to check OAuth configuration.

    This helps verify that OAuth is properly configured and shows
    what callback URL will be used. Useful for troubleshooting.
    Admin access required.

    Returns:
        JSON: OAuth configuration details (without secrets)
    """
    user_id = get_jwt_identity()
    current_user = db.session.get(User, int(user_id))
    if not current_user or not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    consumer_key = current_app.config.get('CONSUMER_KEY', '')
    consumer_secret = current_app.config.get('CONSUMER_SECRET', '')
    mw_uri = current_app.config.get('OAUTH_MWURI', 'https://meta.wikimedia.org/w/index.php')
    use_oob = current_app.config.get('OAUTH_USE_OOB', False)
    custom_callback_path = current_app.config.get('OAUTH_CALLBACK_PATH', None)

    # Build callback URL based on environment
    # For local development: http://localhost:5000/api/user/oauth/callback
    # For Toolforge: https://wikieval.toolforge.org/oauth/callback
    # (if OAUTH_CALLBACK_PATH is set)
    scheme = request.scheme
    host = request.host
    if custom_callback_path:
        callback_url = f"{scheme}://{host}{custom_callback_path}"
    else:
        # Default callback URL for local development
        callback_url = f"{scheme}://{host}/api/user/oauth/callback"

    # Build instruction message for callback URL registration
    callback_instruction = (
        f'Your OAuth consumer must be registered with this exact '
        f'callback URL: {callback_url}'
    )

    return jsonify({
        'oauth_configured': bool(consumer_key and consumer_secret),
        'consumer_key': consumer_key[:10] + '...' if consumer_key else 'NOT SET',
        'consumer_secret_set': bool(consumer_secret),
        'mw_uri': mw_uri,
        'use_oob': use_oob,
        'callback_url': callback_url,
        'custom_callback_path': custom_callback_path,
        'instructions': {
            'if_use_oob_true': 'Your OAuth consumer must be registered with "oob" (out-of-band)',
            'if_use_oob_false': callback_instruction,
            'check_registration': (
                'Go to https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration '
                'to verify your consumer settings'
            )
        }
    }), 200
