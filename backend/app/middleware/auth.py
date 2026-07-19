"""
Authentication utilities and middleware for WikiContest Application
Handles JWT token management and user authentication
"""

from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    verify_jwt_in_request,
    get_jwt
)
from app.database import db
from app.models.user import User


# ------------------------------------------------------------------------
# USER AUTHENTICATION UTILITIES
# ------------------------------------------------------------------------

def get_current_user():
    """
    Get the current authenticated user from JWT token

    Returns:
        User: Current user instance or None if not authenticated
    """
    try:
        # Verify JWT token exists and is valid in current request
        verify_jwt_in_request()

        # Extract user ID from JWT claims
        user_id = get_jwt_identity()

        # Convert string user_id back to integer for database query
        # JWT stores identity as string, but database expects integer
        return db.session.get(User, int(user_id))
    except Exception:
        # Return None if token is invalid, expired, or missing
        return None


# ------------------------------------------------------------------------
# BASIC AUTHENTICATION DECORATORS
# ------------------------------------------------------------------------

def require_auth(f):
    """
    Decorator to require authentication for a route

    Args:
        f: Function to decorate

    Returns:
        Decorated function that requires authentication
    """
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        # Fetch authenticated user from JWT token
        user = get_current_user()
        if not user:
            # User not found in database (deleted user with valid token)
            return jsonify({'error': 'Invalid user'}), 401

        # Attach user to request context for easy access in route handlers
        request.current_user = user
        return f(*args, **kwargs)

    return decorated_function


def require_role(roles):
    """
    Decorator to require specific roles for a route

    Args:
        roles: List of allowed roles or single role string

    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            # Authenticate user first
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Invalid user'}), 401

            # Normalize roles to list format for consistent checking
            if isinstance(roles, str):
                allowed_roles = [roles]
            else:
                allowed_roles = roles

            # Check if user has required role
            # Superadmin role is strictly enforced - only superadmins can access superadmin-only endpoints
            # Admins can bypass other role checks (like 'admin' role) but NOT superadmin
            if user.role not in allowed_roles:
                # Special case: if 'superadmin' is required, only superadmins can access
                # Admins do NOT bypass superadmin requirement
                if 'superadmin' in allowed_roles:
                    return jsonify({'error': 'Insufficient permissions'}), 403
                # For other roles (like 'admin'), admins can bypass
                if not user.is_admin():
                    return jsonify({'error': 'Insufficient permissions'}), 403

            # Attach user to request context
            request.current_user = user
            return f(*args, **kwargs)

        return decorated_function
    return decorator


# ------------------------------------------------------------------------
# SUBMISSION-SPECIFIC PERMISSION DECORATORS
# ------------------------------------------------------------------------

def require_submission_permission(permission_type):
    """
    Decorator to require specific submission permissions

    Args:
        permission_type: Type of permission ('owner', 'jury', 'view')

    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            # Authenticate user
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Invalid user'}), 401

            # Extract submission_id from URL route parameters
            submission_id = kwargs.get('submission_id')
            if not submission_id:
                return jsonify({'error': 'Submission ID required'}), 400

            # Fetch submission from database
            from app.models.submission import Submission
            submission = db.session.get(Submission, submission_id)
            if not submission:
                return jsonify({'error': 'Submission not found'}), 404

            # Check permissions based on requested permission type
            has_permission = False

            if permission_type == 'owner':
                # Only submission owner or admin can access
                has_permission = (submission.user_id == user.id) or user.is_admin()
            elif permission_type == 'jury':
                # Only jury members who can judge this submission
                has_permission = submission.can_be_judged_by(user)
            elif permission_type == 'view':
                # Anyone with view permission (jury, organizers, owner)
                has_permission = submission.can_be_viewed_by(user)

            if not has_permission:
                return jsonify({'error': 'Insufficient permissions for this submission'}), 403

            # Attach both user and submission to request context
            request.current_user = user
            request.current_submission = submission
            return f(*args, **kwargs)

        return decorated_function
    return decorator


# ------------------------------------------------------------------------
# REQUEST VALIDATION DECORATORS
# ------------------------------------------------------------------------

def validate_json_data(required_fields):
    """
    Decorator to validate JSON data in request

    Args:
        required_fields: List of required field names

    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Ensure request content-type is JSON
            if not request.is_json:
                return jsonify({'error': 'Request must be JSON'}), 400

            # Parse JSON body
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400

            # Validate all required fields are present
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400

            # Attach validated data to request context for easy access
            request.validated_data = data
            return f(*args, **kwargs)

        return decorated_function
    return decorator


# ------------------------------------------------------------------------
# ERROR HANDLING DECORATOR
# ------------------------------------------------------------------------

def handle_errors(f):
    """
    Decorator to handle common errors in route functions

    Args:
        f: Function to decorate

    Returns:
        Decorated function with error handling
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Execute the wrapped function
            return f(*args, **kwargs)
        except ValueError as e:
            # Handle validation errors (400 Bad Request)
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            # Log unexpected errors for debugging
            current_app.logger.error(f"Error in {f.__name__}: {str(e)}")
            # Return generic error to avoid exposing internal details
            return jsonify({'error': 'Internal server error'}), 500

    return decorated_function