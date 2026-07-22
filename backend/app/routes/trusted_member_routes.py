"""
Trusted member management routes for WikiEval Application.

Handles creator-account (trusted member) requests, listing, and
superadmin approval/rejection/add/remove. Extracted from the original
monolithic user_routes.py. Registered at /api/user along with the other
user blueprints.
"""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app

from app.database import db
from app.extensions import limiter
from app.middleware.auth import require_auth, require_role, handle_errors
from app.models.user import User
from app.models.trusted_member_request import TrustedMemberRequest

# Create blueprint
trusted_bp = Blueprint('trusted_member', __name__)


@trusted_bp.route('/trusted-members/request', methods=['POST'])
@limiter.limit("3/day")
@require_auth
@handle_errors
def request_trusted_member():
    """
    Request trusted-member status using the user's MediaWiki edit history.
    
    A user with at least 300 edits is approved automatically. Otherwise, or when
    the edit count cannot be verified, a non-empty reason is required for
    superadmin review.
    
    Request body:
        reason (str): Explanation for the request when automatic approval is unavailable.
    
    Returns:
        JSON response describing whether the request was approved or submitted for review.
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
    existing_pending = TrustedMemberRequest.query.filter_by(
        user_id=user.id, status='pending'
    ).first()
    if existing_pending:
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
        request_record = TrustedMemberRequest(
            user_id=user.id,
            reason=reason,
            status='pending',
        )
        db.session.add(request_record)
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
        request_record = TrustedMemberRequest(
            user_id=user.id,
            reason=None,
            status='approved',
            reviewed_by=user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db.session.add(request_record)
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
    request_record = TrustedMemberRequest(
        user_id=user.id,
        reason=reason,
        status='pending',
    )
    db.session.add(request_record)
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
    Retrieve pending trusted-member requests for administrative review.
    
    Returns:
        A JSON response containing each request's user ID, username, email, role,
        creation timestamp, request timestamp, and reason.
    """
    # Get all pending requests, ordered by creation time (newest first)
    requests = TrustedMemberRequest.query.filter_by(status='pending').order_by(
        TrustedMemberRequest.created_at.desc()
    ).all()

    return jsonify({
        'requests': [{
            'id': req.id,
            'user_id': req.user_id,
            'username': req.requester.username if req.requester else None,
            'email': req.requester.email if req.requester else None,
            'role': req.requester.role if req.requester else None,
            'created_at': req.requester.created_at.isoformat() if req.requester and req.requester.created_at else None,
            'requested_at': req.created_at.isoformat() if req.created_at else None,
            'request_reason': req.reason,
        } for req in requests]
    }), 200


@trusted_bp.route('/trusted-members', methods=['GET'])
@require_role('superadmin')
@handle_errors
def get_trusted_members():
    """
    List all trusted members, including superadmins.
    
    Returns:
        JSON response containing each member's ID, username, email, role,
        superadmin status, and creation timestamp.
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
    Approve a user's request for trusted-member status.
    
    Parameters:
        user_id: ID of the user to approve.
    
    Returns:
        JSON response containing a success message, or an error response if the user is not found or is a superadmin.
    """
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Superadmins are automatically trusted, no need to approve
    if user.is_superadmin():
        return jsonify({
            'error': 'Superadmins are automatically trusted members'
        }), 400

    # Approve the request — update the latest pending TrustedMemberRequest
    user.is_trusted_member = True
    existing_request = TrustedMemberRequest.query.filter_by(
        user_id=user.id, status='pending'
    ).order_by(TrustedMemberRequest.created_at.desc()).first()
    if existing_request:
        existing_request.status = 'approved'
        existing_request.reviewed_by = user.id
        existing_request.reviewed_at = datetime.now(timezone.utc)
    else:
        request_record = TrustedMemberRequest(
            user_id=user.id,
            reason=None,
            status='approved',
            reviewed_by=user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db.session.add(request_record)
    user.save()

    return jsonify({
        'message': f'User {user.username} has been approved as a trusted member'
    }), 200


@trusted_bp.route('/trusted-members/<int:user_id>/reject', methods=['POST'])
@require_role('superadmin')
@handle_errors
def reject_trusted_member(user_id):
    """
    Reject a user's pending trusted-member request.
    
    Parameters:
    	user_id (int): ID of the user whose request is being rejected.
    
    Returns:
    	JSON response confirming rejection, or a 404 error if the user does not exist.
    """
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Clear request info and reject
    user.is_trusted_member = False
    existing_request = TrustedMemberRequest.query.filter_by(
        user_id=user.id, status='pending'
    ).order_by(TrustedMemberRequest.created_at.desc()).first()
    if existing_request:
        existing_request.status = 'rejected'
        existing_request.reviewed_by = user.id
        existing_request.reviewed_at = datetime.now(timezone.utc)
    else:
        request_record = TrustedMemberRequest(
            user_id=user.id,
            reason=None,
            status='rejected',
            reviewed_by=user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db.session.add(request_record)
    user.save()

    return jsonify({
        'message': f'Trusted member request for {user.username} has been rejected'
    }), 200


@trusted_bp.route('/trusted-members/<int:user_id>/add', methods=['POST'])
@require_role('superadmin')
@handle_errors
def add_trusted_member(user_id):
    """
    Add a user to the trusted member group.
    
    Args:
        user_id: ID of the user to add as a trusted member.
    
    Returns:
        JSON response containing a success message, or an error response if the user
        is not found or is a superadmin.
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
    request_record = TrustedMemberRequest(
        user_id=user.id,
        reason=None,
        status='approved',
        reviewed_by=user.id,
        reviewed_at=datetime.now(timezone.utc),
    )
    db.session.add(request_record)
    user.save()

    return jsonify({
        'message': f'User {user.username} has been added as a trusted member'
    }), 200


@trusted_bp.route('/trusted-members/<int:user_id>/remove', methods=['POST'])
@require_role('superadmin')
@handle_errors
def remove_trusted_member(user_id):
    """
    Remove a user's trusted-member status.
    
    Parameters:
        user_id: ID of the user whose trusted-member status is removed.
    
    Returns:
        A confirmation response, or an error response if the user is not found or is a superadmin.
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
