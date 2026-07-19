"""
Contest organizer routes for WikiContest Application.
"""

from datetime import datetime, timezone
import os
import traceback

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.middleware.auth import require_auth, require_role, handle_errors, validate_json_data
from app.models.contest import Contest
from app.models.submission import Submission
from app.models.user import User
from app.models.contest_request import ContestRequest
from app.utils import (
    validate_contest_submission_access,
    get_article_size_at_timestamp,
    extract_page_title_from_url,
    get_latest_revision_author,
    build_mediawiki_revisions_api_params,
    get_mediawiki_headers,
    validate_template_link,
    extract_template_name_from_url,
    check_article_has_template,
    prepend_template_to_article,
    extract_category_name_from_url,
    check_article_has_category,
    append_categories_to_article,
    fetch_article_metrics,
    get_article_reference_count,
    get_detailed_reference_counts,
    get_mediawiki_user_edit_count,
    get_article_image_count,
    get_article_infobox_count,
    get_article_incoming_links,
    get_article_outgoing_links,
    crawl_category_articles,
    MEDIAWIKI_API_TIMEOUT,
)
from app.utils.url_validation import validate_wiki_url
from app.routes._contest_helpers import validate_date_string, parse_date_or_none


# Create Flask blueprint
contest_org_bp = Blueprint("contest_org", __name__)


@contest_org_bp.route("/<int:contest_id>/organizers", methods=["GET"])
@require_auth
@handle_errors
def get_contest_organizers(contest_id):
    """
    Get all organizers for a specific contest

    Returns list of organizer usernames.

    Args:
        contest_id: Contest ID

    Returns:
        JSON response with list of organizer usernames
    """
    user = request.current_user

    # Get contest
    contest = Contest.query.get(contest_id)
    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    # Check permissions - must be organizer or admin
    if not (user.is_admin() or user.is_contest_organizer(contest)):
        return jsonify({"error": "Access denied"}), 403

    # Get organizers list
    organizers = contest.get_organizers()

    return (
        jsonify(
            {
                "contest_id": contest_id,
                "organizers": organizers,
                "creator": contest.created_by,
            }
        ),
        200,
    )


@contest_org_bp.route("/<int:contest_id>/organizers", methods=["POST"])
@require_auth
@handle_errors
@validate_json_data(["username"])
def add_contest_organizer(contest_id):
    """
    Add a new organizer to a contest

    Only creator and admins can add organizers.

    Expected JSON data:
        username: Username of the user to add as organizer

    Args:
        contest_id: Contest ID

    Returns:
        JSON response with success message
    """
    user = request.current_user
    data = request.validated_data

    # Get contest
    contest = Contest.query.get(contest_id)
    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    # Check permissions - must be creator or admin
    if not (user.is_admin() or user.is_contest_organizer(contest)):
        return (
            jsonify({"error": "Only the contest creator or admins can add organizers"}),
            403,
        )

    # Get username to add
    username_to_add = data["username"].strip()

    if not username_to_add:
        return jsonify({"error": "Username is required"}), 400

    # Validate user exists in the system
    from app.models.user import User

    organizer_user = User.query.filter_by(username=username_to_add).first()
    if not organizer_user:
        return jsonify({"error": f'User "{username_to_add}" not found'}), 404

    # Add organizer using model method
    success, error_message = contest.add_organizer(username_to_add)

    if not success:
        return jsonify({"error": error_message}), 400

    # Save changes to database
    contest.save()

    # Get updated organizers list
    organizers = contest.get_organizers()

    return (
        jsonify({"message": "Organizer added successfully", "organizers": organizers}),
        201,
    )


@contest_org_bp.route("/<int:contest_id>/organizers/<username>", methods=["DELETE"])
@require_auth
@handle_errors
def remove_contest_organizer(contest_id, username):
    """
    Remove an organizer from a contest

    Only creator and admins can remove organizers.
    Cannot remove creator.

    Args:
        contest_id: Contest ID
        username: Username to remove

    Returns:
        JSON response with success message
    """
    user = request.current_user

    # Get contest
    contest = Contest.query.get(contest_id)
    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    # Check permissions - must be creator or admin
    if not (user.is_admin() or user.is_contest_organizer(contest)):
        return (
            jsonify(
                {"error": "Only the contest creator or admins can remove organizers"}
            ),
            403,
        )

    # Remove organizer using model method
    success, error_message = contest.remove_organizer(username)

    if not success:
        return jsonify({"error": error_message}), 400

    # Save changes to database
    contest.save()

    # Get updated organizers list
    organizers = contest.get_organizers()

    return jsonify({
        'message': 'Organizer removed successfully',
        'organizers': organizers
    }), 200


