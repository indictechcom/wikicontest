"""
Contest request routes for WikiContest Application.
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
contest_req_bp = Blueprint("contest_req", __name__)


@contest_req_bp.route("/requests", methods=["POST"])
@require_auth
@handle_errors
@validate_json_data(["name", "project_name", "jury_members"])
def create_contest_request():
    """
    Create a contest creation request (for non-privileged users)

    Regular users who are not superadmin or trusted members can submit
    requests to create contests. Superadmins can review and approve/reject
    these requests.

    Expected JSON data: Same as create_contest endpoint

    Returns:
        JSON response with success message and request ID
    """
    user = request.current_user
    data = request.validated_data

    # -----------------------------------------------------------------------
    # Check if user already has permission to create contests
    # -----------------------------------------------------------------------
    # If user can already create contests, they shouldn't use this endpoint
    if user.can_create_contests():
        return jsonify({
            'error': 'You already have permission to create contests. Use the regular create contest endpoint.'
        }), 400

    # -----------------------------------------------------------------------
    # Validate Required Fields (same as create_contest)
    # -----------------------------------------------------------------------
    name = data["name"].strip()
    project_name = data["project_name"].strip()
    jury_members = data["jury_members"]

    if not name:
        return jsonify({"error": "Contest name is required"}), 400

    if not project_name:
        return jsonify({"error": "Project name is required"}), 400

    if not isinstance(jury_members, list) or len(jury_members) == 0:
        return (
            jsonify({"error": "Jury members must be a non-empty array of usernames"}),
            400,
        )

    # -----------------------------------------------------------------------
    # Validate Jury Members Exist in Database
    # -----------------------------------------------------------------------
    existing_users = User.query.filter(User.username.in_(jury_members)).all()
    existing_usernames = [user.username for user in existing_users]
    missing_users = [
        username for username in jury_members if username not in existing_usernames
    ]

    if missing_users:
        return (
            jsonify(
                {
                    "error": f'These jury members do not exist: {", ".join(missing_users)}'
                }
            ),
            400,
        )

    # -----------------------------------------------------------------------
    # Parse Optional Fields (same as create_contest)
    # -----------------------------------------------------------------------
    description_value = data.get("description")
    if description_value is None or description_value == "":
        description = None
    else:
        description = str(description_value).strip() or None

    # Parse and validate dates
    start_date = validate_date_string(data.get("start_date"))
    end_date = validate_date_string(data.get("end_date"))

    # Validate date logic (end must be after start)
    if start_date and end_date and start_date >= end_date:
        return jsonify({"error": "End date must be after start date"}), 400

    # Parse rules
    rules = data.get("rules", {})
    if not isinstance(rules, dict):
        rules = {}

    # Parse scoring settings
    marks_accepted = data.get("marks_setting_accepted", 0)
    marks_rejected = data.get("marks_setting_rejected", 0)
    allowed_submission_type = data.get("allowed_submission_type", "both")

    try:
        marks_accepted = int(marks_accepted)
        marks_rejected = int(marks_rejected)
    except (ValueError, TypeError):
        return jsonify({"error": "Marks settings must be valid integers"}), 400

    # Parse article requirements
    min_byte_count = data.get("min_byte_count")
    if min_byte_count is None:
        return jsonify({"error": "Minimum byte count is required"}), 400

    try:
        min_byte_count = int(min_byte_count)
        if min_byte_count < 0:
            return jsonify({"error": "Minimum byte count must be non-negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Minimum byte count must be a valid integer"}), 400

    min_reference_count = data.get("min_reference_count", 0)
    try:
        min_reference_count = int(min_reference_count)
        if min_reference_count < 0:
            return jsonify({"error": "Minimum reference count must be non-negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Minimum reference count must be a valid integer"}), 400

    # Validate categories
    categories = data.get("categories")
    if not categories or not isinstance(categories, list) or len(categories) == 0:
        return jsonify({"error": "At least one category URL is required"}), 400

    for category_url in categories:
        if not isinstance(category_url, str) or not category_url.strip():
            return (
                jsonify({"error": "All category URLs must be non-empty strings"}),
                400,
            )
        if not (
            category_url.startswith("http://") or category_url.startswith("https://")
        ):
            return (
                jsonify({"error": "All category URLs must be valid HTTP/HTTPS URLs"}),
                400,
            )

    # Validate scoring parameters (same validation as create_contest)
    scoring_parameters = data.get("scoring_parameters")
    if scoring_parameters:
        if not isinstance(scoring_parameters, dict):
            return jsonify({"error": "Scoring parameters must be an object"}), 400

        if scoring_parameters.get("enabled"):
            if "parameters" not in scoring_parameters:
                return (
                    jsonify(
                        {"error": 'Scoring parameters must include "parameters" array'}
                    ),
                    400,
                )

            parameters = scoring_parameters["parameters"]
            if not isinstance(parameters, list) or len(parameters) == 0:
                return (
                    jsonify({"error": "At least one scoring parameter is required"}),
                    400,
                )

            total_weight = 0
            for param in parameters:
                if not isinstance(param, dict):
                    return jsonify({"error": "Each parameter must be an object"}), 400
                if "name" not in param or "weight" not in param:
                    return (
                        jsonify(
                            {"error": 'Each parameter must have "name" and "weight"'}
                        ),
                        400,
                    )
                try:
                    weight = int(param["weight"])
                    if weight < 0 or weight > 100:
                        return jsonify({"error": f"Weight must be 0-100"}), 400
                    total_weight += weight
                except (ValueError, TypeError):
                    return jsonify({"error": "Weight must be a valid integer"}), 400

            if total_weight != 100:
                return (
                    jsonify({"error": f"Weights must sum to 100, got {total_weight}"}),
                    400,
                )

    # Parse template_link
    template_link = data.get('template_link')
    if template_link:
        template_link = template_link.strip()
        if template_link:
            validation_result = validate_template_link(template_link)
            if not validation_result['valid']:
                return jsonify({
                    'error': f"Invalid template link: {validation_result['error']}"
                }), 400
        else:
            template_link = None

    # -----------------------------------------------------------------------
    # Create Contest Request
    # -----------------------------------------------------------------------
    try:
        # Parse additional organizers
        additional_organizers = data.get('organizers', [])
        if not isinstance(additional_organizers, list):
            additional_organizers = []

        # Create contest request instance
        contest_request = ContestRequest(
            user_id=user.id,
            name=name,
            project_name=project_name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            rules=rules,
            marks_setting_accepted=marks_accepted,
            marks_setting_rejected=marks_rejected,
            jury_members=jury_members,
            allowed_submission_type=allowed_submission_type,
            min_byte_count=min_byte_count,
            categories=categories,
            template_link=template_link,
            scoring_parameters=scoring_parameters,
            organizers=additional_organizers,
            min_reference_count=min_reference_count,
        )

        # Save to database
        contest_request.save()

        return (
            jsonify(
                {
                    "message": "Contest creation request submitted successfully. A superadmin will review your request.",
                    "requestId": contest_request.id
                }
            ),
            201,
        )

    except Exception:  # pylint: disable=broad-exception-caught
        # Log error internally but don't expose details to client
        return jsonify({"error": "Failed to create contest request"}), 500


@contest_req_bp.route("/requests", methods=["GET"])
@require_role('superadmin')
@handle_errors
def get_contest_requests():
    """
    Get all contest creation requests (superadmin only)

    Returns:
        JSON response with list of contest requests
    """
    # Get all pending requests, ordered by creation date (newest first)
    requests = ContestRequest.query.filter_by(status='pending').order_by(
        ContestRequest.created_at.desc()
    ).all()

    return jsonify({
        'requests': [req.to_dict() for req in requests]
    }), 200


@contest_req_bp.route("/requests/<int:request_id>/approve", methods=["POST"])
@require_role('superadmin')
@handle_errors
def approve_contest_request(request_id):
    """
    Approve a contest creation request and create the contest (superadmin only)

    Args:
        request_id: Contest request ID to approve

    Returns:
        JSON response with success message and created contest ID
    """
    user = request.current_user
    contest_request = ContestRequest.query.get(request_id)

    if not contest_request:
        return jsonify({'error': 'Contest request not found'}), 404

    if contest_request.status != 'pending':
        return jsonify({
            'error': f'Request has already been {contest_request.status}'
        }), 400

    # Get the requester user to use as contest creator
    requester = User.query.get(contest_request.user_id)
    if not requester:
        return jsonify({'error': 'Requester user not found'}), 404

    # Create the contest from the request data
    try:
        contest = Contest(
            name=contest_request.name,
            project_name=contest_request.project_name,
            created_by=requester.username,
            description=contest_request.description,
            start_date=contest_request.start_date,
            end_date=contest_request.end_date,
            rules=contest_request.get_rules(),
            marks_setting_accepted=contest_request.marks_setting_accepted,
            marks_setting_rejected=contest_request.marks_setting_rejected,
            jury_members=contest_request.get_jury_members(),
            allowed_submission_type=contest_request.allowed_submission_type,
            min_byte_count=contest_request.min_byte_count,
            categories=contest_request.get_categories(),
            template_link=contest_request.template_link,
            scoring_parameters=contest_request.get_scoring_parameters(),
            organizers=contest_request.get_organizers(),
            min_reference_count=contest_request.min_reference_count,
        )

        # Save contest to database
        contest.save()

        # Update request status
        contest_request.status = 'approved'
        contest_request.reviewed_by = user.id
        contest_request.reviewed_at = datetime.utcnow()
        contest_request.save()

        return jsonify({
            'message': 'Contest request approved and contest created successfully',
            'contestId': contest.id,
            'requestId': contest_request.id
        }), 200

    except Exception as e:  # pylint: disable=broad-exception-caught
        # Log error for debugging
        current_app.logger.error(f'Error approving contest request: {str(e)}')
        return jsonify({
            'error': 'Failed to create contest from request'
        }), 500


@contest_req_bp.route("/requests/<int:request_id>/reject", methods=["POST"])
@require_role('superadmin')
@handle_errors
def reject_contest_request(request_id):
    """
    Reject a contest creation request (superadmin only)

    Args:
        request_id: Contest request ID to reject

    Expected JSON data (optional):
        rejection_reason: Reason for rejection

    Returns:
        JSON response with success message
    """
    user = request.current_user
    # Get JSON data if provided (rejection_reason is optional)
    data = request.get_json() or {}

    contest_request = ContestRequest.query.get(request_id)

    if not contest_request:
        return jsonify({'error': 'Contest request not found'}), 404

    if contest_request.status != 'pending':
        return jsonify({
            'error': f'Request has already been {contest_request.status}'
        }), 400

    # Update request status
    contest_request.status = 'rejected'
    contest_request.reviewed_by = user.id
    contest_request.reviewed_at = datetime.utcnow()
    contest_request.rejection_reason = data.get('rejection_reason', '')
    contest_request.save()

    return jsonify({
        'message': 'Contest request rejected successfully',
        'requestId': contest_request.id
    }), 200

