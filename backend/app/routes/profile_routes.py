"""
Profile & dashboard routes for WikiContest Application.

Handles user dashboard data, profile retrieval/update, user search, and
username lookup. Extracted from the original monolithic user_routes.py.
Registered at /api/user along with the other user blueprints.
"""

from flask import Blueprint, request, jsonify

from app.database import db
from app.extensions import limiter
from app.middleware.auth import require_auth, require_role, handle_errors, validate_json_data
from app.models.user import User
from app.routes._user_helpers import validate_email, validate_username

# Create blueprint
profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/dashboard', methods=['GET'])
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

    # Contest-wise scores
    contest_scores = db.session.query(
        Contest.id.label('contest_id'),
        Contest.name.label('contest_name'),
        db.func.sum(Submission.score).label('contest_score'),
        db.func.count(Submission.id).label('submission_count')
    ).join(Submission).filter(
        Submission.user_id == user.id
    ).group_by(Contest.id, Contest.name).order_by(Contest.name).all()

    # Submissions grouped by contest
    submissions_query = db.session.query(
        Submission,
        Contest.name.label('contest_name')
    ).join(Contest).filter(
        Submission.user_id == user.id
    ).order_by(Submission.submitted_at.desc()).all()

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

    # Organized contests (created by user OR listed as additional organizer)
    organized_candidates = Contest.query.filter(
        db.or_(
            Contest.created_by == user.username,
            Contest.organizers.ilike(f'%{user.username}%')
        )
    ).order_by(Contest.created_at.desc()).all()
    organized_contests_data = []
    for contest in organized_candidates:
        contest_data = contest.to_dict()
        contest_data['submission_count'] = contest.get_submission_count()
        organized_contests_data.append(contest_data)

    # Jury contests
    jury_contests = Contest.query.filter(
        Contest.jury_members.like(f'%{user.username}%')
    ).all()
    jury_contests_data = []
    for contest in jury_contests:
        contest_data = contest.to_dict()
        contest_data['submission_count'] = contest.get_submission_count()
        jury_contests_data.append(contest_data)

    # Participated contests (contests jisme user ne submit kiya)
    participated_contests_query = db.session.query(
        Contest,
        db.func.min(Submission.submitted_at).label('submitted_at')
    ).join(
        Submission, Contest.id == Submission.contest_id
    ).filter(
        Submission.user_id == user.id
    ).group_by(Contest.id).order_by(
        db.func.min(Submission.submitted_at).desc()
    ).all()

    participated_contests_data = []
    for contest, submitted_at in participated_contests_query:
        contest_data = contest.to_dict()
        contest_data['submitted_at'] = submitted_at.isoformat() if submitted_at else None
        participated_contests_data.append(contest_data)

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
        'organized_contests': organized_contests_data,
        'jury_contests': jury_contests_data,
        'participated_contests': participated_contests_data  # NEW
    }), 200


@profile_bp.route('/dashboard/access', methods=['GET'])
@require_auth
@handle_errors
def get_dashboard_access():
    """
    Get which dashboards the current user can access.

    Returns:
        JSON response with boolean flags for each dashboard type
    """
    user = request.current_user

    from app.models.contest import Contest

    # Check if user is organizer of any contest
    is_organizer = Contest.query.filter(
        db.or_(
            Contest.created_by == user.username,
            Contest.organizers.ilike(f'%{user.username}%')
        )
    ).first() is not None

    # Check if user is jury of any contest
    is_jury = Contest.query.filter(
        Contest.jury_members.like(f'%{user.username}%')
    ).first() is not None

    # Trusted members and superadmins always have access to the organizer dashboard
    can_access_organizer = is_organizer or user.is_trusted_member or user.is_superadmin()

    return jsonify({
        'can_access_participant': True,  # All authenticated users
        'can_access_organizer': can_access_organizer,
        'can_access_jury': is_jury
    }), 200


@profile_bp.route('/all', methods=['GET'])
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


@profile_bp.route('/profile', methods=['GET'])
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


@profile_bp.route('/profile', methods=['PUT'])
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


@profile_bp.route('/search', methods=['GET'])
@limiter.limit("30/minute")
@require_auth
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

    # Search users whose username starts with the query (prefix match).
    # Escape SQL LIKE wildcards to prevent injection via % or _ characters.
    escaped = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    users = User.query.filter(
        User.username.ilike(f'{escaped}%', escape='\\')
    ).limit(limit).all()

    return jsonify({
        'users': [{'username': user.username, 'id': user.id} for user in users]
    }), 200


@profile_bp.route('/<int:user_id>/username', methods=['GET'])
@require_auth
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
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Return only non-sensitive user information
    return jsonify({
        'id': user.id,
        'username': user.username
    }), 200
