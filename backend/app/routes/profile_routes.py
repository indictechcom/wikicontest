"""
Profile & dashboard routes for WikiEval Application.

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
    Assemble the authenticated user's dashboard data.
    
    Returns:
        A JSON response containing the username, total score, contest-wise
        scores, submissions grouped by contest, organized contests, jury
        contests, and participated contests.
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
    # Escape SQL LIKE wildcards to prevent false matches via % or _ characters
    escaped_username = user.username.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    organized_candidates = Contest.query.filter(
        db.or_(
            Contest.created_by == user.username,
            Contest.organizers == escaped_username,  # Exact match (only organizer)
            Contest.organizers.ilike(f'{escaped_username},%', escape='\\'),  # First in list
            Contest.organizers.ilike(f'%,{escaped_username},%', escape='\\'),  # Middle of list
            Contest.organizers.ilike(f'%,{escaped_username}', escape='\\')  # Last in list
        )
    ).order_by(Contest.created_at.desc()).all()
    organized_contests_data = []
    for contest in organized_candidates:
        contest_data = contest.to_dict()
        contest_data['submission_count'] = contest.get_submission_count()
        organized_contests_data.append(contest_data)

    # Jury contests
    # Escape SQL LIKE wildcards to prevent false matches via % or _ characters
    jury_contests = Contest.query.filter(
        db.or_(
            Contest.jury_members == escaped_username,  # Exact match (only jury member)
            Contest.jury_members.ilike(f'{escaped_username},%', escape='\\'),  # First in list
            Contest.jury_members.ilike(f'%,{escaped_username},%', escape='\\'),  # Middle of list
            Contest.jury_members.ilike(f'%,{escaped_username}', escape='\\')  # Last in list
        )
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
    Determine which dashboard sections the authenticated user can access.
    
    Returns:
        A JSON response containing participant, organizer, and jury access flags.
    """
    user = request.current_user

    from app.models.contest import Contest

    # Escape SQL LIKE wildcards to prevent false matches via % or _ characters
    escaped_username = user.username.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

    # Check if user is organizer of any contest
    is_organizer = Contest.query.filter(
        db.or_(
            Contest.created_by == user.username,
            Contest.organizers == escaped_username,
            Contest.organizers.ilike(f'{escaped_username},%', escape='\\'),
            Contest.organizers.ilike(f'%,{escaped_username},%', escape='\\'),
            Contest.organizers.ilike(f'%,{escaped_username}', escape='\\')
        )
    ).first() is not None

    # Check if user is jury of any contest
    is_jury = Contest.query.filter(
        db.or_(
            Contest.jury_members == escaped_username,
            Contest.jury_members.ilike(f'{escaped_username},%', escape='\\'),
            Contest.jury_members.ilike(f'%,{escaped_username},%', escape='\\'),
            Contest.jury_members.ilike(f'%,{escaped_username}', escape='\\')
        )
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
    Retrieve all users as serialized profile data.
    
    Returns:
        A JSON response containing a list of all users.
    """
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200


@profile_bp.route('/profile', methods=['GET'])
@require_auth
@handle_errors
def get_profile():
    """
    Return the authenticated user's profile data.
    
    Returns:
        JSON response containing the user's serialized profile.
    """
    user = request.current_user
    return jsonify(user.to_dict()), 200


@profile_bp.route('/profile', methods=['PUT'])
@require_auth
@handle_errors
@validate_json_data(['username', 'email'])
def update_profile():
    """
    Update the authenticated user's username and email address.
    
    Input values are trimmed, the email is lowercased, and both fields must be valid and unique.
    
    Returns:
        A success response when the profile is updated, or an error response when validation or uniqueness checks fail.
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
    Search for users by a case-insensitive username prefix.
    
    Parameters:
        q (str): Username prefix; queries shorter than two characters return no users.
        limit (int): Maximum number of users to return. Defaults to 10.
    
    Returns:
        JSON response containing matching usernames and user IDs.
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
    Retrieve a user's ID and username by user ID.
    
    Args:
        user_id: The ID of the user to retrieve.
    
    Returns:
        A JSON response containing the user's ID and username, or a 404 error if the user does not exist.
    """
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Return only non-sensitive user information
    return jsonify({
        'id': user.id,
        'username': user.username
    }), 200
