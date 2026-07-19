"""
Authentication routes for WikiContest Application.

Handles user registration, login, and logout. Extracted from the original
monolithic user_routes.py. Registered at /api/user along with the other
user blueprints.
"""

from flask import Blueprint, request, jsonify, make_response, session, current_app
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies

from app.database import db
from app.extensions import limiter
from app.middleware.auth import require_auth, handle_errors, validate_json_data
from app.models.user import User
from app.routes._user_helpers import validate_email, validate_username

# Create blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5/minute")
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


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10/minute")
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


@auth_bp.route('/logout', methods=['POST'])
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
