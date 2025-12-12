"""
User Routes for WikiContest Application
Handles user registration, login, logout, and dashboard functionality
"""

import re
import time

from flask import Blueprint, request, jsonify, make_response, session, redirect, current_app
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies
import mwoauth

from database import db
from middleware.auth import require_auth, require_role, handle_errors, validate_json_data
from models.user import User
# Temporary storage for OAuth tokens (in-memory cache)
# This is used as a fallback when session cookies don't persist across redirects
_oauth_token_cache = {}

# Create blueprint
user_bp = Blueprint('user', __name__)

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

    # Validate input data
    if not validate_username(username):
        return jsonify({'error': 'Username must be 3-20 characters, alphanumeric and underscores only'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400

    if role not in ['user', 'admin']:
        return jsonify({'error': 'Invalid role'}), 400

    # Check if username already exists
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400

    # Create new user
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
    # Get JSON data directly
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    # Find user by email
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    try:
        # Create JWT token
        access_token = create_access_token(identity=str(user.id))

        # Create response
        response = make_response(jsonify({
            'message': 'Login successful',
            'userId': user.id,
            'username': user.username
        }))

        # Set JWT token in HTTP-only cookie
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

    # Unset JWT cookies
    unset_jwt_cookies(response)

    # Manually clear cookies to ensure they're removed across ports
    # This is important for localhost:5000 -> localhost:5173 scenarios
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

    # Get contest-wise scores
    from models.submission import Submission
    from models.contest import Contest

    contest_scores = db.session.query(
        Contest.id.label('contest_id'),
        Contest.name.label('contest_name'),
        db.func.sum(Submission.score).label('contest_score'),
        db.func.count(Submission.id).label('submission_count')
    ).join(Submission, Contest.id == Submission.contest_id).filter(
        Submission.user_id == user.id
    ).group_by(Contest.id, Contest.name).order_by(Contest.name).all()

    # Get all user's submissions grouped by contest
    submissions_query = db.session.query(
        Submission,
        Contest.name.label('contest_name')
    ).join(Contest, Submission.contest_id == Contest.id).filter(
        Submission.user_id == user.id
    ).order_by(Submission.submitted_at.desc()).all()

    # Group submissions by contest
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

    # Get contests created by user
    created_contests = Contest.query.filter_by(created_by=user.username).all()
    created_contests_data = []
    for contest in created_contests:
        contest_data = contest.to_dict()
        contest_data['submission_count'] = contest.get_submission_count()
        created_contests_data.append(contest_data)

    # Get contests where user is a jury member
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

    # Validate input data
    if not validate_username(new_username):
        return jsonify({'error': 'Username must be 3-20 characters, alphanumeric and underscores only'}), 400

    if not validate_email(new_email):
        return jsonify({'error': 'Invalid email format'}), 400

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

    # Update user data
    user.username = new_username
    user.email = new_email
    user.save()

    return jsonify({'message': 'Profile updated successfully'}), 200

# =============================================================================
# OAUTH ROUTES (Wikimedia OAuth 1.0a)
# =============================================================================

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
        # Generate OAuth request token
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
    # Get OAuth 1.0a configuration from app config (loaded from .env file)
    # These values come from the .env file: CONSUMER_KEY, CONSUMER_SECRET, OAUTH_MWURI
    consumer_key = current_app.config.get('CONSUMER_KEY')
    consumer_secret = current_app.config.get('CONSUMER_SECRET')
    mw_uri = current_app.config.get('OAUTH_MWURI', 'https://meta.wikimedia.org/w/index.php')

    # Get OAuth parameters from callback
    oauth_verifier = request.args.get('oauth_verifier')
    oauth_token = request.args.get('oauth_token')

    # Get stored request token from session (primary method)
    request_token_key = session.get('request_token')
    request_secret = session.get('request_secret')

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

    # Validate callback parameters
    if not oauth_verifier or not oauth_token:
        return jsonify({'error': 'Missing OAuth parameters'}), 400

    if not request_token_key or not request_secret:
        # Provide more detailed error message
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

        # Get user identity from Wikimedia
        identity = mwoauth.identify(mw_uri, consumer_token, access_token)

        # Extract user information
        username = identity.get('username', '')

        if not username:
            return jsonify({'error': 'Failed to get user information from Wikimedia'}), 500

        # Find or create user in database
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
            user.save()
        else:
            # Update existing user if needed
            # OAuth users might not have a password set
            pass

        # Create JWT token for the user
        access_token_jwt = create_access_token(identity=str(user.id))

        # Clear OAuth session data
        session.pop('request_token', None)
        session.pop('request_secret', None)

        # Determine redirect URL based on environment
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

    if not query or len(query) < 2:
        return jsonify({'users': []}), 200

    # Search users whose username starts with or contains the query
    users = User.query.filter(
        User.username.ilike(f'%{query}%')
    ).limit(limit).all()

    return jsonify({
        'users': [{'username': user.username, 'id': user.id} for user in users]
    }), 200
