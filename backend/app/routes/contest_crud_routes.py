"""
Contest CRUD routes for WikiContest Application.
"""

from datetime import datetime, timezone
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
    validate_template_link,
)
from app.utils.url_validation import validate_wiki_url
from app.services.outreach_dashboard import (
    validate_outreach_url,
)
from app.routes._contest_helpers import validate_date_string, parse_date_or_none


# Create Flask blueprint
contest_crud_bp = Blueprint("contest_crud", __name__)


@contest_crud_bp.route("/", methods=["GET"])
@handle_errors
def get_all_contests():
    """
    Get all contests categorized by status (current, upcoming, past)

    Query params:
        page (int): Page number, default 1
        per_page (int): Items per page, default 20, max 100

    Returns:
        JSON response with contests categorized by status
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    # Fetch paginated contests, newest first
    pagination = Contest.query.order_by(Contest.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    contests = pagination.items

    # Categorize contests by status
    current = []
    upcoming = []
    past = []

    for contest in contests:
        contest_data = contest.to_dict()

        # Categorize based on date ranges
        if contest.is_active():
            current.append(contest_data)
        elif contest.is_upcoming():
            upcoming.append(contest_data)
        elif contest.is_past():
            past.append(contest_data)

    # Return categorized contests with pagination metadata and caching headers
    response = jsonify({
        "contests": {"current": current, "upcoming": upcoming, "past": past},
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages,
    })
    response.headers['Cache-Control'] = 'public, max-age=60'
    return response, 200

@contest_crud_bp.route("/<int:contest_id>", methods=["GET"])
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
    contest = db.session.get(Contest, contest_id)

    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    response = jsonify(contest.to_dict())
    response.headers['Cache-Control'] = 'public, max-age=60'
    return response, 200


@contest_crud_bp.route("/name/<name>", methods=["GET"])
@require_auth
@handle_errors
def get_contest_by_name(name):
    """
    Get a specific contest by name (slugified URL format)

    Handles various name formats and special characters by normalizing slugs
    Requires authentication - users must be logged in to view contest details.

    Args:
        name: Contest name in slug format (e.g., "my-contest-2024")

    Returns:
        JSON response with contest data
    """
    import re

    # Fetch all contests for slug matching
    contests = Contest.query.all()
    contest = None

    # Normalize the input slug (lowercase, collapse multiple hyphens)
    normalized_slug = re.sub(r"[-\s]+", "-", name.lower().strip())

    # Find matching contest by generating slug from each contest name
    for contest_item in contests:
        # Generate slug using same logic as frontend
        contest_slug = contest_item.name.lower().strip()
        contest_slug = re.sub(r"\s+", "-", contest_slug)  # Spaces to hyphens
        contest_slug = re.sub(r"[^\w\-]+", "", contest_slug)  # Remove special chars
        contest_slug = re.sub(r"\-\-+", "-", contest_slug)  # Collapse hyphens
        contest_slug = contest_slug.strip("-")  # Remove leading/trailing hyphens

        # Compare normalized slugs
        if contest_slug == normalized_slug:
            contest = contest_item
            break

    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    response = jsonify(contest.to_dict())
    response.headers['Cache-Control'] = 'public, max-age=60'
    return response, 200

@contest_crud_bp.route("/<int:contest_id>/leaderboard", methods=["GET"])
@require_auth
@handle_errors
def get_contest_leaderboard_detailed(contest_id):
    """
    Get detailed leaderboard for a contest with user statistics

    Supports filtering, sorting, and pagination of results

    Query Parameters:
        filter: 'reviewed', 'pending', or 'all' (default: 'all')
        min_marks: Minimum marks threshold (optional)
        sort_by: 'marks' or 'submissions' (default: 'marks')
        page: Page number for pagination (default: 1)
        per_page: Results per page (default: 50)

    Returns:
        JSON response with:
        - contest_stats: Overall contest statistics
        - leaderboard: Ranked list of users with their stats
        - pagination: Pagination metadata
    """
    from sqlalchemy import func, case

    # Verify contest exists
    contest = db.session.get(Contest, contest_id)
    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    # Parse and validate query parameters
    filter_type = request.args.get("filter", "all")
    min_marks = request.args.get("min_marks", type=int)
    sort_by = request.args.get("sort_by", "marks")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Build base query - aggregate submissions per user
    base_query = (
        db.session.query(
            User.id.label("user_id"),
            User.username,
            func.count(Submission.id).label("total_submissions"),
            func.sum(Submission.score).label("total_marks"),
            func.sum(
                case((Submission.status.in_(["accepted", "rejected"]), 1), else_=0)
            ).label("reviewed_count"),
            func.sum(case((Submission.status == "pending", 1), else_=0)).label(
                "pending_count"
            ),
        )
        .select_from(User)
        .join(Submission, User.id == Submission.user_id)
        .filter(Submission.contest_id == contest_id)
        .group_by(User.id, User.username)
    )

    # Apply status filter
    if filter_type == "reviewed":
        # Only users with at least one reviewed submission
        base_query = base_query.having(
            func.sum(
                case((Submission.status.in_(["accepted", "rejected"]), 1), else_=0)
            )
            > 0
        )
    elif filter_type == "pending":
        # Only users with at least one pending submission
        base_query = base_query.having(
            func.sum(case((Submission.status == "pending", 1), else_=0)) > 0
        )

    # Apply minimum marks filter
    if min_marks is not None:
        base_query = base_query.having(func.sum(Submission.score) >= min_marks)

    # Apply sorting (marks descending by default)
    if sort_by == "submissions":
        base_query = base_query.order_by(
            func.count(Submission.id).desc(), func.sum(Submission.score).desc()
        )
    else:  # Default: sort by marks
        base_query = base_query.order_by(
            func.sum(Submission.score).desc(), func.count(Submission.id).desc()
        )

    # Execute query with pagination
    paginated = base_query.paginate(page=page, per_page=per_page, error_out=False)

    # Build leaderboard with sequential ranks
    leaderboard = []
    for index, row in enumerate(paginated.items, start=(page - 1) * per_page + 1):
        leaderboard.append(
            {
                "rank": index,
                "user_id": row.user_id,
                "username": row.username,
                "total_submissions": row.total_submissions or 0,
                "total_marks": int(row.total_marks or 0),
                "reviewed_count": row.reviewed_count or 0,
                "pending_count": row.pending_count or 0,
            }
        )

    # Get contest-wide statistics
    contest_stats_query = (
        db.session.query(
            func.count(Submission.id).label("total_submissions"),
            func.sum(
                case((Submission.status.in_(["accepted", "rejected"]), 1), else_=0)
            ).label("total_reviewed"),
            func.sum(case((Submission.status == "pending", 1), else_=0)).label(
                "total_pending"
            ),
            func.sum(Submission.score).label("total_marks_awarded"),
        )
        .filter(Submission.contest_id == contest_id)
        .first()
    )

    contest_stats = {
        "total_submissions": contest_stats_query.total_submissions or 0,
        "total_reviewed": contest_stats_query.total_reviewed or 0,
        "total_pending": contest_stats_query.total_pending or 0,
        "total_marks_awarded": int(contest_stats_query.total_marks_awarded or 0),
    }

    return (
        jsonify(
            {
                "contest": {
                    "id": contest.id,
                    "name": contest.name,
                    "status": contest.get_status(),
                },
                "contest_stats": contest_stats,
                "leaderboard": leaderboard,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_pages": paginated.pages,
                    "total_results": paginated.total,
                },
                "filters": {
                    "filter_type": filter_type,
                    "min_marks": min_marks,
                    "sort_by": sort_by,
                },
            }
        ),
        200,
    )


@contest_crud_bp.route("/", methods=["POST"])
@require_auth
@handle_errors
@validate_json_data(["name", "project_name", "jury_members"])
def create_contest():
    """
    Create a new contest with validation and initialization

    Validates all required fields, jury members, dates, categories,
    and scoring parameters before creating the contest

    Only trusted members and superadmins can create contests.
    Regular users can still submit and participate in contests.

    Expected JSON data:
        name: Name of the contest (required)
        project_name: Name of the associated project (required)
        jury_members: List of jury member usernames (required)
        description: Optional description
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        rules: Optional rules object
        marks_setting_accepted: Points for accepted submissions (default: 0)
        marks_setting_rejected: Points for rejected submissions (default: 0)
        min_byte_count: Minimum article byte count (required)
        min_reference_count: Minimum reference count (default: 0)
        categories: List of MediaWiki category URLs (optional)
        scoring_parameters: Multi-parameter scoring config (optional)
        organizers: Additional organizer usernames (optional)

    Returns:
        JSON response with success message and contest ID
    """
    user = request.current_user
    data = request.validated_data

    # -----------------------------------------------------------------------
    # Check Trusted Member Status
    # -----------------------------------------------------------------------
    # Only trusted members and superadmins can create contests
    if not user.can_create_contests():
        return jsonify({
            'error': 'Only trusted members can create contests. Please request trusted member status or contact a superadmin.'
        }), 403

    # -----------------------------------------------------------------------
    # Validate Required Fields
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
    # Parse Optional Fields
    # -----------------------------------------------------------------------

    # Handle description (can be None, empty string, or text)
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

    # Parse rules (store as dict, converted to JSON in model)
    rules = data.get("rules", {})
    if not isinstance(rules, dict):
        rules = {}

    # -----------------------------------------------------------------------
    # Parse Scoring Settings
    # -----------------------------------------------------------------------

    marks_accepted = data.get("marks_setting_accepted", 0)
    marks_rejected = data.get("marks_setting_rejected", 0)
    allowed_submission_type = data.get("allowed_submission_type", "both")

    try:
        marks_accepted = int(marks_accepted)
        marks_rejected = int(marks_rejected)
    except (ValueError, TypeError):
        return jsonify({"error": "Marks settings must be valid integers"}), 400

    # -----------------------------------------------------------------------
    # Parse Article Requirements
    # -----------------------------------------------------------------------

    # Minimum byte count (required field)
    min_byte_count = data.get("min_byte_count")

    if min_byte_count is None:
        return jsonify({"error": "Minimum byte count is required"}), 400

    try:
        min_byte_count = int(min_byte_count)
        if min_byte_count < 0:
            return jsonify({"error": "Minimum byte count must be non-negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Minimum byte count must be a valid integer"}), 400

    # Minimum reference count (optional, default 0 = no requirement)
    min_reference_count = data.get("min_reference_count", 0)

    try:
        min_reference_count = int(min_reference_count)
        if min_reference_count < 0:
            return (
                jsonify({"error": "Minimum reference count must be non-negative"}),
                400,
            )
    except (ValueError, TypeError):
        return (
            jsonify({"error": "Minimum reference count must be a valid integer"}),
            400,
        )

    # -----------------------------------------------------------------------
    # Validate Categories (Optional)
    # -----------------------------------------------------------------------

    categories = data.get("categories", [])
    if not isinstance(categories, list):
        categories = []
    # Filter out empty strings
    categories = [c for c in categories if isinstance(c, str) and c.strip()]

    # Validate each category URL format (only if categories are provided)
    for category_url in categories:
        if not (
            category_url.startswith("http://") or category_url.startswith("https://")
        ):
            return (
                jsonify({"error": "All category URLs must be valid HTTP/HTTPS URLs"}),
                400,
            )

    scoring_parameters = data.get("scoring_parameters")

    if scoring_parameters:
        if not isinstance(scoring_parameters, dict):
            return jsonify({"error": "Scoring parameters must be an object"}), 400

        # Validate multi-parameter scoring structure
        if scoring_parameters.get("enabled"):
            current_app.logger.info(f"[SCORING CREATE] Multi-parameter enabled")

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

            # Validate parameter weights sum to 100
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
    else:
        #  If no scoring_parameters provided, set to None (will use simple scoring)
        scoring_parameters = None

    # -----------------------------------------------------------------------
    # Validate Automated Settings (Optional)
    # -----------------------------------------------------------------------

    automated_settings = data.get("automated_settings")

    if automated_settings:
        if not isinstance(automated_settings, dict):
            return jsonify({"error": "Automated settings must be an object"}), 400

        # Validate automated scoring structure if enabled
        if automated_settings.get("enabled"):
            current_app.logger.info(f"[AUTOMATED CREATE] Automated scoring enabled")

            # Validate eligibility section
            eligibility = automated_settings.get("eligibility", {})
            if not isinstance(eligibility, dict):
                eligibility = {}

            # Validate evaluation section
            evaluation = automated_settings.get("evaluation", {})
            if not isinstance(evaluation, dict):
                evaluation = {}

            # Validate numeric values in eligibility
            # NOTE: min_bytes and min_references are intentionally NOT included here.
            # The automated evaluation engine reads those from the common contest fields
            # (min_byte_count, min_reference_count) set via the UI, which are shared
            # across all three scoring modes. This avoids the redundancy of having
            # two separate sets of fields for the same thresholds.
            # See PR #198 Comment #13 for full context.
            for field in ["min_edits", "min_outgoing_links"]:
                value = eligibility.get(field)
                if value is not None:
                    try:
                        eligibility[field] = int(value)
                        if eligibility[field] < 0:
                            return jsonify({"error": f"{field} must be non-negative"}), 400
                    except (ValueError, TypeError):
                        return jsonify({"error": f"{field} must be a valid integer"}), 400

            # Validate numeric values in evaluation
            for field in ["points_per_accepted", "points_per_byte", "points_per_incoming_link",
                          "points_per_outgoing_link", "points_per_category", "points_per_new_reference",
                          "points_per_reused_reference", "points_per_infobox", "points_per_image"]:
                value = evaluation.get(field)
                if value is not None:
                    try:
                        evaluation[field] = float(value)
                        if evaluation[field] < 0:
                            return jsonify({"error": f"{field} must be non-negative"}), 400
                    except (ValueError, TypeError):
                        return jsonify({"error": f"{field} must be a valid number"}), 400

            # Update with validated values
            automated_settings["eligibility"] = eligibility
            automated_settings["evaluation"] = evaluation

            # When automated mode is enabled, scoring_parameters should be null
            scoring_parameters = None
    else:
        automated_settings = None

    # -----------------------------------------------------------------------
    # Create Contest
    # -----------------------------------------------------------------------

    # Parse template_link (optional)
    # If provided, validate that it points to a valid Wiki template page
    template_link = data.get("template_link")
    if template_link:
        template_link = template_link.strip()
        if template_link:  # Non-empty after strip
            validation_result = validate_template_link(template_link)
            if not validation_result["valid"]:
                return (
                    jsonify(
                        {
                            "error": f"Invalid template link: {validation_result['error']}"
                        }
                    ),
                    400,
                )
        else:
            template_link = None  # Empty string becomes None

    # Parse outreach_dashboard_url (optional)
    outreach_dashboard_url = data.get("outreach_dashboard_url")
    if outreach_dashboard_url:
        outreach_dashboard_url = outreach_dashboard_url.strip()
        if outreach_dashboard_url:  # Non-empty after strip
            validation_result = validate_outreach_url(outreach_dashboard_url)
            if not validation_result["valid"]:
                return (
                    jsonify(
                        {
                            "error": f"Invalid Outreach Dashboard URL: {validation_result['error']}"
                        }
                    ),
                    400,
                )
        else:
            outreach_dashboard_url = None  # Empty string becomes None
    else:
        outreach_dashboard_url = None

    # Create contest
    try:
        # Parse additional organizers (creator is automatically added)
        additional_organizers = data.get("organizers", [])
        if not isinstance(additional_organizers, list):
            additional_organizers = []

        # Create contest instance
        contest = Contest(
            name=name,
            project_name=project_name,
            created_by=user.username,
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
            outreach_dashboard_url=outreach_dashboard_url,
            scoring_parameters=scoring_parameters,
            automated_settings=automated_settings,
            organizers=additional_organizers,
            min_reference_count=min_reference_count,
        )

        # Save to database
        saved_params = contest.get_scoring_parameters()
        current_app.logger.info(f"[SCORING CREATE] Saved to DB: {saved_params}")
        contest.save()
        return (
            jsonify(
                {"message": "Contest created successfully", "contestId": contest.id}
            ),
            201,
        )

    except Exception:  # pylint: disable=broad-exception-caught
        # Log error internally but don't expose details to client
        return jsonify({"error": "Failed to create contest"}), 500

@contest_crud_bp.route("/<int:contest_id>", methods=["DELETE"])
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
    contest = db.session.get(Contest, contest_id)

    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    # Check permissions - only admins or contest organizers can delete
    if not (user.is_admin() or user.is_contest_organizer(contest)):
        return jsonify({"error": "You are not allowed to delete this contest"}), 403

    try:
        # Delete associated submissions first to maintain referential integrity
        Submission.query.filter_by(contest_id=contest_id).delete()

        # Delete the contest itself
        contest.delete()

        return jsonify({"message": "Contest deleted successfully"}), 200

    except Exception:  # pylint: disable=broad-exception-caught
        # Log error for debugging but don't expose details to client
        return jsonify({"error": "Failed to delete contest"}), 500
@contest_crud_bp.route("/<int:contest_id>", methods=["PUT"])
@require_auth
@handle_errors
def update_contest(contest_id):
    user = request.current_user
    try:
        # Handle both JSON and non-JSON content types
        if not request.is_json:
            data = request.get_json(force=True, silent=True) or {}
        else:
            data = request.get_json() or {}

        current_app.logger.debug("update_contest payload: %s", data)

        contest = db.session.get(Contest, contest_id)
        if not contest:
            return jsonify({"error": "Contest not found"}), 404

        # Permission check: creator or admin only
        if (
            not (hasattr(user, "is_admin") and user.is_admin())
            and user.username != contest.created_by
        ):
            return jsonify({"error": "Permission denied"}), 403

        # --- CRITICAL: Scoring System Change Validation ---
        if "scoring_parameters" in data:
            # Get current and proposed scoring modes
            current_mode = contest.get_scoring_mode()

            proposed_params = data.get("scoring_parameters")
            if proposed_params is None:
                proposed_mode = "simple"
            elif (
                isinstance(proposed_params, dict)
                and proposed_params.get("enabled") is True
            ):
                proposed_mode = "multi_parameter"
            else:
                proposed_mode = "simple"

            # Check if mode is changing
            if current_mode != proposed_mode:
                can_change, reason = contest.can_change_scoring_system()
                if not can_change:
                    return (
                        jsonify(
                            {
                                "error": reason,
                                "current_mode": current_mode,
                                "attempted_mode": proposed_mode,
                                "locked": True,
                            }
                        ),
                        400,
                    )

        # --- Basic Metadata Fields ---
        if "name" in data:
            contest.name = data.get("name") or contest.name
        if "project_name" in data:
            contest.project_name = data.get("project_name") or contest.project_name

        if "description" in data:
            contest.description = data.get("description")

        # Rules can be submitted as string or dict
        rules_payload = data.get("rules", None)
        if rules_payload is not None:
            if isinstance(rules_payload, str):
                contest.set_rules({"text": rules_payload})
            elif isinstance(rules_payload, dict):
                contest.set_rules(rules_payload)
            else:
                contest.set_rules({"text": ""})

        # Submission type validation
        if "allowed_submission_type" in data:
            new_type = data.get("allowed_submission_type", "both")

            # Validate only allowed values
            if new_type not in ["new", "expansion", "both"]:
                return jsonify({"error": "Invalid allowed_submission_type"}), 400

            contest.allowed_submission_type = new_type

        # --- Date Fields ---
        if "start_date" in data:
            parsed = parse_date_or_none(data.get("start_date"))
            if parsed is None and data.get("start_date") not in (None, ""):
                return jsonify({"error": "Invalid start_date format"}), 400
            contest.start_date = parsed

        if "end_date" in data:
            parsed = parse_date_or_none(data.get("end_date"))
            if parsed is None and data.get("end_date") not in (None, ""):
                return jsonify({"error": "Invalid end_date format"}), 400
            contest.end_date = parsed

        # Ensure start_date is before end_date
        if contest.start_date and contest.end_date:
            if contest.start_date >= contest.end_date:
                return jsonify({"error": "start_date must be < end_date"}), 400

        # --- Scoring Settings ---
        if "marks_setting_accepted" in data:
            try:
                contest.marks_setting_accepted = int(
                    data.get("marks_setting_accepted") or 0
                )
            except (TypeError, ValueError):
                return jsonify({"error": "marks_setting_accepted must be integer"}), 400

        if "marks_setting_rejected" in data:
            try:
                contest.marks_setting_rejected = int(
                    data.get("marks_setting_rejected") or 0
                )
            except (TypeError, ValueError):
                return jsonify({"error": "marks_setting_rejected must be integer"}), 400

        # --- Article Requirements ---
        # Minimum byte count requirement
        if "min_byte_count" in data:
            min_byte_count_value = data.get("min_byte_count")
            if min_byte_count_value is None or min_byte_count_value == "":
                return jsonify({"error": "Minimum byte count is required"}), 400
            try:
                min_byte_count = int(min_byte_count_value)
                if min_byte_count < 0:
                    return (
                        jsonify({"error": "Minimum byte count must be non-negative"}),
                        400,
                    )
                contest.min_byte_count = min_byte_count
            except (TypeError, ValueError):
                return jsonify({"error": "min_byte_count must be a valid integer"}), 400

        # Minimum reference count requirement
        if "min_reference_count" in data:
            min_reference_count_value = data.get("min_reference_count")
            try:
                min_reference_count = int(min_reference_count_value)
                if min_reference_count < 0:
                    return (
                        jsonify(
                            {"error": "Minimum reference count must be non-negative"}
                        ),
                        400,
                    )
                contest.min_reference_count = min_reference_count
            except (TypeError, ValueError):
                return (
                    jsonify({"error": "min_reference_count must be a valid integer"}),
                    400,
                )

        # --- Categories (Optional) ---
        if "categories" in data:
            categories_value = data.get("categories")
            if not isinstance(categories_value, list):
                categories_value = []
            # Filter out empty strings
            categories_value = [c for c in categories_value if isinstance(c, str) and c.strip()]

            # Validate each category URL format (only if categories are provided)
            for category_url in categories_value:
                if not (
                    category_url.startswith("http://")
                    or category_url.startswith("https://")
                ):
                    return (
                        jsonify(
                            {"error": "All category URLs must be valid HTTP/HTTPS URLs"}
                        ),
                        400,
                    )

            contest.set_categories(categories_value)

        # --- Template link ---
        if "template_link" in data:
            template_link_value = data.get("template_link")
            if template_link_value:
                template_link_value = template_link_value.strip()
                if template_link_value:  # Non-empty after strip
                    validation_result = validate_template_link(template_link_value)
                    if not validation_result["valid"]:
                        return (
                            jsonify(
                                {
                                    "error": f"Invalid template link: {validation_result['error']}"
                                }
                            ),
                            400,
                        )
                    contest.template_link = template_link_value
                else:
                    contest.template_link = None  # Empty string clears the field
            else:
                contest.template_link = None  # None clears the field

        # --- Outreach Dashboard URL ---
        if "outreach_dashboard_url" in data:
            outreach_url_value = data.get("outreach_dashboard_url")
            if outreach_url_value:
                outreach_url_value = outreach_url_value.strip()
                if outreach_url_value:  # Non-empty after strip
                    validation_result = validate_outreach_url(outreach_url_value)
                    if not validation_result["valid"]:
                        return (
                            jsonify(
                                {
                                    "error": f"Invalid Outreach Dashboard URL: {validation_result['error']}"
                                }
                            ),
                            400,
                        )
                    contest.outreach_dashboard_url = outreach_url_value
                else:
                    contest.outreach_dashboard_url = None  # Empty string clears the field
            else:
                contest.outreach_dashboard_url = None  # None clears the field

        # --- Jury Members ---
        # Accept both list and comma-separated string formats
        if "jury_members" in data:
            jury_members_value = data.get("jury_members")
            if isinstance(jury_members_value, list):
                contest.set_jury_members(jury_members_value)
            elif isinstance(jury_members_value, str):
                arr = [x.strip() for x in jury_members_value.split(",") if x.strip()]
                contest.set_jury_members(arr)
            else:
                contest.set_jury_members([])

        # --- Scoring Parameters (Multi-Parameter Support) ---
        if "scoring_parameters" in data:
            sp = data.get("scoring_parameters")
            # Accept explicit null to disable scoring parameters
            if sp is None:
                contest.set_scoring_parameters(None)
            elif not isinstance(sp, dict):
                return jsonify({"error": "scoring_parameters must be an object"}), 400
            else:
                # Validate multi-parameter structure if enabled
                if sp.get("enabled"):
                    params = sp.get("parameters")
                    if (
                        "parameters" not in sp
                        or not isinstance(params, list)
                        or len(params) == 0
                    ):
                        return (
                            jsonify(
                                {"error": "At least one scoring parameter is required"}
                            ),
                            400,
                        )

                    total_weight = 0
                    # Validate each parameter has required fields and valid weights
                    for param in params:
                        if not isinstance(param, dict):
                            return (
                                jsonify({"error": "Each parameter must be an object"}),
                                400,
                            )
                        if "name" not in param or "weight" not in param:
                            return (
                                jsonify(
                                    {
                                        "error": 'Each parameter must have "name" and "weight"'
                                    }
                                ),
                                400,
                            )
                        try:
                            weight = int(param["weight"])
                            if weight < 0 or weight > 100:
                                return jsonify({"error": f"Weight must be 0-100"}), 400
                            total_weight += weight
                        except (ValueError, TypeError):
                            return (
                                jsonify({"error": "Weight must be a valid integer"}),
                                400,
                            )

                    # Ensure weights sum to exactly 100%
                    if total_weight != 100:
                        return (
                            jsonify(
                                {
                                    "error": f"Weights must sum to 100, got {total_weight}"
                                }
                            ),
                            400,
                        )
                # Persist validated scoring params (model will JSON-encode)
                try:
                    contest.set_scoring_parameters(sp)
                except ValueError as ve:
                    return jsonify({"error": str(ve)}), 400

        # --- Automated Settings (Automated Scoring Mode) ---
        if "automated_settings" in data:
            as_settings = data.get("automated_settings")

            # Accept explicit null to disable automated settings
            if as_settings is None:
                contest.set_automated_settings(None)
            elif not isinstance(as_settings, dict):
                return jsonify({"error": "automated_settings must be an object"}), 400
            else:
                # Validate automated scoring structure if enabled
                if as_settings.get("enabled"):
                    # Validate eligibility section
                    eligibility = as_settings.get("eligibility", {})
                    if not isinstance(eligibility, dict):
                        eligibility = {}

                    # Validate evaluation section
                    evaluation = as_settings.get("evaluation", {})
                    if not isinstance(evaluation, dict):
                        evaluation = {}

                    # Validate numeric values in eligibility
                    for field in ["min_edits", "min_outgoing_links"]:
                        value = eligibility.get(field)
                        if value is not None:
                            try:
                                eligibility[field] = int(value)
                                if eligibility[field] < 0:
                                    return jsonify({"error": f"{field} must be non-negative"}), 400
                            except (ValueError, TypeError):
                                return jsonify({"error": f"{field} must be a valid integer"}), 400

                    # Validate numeric values in evaluation
                    for field in ["points_per_accepted", "points_per_byte", "points_per_incoming_link",
                                  "points_per_outgoing_link", "points_per_category", "points_per_new_reference",
                                  "points_per_reused_reference", "points_per_infobox", "points_per_image"]:
                        value = evaluation.get(field)
                        if value is not None:
                            try:
                                evaluation[field] = float(value)
                                if evaluation[field] < 0:
                                    return jsonify({"error": f"{field} must be non-negative"}), 400
                            except (ValueError, TypeError):
                                return jsonify({"error": f"{field} must be a valid number"}), 400

                    # Update with validated values
                    as_settings["eligibility"] = eligibility
                    as_settings["evaluation"] = evaluation

                    # When automated mode is enabled, disable multi-parameter scoring
                    contest.set_scoring_parameters(None)

                # Persist validated automated settings
                contest.set_automated_settings(as_settings)

        # --- Organizers ---
        if "organizers" in data:
            organizers_payload = data.get("organizers")

            if organizers_payload is not None:
                if isinstance(organizers_payload, list):
                    # List of usernames provided
                    contest.set_organizers(organizers_payload, contest.created_by)
                elif isinstance(organizers_payload, str):
                    # Comma-separated string provided
                    organizers_list = [
                        u.strip() for u in organizers_payload.split(",") if u.strip()
                    ]
                    contest.set_organizers(organizers_list, contest.created_by)

        # Persist all changes to database
        db.session.add(contest)
        db.session.commit()

        current_app.logger.info("Contest %s updated by %s", contest_id, user.username)
        return (
            jsonify({"message": "Contest updated", "contest": contest.to_dict()}),
            200,
        )

    except Exception as exc:  # pylint: disable=broad-exception-caught
        current_app.logger.error("Error updating contest %s: %s", contest_id, exc)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500


# ------------------------------------------------------------------------
