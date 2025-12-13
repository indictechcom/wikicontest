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
from app.models.user import User

def get_current_user():
    """
    Get the current authenticated user from JWT token
    
    Returns:
        User: Current user instance or None if not authenticated
    """
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        # Convert string user_id back to integer for database query
        return User.query.get(int(user_id))
    except Exception:
        return None

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
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Invalid user'}), 401
        
        # Add user to request context
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
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Invalid user'}), 401
            
            # Convert single role to list
            if isinstance(roles, str):
                allowed_roles = [roles]
            else:
                allowed_roles = roles
            
            # Check if user has required role
            if user.role not in allowed_roles and not user.is_admin():
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            request.current_user = user
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_contest_permission(permission_type):
    """
    Decorator to require specific contest permissions
    
    Args:
        permission_type: Type of permission ('creator', 'jury', 'participant')
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Invalid user'}), 401
            
            # Get contest_id from URL parameters
            contest_id = kwargs.get('id')
            if not contest_id:
                return jsonify({'error': 'Contest ID required'}), 400
            
            # Get contest from database
            from models.contest import Contest
            contest = Contest.query.get(contest_id)
            if not contest:
                return jsonify({'error': 'Contest not found'}), 404
            
            # Check permissions
            has_permission = False
            
            if permission_type == 'creator':
                has_permission = user.is_contest_creator(contest) or user.is_admin()
            elif permission_type == 'jury':
                has_permission = user.is_jury_member(contest) or user.is_admin()
            elif permission_type == 'participant':
                # For now, any authenticated user can participate
                has_permission = True
            
            if not has_permission:
                return jsonify({'error': 'Insufficient permissions for this contest'}), 403
            
            request.current_user = user
            request.current_contest = contest
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

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
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Invalid user'}), 401
            
            # Get submission_id from URL parameters
            submission_id = kwargs.get('id')
            if not submission_id:
                return jsonify({'error': 'Submission ID required'}), 400
            
            # Get submission from database
            from models.submission import Submission
            submission = Submission.query.get(submission_id)
            if not submission:
                return jsonify({'error': 'Submission not found'}), 404
            
            # Check permissions
            has_permission = False
            
            if permission_type == 'owner':
                has_permission = (submission.user_id == user.id) or user.is_admin()
            elif permission_type == 'jury':
                has_permission = submission.can_be_judged_by(user)
            elif permission_type == 'view':
                has_permission = submission.can_be_viewed_by(user)
            
            if not has_permission:
                return jsonify({'error': 'Insufficient permissions for this submission'}), 403
            
            request.current_user = user
            request.current_submission = submission
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

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
            if not request.is_json:
                return jsonify({'error': 'Request must be JSON'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            # Check for required fields
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            
            # Add validated data to request context
            request.validated_data = data
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

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
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            # Log the full error for debugging
            error_message = str(e)
            current_app.logger.error(f"Error in {f.__name__}: {error_message}", exc_info=True)
            
            # In debug mode, show the actual error message for easier debugging
            # In production, show generic message for security
            if current_app.config.get('DEBUG', False):
                return jsonify({'error': f'Internal server error: {error_message}'}), 500
            else:
                return jsonify({'error': 'Internal server error'}), 500
    
    return decorated_function