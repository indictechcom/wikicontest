"""
Contest organizer routes for WikiEval Application.
"""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.middleware.auth import require_auth, require_role, handle_errors, validate_json_data
from app.models.contest import Contest
from app.models.submission import Submission
from app.models.user import User
from app.models.contest_request import ContestRequest
from app.utils.url_validation import validate_wiki_url
from app.routes._contest_helpers import validate_date_string, parse_date_or_none


# Create Flask blueprint
contest_org_bp = Blueprint("contest_org", __name__)


@contest_org_bp.route("/<int:contest_id>/organizers", methods=["GET"])
@require_auth
@handle_errors
def get_contest_organizers(contest_id):
    """
    Retrieve the organizers and creator for a contest.
    
    Parameters:
        contest_id (int): Identifier of the contest.
    
    Returns:
        JSON response containing the contest ID, organizer usernames, and creator, with HTTP status 200.
        Returns an error response with HTTP status 404 if the contest does not exist or 403 if access is denied.
    """
    user = request.current_user

    # Get contest
    contest = db.session.get(Contest, contest_id)
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
                "creator": contest.creator.username if contest.creator else None,
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
    Add an existing user as an organizer of a contest.
    
    Parameters:
        contest_id (int): The ID of the contest.
    
    Returns:
        A response containing a success message and the updated organizer list.
    """
    user = request.current_user
    data = request.validated_data

    # Get contest
    contest = db.session.get(Contest, contest_id)
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
    Remove an organizer from a contest.
    
    Parameters:
        contest_id: ID of the contest.
        username: Username of the organizer to remove.
    
    Returns:
        A JSON response containing a success message and the updated organizer
        list, or an error response when the contest or organizer is unavailable
        or the user lacks permission.
    """
    user = request.current_user

    # Get contest
    contest = db.session.get(Contest, contest_id)
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


