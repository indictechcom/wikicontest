"""
Contest Routes for WikiContest Application
Handles contest creation, retrieval, and management functionality
"""

from datetime import datetime
import traceback

from flask import Blueprint, request, jsonify, current_app

from app.database import db
from app.middleware.auth import require_auth, handle_errors, validate_json_data
from app.models.contest import Contest
from app.models.submission import Submission
from app.models.user import User
from app.utils import (
    validate_contest_submission_access,
    get_article_size_at_timestamp,
    extract_page_title_from_url,
    get_latest_revision_author,
    build_mediawiki_revisions_api_params,
    get_mediawiki_headers
)

# Create blueprint
contest_bp = Blueprint('contest', __name__)

def validate_date_string(date_str):
    """
    Validate date string format (YYYY-MM-DD)

    Args:
        date_str: Date string to validate

    Returns:
        date: Parsed date object or None if invalid
    """
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

@contest_bp.route('/', methods=['GET'])
@require_auth
@handle_errors
def get_all_contests():
    """
    Get all contests categorized by status
    Requires authentication - users must be logged in to view contests.

    Returns:
        JSON response with contests categorized as current, upcoming, and past
    """
    contests = Contest.query.order_by(Contest.created_at.desc()).all()

    current = []
    upcoming = []
    past = []

    for contest in contests:
        contest_data = contest.to_dict()

        if contest.is_active():
            current.append(contest_data)
        elif contest.is_upcoming():
            upcoming.append(contest_data)
        elif contest.is_past():
            past.append(contest_data)

    return jsonify({
        'current': current,
        'upcoming': upcoming,
        'past': past
    }), 200

@contest_bp.route('/', methods=['POST'])
@require_auth
@handle_errors
@validate_json_data(['name', 'project_name', 'jury_members'])
def create_contest():
    """
    Create a new contest

    Expected JSON data:
        name: Name of the contest
        project_name: Name of the associated project
        jury_members: List of jury member usernames
        code_link: Optional link to contest's code repository
        description: Optional description of the contest
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        rules: Optional rules object
        marks_setting_accepted: Optional points for accepted submissions
        marks_setting_rejected: Optional points for rejected submissions

    Returns:
        JSON response with success message and contest ID
    """
    user = request.current_user
    data = request.validated_data

    # Validate required fields
    name = data['name'].strip()
    project_name = data['project_name'].strip()
    jury_members = data['jury_members']

    if not name:
        return jsonify({'error': 'Contest name is required'}), 400

    if not project_name:
        return jsonify({'error': 'Project name is required'}), 400

    if not isinstance(jury_members, list) or len(jury_members) == 0:
        return jsonify({'error': 'Jury members must be a non-empty array of usernames'}), 400

    # Validate jury members exist
    existing_users = User.query.filter(User.username.in_(jury_members)).all()
    existing_usernames = [user.username for user in existing_users]
    missing_users = [username for username in jury_members if username not in existing_usernames]

    if missing_users:
        return jsonify({'error': f'These jury members do not exist: {", ".join(missing_users)}'}), 400

    # Parse optional fields
    # Handle code_link: can be None (from frontend), empty string, or a URL
    code_link_value = data.get('code_link')
    if code_link_value is None or code_link_value == '':
        code_link = None
    else:
        code_link = str(code_link_value).strip() or None

    # Handle description: can be None, empty string, or text
    description_value = data.get('description')
    if description_value is None or description_value == '':
        description = None
    else:
        description = str(description_value).strip() or None

    # Parse dates
    start_date = validate_date_string(data.get('start_date'))
    end_date = validate_date_string(data.get('end_date'))

    # Validate date logic
    if start_date and end_date and start_date >= end_date:
        return jsonify({'error': 'End date must be after start date'}), 400

    # Parse rules
    rules = data.get('rules', {})
    if not isinstance(rules, dict):
        rules = {}

    # Parse scoring settings
    marks_accepted = data.get('marks_setting_accepted', 0)
    marks_rejected = data.get('marks_setting_rejected', 0)
    allowed_submission_type = data.get("allowed_submission_type", "both")

    try:
        marks_accepted = int(marks_accepted)
        marks_rejected = int(marks_rejected)
    except (ValueError, TypeError):
        return jsonify({'error': 'Marks settings must be valid integers'}), 400

    # Create contest
    try:
        contest = Contest(
            name=name,
            project_name=project_name,
            created_by=user.username,
            code_link=code_link,
            description=description,
            start_date=start_date,
            end_date=end_date,
            rules=rules,
            marks_setting_accepted=marks_accepted,
            marks_setting_rejected=marks_rejected,
            jury_members=jury_members,
            allowed_submission_type=allowed_submission_type
        )

        contest.save()

        return jsonify({
            'message': 'Contest created successfully',
            'contestId': contest.id
        }), 201

    except Exception:  # pylint: disable=broad-exception-caught
        # Log error for debugging but don't expose details to client
        return jsonify({'error': 'Failed to create contest'}), 500

@contest_bp.route('/<int:contest_id>', methods=['GET'])
@require_auth
@handle_errors
def get_contest_by_id(contest_id):
    """
    Get a specific contest by ID
    Requires authentication - users must be logged in to view contest details.

    Args:
        contest_id: Contest ID

    Returns:
        JSON response with contest data
    """
    contest = Contest.query.get(contest_id)

    if not contest:
        return jsonify({'error': 'Contest not found'}), 404

    return jsonify(contest.to_dict()), 200

@contest_bp.route('/name/<name>', methods=['GET'])
@require_auth
@handle_errors
def get_contest_by_name(name):
    """
    Get a specific contest by name (slugified)
    Requires authentication - users must be logged in to view contest details.

    Args:
        name: Contest name in slug format (e.g., "price-sanford")

    Returns:
        JSON response with contest data
    """
    import re

    # Get all contests and find the one matching the slug
    # This approach handles various name formats and special characters
    contests = Contest.query.all()
    contest = None

    # Normalize the input slug (lowercase, remove extra hyphens)
    normalized_slug = re.sub(r'[-\s]+', '-', name.lower().strip())

    for contest_item in contests:
        # Create slug from contest name (same logic as frontend slugify)
        contest_slug = contest_item.name.lower().strip()
        # Replace spaces with hyphens
        contest_slug = re.sub(r'\s+', '-', contest_slug)
        # Remove special characters except hyphens
        contest_slug = re.sub(r'[^\w\-]+', '', contest_slug)
        # Replace multiple hyphens with single hyphen
        contest_slug = re.sub(r'\-\-+', '-', contest_slug)
        # Remove leading/trailing hyphens
        contest_slug = contest_slug.strip('-')

        # Compare normalized slugs
        if contest_slug == normalized_slug:
            contest = contest_item
            break

    if not contest:
        return jsonify({'error': 'Contest not found'}), 404

    return jsonify(contest.to_dict()), 200

@contest_bp.route('/<int:contest_id>/leaderboard', methods=['GET'])
@require_auth
@handle_errors
def get_contest_leaderboard(contest_id):
    """
    Get leaderboard for a specific contest
    Requires authentication - users must be logged in to view leaderboard.

    Args:
        contest_id: Contest ID

    Returns:
        JSON response with leaderboard data
    """
    contest = Contest.query.get(contest_id)

    if not contest:
        return jsonify({'error': 'Contest not found'}), 404

    leaderboard = contest.get_leaderboard()

    return jsonify(leaderboard), 200

@contest_bp.route('/<int:contest_id>', methods=['DELETE'])
@require_auth
@handle_errors
def delete_contest(contest_id):
    """
    Delete a contest (admin or creator only)

    Args:
        contest_id: Contest ID

    Returns:
        JSON response with success message
    """
    user = request.current_user
    contest = Contest.query.get(contest_id)

    if not contest:
        return jsonify({'error': 'Contest not found'}), 404

    # Check permissions
    if not (user.is_admin() or user.is_contest_creator(contest)):
        return jsonify({'error': 'You are not allowed to delete this contest'}), 403

    try:
        # Delete associated submissions first
        Submission.query.filter_by(contest_id=contest_id).delete()

        # Delete contest
        contest.delete()

        return jsonify({'message': 'Contest deleted successfully'}), 200

    except Exception:  # pylint: disable=broad-exception-caught
        # Log error for debugging but don't expose details to client
        return jsonify({'error': 'Failed to delete contest'}), 500


def parse_date_or_none(date_str):
    """Parse a date string and return date or None when invalid."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        try:
            return datetime.fromisoformat(date_str).date()
        except ValueError:
            return None

@contest_bp.route('/<int:contest_id>', methods=['PUT'])
@require_auth
def update_contest(contest_id):  # pylint: disable=too-many-return-statements
    user = request.current_user
    try:
        if not request.is_json:
            data = request.get_json(force=True, silent=True) or {}
        else:
            data = request.get_json() or {}

        current_app.logger.debug("update_contest payload: %s", data)

        contest = Contest.query.get(contest_id)
        if not contest:
            return jsonify({'error': 'Contest not found'}), 404

        # permission: creator or admin (adjust to your auth model)
        if not (hasattr(user, 'is_admin') and user.is_admin()) and user.username != contest.created_by:
            return jsonify({'error': 'Permission denied'}), 403

        # --- Basic fields ---
        if 'name' in data:
            contest.name = data.get('name') or contest.name
        if 'project_name' in data:
            contest.project_name = data.get('project_name') or contest.project_name

        if 'description' in data:
            contest.description = data.get('description')

        rules_payload = data.get('rules', None)
        if rules_payload is not None:
            if isinstance(rules_payload, str):
                contest.set_rules({'text': rules_payload})
            elif isinstance(rules_payload, dict):
                contest.set_rules(rules_payload)
            else:
                contest.set_rules({'text': ''})

        if "allowed_submission_type" in data:
            new_type = data.get("allowed_submission_type", "both")

            # Validate only allowed values
            if new_type not in ["new", "expansion", "both"]:
                return jsonify({"error": "Invalid allowed_submission_type"}), 400

            contest.allowed_submission_type = new_type

        # --- Dates ---
        if 'start_date' in data:
            parsed = parse_date_or_none(data.get('start_date'))
            if parsed is None and data.get('start_date') not in (None, ''):
                return jsonify({'error': 'Invalid start_date format'}), 400
            contest.start_date = parsed

        if 'end_date' in data:
            parsed = parse_date_or_none(data.get('end_date'))
            if parsed is None and data.get('end_date') not in (None, ''):
                return jsonify({'error': 'Invalid end_date format'}), 400
            contest.end_date = parsed

        if contest.start_date and contest.end_date:
            if contest.start_date >= contest.end_date:
                return jsonify({'error': 'start_date must be < end_date'}), 400

        if 'marks_setting_accepted' in data:
            try:
                contest.marks_setting_accepted = int(data.get('marks_setting_accepted') or 0)
            except (TypeError, ValueError):
                return jsonify({'error': 'marks_setting_accepted must be integer'}), 400

        if 'marks_setting_rejected' in data:
            try:
                contest.marks_setting_rejected = int(data.get('marks_setting_rejected') or 0)
            except (TypeError, ValueError):
                return jsonify({'error': 'marks_setting_rejected must be integer'}), 400

        # --- Jury members: accept list or comma string ---
        if 'jury_members' in data:
            jury_members_value = data.get('jury_members')
            if isinstance(jury_members_value, list):
                contest.set_jury_members(jury_members_value)
            elif isinstance(jury_members_value, str):
                arr = [x.strip() for x in jury_members_value.split(',') if x.strip()]
                contest.set_jury_members(arr)
            else:
                contest.set_jury_members([])

        # --- Code link ---
        if 'code_link' in data:
            link = data.get('code_link')
            contest.code_link = link.strip() if isinstance(link, str) and link.strip() else None

        # Persist
        db.session.add(contest)
        db.session.commit()

        current_app.logger.info("Contest %s updated by %s", contest_id, user.username)
        return jsonify({'message': 'Contest updated', 'contest': contest.to_dict()}), 200

    except Exception as exc:  # pylint: disable=broad-exception-caught
        current_app.logger.error("Error updating contest %s: %s", contest_id, exc)
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500



@contest_bp.route('/<int:contest_id>/submit', methods=['POST'])
@require_auth
@handle_errors
@validate_json_data(['article_link'])
def submit_to_contest(contest_id):  # pylint: disable=too-many-return-statements
    """
    Submit an entry to a contest

    This endpoint accepts only the article URL and automatically fetches
    article information (title, author, etc.) from MediaWiki API.

    Args:
        contest_id: Contest ID

    Expected JSON data:
        article_link: URL to the submitted article

    Returns:
        JSON response with success message and submission ID
    """
    import requests
    from urllib.parse import urlparse

    user = request.current_user
    data = request.validated_data

    # Get contest
    contest = Contest.query.get(contest_id)
    if not contest:
        return jsonify({'error': 'Contest not found'}), 404

    # Validate submission data
    article_link = data['article_link'].strip()

    if not article_link:
        return jsonify({'error': 'Article link is required'}), 400

    # Basic URL validation
    if not (article_link.startswith('http://') or article_link.startswith('https://')):
        return jsonify({'error': 'Article link must be a valid URL'}), 400

    # Check if contest is active
    if not contest.is_active():
        if contest.is_upcoming():
            return jsonify({'error': 'Contest has not started yet'}), 400
        if contest.is_past():
            return jsonify({'error': 'Contest has ended'}), 400
        return jsonify({'error': 'Contest is not active'}), 400

    # Check if user already submitted to this contest
    existing_submission = Submission.query.filter_by(
        user_id=user.id,
        contest_id=contest_id
    ).first()

    if existing_submission:
        return jsonify({'error': 'You have already submitted to this contest'}), 400

    # Fetch article information from MediaWiki API
    article_title = None
    article_author = None
    article_created_at = None
    article_word_count = None
    article_page_id = None
    article_size_at_start = None
    article_expansion_bytes = None

    # MediaWiki API fetching has deep nesting due to complex error handling
    # pylint: disable=too-many-nested-blocks
    try:
        # Extract page title from URL using shared utility function
        page_title = extract_page_title_from_url(article_link)

        if page_title:
            # Parse the article URL to extract base URL
            url_obj = urlparse(article_link)
            base_url = f"{url_obj.scheme}://{url_obj.netloc}"

            # Build MediaWiki API URL
            api_url = f"{base_url}/w/api.php"

            # Build API parameters using shared utility function
            api_params = build_mediawiki_revisions_api_params(page_title)
            # Add additional parameters specific to this endpoint
            api_params['inprop'] = 'url|displaytitle'

            # Make request to MediaWiki API using shared headers
            headers = get_mediawiki_headers()
            response = requests.get(api_url, params=api_params, headers=headers, timeout=10)

            if response.status_code == 200:
                api_data = response.json()

                # Check for API errors
                if 'error' not in api_data:
                    # Handle formatversion=2 (array) or formatversion=1 (object)
                    pages = api_data.get('query', {}).get('pages', [])
                    if pages:
                        # Handle both array (formatversion=2) and object (formatversion=1) formats
                        if isinstance(pages, list):
                            # formatversion=2: pages is an array
                            if len(pages) > 0:
                                page_data = pages[0]
                                page_id = str(page_data.get('pageid', ''))
                            else:
                                page_data = None
                        else:
                            # formatversion=1: pages is an object with page IDs as keys
                            page_id = list(pages.keys())[0]
                            page_data = pages[page_id]

                        # Check if page exists
                        # In formatversion=2, missing pages have 'missing': True
                        # In formatversion=1, missing pages have pageid: -1
                        is_missing = page_data.get('missing', False) if page_data else True
                        has_valid_pageid = page_id and page_id != '-1' and page_id != ''

                        if page_data and has_valid_pageid and not is_missing:
                            # Extract article information
                            article_title = page_data.get('title', page_title)

                            # Get revision information
                            # With formatversion=2, revisions is an array
                            # With rvdir='older', revisions[0] is the newest (latest) revision
                            revisions = page_data.get('revisions', [])
                            if revisions and len(revisions) > 0:
                                # Get latest revision (newest) for word count
                                # With rvdir='older', the first revision is the newest
                                latest_revision = revisions[0]

                                # Get word count from latest revision (most current size)
                                article_word_count = latest_revision.get('size', 0)

                                # Get latest revision (newest) for author at submission time
                                # Use shared utility function to extract author from latest revision
                                # This gets the author who made the most recent edit at submission time
                                article_author = get_latest_revision_author(revisions)
                                if not article_author:
                                    article_author = 'Unknown'

                                # Get oldest revision for creation date
                                if len(revisions) > 1:
                                    oldest_revision = revisions[-1]
                                else:
                                    oldest_revision = revisions[0]

                                # Get creation date from oldest revision
                                article_created_at = oldest_revision.get('timestamp', '')
                                article_page_id = page_id

                                # Debug logging to help diagnose issues
                                try:
                                    current_app.logger.info(
                                        f'Fetched article info: title={article_title}, '
                                        f'author={article_author}, word_count={article_word_count}, '
                                        f'created={article_created_at}, '
                                        f'revisions_count={len(revisions)}'
                                    )
                                    current_app.logger.debug(
                                        f'Latest revision size: {latest_revision.get("size")}, '
                                        f'Oldest revision timestamp: {oldest_revision.get("timestamp")}'
                                    )
                                except Exception:  # pylint: disable=broad-exception-caught
                                    # Logging failure shouldn't break the flow
                                    pass
                            else:
                                # No revisions found - try alternative API call to get revisions
                                # Sometimes revisions aren't returned in the first query
                                try:
                                    # Make a second API call specifically for revisions
                                    # Get 2 revisions: newest (for word count) and oldest (for author/creation)
                                    rev_api_params = {
                                        'action': 'query',
                                        'titles': page_title,
                                        'format': 'json',
                                        'formatversion': '2',
                                        'prop': 'revisions',
                                        'rvprop': 'timestamp|user|userid|size',
                                        'rvlimit': '2',  # Get 2 revisions: newest and oldest
                                        'rvdir': 'older',  # Start from newest, get newest first
                                        'redirects': 'true'
                                    }
                                    rev_response = requests.get(
                                        api_url, params=rev_api_params, headers=headers, timeout=10
                                    )
                                    if rev_response.status_code == 200:
                                        rev_data = rev_response.json()
                                        rev_pages = rev_data.get('query', {}).get('pages', [])
                                        if rev_pages and len(rev_pages) > 0:
                                            rev_page = rev_pages[0]
                                            rev_revisions = rev_page.get('revisions', [])
                                            if rev_revisions and len(rev_revisions) > 0:
                                                # Get latest revision (newest) for word count
                                                # With rvdir='older', the first revision is the newest
                                                latest_rev = rev_revisions[0]

                                                # Get word count from latest revision (most current size)
                                                article_word_count = latest_rev.get('size', 0)

                                                # Get latest revision (newest) for author at submission time
                                                # With rvdir='older', the first revision is the newest (latest)
                                                latest_rev = rev_revisions[0]

                                                # Extract author from latest revision (most recent edit)
                                                # This gets the author who made the most recent edit at submission time
                                                user_id_val = latest_rev.get('userid')
                                                article_author = (
                                                    latest_rev.get('user') or
                                                    (f"User ID: {user_id_val}" if user_id_val else 'Unknown')
                                                )

                                                # Get creation date from oldest revision (for historical reference)
                                                # If we have multiple revisions, the last one in the array is the oldest
                                                # If we only have one revision, it's both the newest and oldest
                                                if len(rev_revisions) > 1:
                                                    oldest_rev = rev_revisions[-1]
                                                else:
                                                    oldest_rev = rev_revisions[0]
                                                article_created_at = oldest_rev.get('timestamp', '')
                                                article_page_id = page_id

                                                try:
                                                    current_app.logger.info(
                                                        f'Got revision data from second API call: '
                                                        f'author={article_author}'
                                                    )
                                                except Exception:  # pylint: disable=broad-exception-caught
                                                    # Logging failure shouldn't break the flow
                                                    pass
                                except Exception as rev_err:  # pylint: disable=broad-exception-caught
                                    # If second API call fails, log it but continue
                                    try:
                                        current_app.logger.warning(
                                            f'Failed to get revisions from second API call: '
                                            f'{str(rev_err)}'
                                        )
                                    except Exception:  # pylint: disable=broad-exception-caught
                                        # Logging failure shouldn't break the flow
                                        pass

                                # Log if still no revisions found
                                if not article_author or article_author == 'Unknown':
                                    try:
                                        current_app.logger.warning(
                                            f'No revisions found for page: {page_title}, '
                                            f'page_data keys: {list(page_data.keys())}, '
                                            f'missing={is_missing}'
                                        )
                                    except Exception:  # pylint: disable=broad-exception-caught
                                        # Logging failure shouldn't break the flow
                                        pass
                        else:
                            # Page is missing or doesn't exist
                            try:
                                current_app.logger.warning(
                                    f'Page not found or missing: {page_title}, '
                                    f'page_id={page_id}, missing={is_missing}'
                                )
                            except Exception:  # pylint: disable=broad-exception-caught
                                # Logging failure shouldn't break the flow
                                pass

        # If we couldn't fetch title from API, use a fallback
        if not article_title:
            # Try to extract from URL as fallback
            if page_title:
                article_title = page_title.replace('_', ' ')
            else:
                article_title = 'Article'  # Last resort fallback

    except Exception as error:  # pylint: disable=broad-exception-caught
        # If MediaWiki API fetch fails, we'll still create the submission
        # but with limited information
        # Log the error but don't fail the submission
        try:
            current_app.logger.warning(
                f'Failed to fetch article info from MediaWiki API: {str(error)}'
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # Logging failure shouldn't break the flow
            pass

        # Use fallback title
        if not article_title:
            article_title = 'Article'

    # Calculate expansion (bytes added between contest start and submission time)
    # Expansion = size at submission time - size at contest start
    if contest.start_date and article_link and article_page_id:
        try:
            from datetime import time

            # Convert contest start_date (Date) to datetime at start of day (00:00:00 UTC)
            # This ensures we get the article size at the beginning of the contest start date
            contest_start_datetime = datetime.combine(contest.start_date, time.min)

            # Get submission time (current time when submission is being created)
            submission_datetime = datetime.utcnow()

            # Get article size at contest start
            size_at_start = get_article_size_at_timestamp(article_link, contest_start_datetime)
            article_size_at_start = size_at_start  # Store the size at contest start

            # Get article size at submission time
            # Use the current article_word_count if available, otherwise query API
            size_at_submission = article_word_count
            if size_at_submission is None:
                size_at_submission = get_article_size_at_timestamp(article_link, submission_datetime)

            # Calculate expansion bytes
            # At submission time, expansion bytes should be 0 since the article hasn't changed yet
            # Expansion bytes will be updated on refresh to show changes since submission
            article_expansion_bytes = 0

            # Log expansion calculation for debugging
            try:
                current_app.logger.info(
                    f'Expansion calculation: size_at_start={size_at_start}, '
                    f'size_at_submission={size_at_submission}, '
                    f'expansion={article_expansion_bytes}'
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        except Exception as exp_error:  # pylint: disable=broad-exception-caught
            # If expansion calculation fails, log but don't fail submission
            try:
                current_app.logger.warning(
                    f'Failed to calculate expansion: {str(exp_error)}'
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            article_expansion_bytes = None

    # Create submission with fetched information
    try:
        submission = Submission(
            user_id=user.id,
            contest_id=contest_id,
            article_title=article_title,
            article_link=article_link,
            status='pending',
            article_author=article_author,
            article_created_at=article_created_at,
            article_word_count=article_word_count,
            article_page_id=article_page_id,
            article_size_at_start=article_size_at_start,
            article_expansion_bytes=article_expansion_bytes
        )

        submission.save()

        # Debug: Log what was saved
        try:
            current_app.logger.info(
                f'Submission saved: id={submission.id}, '
                f'author={submission.article_author}, '
                f'word_count={submission.article_word_count}'
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # Logging failure shouldn't break the flow
            pass

        return jsonify({
            'message': 'Submission created successfully',
            'submissionId': submission.id,
            'contest_id': contest_id,
            'article_title': article_title,
            'article_author': article_author,
            'article_word_count': article_word_count,
            'article_created_at': article_created_at,
            'article_expansion_bytes': article_expansion_bytes
        }), 201

    except Exception:  # pylint: disable=broad-exception-caught
        # Log error for debugging but don't expose details to client
        return jsonify({'error': 'Failed to create submission'}), 500

@contest_bp.route('/<int:contest_id>/submissions', methods=['GET'])
@require_auth
@handle_errors
def get_contest_submissions(contest_id):
    """
    Get all submissions for a specific contest (admin, jury, or creator only)

    Args:
        contest_id: Contest ID

    Returns:
        JSON response with submissions data
    """
    user = request.current_user

    # Validate contest access and permissions using shared utility function
    # This eliminates duplicate code across different route files
    contest, error_response = validate_contest_submission_access(contest_id, user, Contest)
    if error_response:
        return error_response

    # Get submissions with user information
    submissions = db.session.query(
        Submission,
        User.username,
        User.email
    ).join(User).filter(
        Submission.contest_id == contest_id
    ).order_by(Submission.submitted_at.desc()).all()

    submissions_data = []
    for submission, username, email in submissions:
        submission_data = submission.to_dict(include_user_info=True)
        submission_data.update({
            'username': username,
            'email': email,
            'contest_name': contest.name
        })
        submissions_data.append(submission_data)

    return jsonify(submissions_data), 200
