"""
Submission Routes for WikiContest Application
Handles submission management and review functionality
"""

from urllib.parse import urlparse

import requests
from flask import Blueprint, jsonify, request

from app.database import db
from app.middleware.auth import handle_errors, require_auth, require_submission_permission, validate_json_data
from app.models.contest import Contest
from app.models.submission import Submission
from app.utils import (
    validate_contest_submission_access,
    extract_page_title_from_url,
    get_latest_revision_author,
    build_mediawiki_revisions_api_params,
    get_mediawiki_headers
)

# Create blueprint
submission_bp = Blueprint('submission', __name__)

@submission_bp.route('/', methods=['GET'])
@require_auth
@handle_errors
def get_all_submissions():
    """
    Get all submissions (admin only)

    Returns:
        JSON response with all submissions
    """
    user = request.current_user

    if not user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    submissions = Submission.query.order_by(Submission.submitted_at.desc()).all()

    submissions_data = []
    for submission in submissions:
        submission_data = submission.to_dict(include_user_info=True)
        submissions_data.append(submission_data)

    return jsonify(submissions_data), 200

@submission_bp.route('/<int:submission_id>', methods=['GET'])
@require_submission_permission('view')
@handle_errors
def get_submission_by_id(submission_id):  # pylint: disable=unused-argument
    """
    Get a specific submission by ID

    Args:
        submission_id: Submission ID

    Returns:
        JSON response with submission data
    """
    submission = request.current_submission

    # Get additional information
    submission_data = submission.to_dict(include_user_info=True)

    return jsonify(submission_data), 200

@submission_bp.route('/<int:submission_id>', methods=['PUT'])
@require_submission_permission('jury')
@handle_errors
@validate_json_data(['status'])
def update_submission_status(submission_id):  # pylint: disable=unused-argument
    """
    Update submission status and score (jury or admin only)

    Args:
        submission_id: Submission ID

    Expected JSON data:
        status: New status ('accepted' or 'rejected')

    Returns:
        JSON response with success message and updated status/score
    """
    submission = request.current_submission
    data = request.validated_data

    new_status = data['status'].strip().lower()

    # Validate status
    if new_status not in ['accepted', 'rejected']:
        return jsonify({'error': 'Status must be either "accepted" or "rejected"'}), 400

    # Check if status is already set
    if submission.status == new_status:
        return jsonify({
            'message': f'Submission is already {new_status}. No changes made.',
            'status': submission.status,
            'score': submission.score
        }), 200

    # Update submission status and score
    try:
        updated = submission.update_status(new_status)

        if updated:
            return jsonify({
                'message': 'Submission updated successfully',
                'status': submission.status,
                'score': submission.score
            }), 200
        return jsonify({
            'message': 'No changes made to submission',
            'status': submission.status,
            'score': submission.score
        }), 200

    except Exception:  # pylint: disable=broad-exception-caught
        # Log error for debugging but don't expose details to client
        return jsonify({'error': 'Failed to update submission'}), 500

@submission_bp.route('/user/<int:user_id>', methods=['GET'])
@require_auth
@handle_errors
def get_user_submissions(user_id):
    """
    Get all submissions by a specific user

    Args:
        user_id: User ID

    Returns:
        JSON response with user's submissions
    """
    current_user = request.current_user

    # Users can only view their own submissions unless they're admin
    if not current_user.is_admin() and current_user.id != user_id:
        return jsonify({'error': 'You can only view your own submissions'}), 403

    submissions = Submission.query.filter_by(user_id=user_id).order_by(
        Submission.submitted_at.desc()
    ).all()

    submissions_data = []
    for submission in submissions:
        submission_data = submission.to_dict(include_user_info=True)
        submissions_data.append(submission_data)

    return jsonify(submissions_data), 200

@submission_bp.route('/contest/<int:contest_id>', methods=['GET'])
@require_auth
@handle_errors
def get_contest_submissions(contest_id):
    """
    Retrieve all submissions for a specific contest.
    
    This endpoint returns submissions with basic information.
    Access is restricted to admins, contest creators, and jury members.

    Args:
        contest_id: The ID of the contest to get submissions for

    Returns:
        JSON response containing list of submission data
    """
    user = request.current_user

    # Validate contest access and permissions using shared utility function
    # This eliminates duplicate code across different route files
    # Note: contest variable is validated but not used in this route
    _contest, error_response = validate_contest_submission_access(contest_id, user, Contest)
    if error_response:
        return error_response

    submissions = Submission.query.filter_by(contest_id=contest_id).order_by(
        Submission.submitted_at.desc()
    ).all()

    submissions_data = []
    for submission in submissions:
        submission_data = submission.to_dict(include_user_info=True)
        submissions_data.append(submission_data)

    return jsonify(submissions_data), 200

@submission_bp.route('/pending', methods=['GET'])
@require_auth
@handle_errors
def get_pending_submissions():
    """
    Get all pending submissions that the user can judge

    Returns:
        JSON response with pending submissions
    """
    user = request.current_user

    # Get all pending submissions
    pending_submissions = Submission.query.filter_by(status='pending').all()

    # Filter submissions that user can judge
    judgeable_submissions = []
    for submission in pending_submissions:
        if submission.can_be_judged_by(user):
            submission_data = submission.to_dict(include_user_info=True)
            judgeable_submissions.append(submission_data)

    return jsonify(judgeable_submissions), 200

@submission_bp.route('/stats', methods=['GET'])
@require_auth
@handle_errors
def get_submission_stats():
    """
    Get submission statistics for the current user

    Returns:
        JSON response with submission statistics
    """
    user = request.current_user

    # Get user's submission statistics
    total_submissions = Submission.query.filter_by(user_id=user.id).count()
    accepted_submissions = Submission.query.filter_by(
        user_id=user.id,
        status='accepted'
    ).count()
    rejected_submissions = Submission.query.filter_by(
        user_id=user.id,
        status='rejected'
    ).count()
    pending_submissions = Submission.query.filter_by(
        user_id=user.id,
        status='pending'
    ).count()

    # Get total score from submissions
    total_score = db.session.query(db.func.sum(Submission.score)).filter_by(
        user_id=user.id
    ).scalar() or 0

    return jsonify({
        'total_submissions': total_submissions,
        'accepted_submissions': accepted_submissions,
        'rejected_submissions': rejected_submissions,
        'pending_submissions': pending_submissions,
        'total_score': total_score,
        'acceptance_rate': (accepted_submissions / total_submissions * 100) if total_submissions > 0 else 0
    }), 200

@submission_bp.route('/contest/<int:contest_id>/refresh-metadata', methods=['POST'])
@require_auth
@handle_errors
def refresh_metadata(contest_id):
    """
    Refresh article metadata (word count, author, etc.) for all submissions in a contest.
    
    This endpoint fetches the latest metadata from MediaWiki API for all submissions
    in the specified contest and updates the database with the current values.
    
    Args:
        contest_id: The ID of the contest to refresh submissions for
        
    Returns:
        JSON response with refresh results
    """
    user = request.current_user

    # Validate contest access and permissions
    # Note: contest variable is validated but not used in this route
    _contest, error_response = validate_contest_submission_access(contest_id, user, Contest)
    if error_response:
        return error_response

    # Get all submissions for this contest
    submissions = Submission.query.filter_by(contest_id=contest_id).all()

    if not submissions:
        return jsonify({
            'message': 'No submissions found for this contest',
            'updated': 0,
            'failed': 0,
            'total': 0
        }), 200

    updated = 0
    failed = 0

    # Function to fetch article info (same logic as backfill script)
    def fetch_article_info(article_link):
        """Fetch article information from MediaWiki API"""
        try:
            # Extract page title from URL using shared utility function
            page_title = extract_page_title_from_url(article_link)
            if not page_title:
                return None

            # Parse the article URL to extract base URL
            url_obj = urlparse(article_link)
            base_url = f"{url_obj.scheme}://{url_obj.netloc}"

            # Build API request - get 2 revisions (newest and oldest)
            api_url = f"{base_url}/w/api.php"
            # Build API parameters using shared utility function
            api_params = build_mediawiki_revisions_api_params(page_title)
            # Get headers using shared utility function
            headers = get_mediawiki_headers()

            response = requests.get(api_url, params=api_params, headers=headers, timeout=10)

            if response.status_code != 200:
                return None

            data = response.json()

            if 'error' in data:
                return None

            pages = data.get('query', {}).get('pages', [])
            if not pages:
                return None

            page_data = pages[0]
            is_missing = page_data.get('missing', False)
            page_id = str(page_data.get('pageid', ''))

            if is_missing or not page_id or page_id == '-1':
                return None

            # Get revision info
            # With rvdir='older', revisions[0] is the newest (latest) revision
            revisions = page_data.get('revisions', [])
            if not revisions or len(revisions) == 0:
                return None

            # Get latest revision (newest) for current size and author
            latest_revision = revisions[0]
            # Current size from latest revision (used for expansion bytes calculation on refresh)
            current_size = latest_revision.get('size', 0)

            # Extract author from latest revision (newest revision at submission time)
            # Use shared utility function to extract author from latest revision
            # This gets the author who made the most recent edit at submission time
            article_author = get_latest_revision_author(revisions)

            # Get latest revision timestamp
            latest_revision_timestamp = latest_revision.get('timestamp', '')

            # Get oldest revision (creation) for creation date (for historical reference)
            if len(revisions) > 1:
                oldest_revision = revisions[-1]
            else:
                oldest_revision = revisions[0]

            return {
                'article_author': article_author,  # Author from latest revision at submission time
                'article_created_at': oldest_revision.get('timestamp', ''),
                # Current size from API (used for expansion bytes calculation, not stored as article_word_count)
                'current_size': current_size,
                'article_page_id': page_id,
                # Latest revision metadata (kept for backward compatibility)
                'latest_revision_author': article_author,  # Same as article_author now
                'latest_revision_timestamp': latest_revision_timestamp
            }

        except Exception:  # pylint: disable=broad-exception-caught
            return None

    # Helper function to calculate expansion bytes for a submission
    def calculate_expansion_bytes(submission_item, article_info):
        """
        Calculate expansion bytes relative to submission time.
        
        Expansion bytes = current size - size at submission time (article_word_count)
        This shows how much the article has grown or shrunk since it was submitted.
        Only updates if there's an actual change in size.
        """
        if not submission_item.article_link:
            return

        try:
            # Get current size from API (latest revision size)
            # This is the current/latest size of the article from the API
            current_size = article_info.get('current_size')

            # Get original size at submission time (article_word_count)
            # This is the size when the article was submitted
            original_size_at_submission = submission_item.article_word_count

            # Calculate expansion bytes: current size - size at submission time
            # This shows the change since submission (can be positive or negative)
            # Only update if there's an actual change
            if current_size is not None and original_size_at_submission is not None:
                expansion_bytes = current_size - original_size_at_submission
                # Only update expansion bytes if there's a change
                # This ensures we track actual changes since submission
                submission_item.article_expansion_bytes = expansion_bytes
            elif current_size is not None and original_size_at_submission is None:
                # If original size wasn't set, use current size as expansion
                # (article was created after submission, which shouldn't happen)
                submission_item.article_expansion_bytes = current_size
            # If both are None, leave expansion_bytes as None (don't update)

        except Exception as exp_error:  # pylint: disable=broad-exception-caught
            # If expansion calculation fails, log but don't fail the update
            try:
                from flask import current_app
                current_app.logger.warning(
                    f'Failed to calculate expansion for submission {submission_item.id}: {str(exp_error)}'
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    # Refresh metadata for each submission
    for submission in submissions:
        info = fetch_article_info(submission.article_link)

        if info:
            # Update submission with latest metadata
            # Do NOT update article_author - it should remain fixed at submission time
            # Only update if it's not already set (for backward compatibility with old submissions)
            if info.get('article_author') and not submission.article_author:
                submission.article_author = info['article_author']
            if info.get('article_created_at') and not submission.article_created_at:
                submission.article_created_at = info['article_created_at']
            # Do NOT update article_word_count - it should remain fixed at submission time
            # article_word_count represents the size at the time of submission
            if info.get('article_page_id'):
                submission.article_page_id = info['article_page_id']

            # Calculate expansion bytes on refresh
            # Expansion bytes = current size - size at submission time
            # This shows how much the article has changed since submission
            # When refreshing metadata, ONLY update expansion bytes
            # Do NOT update: article_author, article_word_count, article_size_at_start
            # These should remain fixed at submission time
            calculate_expansion_bytes(submission, info)

            updated += 1
        else:
            failed += 1

    # Commit all changes
    try:
        db.session.commit()
    except Exception:  # pylint: disable=broad-exception-caught
        db.session.rollback()
        return jsonify({'error': 'Failed to save updates to database'}), 500

    return jsonify({
        'message': f'Refreshed metadata for {updated} submissions',
        'updated': updated,
        'failed': failed,
        'total': len(submissions)
    }), 200
