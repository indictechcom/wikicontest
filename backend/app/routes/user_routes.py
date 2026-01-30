# pylint: disable=too-many-lines,too-many-return-statements
"""
User Routes for WikiContest Application
Handles user registration, login, logout, and dashboard functionality
"""

import re
import time

from flask import Blueprint, request, jsonify, make_response, session, redirect, current_app
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies
import mwoauth

from app.database import db
from app.middleware.auth import require_auth, require_role, handle_errors, validate_json_data
from app.models.user import User

# ------------------------------------------------------------------------
# OAUTH TOKEN CACHE
# ------------------------------------------------------------------------
# Temporary storage for OAuth tokens (in-memory cache)
# This is used as a fallback when session cookies don't persist across redirects
# When users are redirected to Wikimedia for OAuth, session cookies may not
# persist properly, so we cache tokens here as a backup mechanism
_oauth_token_cache = {}

# Create blueprint
user_bp = Blueprint('user', __name__)


# ------------------------------------------------------------------------
# VALIDATION UTILITIES
# ------------------------------------------------------------------------

def validate_email(email):
    """
    Validate email format

    Args:
        email: Email string to validate

    Returns:
        bool: True if valid email, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """
    Validate username format

    Args:
        username: Username string to validate

    Returns:
        bool: True if valid username, False otherwise
    """
    # Username should be 3-20 characters, alphanumeric and underscores only
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(pattern, username) is not None


# ------------------------------------------------------------------------
# USER REGISTRATION & AUTHENTICATION
# ------------------------------------------------------------------------

@user_bp.route('/register', methods=['POST'])
@handle_errors
@validate_json_data(['username', 'email', 'password'])
def register():
    """
    Register a new user

    Expected JSON data:
        username: Unique username (3-20 chars, alphanumeric + underscore)
        email: Valid email address
        password: Password (min 6 chars)
        role: Optional role (defaults to 'user')

    Returns:
        JSON response with success message and user ID
    """
    data = request.validated_data
    username = data['username'].strip()
    email = data['email'].strip().lower()
    password = data['password']
    role = data.get('role', 'user')

    # --- Input Validation ---
    if not validate_username(username):
        return jsonify({'error': 'Username must be 3-20 characters, alphanumeric and underscores only'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400

    # --- Role Validation ---
    # Allow only two roles via the public API for security:
    # - user: regular user (default)
    # - admin: admin-level access
    #
    # IMPORTANT SECURITY NOTE:
    # - "superadmin" role MUST NOT be created through this endpoint.
    # - Superadmin accounts should ONLY be created/updated directly in the database
    #   or via a very secure internal tool, to avoid privilege escalation.
    if role not in ['user', 'admin']:
        return jsonify({'error': 'Invalid role'}), 400

    # --- Uniqueness Checks ---
    # Check if username already exists
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400

    # --- Create User ---
    try:
        user = User(username=username, email=email, password=password, role=role)
        user.save()

        return jsonify({
            'message': 'User created successfully',
            'userId': user.id,
            'username': user.username
        }), 201

    except Exception:  # pylint: disable=broad-exception-caught
        # Log error for debugging but don't expose details to client
        return jsonify({'error': 'Failed to create user'}), 500


@user_bp.route('/login', methods=['POST'])
@handle_errors
def login():
    """
    Login user and create JWT token

    Expected JSON data:
        email: User's email address
        password: User's password

    Returns:
        JSON response with success message and JWT token in cookie
    """
    # Get JSON data directly (not using validator for login to allow flexible error handling)
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    # --- Authenticate User ---
    # Find user by email
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    try:
        # Create JWT token for authenticated session
        access_token = create_access_token(identity=str(user.id))

        # Create response with user info
        # NOTE: we also include the user's role so frontend can know if they are
        # admin / superadmin and adjust UI (like delete buttons) accordingly.
        response = make_response(jsonify({
            'message': 'Login successful',
            'userId': user.id,
            'username': user.username,
            'role': user.role
        }))

        # Set JWT token in HTTP-only cookie for security
        set_access_cookies(response, access_token)

        return response, 200

    except Exception as error:  # pylint: disable=broad-exception-caught
        # Log error for debugging
        current_app.logger.error(f"Error in login process: {str(error)}")
        return jsonify({'error': 'Login failed'}), 500


@user_bp.route('/logout', methods=['POST'])
@handle_errors
def logout():
    """
    Logout user and clear JWT token.

    This works for both regular users and OAuth users.
    It clears the JWT cookie and any OAuth session data.

    Note: Does not require authentication - allows logout even if token is invalid.

    Returns:
        JSON response with success message
    """
    # Clear OAuth session data if present (for OAuth users)
    session.pop('request_token', None)
    session.pop('request_secret', None)

    # Clear JWT token cookie (works for both regular and OAuth users)
    response = make_response(jsonify({'message': 'Logout successful'}))

    # Unset JWT cookies using Flask-JWT-Extended helper
    unset_jwt_cookies(response)

    # Manually clear cookies to ensure they're removed across ports
    # This is important for localhost:5000 -> localhost:5173 scenarios
    # where cookies need to work across different development server ports
    response.set_cookie(
        'access_token_cookie',
        value='',
        expires=0,
        httponly=True,
        samesite='Lax',
        secure=False,
        domain=None,  # None allows cookie to work across localhost ports
        path='/'
    )
    response.set_cookie(
        'csrf_access_token',
        value='',
        expires=0,
        httponly=True,
        samesite='Lax',
        secure=False,
        domain=None,
        path='/'
    )

    return response, 200


# ------------------------------------------------------------------------
# USER DASHBOARD & PROFILE
# ------------------------------------------------------------------------

@user_bp.route('/dashboard', methods=['GET'])
@require_auth
@handle_errors
def get_dashboard():
    """
    Get user dashboard data

    Returns:
        JSON response with user's dashboard information
    """
    user = request.current_user

    # Get user's total score
    total_score = user.score

    # --- Get Contest-wise Scores ---
    from app.models.submission import Submission
    from app.models.contest import Contest

    # Query submissions grouped by contest to calculate scores
    contest_scores = db.session.query(
        Contest.id.label('contest_id'),
        Contest.name.label('contest_name'),
        db.func.sum(Submission.score).label('contest_score'),
        db.func.count(Submission.id).label('submission_count')
    ).join(Submission).filter(
        Submission.user_id == user.id
    ).group_by(Contest.id, Contest.name).order_by(Contest.name).all()

    # --- Get All User's Submissions Grouped by Contest ---
    submissions_query = db.session.query(
        Submission,
        Contest.name.label('contest_name')
    ).join(Contest).filter(
        Submission.user_id == user.id
    ).order_by(Submission.submitted_at.desc()).all()

    # Group submissions by contest for organized display
    submissions_by_contest = {}
    for submission, contest_name in submissions_query:
        contest_id = submission.contest_id
        if contest_id not in submissions_by_contest:
            submissions_by_contest[contest_id] = {
                'contest_id': contest_id,
                'contest_name': contest_name,
                'submissions': []
            }
        submissions_by_contest[contest_id]['submissions'].append(submission.to_dict())

    # --- Get Contests Created by User ---
    created_contests = Contest.query.filter_by(created_by=user.username).all()
    created_contests_data = []
    for contest in created_contests:
        contest_data = contest.to_dict()
        contest_data['submission_count'] = contest.get_submission_count()
        created_contests_data.append(contest_data)

    # --- Get Contests Where User is a Jury Member ---
    jury_contests = Contest.query.filter(
        Contest.jury_members.like(f'%{user.username}%')
    ).all()
    jury_contests_data = []
    for contest in jury_contests:
        contest_data = contest.to_dict()
        contest_data['submission_count'] = contest.get_submission_count()
        jury_contests_data.append(contest_data)

    return jsonify({
        'username': user.username,
        'total_score': total_score,
        'contest_wise_scores': [
            {
                'contest_id': row.contest_id,
                'contest_name': row.contest_name,
                'contest_score': row.contest_score or 0,
                'submission_count': row.submission_count
            }
            for row in contest_scores
        ],
        'submissions_by_contest': list(submissions_by_contest.values()),
        'created_contests': created_contests_data,
        'jury_contests': jury_contests_data
    }), 200


@user_bp.route('/all', methods=['GET'])
@require_role('admin')
@handle_errors
def get_all_users():
    """
    Get all users (admin only)

    Returns:
        JSON response with list of all users
    """
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200


@user_bp.route('/profile', methods=['GET'])
@require_auth
@handle_errors
def get_profile():
    """
    Get current user's profile

    Returns:
        JSON response with user profile data
    """
    user = request.current_user
    return jsonify(user.to_dict()), 200


@user_bp.route('/profile', methods=['PUT'])
@require_auth
@handle_errors
@validate_json_data(['username', 'email'])
def update_profile():
    """
    Update current user's profile

    Expected JSON data:
        username: New username
        email: New email address

    Returns:
        JSON response with success message
    """
    user = request.current_user
    data = request.validated_data

    new_username = data['username'].strip()
    new_email = data['email'].strip().lower()

    # --- Input Validation ---
    if not validate_username(new_username):
        return jsonify({'error': 'Username must be 3-20 characters, alphanumeric and underscores only'}), 400

    if not validate_email(new_email):
        return jsonify({'error': 'Invalid email format'}), 400

    # --- Uniqueness Checks ---
    # Check if username is already taken by another user
    existing_user = User.query.filter(
        User.username == new_username,
        User.id != user.id
    ).first()
    if existing_user:
        return jsonify({'error': 'Username already exists'}), 400

    # Check if email is already taken by another user
    existing_email = User.query.filter(
        User.email == new_email,
        User.id != user.id
    ).first()
    if existing_email:
        return jsonify({'error': 'Email already exists'}), 400

    # --- Update User Data ---
    user.username = new_username
    user.email = new_email
    user.save()

    return jsonify({'message': 'Profile updated successfully'}), 200


# ------------------------------------------------------------------------
# OAUTH ROUTES (Wikimedia OAuth 1.0a)
# ------------------------------------------------------------------------

@user_bp.route('/oauth/login', methods=['GET'])
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

        # Also store in temporary cache as backup (in case session cookies don't persist)
        # This helps when redirecting to external sites where cookies might not work
        _oauth_token_cache[request_token.key] = {
            'secret': request_token.secret,
            'timestamp': time.time()
        }

        # Clean up old cache entries (older than 10 minutes)
        current_time = time.time()
        expired_keys = [k for k, v in _oauth_token_cache.items() if current_time - v['timestamp'] > 600]
        for key in expired_keys:
            _oauth_token_cache.pop(key, None)

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


@user_bp.route('/oauth/callback', methods=['GET'])
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

    # --- Fallback to Cache if Session Failed ---
    # If session doesn't have the token, try to get it from cache (fallback)
    # This handles cases where session cookies don't persist across external redirects
    if not request_token_key or not request_secret:
        if oauth_token in _oauth_token_cache:
            cached_data = _oauth_token_cache.get(oauth_token)
            if cached_data:
                request_token_key = oauth_token
                request_secret = cached_data['secret']
                current_app.logger.info('Retrieved OAuth token from cache (session cookie failed)')
                # Clean up cache entry after use
                _oauth_token_cache.pop(oauth_token, None)

    # Log session data for debugging
    current_app.logger.info(
        f'OAuth callback received - oauth_token: {oauth_token}, '
        f'oauth_verifier: {oauth_verifier}'
    )
    current_app.logger.info(
        f'Session data - request_token_key: {request_token_key}, '
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
        current_app.logger.error(f'Cache keys: {list(_oauth_token_cache.keys())}')
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

        # Log parameters before calling complete
        current_app.logger.info(f'Calling mwoauth.complete with query string: {response_qs.decode("utf-8")}')
        current_app.logger.info(f'oauth_verifier: {oauth_verifier}, oauth_token: {oauth_token}')

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


# ------------------------------------------------------------------------
# USER SEARCH & LOOKUP
# ------------------------------------------------------------------------

@user_bp.route('/search', methods=['GET'])
@handle_errors
def search_users():
    """
    Search users by username (for autocomplete)

    Query parameters:
        q: Search query string
        limit: Maximum results to return (default: 10)

    Returns:
        JSON response with list of matching usernames
    """
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)

    # Require at least 2 characters for search
    if not query or len(query) < 2:
        return jsonify({'users': []}), 200

    # Search users whose username starts with or contains the query
    users = User.query.filter(
        User.username.ilike(f'%{query}%')
    ).limit(limit).all()

    return jsonify({
        'users': [{'username': user.username, 'id': user.id} for user in users]
    }), 200


@user_bp.route('/<int:user_id>/username', methods=['GET'])
@handle_errors
def get_user_username(user_id):
    """
    Get username for a specific user ID

    This is a minimal endpoint that only returns the username,
    not any sensitive information like email or password.

    Args:
        user_id: User ID

    Returns:
        JSON response with username
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Return only non-sensitive user information
    return jsonify({
        'id': user.id,
        'username': user.username
    }), 200


# ------------------------------------------------------------------------
# TRUSTED MEMBER MANAGEMENT ROUTES
# ------------------------------------------------------------------------

@user_bp.route('/trusted-members/request', methods=['POST'])
@require_auth
@handle_errors
def request_trusted_member():
    """
    Request trusted member status (creator account request)

    This endpoint handles creator account requests for users who logged in via MediaWiki OAuth.

    Workflow:
    1. If user has >= 300 edits: automatically grant trusted member status
    2. If user has < 300 edits: require a reason and submit for superadmin review

    Only users who logged in via MediaWiki OAuth can request creator accounts.
    Superadmins don't need permission - they can create contests directly.

    Expected JSON data (for users with < 300 edits):
        reason: Explanation of why the user wants to be a creator (required if edit count < 300)

    Returns:
        JSON response with success message
    """
    user = request.current_user

    # Superadmins are automatically trusted members, no need to request
    if user.is_superadmin():
        return jsonify({
            'error': 'Superadmins are automatically trusted members and can create contests directly'
        }), 400

    # Check if already a trusted member
    if getattr(user, 'is_trusted_member', False):
        return jsonify({
            'error': 'You are already a trusted member'
        }), 400

    # Check if already requested
    if getattr(user, 'trusted_member_request', False):
        return jsonify({
            'error': 'You have already requested trusted member status. Please wait for approval.'
        }), 400

    # Check if user logged in via MediaWiki OAuth
    # Only MediaWiki OAuth users can request creator accounts
    if not user.oauth_token or not user.oauth_token_secret:
        return jsonify({
            'error': 'Only users who logged in via MediaWiki can request creator accounts. Please log in using MediaWiki OAuth.'
        }), 400

    # Get MediaWiki URI from config
    mw_uri = current_app.config.get('OAUTH_MWURI', 'https://meta.wikimedia.org/w/index.php')

    # Get user's edit count from MediaWiki API
    from app.utils import get_mediawiki_user_edit_count
    edit_count = get_mediawiki_user_edit_count(user.username, mw_uri)

    # If we couldn't fetch edit count, require reason (safer default)
    if edit_count is None:
        # Require reason if edit count cannot be determined
        data = request.get_json() or {}
        reason = data.get('reason', '').strip()

        if not reason:
            return jsonify({
                'error': 'Could not verify your edit count. Please provide a reason for requesting creator account status.',
                'requires_reason': True
            }), 400

        # Store request with reason for superadmin review
        user.trusted_member_request = True
        user.trusted_member_request_reason = reason
        user.save()

        return jsonify({
            'message': 'Creator account request submitted successfully. A superadmin will review your request.',
            'auto_approved': False
        }), 200

    # Check edit count threshold (300 edits)
    MIN_EDIT_COUNT = 300

    if edit_count >= MIN_EDIT_COUNT:
        # User has >= 300 edits: automatically grant trusted member status
        user.is_trusted_member = True
        user.trusted_member_request = False  # No need for request flag
        user.trusted_member_request_reason = None  # Clear any previous reason
        user.save()

        return jsonify({
            'message': f'Congratulations! You have {edit_count} edits. Your creator account has been automatically approved.',
            'auto_approved': True,
            'edit_count': edit_count
        }), 200

    # User has < 300 edits: require reason for superadmin review
    data = request.get_json() or {}
    reason = data.get('reason', '').strip()

    if not reason:
        return jsonify({
            'error': f'You have {edit_count} edits, which is below the minimum of {MIN_EDIT_COUNT} edits for automatic approval. Please provide a reason for requesting creator account status.',
            'requires_reason': True,
            'edit_count': edit_count,
            'min_edit_count': MIN_EDIT_COUNT
        }), 400

    # Store request with reason for superadmin review
    user.trusted_member_request = True
    user.trusted_member_request_reason = reason
    user.save()

    return jsonify({
        'message': f'Your creator account request has been submitted for review. You have {edit_count} edits (minimum {MIN_EDIT_COUNT} for automatic approval). A superadmin will review your request.',
        'auto_approved': False,
        'edit_count': edit_count
    }), 200


@user_bp.route('/trusted-members/requests', methods=['GET'])
@require_role('superadmin')
@handle_errors
def get_trusted_member_requests():
    """
    Get all pending trusted member requests (superadmin only)

    Returns list of users who have requested trusted member status.

    Returns:
        JSON response with list of pending requests
    """
    # Get all users with pending requests
    requests = User.query.filter_by(trusted_member_request=True, is_trusted_member=False).all()

    return jsonify({
        'requests': [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'requested_at': user.created_at.isoformat() if user.created_at else None,  # Using created_at as proxy
            'request_reason': getattr(user, 'trusted_member_request_reason', None)  # Include reason for review
        } for user in requests]
    }), 200


@user_bp.route('/trusted-members', methods=['GET'])
@require_role('superadmin')
@handle_errors
def get_trusted_members():
    """
    Get all trusted members (superadmin only)

    Returns list of all users who are trusted members.

    Returns:
        JSON response with list of trusted members
    """
    # Get all trusted members (excluding superadmins as they're automatically trusted)
    trusted_members = User.query.filter_by(is_trusted_member=True).all()

    # Also include superadmins in the list
    superadmins = User.query.filter_by(role='superadmin').all()

    # Combine and deduplicate
    all_trusted = {user.id: user for user in trusted_members + superadmins}

    return jsonify({
        'trusted_members': [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_superadmin': user.is_superadmin(),
            'created_at': user.created_at.isoformat() if user.created_at else None
        } for user in all_trusted.values()]
    }), 200


@user_bp.route('/trusted-members/<int:user_id>/approve', methods=['POST'])
@require_role('superadmin')
@handle_errors
def approve_trusted_member(user_id):
    """
    Approve a trusted member request (superadmin only)

    Approves a user's request to become a trusted member.
    This allows them to create contests.

    Args:
        user_id: User ID to approve

    Returns:
        JSON response with success message
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Superadmins are automatically trusted, no need to approve
    if user.is_superadmin():
        return jsonify({
            'error': 'Superadmins are automatically trusted members'
        }), 400

    # Approve the request
    user.is_trusted_member = True
    user.trusted_member_request = False  # Clear the request flag
    user.trusted_member_request_reason = None  # Clear the reason
    user.save()

    return jsonify({
        'message': f'User {user.username} has been approved as a trusted member'
    }), 200


@user_bp.route('/trusted-members/<int:user_id>/reject', methods=['POST'])
@require_role('superadmin')
@handle_errors
def reject_trusted_member(user_id):
    """
    Reject a trusted member request (superadmin only)

    Rejects a user's request to become a trusted member.
    The request flag is cleared, but they can request again later.

    Args:
        user_id: User ID to reject

    Returns:
        JSON response with success message
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Clear the request flag and reason (rejection)
    user.trusted_member_request = False
    user.trusted_member_request_reason = None
    user.save()

    return jsonify({
        'message': f'Trusted member request for {user.username} has been rejected'
    }), 200


@user_bp.route('/trusted-members/<int:user_id>/add', methods=['POST'])
@require_role('superadmin')
@handle_errors
def add_trusted_member(user_id):
    """
    Manually add a user as trusted member (superadmin only)

    Allows superadmin to directly add a user as trusted member
    without requiring a request from the user.

    Args:
        user_id: User ID to add as trusted member

    Returns:
        JSON response with success message
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Superadmins are automatically trusted, no need to add
    if user.is_superadmin():
        return jsonify({
            'error': 'Superadmins are automatically trusted members'
        }), 400

    # Add as trusted member
    user.is_trusted_member = True
    user.trusted_member_request = False  # Clear any pending request
    user.trusted_member_request_reason = None  # Clear any reason
    user.save()

    return jsonify({
        'message': f'User {user.username} has been added as a trusted member'
    }), 200


@user_bp.route('/trusted-members/<int:user_id>/remove', methods=['POST'])
@require_role('superadmin')
@handle_errors
def remove_trusted_member(user_id):
    """
    Remove trusted member status from a user (superadmin only)

    Removes a user's trusted member status.
    They will no longer be able to create contests (unless they're superadmin).

    Args:
        user_id: User ID to remove from trusted members

    Returns:
        JSON response with success message
    """
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Cannot remove superadmin status (they're automatically trusted)
    if user.is_superadmin():
        return jsonify({
            'error': 'Cannot remove trusted member status from superadmin'
        }), 400

    # Remove trusted member status
    user.is_trusted_member = False
    user.save()

    return jsonify({
        'message': f'User {user.username} has been removed from trusted members'
    }), 200