"""
OAuth routes for WikiContest Application.

Handles Wikimedia OAuth 1.0a login initiation and callback. Extracted from
the original monolithic user_routes.py. Registered at /api/user along with
the other user blueprints.
"""

from flask import Blueprint, request, jsonify, make_response, redirect, session, current_app
from flask_jwt_extended import create_access_token, set_access_cookies
import mwoauth

from app.extensions import limiter
from app.middleware.auth import handle_errors
from app.models.user import User
from app.models.oauth_token_cache import OAuthTokenCache

# Create blueprint
oauth_bp = Blueprint('oauth', __name__)


@oauth_bp.route('/oauth/login', methods=['GET'])
@limiter.limit("10/minute")
@handle_errors
def oauth_login():
    """
    Initiate OAuth login with Wikimedia.

    This route starts the OAuth 1.0a authentication flow with Wikimedia.
    It uses the OAuth consumer credentials from the .env file.

    Returns:
        Redirect to Wikimedia OAuth authorization page
    """
    # --- Get OAuth Configuration ---
    # Get OAuth 1.0a configuration from app config (loaded from .env file)
    # These values come from the .env file: CONSUMER_KEY, CONSUMER_SECRET, OAUTH_MWURI
    consumer_key = current_app.config.get('CONSUMER_KEY')
    consumer_secret = current_app.config.get('CONSUMER_SECRET')
    mw_uri = current_app.config.get('OAUTH_MWURI', 'https://meta.wikimedia.org/w/index.php')

    # Check if OAuth is configured
    if not consumer_key or not consumer_secret:
        return jsonify({
            'error': 'OAuth not configured. Please set CONSUMER_KEY and CONSUMER_SECRET in .env file'
        }), 500

    # Log OAuth configuration for debugging
    current_app.logger.info(f'OAuth login initiated - Consumer Key: {consumer_key[:10]}...')
    current_app.logger.info(f'OAuth MW URI: {mw_uri}')

    try:
        # --- Build Callback URL ---
        # The callback URL must match exactly what's registered in OAuth consumer
        # Build absolute callback URL from request
        # Use request.scheme and request.host to build proper absolute URL
        scheme = request.scheme  # 'http' or 'https'
        host = request.host  # '127.0.0.1:5000' or domain name

        # For local development, ensure we use 'localhost' not '127.0.0.1'
        # OAuth consumer is registered with 'localhost:5000', so we must use that exact format
        if '127.0.0.1' in host or (host.startswith('localhost') and ':' not in host):
            # Extract port if present
            port = ':5000'  # Default port
            if ':' in host:
                port = ':' + host.split(':')[1]
            # Force localhost for local development to match OAuth consumer registration
            host = f'localhost{port}'

        # Check if we should use a custom callback path (e.g., for Toolforge)
        # Toolforge OAuth consumer is registered with /oauth/callback
        # Regular deployment uses /api/user/oauth/callback
        # For local development: http://localhost:5000/api/user/oauth/callback
        custom_callback_path = current_app.config.get('OAUTH_CALLBACK_PATH', None)
        if custom_callback_path:
            # Use custom callback path (e.g., /oauth/callback for Toolforge)
            callback_url = f"{scheme}://{host}{custom_callback_path}"
        else:
            # Use default blueprint route path
            # This will be: http://localhost:5000/api/user/oauth/callback for local development
            callback_url = f"{scheme}://{host}/api/user/oauth/callback"

        # Log the exact callback URL being used for debugging
        current_app.logger.info(f'Built callback URL: {callback_url}')
        current_app.logger.info(
            f'Request host: {request.host}, Scheme: {scheme}, Final host: {host}'
        )

        # --- Determine Callback Parameter ---
        # Check if OAuth consumer is registered with "oob" (out-of-band)
        # If your OAuth consumer was registered with "oob", you must use "oob" here
        # Otherwise, use the callback URL that matches your registration
        # Most web applications should register with a callback URL, not "oob"
        use_oob = current_app.config.get('OAUTH_USE_OOB', False)

        if use_oob:
            # Use "oob" for out-of-band (manual verification code entry)
            # This is required if OAuth consumer was registered with "oob"
            callback_param = "oob"
            current_app.logger.info('Using OAuth callback: oob (out-of-band)')
            current_app.logger.warning(
                'OAuth consumer registered with "oob" - '
                'user will need to manually enter verification code'
            )
        else:
            # Use the callback URL for automatic redirect
            # This must match exactly what was registered in OAuth consumer
            callback_param = callback_url
            current_app.logger.info(f'Using OAuth callback URL: {callback_url}')
            current_app.logger.info(
                f'IMPORTANT: Make sure your OAuth consumer is registered with '
                f'this exact callback URL: {callback_url}'
            )

        # --- Initiate OAuth Flow ---
        # Create OAuth consumer
        consumer_token = mwoauth.ConsumerToken(consumer_key, consumer_secret)

        # Get request token from Wikimedia
        # The callback parameter is required and must match OAuth consumer registration exactly
        # If registered with "oob", use "oob". If registered with URL, use that exact URL
        redirect_url, request_token = mwoauth.initiate(
            mw_uri,
            consumer_token,
            callback=callback_param
        )

        # --- Store Request Token ---
        # Store request token in session for later verification
        session['request_token'] = request_token.key
        session['request_secret'] = request_token.secret

        # Also store in database-backed cache as backup (in case session cookies
        # don't persist across the cross-site redirect to Wikimedia).
        # Uses a DB table instead of in-memory dict so tokens survive across
        # multiple Gunicorn workers (each worker has its own memory space).
        OAuthTokenCache.store(request_token.key, request_token.secret)

        # Opportunistically clean up expired entries
        try:
            OAuthTokenCache.cleanup_expired()
        except Exception:  # pylint: disable=broad-exception-caught
            # Cleanup failure should never block the login flow
            pass

        # Explicitly save session before redirect to ensure it persists
        # This is critical for OAuth flow where we redirect to external site
        session.permanent = True  # Make session persistent
        session.modified = True  # Mark session as modified to ensure it's saved

        # Log session storage for debugging
        current_app.logger.info(f'Session stored - request_token: {request_token.key[:10]}...')
        current_app.logger.info(f'Session keys: {list(session.keys())}')
        current_app.logger.info('Token also cached as backup')

        # Create response with redirect to ensure session cookie is set
        response = make_response(redirect(redirect_url))

        # Redirect user to Wikimedia for authorization
        return response

    except Exception as error:  # pylint: disable=broad-exception-caught
        # OAuth can fail in many ways, so we catch all exceptions
        current_app.logger.error(f'OAuth initiation error: {str(error)}')
        return jsonify({
            'error': 'Failed to initiate OAuth login',
            'details': str(error)
        }), 500


@oauth_bp.route('/oauth/callback', methods=['GET'])
@handle_errors
def oauth_callback():
    """
    Handle OAuth callback from Wikimedia.

    This route is called by Wikimedia after the user authorizes the application.
    It exchanges the request token for an access token and creates/updates the user.

    Query parameters:
        oauth_verifier: Verification code from Wikimedia
        oauth_token: Request token (should match session)

    Returns:
        Redirect to frontend with success message or error
    """
    # --- Get OAuth Configuration ---
    # Get OAuth 1.0a configuration from app config (loaded from .env file)
    # These values come from the .env file: CONSUMER_KEY, CONSUMER_SECRET, OAUTH_MWURI
    consumer_key = current_app.config.get('CONSUMER_KEY')
    consumer_secret = current_app.config.get('CONSUMER_SECRET')
    mw_uri = current_app.config.get('OAUTH_MWURI', 'https://meta.wikimedia.org/w/index.php')

    # --- Get OAuth Parameters from Callback ---
    oauth_verifier = request.args.get('oauth_verifier')
    oauth_token = request.args.get('oauth_token')

    # Get stored request token from session (primary method)
    request_token_key = session.get('request_token')
    request_secret = session.get('request_secret')

    # --- Fallback to DB Cache if Session Failed ---
    # If session doesn't have the token, try to get it from database cache.
    # This handles cases where session cookies don't persist across external redirects,
    # or where the session was stored by a different Gunicorn worker.
    if not request_token_key or not request_secret:
        cached_secret = OAuthTokenCache.retrieve_and_delete(oauth_token)
        if cached_secret:
            request_token_key = oauth_token
            request_secret = cached_secret
            current_app.logger.info('Retrieved OAuth token from DB cache (session cookie failed)')

    # Log session data for debugging (tokens masked to avoid log exposure)
    def _mask(value):
        if not value:
            return value
        return f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"

    current_app.logger.info(
        f'OAuth callback received - oauth_token: {_mask(oauth_token)}, '
        f'oauth_verifier: {_mask(oauth_verifier)}'
    )
    current_app.logger.info(
        f'Session data - request_token_key: {_mask(request_token_key)}, '
        f'request_secret: {bool(request_secret)}'
    )
    current_app.logger.info(f'Session keys: {list(session.keys())}')

    # --- Validate Callback Parameters ---
    if not oauth_verifier or not oauth_token:
        return jsonify({'error': 'Missing OAuth parameters'}), 400

    if not request_token_key or not request_secret:
        # Provide more detailed error message for debugging
        current_app.logger.error('OAuth session expired - session data missing')
        current_app.logger.error(f'Available session keys: {list(session.keys())}')
        return jsonify({
            'error': 'OAuth session expired. Please try again.',
            'details': (
                'Session data was not found. Make sure cookies are enabled '
                'and you\'re using the same browser session.'
            )
        }), 400

    if oauth_token != request_token_key:
        return jsonify({'error': 'Invalid OAuth token'}), 400

    try:
        # --- Exchange Request Token for Access Token ---
        # Create consumer and request tokens
        consumer_token = mwoauth.ConsumerToken(consumer_key, consumer_secret)
        request_token = mwoauth.RequestToken(request_token_key, request_secret)

        # Exchange request token for access token
        # mwoauth.complete expects the full query string as BYTES, not a string
        # request.query_string is already bytes, which is what we need
        response_qs = request.query_string

        # Log parameters before calling complete (query string masked to avoid token exposure)
        current_app.logger.info(
            f'Calling mwoauth.complete with query string length: {len(response_qs)} bytes'
        )
        current_app.logger.info(
            f'oauth_verifier: {_mask(oauth_verifier)}, oauth_token: {_mask(oauth_token)}'
        )

        access_token = mwoauth.complete(
            mw_uri,
            consumer_token,
            request_token,
            response_qs  # Pass the full query string as bytes (not decoded)
        )

        # --- Get User Identity from Wikimedia ---
        identity = mwoauth.identify(mw_uri, consumer_token, access_token)

        # Extract user information
        username = identity.get('username', '')

        if not username:
            return jsonify({'error': 'Failed to get user information from Wikimedia'}), 500

        # --- Find or Create User in Database ---
        # Use username as the unique identifier
        user = User.query.filter_by(username=username).first()

        if not user:
            # Create new user from OAuth
            # OAuth users don't need a password, but User model requires one
            # Generate a random secure password that will never be used
            import secrets
            random_password = secrets.token_urlsafe(32)
            # User.__init__ will automatically hash the password via set_password
            user = User(
                username=username,
                email=f'{username}@wikimedia.oauth',  # Placeholder email
                password=random_password,  # Random password (OAuth users won't use it)
                role='user'
            )
            # Store OAuth tokens for MediaWiki API editing (template enforcement)
            user.oauth_token = access_token.key
            user.oauth_token_secret = access_token.secret
            user.save()
        else:
            # Update existing user's OAuth tokens
            # Store the new OAuth tokens each time user authenticates
            # This ensures we always have valid, up-to-date tokens for MediaWiki editing
            user.oauth_token = access_token.key
            user.oauth_token_secret = access_token.secret
            user.save()

        # --- Create JWT Token ---
        # Create JWT token for the user
        access_token_jwt = create_access_token(identity=str(user.id))

        # Clear OAuth session data
        session.pop('request_token', None)
        session.pop('request_secret', None)

        # --- Determine Redirect URL ---
        # IMPORTANT: OAuth callback URL is fixed at http://localhost:5000/api/user/oauth/callback
        # But we should always redirect to Vue.js dev server (localhost:5173) after OAuth
        # This ensures the Vue.js app can process the oauth_success parameter

        # Check for frontend URL in environment variable (for production)
        frontend_url = current_app.config.get('FRONTEND_URL')

        if frontend_url:
            # Production: use configured frontend URL
            redirect_url = f"{frontend_url}/?oauth_success=true"
        else:
            # Development: Always redirect to Vue.js dev server
            # This ensures the Vue.js app loads properly and can process OAuth callback
            redirect_url = 'http://localhost:5173/?oauth_success=true'

        # --- Create Response with JWT Cookie ---
        # Create response with redirect to frontend
        # Always use external redirect (full URL) to ensure proper cookie handling
        response = make_response(redirect(redirect_url, code=302))

        # Set JWT token in HTTP-only cookie
        # Important: For cross-port cookies (localhost:5000 -> localhost:5173)
        # The cookie needs to work across different ports on localhost
        # Flask-JWT-Extended's set_access_cookies handles this automatically
        # with the JWT_COOKIE_SECURE=False and proper CORS configuration
        set_access_cookies(response, access_token_jwt)

        return response

    except Exception as error:  # pylint: disable=broad-exception-caught
        # OAuth can fail in many ways, so we catch all exceptions
        current_app.logger.error(f'OAuth callback error: {str(error)}')
        return jsonify({
            'error': 'OAuth authentication failed',
            'details': str(error)
        }), 500
