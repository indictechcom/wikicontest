"""
Authentication utilities and middleware for WikiEval Application
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
    Retrieve the authenticated user for the current request.
    
    Returns:
        User | None: The authenticated user, or None if the JWT is invalid,
            missing, or the user cannot be loaded.
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
    Decorate a route handler to require an authenticated user.
    
    Parameters:
        f: The route handler to protect.
    
    Returns:
        A decorated route handler that returns a 401 response when the authenticated user cannot be found.
    """
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        # Fetch authenticated user from JWT token
        """
        Authenticate the request and make the current user available to the wrapped route handler.
        
        Returns:
            The wrapped handler's response, or a 401 response if the authenticated user
            cannot be found.
        """
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
    Create a decorator that restricts route access by user role.
    
    Args:
        roles: A role name or iterable of permitted role names. Administrators
            may bypass requirements other than ``superadmin``.
    
    Returns:
        A decorator that enforces authentication and role-based access.
    """
    def decorator(f):
        """
        Enforce authentication and role-based access for a route handler.
        
        Parameters:
            f (callable): The route handler to protect.
        
        Returns:
            callable: A wrapped route handler that permits users with an allowed role,
                or administrators for non-superadmin roles.
        """
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            # Authenticate user first
            """
            Enforce authentication and role-based access for the wrapped request handler.
            
            Parameters:
                *args: Positional arguments passed to the wrapped handler.
                **kwargs: Keyword arguments passed to the wrapped handler.
            
            Returns:
                The wrapped handler's response, or a 401 response for an invalid user or a 403 response when the user lacks permission.
            """
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
    Create a decorator that restricts access to a submission based on a permission type.
    
    Parameters:
        permission_type (str): Permission to enforce: ``'owner'``, ``'jury'``, or
            ``'view'``.
    
    Returns:
        A decorator that authorizes access and attaches the authenticated user and
        submission to the request context.
    """
    def decorator(f):
        """
        Create a route decorator that enforces a user's permission to access a submission.
        
        Parameters:
            f (callable): Route handler to protect.
        
        Returns:
            callable: A decorated route handler that authorizes access using the configured permission type.
        """
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            # Authenticate user
            """
            Authorize access to a submission before invoking the wrapped handler.
            
            Parameters:
                *args: Positional arguments for the wrapped handler.
                **kwargs: Keyword arguments for the wrapped handler, including
                    ``submission_id``.
            
            Returns:
                The wrapped handler's result, or an error response when authentication,
                submission lookup, or permission checks fail.
            """
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
    Create a decorator that validates required fields in a JSON request body.
    
    Parameters:
        required_fields: Field names that must be present in the request data.
    
    Returns:
        A decorator that attaches validated request data to `request.validated_data` and rejects invalid requests with an HTTP 400 response.
    """
    def decorator(f):
        """
        Validate the request body before invoking the wrapped route handler.
        
        Parameters:
            f (callable): Route handler to invoke after validation.
        
        Returns:
            callable: A wrapped route handler that stores validated JSON data in
            `request.validated_data` and returns a 400 response when validation fails.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Ensure request content-type is JSON
            """
            Validate the request body and provide the parsed data to the wrapped handler.
            
            Returns:
                The wrapped handler's response, or a 400 response when the request body is
                missing, not JSON, or lacks required fields.
            """
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
    Handle errors raised by a route function and return appropriate JSON responses.
    
    Parameters:
        f: The route function to wrap.
    
    Returns:
        A decorated function that returns a 400 response for ValueError exceptions and a 500 response for other exceptions.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        """
        Execute the wrapped function and convert raised errors into HTTP error responses.
        
        Returns:
            The wrapped function's result, or a 400 response for `ValueError` and a
            500 response for other exceptions.
        """
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
