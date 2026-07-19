"""
Trusted member management routes for WikiContest Application.

Handles creator-account (trusted member) requests, listing, and
superadmin approval/rejection/add/remove. Extracted from the original
monolithic user_routes.py. Registered at /api/user along with the other
user blueprints.
"""

from flask import Blueprint, request, jsonify, current_app

from app.database import db
from app.extensions import limiter
from app.middleware.auth import require_auth, require_role, handle_errors
from app.models.user import User

# Create blueprint
trusted_bp = Blueprint('trusted_member', __name__)


@trusted_bp.route('/trusted-members/request', methods=['POST'])
@limiter.limit("3/day")
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

    # Check if request is already pending
    # Users can re-request if their previous request was rejected
    request_status = getattr(user, 'trusted_member_request_status', None)
    if request_status == 'pending':
        return jsonify({
            'error': 'You have already requested trusted member status. Please wait for approval.'
        }), 400

    # Check if user logged in via MediaWiki OAuth
    # Only MediaWiki OAuth users can request creator accounts
    if not user.oauth_token or not user.oauth_token_secret:
        return jsonify({
            'error': (
                'Only users who logged in via MediaWiki can request creator accounts. '
                'Please log in using MediaWiki OAuth.'
            )
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
                'error': (
                    'Could not verify your edit count. '
                    'Please provide a reason for requesting creator account status.'
                ),
                'requires_reason': True
            }), 400

        # Store request with reason for superadmin review
        user.trusted_member_request = True
        user.trusted_member_request_reason = reason
        user.trusted_member_request_status = 'pending'
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
        user.trusted_member_request_status = 'approved'
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
            'error': (
                f'You have {edit_count} edits, which is below the minimum of {MIN_EDIT_COUNT} edits '
                f'for automatic approval. Please provide a reason for requesting creator account status.'
            ),
            'requires_reason': True,
            'edit_count': edit_count,
            'min_edit_count': MIN_EDIT_COUNT
        }), 400

    # Store request with reason for superadmin review
    user.trusted_member_request = True
    user.trusted_member_request_reason = reason
    user.trusted_member_request_status = 'pending'
    user.save()

    return jsonify({
        'message': (
            f'Your creator account request has been submitted for review. You have {edit_count} edits '
            f'(minimum {MIN_EDIT_COUNT} for automatic approval). A superadmin will review your request.'
        ),
        'auto_approved': False,
        'edit_count': edit_count
    }), 200


@trusted_bp.route('/trusted-members/requests', methods=['GET'])
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


@trusted_bp.route('/trusted-members', methods=['GET'])
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


@trusted_bp.route('/trusted-members/<int:user_id>/approve', methods=['POST'])
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
    user = db.session.get(User, user_id)

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
    user.trusted_member_request_status = 'approved'
    user.save()

    return jsonify({
        'message': f'User {user.username} has been approved as a trusted member'
    }), 200


@trusted_bp.route('/trusted-members/<int:user_id>/reject', methods=['POST'])
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
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Clear the request flag and reason (rejection)
    user.trusted_member_request = False
    user.trusted_member_request_reason = None
    user.trusted_member_request_status = 'rejected'
    user.save()

    return jsonify({
        'message': f'Trusted member request for {user.username} has been rejected'
    }), 200


@trusted_bp.route('/trusted-members/<int:user_id>/add', methods=['POST'])
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
    user = db.session.get(User, user_id)

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
    user.trusted_member_request_status = 'approved'
    user.save()

    return jsonify({
        'message': f'User {user.username} has been added as a trusted member'
    }), 200


@trusted_bp.route('/trusted-members/<int:user_id>/remove', methods=['POST'])
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
    user = db.session.get(User, user_id)

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
