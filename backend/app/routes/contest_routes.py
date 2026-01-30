# pylint: disable=too-many-lines,too-many-return-statements,too-many-nested-blocks
"""
Contest Routes for WikiContest Application
Handles contest creation, retrieval, and management functionality
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
    get_article_reference_count,
    MEDIAWIKI_API_TIMEOUT,
)
from app.services.outreach_dashboard import (
    validate_outreach_url,
    fetch_course_data,
    fetch_course_users,
    fetch_course_articles,
    fetch_course_uploads,
)


# ------------------------------------------------------------------------
# BLUEPRINT SETUP
# ------------------------------------------------------------------------

# Create Flask blueprint for contest-related routes
contest_bp = Blueprint("contest", __name__)


# ------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------


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
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_date_or_none(date_str):
    """
    Parse a date string with multiple format fallbacks

    Tries YYYY-MM-DD format first, then ISO format

    Args:
        date_str: Date string to parse

    Returns:
        date: Parsed date object or None if invalid
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        try:
            return datetime.fromisoformat(date_str).date()
        except ValueError:
            return None


# ------------------------------------------------------------------------
# CONTEST RETRIEVAL ROUTES
# ------------------------------------------------------------------------


@contest_bp.route("/", methods=["GET"])
@require_auth
@handle_errors
def get_all_contests():
    """
    Get all contests categorized by status (current, upcoming, past)

    Requires authentication - users must be logged in to view contests.

    Returns:
        JSON response with contests categorized by status
    """
    # Fetch all contests, newest first
    contests = Contest.query.order_by(Contest.created_at.desc()).all()

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

    return jsonify({"current": current, "upcoming": upcoming, "past": past}), 200


@contest_bp.route("/<int:contest_id>/outreach-data", methods=["GET"])
@require_auth
@handle_errors
def get_contest_outreach_data(contest_id):
    """
    Get Outreach Dashboard course data for a contest

    Requires authentication - users must be logged in to view contest details.

    Args:
        contest_id: Contest ID

    Returns:
        JSON response with Outreach Dashboard course data or error message
    """
    contest = Contest.query.get(contest_id)

    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    if not contest.outreach_dashboard_url:
        return jsonify({"error": "Contest does not have an Outreach Dashboard URL"}), 400

    # Fetch course data from Outreach Dashboard API
    result = fetch_course_data(contest.outreach_dashboard_url)

    if result["success"]:
        return jsonify({
            "success": True,
            "data": result["data"]
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": result["error"]
        }), 400


@contest_bp.route("/<int:contest_id>/outreach-users", methods=["GET"])
@require_auth
@handle_errors
def get_outreach_dashboard_users(contest_id):
    """
    Fetch Outreach Dashboard course users data for a contest.

    Args:
        contest_id: ID of the contest

    Returns:
        JSON response with Outreach Dashboard course users data or error message
    """
    contest = Contest.query.get(contest_id)

    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    if not contest.outreach_dashboard_url:
        return jsonify({"error": "Contest does not have an Outreach Dashboard URL"}), 400

    # Fetch course users data from Outreach Dashboard API
    result = fetch_course_users(contest.outreach_dashboard_url)

    if result["success"]:
        return jsonify({
            "success": True,
            "data": result["data"]
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": result["error"]
        }), 400


@contest_bp.route("/<int:contest_id>/outreach-articles", methods=["GET"])
@require_auth
@handle_errors
def get_outreach_dashboard_articles(contest_id):
    """
    Fetch Outreach Dashboard course articles data for a contest.

    Args:
        contest_id: ID of the contest

    Returns:
        JSON response with Outreach Dashboard course articles data or error message
    """
    contest = Contest.query.get(contest_id)

    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    if not contest.outreach_dashboard_url:
        return jsonify({"error": "Contest does not have an Outreach Dashboard URL"}), 400

    # Fetch course articles data from Outreach Dashboard API
    result = fetch_course_articles(contest.outreach_dashboard_url)

    if result["success"]:
        return jsonify({
            "success": True,
            "data": result["data"]
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": result["error"]
        }), 400


@contest_bp.route("/<int:contest_id>/outreach-uploads", methods=["GET"])
@require_auth
@handle_errors
def get_outreach_dashboard_uploads(contest_id):
    """
    Fetch Outreach Dashboard course uploads data for a contest.

    Args:
        contest_id: ID of the contest

    Returns:
        JSON response with Outreach Dashboard course uploads data or error message
    """
    contest = Contest.query.get(contest_id)

    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    if not contest.outreach_dashboard_url:
        return jsonify({"error": "Contest does not have an Outreach Dashboard URL"}), 400

    # Fetch course uploads data from Outreach Dashboard API
    result = fetch_course_uploads(contest.outreach_dashboard_url)

    if result["success"]:
        return jsonify({
            "success": True,
            "data": result["data"]
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": result["error"]
        }), 400


@contest_bp.route("/<int:contest_id>", methods=["GET"])
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
        return jsonify({"error": "Contest not found"}), 404

    return jsonify(contest.to_dict()), 200


@contest_bp.route("/name/<name>", methods=["GET"])
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

    return jsonify(contest.to_dict()), 200


@contest_bp.route("/<int:contest_id>/leaderboard", methods=["GET"])
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
    contest = Contest.query.get(contest_id)
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


# ------------------------------------------------------------------------
# CONTEST CREATION ROUTE
# ------------------------------------------------------------------------


@contest_bp.route("/", methods=["POST"])
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
        categories: List of MediaWiki category URLs (required)
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
    # Validate Categories (Required)
    # -----------------------------------------------------------------------

    categories = data.get("categories")
    if not categories or not isinstance(categories, list) or len(categories) == 0:
        return jsonify({"error": "At least one category URL is required"}), 400

    # Validate each category URL format
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


# ------------------------------------------------------------------------
# CONTEST DELETION ROUTE
# ------------------------------------------------------------------------
@contest_bp.route("/<int:contest_id>", methods=["DELETE"])
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


# ------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ------------------------------------------------------------------------


def parse_date_or_none(date_str):
    """Parse a date string and return date or None when invalid."""
    if not date_str:
        return None
    try:
        # Try standard format first (YYYY-MM-DD)
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        try:
            # Fallback to ISO format
            return datetime.fromisoformat(date_str).date()
        except ValueError:
            return None


# ------------------------------------------------------------------------
# CONTEST UPDATE ENDPOINT
# ------------------------------------------------------------------------


@contest_bp.route("/<int:contest_id>", methods=["PUT"])
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

        contest = Contest.query.get(contest_id)
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

        # --- Categories ---
        if "categories" in data:
            categories_value = data.get("categories")
            if (
                not categories_value
                or not isinstance(categories_value, list)
                or len(categories_value) == 0
            ):
                return jsonify({"error": "At least one category URL is required"}), 400

            # Validate each category URL
            for category_url in categories_value:
                if not isinstance(category_url, str) or not category_url.strip():
                    return (
                        jsonify(
                            {"error": "All category URLs must be non-empty strings"}
                        ),
                        400,
                    )
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
# CONTEST SUBMISSION ENDPOINT
# ------------------------------------------------------------------------


@contest_bp.route("/<int:contest_id>/submit", methods=["POST"])
@require_auth
@handle_errors
@validate_json_data(["article_link"])
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
        return jsonify({"error": "Contest not found"}), 404

    # --- Input Validation ---
    article_link = data["article_link"].strip()

    if not article_link:
        return jsonify({"error": "Article link is required"}), 400

    # Basic URL validation
    if not (article_link.startswith("http://") or article_link.startswith("https://")):
        return jsonify({"error": "Article link must be a valid URL"}), 400

    # --- Contest Status Checks ---
    if not contest.is_active():
        if contest.is_upcoming():
            return jsonify({"error": "Contest has not started yet"}), 400
        if contest.is_past():
            return jsonify({"error": "Contest has ended"}), 400
        return jsonify({"error": "Contest is not active"}), 400

    # Check for duplicate submission
    existing_submission = Submission.query.filter_by(
        user_id=user.id, contest_id=contest_id, article_link=article_link
    ).first()

    if existing_submission:
        return (
            jsonify(
                {"error": "You have already submitted this article to this contest"}
            ),
            400,
        )

    # --- Initialize Article Metadata Variables ---
    article_title = None
    article_author = None
    article_created_at = None
    article_word_count = None
    article_page_id = None
    article_size_at_start = None
    article_expansion_bytes = None
    article_reference_count = None

    # --- Fetch Article Information from MediaWiki API ---
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
            api_params["inprop"] = "url|displaytitle"

            # Make request to MediaWiki API using shared headers
            # Use increased timeout to handle slow API responses
            headers = get_mediawiki_headers()
            response = requests.get(
                api_url,
                params=api_params,
                headers=headers,
                timeout=MEDIAWIKI_API_TIMEOUT,
            )

            if response.status_code == 200:
                api_data = response.json()

                # Check for API errors
                if "error" not in api_data:
                    # Handle formatversion=2 (array) or formatversion=1 (object)
                    pages = api_data.get("query", {}).get("pages", [])
                    if pages:
                        # Handle both array (formatversion=2) and object (formatversion=1) formats
                        if isinstance(pages, list):
                            # formatversion=2: pages is an array
                            if len(pages) > 0:
                                page_data = pages[0]
                                page_id = str(page_data.get("pageid", ""))
                            else:
                                page_data = None
                        else:
                            # formatversion=1: pages is an object with page IDs as keys
                            page_id = list(pages.keys())[0]
                            page_data = pages[page_id]

                        # Check if page exists
                        # In formatversion=2, missing pages have 'missing': True
                        # In formatversion=1, missing pages have pageid: -1
                        is_missing = (
                            page_data.get("missing", False) if page_data else True
                        )
                        has_valid_pageid = page_id and page_id != "-1" and page_id != ""

                        if page_data and has_valid_pageid and not is_missing:
                            # Extract article title
                            article_title = page_data.get("title", page_title)

                            # --- Get Revision Information ---
                            # With formatversion=2, revisions is an array
                            # With rvdir='older', revisions[0] is the newest (latest) revision
                            revisions = page_data.get("revisions", [])
                            if revisions and len(revisions) > 0:
                                # Get latest revision (newest) for word count
                                # With rvdir='older', the first revision is the newest
                                latest_revision = revisions[0]

                                # Get word count from latest revision (most current size)
                                article_word_count = latest_revision.get("size", 0)

                                # Get latest revision (newest) for author at submission time
                                # Use shared utility function to extract author from latest revision
                                # This gets the author who made the most recent edit at submission time
                                article_author = get_latest_revision_author(revisions)
                                if not article_author:
                                    article_author = "Unknown"

                                # Get oldest revision for creation date
                                if len(revisions) > 1:
                                    oldest_revision = revisions[-1]
                                else:
                                    oldest_revision = revisions[0]

                                # Get creation date from oldest revision
                                # Parse ISO 8601 timestamp string to datetime object
                                timestamp_str = oldest_revision.get("timestamp", "")
                                if timestamp_str:
                                    # MediaWiki API returns timestamps in ISO 8601 format with 'Z' suffix
                                    # Replace 'Z' with '+00:00' for UTC timezone, then parse
                                    timestamp_str = timestamp_str.replace("Z", "+00:00")
                                    try:
                                        article_created_at = datetime.fromisoformat(
                                            timestamp_str
                                        )
                                    except (ValueError, AttributeError):
                                        # If parsing fails, set to None
                                        article_created_at = None
                                else:
                                    article_created_at = None
                                article_page_id = page_id

                                # Debug logging to help diagnose issues
                                try:
                                    current_app.logger.info(
                                        f"Fetched article info: title={article_title}, "
                                        f"author={article_author}, word_count={article_word_count}, "
                                        f"created={article_created_at}, "
                                        f"revisions_count={len(revisions)}"
                                    )
                                    current_app.logger.debug(
                                        f'Latest revision size: {latest_revision.get("size")}, '
                                        f'Oldest revision timestamp: {oldest_revision.get("timestamp")}'
                                    )
                                except (
                                    Exception
                                ):  # pylint: disable=broad-exception-caught
                                    # Logging failure shouldn't break the flow
                                    pass
                            else:
                                # --- Fallback: No Revisions Found ---
                                # Try alternative API call to get revisions
                                # Sometimes revisions aren't returned in the first query
                                try:
                                    # Make a second API call specifically for revisions
                                    # Get 2 revisions: newest (for word count) and oldest (for author/creation)
                                    rev_api_params = {
                                        "action": "query",
                                        "titles": page_title,
                                        "format": "json",
                                        "formatversion": "2",
                                        "prop": "revisions",
                                        "rvprop": "timestamp|user|userid|size",
                                        "rvlimit": "2",  # Get 2 revisions: newest and oldest
                                        "rvdir": "older",  # Start from newest, get newest first
                                        "redirects": "true",
                                    }
                                    rev_response = requests.get(
                                        api_url,
                                        params=rev_api_params,
                                        headers=headers,
                                        timeout=MEDIAWIKI_API_TIMEOUT,
                                    )
                                    if rev_response.status_code == 200:
                                        rev_data = rev_response.json()
                                        rev_pages = rev_data.get("query", {}).get(
                                            "pages", []
                                        )
                                        if rev_pages and len(rev_pages) > 0:
                                            rev_page = rev_pages[0]
                                            rev_revisions = rev_page.get(
                                                "revisions", []
                                            )
                                            if rev_revisions and len(rev_revisions) > 0:
                                                # Get latest revision (newest) for word count
                                                # With rvdir='older', the first revision is the newest
                                                latest_rev = rev_revisions[0]

                                                # Get word count from latest revision (most current size)
                                                article_word_count = latest_rev.get(
                                                    "size", 0
                                                )

                                                # Get latest revision (newest) for author at submission time
                                                # With rvdir='older', the first revision is the newest (latest)
                                                latest_rev = rev_revisions[0]

                                                # Extract author from latest revision (most recent edit)
                                                # This gets the author who made the most recent edit at submission time
                                                user_id_val = latest_rev.get("userid")
                                                article_author = latest_rev.get(
                                                    "user"
                                                ) or (
                                                    f"User ID: {user_id_val}"
                                                    if user_id_val
                                                    else "Unknown"
                                                )

                                                # Get creation date from oldest revision (for historical reference)
                                                # If we have multiple revisions, the last one in the array is the oldest
                                                # If we only have one revision, it's both the newest and oldest
                                                if len(rev_revisions) > 1:
                                                    oldest_rev = rev_revisions[-1]
                                                else:
                                                    oldest_rev = rev_revisions[0]
                                                # Parse ISO 8601 timestamp string to datetime object
                                                timestamp_str = oldest_rev.get(
                                                    "timestamp", ""
                                                )
                                                if timestamp_str:
                                                    # MediaWiki API returns timestamps in ISO 8601 format with 'Z' suffix
                                                    # Replace 'Z' with '+00:00' for UTC timezone, then parse
                                                    timestamp_str = (
                                                        timestamp_str.replace(
                                                            "Z", "+00:00"
                                                        )
                                                    )
                                                    try:
                                                        article_created_at = (
                                                            datetime.fromisoformat(
                                                                timestamp_str
                                                            )
                                                        )
                                                    except (ValueError, AttributeError):
                                                        # If parsing fails, set to None
                                                        article_created_at = None
                                                else:
                                                    article_created_at = None
                                                article_page_id = page_id

                                                try:
                                                    current_app.logger.info(
                                                        f"Got revision data from second API call: "
                                                        f"author={article_author}"
                                                    )
                                                except (
                                                    Exception
                                                ):  # pylint: disable=broad-exception-caught
                                                    # Logging failure shouldn't break the flow
                                                    pass
                                except (
                                    Exception
                                ) as rev_err:  # pylint: disable=broad-exception-caught
                                    # If second API call fails, log it but continue
                                    try:
                                        current_app.logger.warning(
                                            f"Failed to get revisions from second API call: "
                                            f"{str(rev_err)}"
                                        )
                                    except (
                                        Exception
                                    ):  # pylint: disable=broad-exception-caught
                                        # Logging failure shouldn't break the flow
                                        pass

                                # Log if still no revisions found
                                if not article_author or article_author == "Unknown":
                                    try:
                                        current_app.logger.warning(
                                            f"No revisions found for page: {page_title}, "
                                            f"page_data keys: {list(page_data.keys())}, "
                                            f"missing={is_missing}"
                                        )
                                    except (
                                        Exception
                                    ):  # pylint: disable=broad-exception-caught
                                        # Logging failure shouldn't break the flow
                                        pass
                        else:
                            # Page is missing or doesn't exist
                            try:
                                current_app.logger.warning(
                                    f"Page not found or missing: {page_title}, "
                                    f"page_id={page_id}, missing={is_missing}"
                                )
                            except Exception:  # pylint: disable=broad-exception-caught
                                # Logging failure shouldn't break the flow
                                pass

        # --- Fallback: Use URL-based Title ---
        # If we couldn't fetch title from API, use a fallback
        if not article_title:
            # Try to extract from URL as fallback
            if page_title:
                article_title = page_title.replace("_", " ")
            else:
                article_title = "Article"  # Last resort fallback

    except requests.exceptions.Timeout as timeout_error:
        # Handle timeout errors specifically with a clear error message
        # Timeout means the MediaWiki API didn't respond within the timeout period
        # This could be due to slow API response, network issues, or high server load
        try:
            current_app.logger.warning(
                f"MediaWiki API request timed out after {MEDIAWIKI_API_TIMEOUT} seconds: {str(timeout_error)}"
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # Logging failure shouldn't break the flow
            pass

        # Return a clear error message to the user
        # We can't create a submission without article information (byte count is required)
        return (
            jsonify(
                {
                    "error": (
                        f"Request to MediaWiki API timed out after {MEDIAWIKI_API_TIMEOUT} seconds. "
                        "The server may be slow or experiencing high traffic. Please try again in a moment."
                    )
                }
            ),
            504,
        )  # 504 Gateway Timeout is the appropriate status code

    except Exception as error:  # pylint: disable=broad-exception-caught
        # If MediaWiki API fetch fails for other reasons, we'll still create the submission
        # but with limited information
        # Log the error but don't fail the submission
        try:
            current_app.logger.warning(
                f"Failed to fetch article info from MediaWiki API: {str(error)}"
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # Logging failure shouldn't break the flow
            pass

        # Use fallback title
        if not article_title:
            article_title = "Article"

    # --- Calculate Article Expansion ---
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
            size_at_start = get_article_size_at_timestamp(
                article_link, contest_start_datetime
            )
            article_size_at_start = size_at_start  # Store the size at contest start

            # Get article size at submission time
            # Use the current article_word_count if available, otherwise query API
            size_at_submission = article_word_count
            if size_at_submission is None:
                size_at_submission = get_article_size_at_timestamp(
                    article_link, submission_datetime
                )

            # Calculate expansion bytes
            # At submission time, expansion bytes should be 0 since the article hasn't changed yet
            # Expansion bytes will be updated on refresh to show changes since submission
            article_expansion_bytes = 0

            # Log expansion calculation for debugging
            try:
                current_app.logger.info(
                    f"Expansion calculation: size_at_start={size_at_start}, "
                    f"size_at_submission={size_at_submission}, "
                    f"expansion={article_expansion_bytes}"
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        except Exception as exp_error:  # pylint: disable=broad-exception-caught
            # If expansion calculation fails, log but don't fail submission
            try:
                current_app.logger.warning(
                    f"Failed to calculate expansion: {str(exp_error)}"
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            article_expansion_bytes = None

    # --- Fetch Reference Count ---
    # Fetch reference count (footnotes + external links) using shared utility
    # This counts both <ref> tags and external URLs from the latest revision
    # This is done after fetching article info but before validation
    try:
        article_reference_count = get_article_reference_count(article_link)
    except Exception as ref_error:  # pylint: disable=broad-exception-caught
        # If reference count fetch fails, log but don't fail submission
        # Validation will handle None case
        try:
            current_app.logger.warning(
                f"Failed to fetch reference count: {str(ref_error)}"
            )
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        article_reference_count = None

    # --- Validate Article Requirements ---
    # Validate article byte count against contest requirements
    # This check happens after fetching article information from MediaWiki API
    # article_word_count is actually the byte count (size) from MediaWiki API
    # min_byte_count is always required, so always validate
    is_valid_byte_count, byte_count_error = contest.validate_byte_count(
        article_word_count
    )
    if not is_valid_byte_count:
        return jsonify({"error": byte_count_error}), 400

    # Validate article reference count against contest requirements
    # min_reference_count is optional (0 = no requirement), so only validate if > 0
    is_valid_reference_count, reference_count_error = contest.validate_reference_count(
        article_reference_count
    )
    if not is_valid_reference_count:
        return jsonify({"error": reference_count_error}), 400

    # Template enforcement logic
    # If contest has a template_link, check if article has the template and add it if not
    template_added = False
    template_error = None

    if contest.template_link:
        try:
            # Log template enforcement start
            current_app.logger.info(
                f"Template enforcement: contest_id={contest_id}, template_link={contest.template_link}, "
                f"user_id={user.id}, has_oauth_token={bool(user.oauth_token)}, "
                f"has_oauth_secret={bool(user.oauth_token_secret)}"
            )

            # Extract template name from the contest's template link
            template_name = extract_template_name_from_url(contest.template_link)
            current_app.logger.info(f"Extracted template name: {template_name}")

            if template_name:
                # Check if article already has the template at the beginning
                template_check = check_article_has_template(article_link, template_name)

                if template_check.get("error"):
                    # Log warning but don't fail submission
                    try:
                        current_app.logger.warning(
                            f"Template check failed for {article_link}: {template_check['error']}"
                        )
                    except Exception:  # pylint: disable=broad-exception-caught
                        pass
                elif not template_check.get("has_template"):
                    # Template not present, attempt to add it
                    current_app.logger.info(
                        f"Template not found in article. Attempting to add..."
                    )

                    # Check if user has OAuth tokens
                    if user.oauth_token and user.oauth_token_secret:
                        current_app.logger.info(
                            f"User has OAuth tokens. Proceeding with edit..."
                        )
                        # Get OAuth consumer credentials from config
                        consumer_key = current_app.config.get("CONSUMER_KEY")
                        consumer_secret = current_app.config.get("CONSUMER_SECRET")

                        if consumer_key and consumer_secret:
                            # Log the target wiki for debugging OAuth issues
                            from urllib.parse import urlparse

                            article_domain = urlparse(article_link).netloc
                            current_app.logger.info(
                                f"Attempting OAuth edit on wiki: {article_domain}"
                            )

                            # Attempt to prepend template to article
                            edit_result = prepend_template_to_article(
                                article_url=article_link,
                                template_name=template_name,
                                oauth_token=user.oauth_token,
                                oauth_token_secret=user.oauth_token_secret,
                                consumer_key=consumer_key,
                                consumer_secret=consumer_secret,
                                edit_summary=f"Adding {{{{{template_name}}}}} contest template (via WikiContest submission)",
                            )

                            if edit_result.get("success"):
                                template_added = True
                                try:
                                    current_app.logger.info(
                                        f"Successfully added template {{{{{template_name}}}}} to {article_link}"
                                    )
                                except (
                                    Exception
                                ):  # pylint: disable=broad-exception-caught
                                    pass
                            else:
                                template_error = edit_result.get(
                                    "error", "Unknown error"
                                )
                                try:
                                    current_app.logger.warning(
                                        f"Failed to add template to {article_link}: {template_error}"
                                    )

                                    # Provide helpful error messages for common OAuth issues
                                    if "readapidenied" in template_error.lower():
                                        current_app.logger.error(
                                            f"OAuth permission error: The OAuth consumer does not have read/edit "
                                            f"permissions on this wiki. Ensure the OAuth consumer is registered on "
                                            f"the target wiki (not just meta.wikimedia.org) with 'Edit existing pages' grant."
                                        )
                                    elif (
                                        "mwoauth-invalid-authorization"
                                        in template_error.lower()
                                    ):
                                        current_app.logger.error(
                                            f"OAuth authentication error: Invalid OAuth signature. Verify CONSUMER_KEY "
                                            f"and CONSUMER_SECRET match the registered OAuth consumer."
                                        )
                                except (
                                    Exception
                                ):  # pylint: disable=broad-exception-caught
                                    pass
                        else:
                            template_error = "OAuth consumer credentials not configured"
                            current_app.logger.warning(
                                f"OAuth consumer credentials not configured: "
                                f"CONSUMER_KEY={bool(consumer_key)}, "
                                f"CONSUMER_SECRET={bool(consumer_secret)}"
                            )
                    else:
                        template_error = (
                            "User does not have OAuth tokens for Wikipedia editing"
                        )
                        current_app.logger.warning(
                            f"User {user.id} does not have OAuth tokens: "
                            f"oauth_token={user.oauth_token}, oauth_token_secret={user.oauth_token_secret}"
                        )
                else:
                    # Template already present
                    try:
                        current_app.logger.info(
                            f"Template {{{{{template_name}}}}} already present in {article_link}"
                        )
                    except Exception:  # pylint: disable=broad-exception-caught
                        pass
            else:
                template_error = (
                    "Could not extract template name from contest template link"
                )
        except Exception as template_err:  # pylint: disable=broad-exception-caught
            template_error = str(template_err)
            try:
                current_app.logger.error(
                    f"Template enforcement error: {template_error}"
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    # Category enforcement logic
    # If contest has categories, check if article has them and add missing ones
    # This is a separate MediaWiki API request from template attachment
    categories_added = []
    category_error = None

    contest_categories = contest.get_categories()
    if contest_categories:
        try:
            # Log category enforcement start
            current_app.logger.info(
                f"Category enforcement: contest_id={contest_id}, categories={contest_categories}, "
                f"user_id={user.id}, has_oauth_token={bool(user.oauth_token)}, "
                f"has_oauth_secret={bool(user.oauth_token_secret)}"
            )

            # Extract category names from URLs
            category_names = []
            for category_url in contest_categories:
                category_name = extract_category_name_from_url(category_url)
                if category_name:
                    category_names.append(category_name)
                    current_app.logger.info(
                        f"Extracted category name: {category_name} from {category_url}"
                    )
                else:
                    current_app.logger.warning(
                        f"Could not extract category name from URL: {category_url}"
                    )

            if category_names:
                # Check which categories the article already has
                categories_to_add = []
                for category_name in category_names:
                    category_check = check_article_has_category(
                        article_link, category_name
                    )

                    if category_check.get("error"):
                        # Log warning but continue - we'll try to add it anyway
                        try:
                            current_app.logger.warning(
                                f"Category check failed for {category_name} in {article_link}: {category_check['error']}"
                            )
                        except Exception:  # pylint: disable=broad-exception-caught
                            pass
                        # Add to list anyway - better to try than skip
                        categories_to_add.append(category_name)
                    elif not category_check.get("has_category"):
                        # Category not present, add it to the list
                        categories_to_add.append(category_name)
                        current_app.logger.info(
                            f"Category {category_name} not found in article. Will add..."
                        )
                    else:
                        # Category already present
                        try:
                            current_app.logger.info(
                                f"Category {category_name} already present in {article_link}"
                            )
                        except Exception:  # pylint: disable=broad-exception-caught
                            pass

                # If there are categories to add, attempt to add them
                if categories_to_add:
                    current_app.logger.info(
                        f"Attempting to add {len(categories_to_add)} categories to article..."
                    )

                    # Check if user has OAuth tokens
                    if user.oauth_token and user.oauth_token_secret:
                        current_app.logger.info(
                            f"User has OAuth tokens. Proceeding with category edit..."
                        )
                        # Get OAuth consumer credentials from config
                        consumer_key = current_app.config.get("CONSUMER_KEY")
                        consumer_secret = current_app.config.get("CONSUMER_SECRET")

                        if consumer_key and consumer_secret:
                            # Log the target wiki for debugging OAuth issues
                            from urllib.parse import urlparse

                            article_domain = urlparse(article_link).netloc
                            current_app.logger.info(
                                f"Attempting OAuth edit on wiki: {article_domain} for categories"
                            )

                            # Attempt to append categories to article
                            # This is a separate MediaWiki API request from template attachment
                            edit_result = append_categories_to_article(
                                article_url=article_link,
                                category_names=categories_to_add,
                                oauth_token=user.oauth_token,
                                oauth_token_secret=user.oauth_token_secret,
                                consumer_key=consumer_key,
                                consumer_secret=consumer_secret,
                                edit_summary=f"Adding contest categories (via WikiContest submission)",
                            )

                            if edit_result.get("success"):
                                categories_added = edit_result.get(
                                    "categories_added", []
                                )
                                categories_skipped = edit_result.get(
                                    "categories_skipped", []
                                )
                                try:
                                    current_app.logger.info(
                                        f"Successfully added categories {categories_added} to {article_link}"
                                    )
                                    if categories_skipped:
                                        current_app.logger.info(
                                            f"Categories {categories_skipped} were already present and skipped"
                                        )
                                except (
                                    Exception
                                ):  # pylint: disable=broad-exception-caught
                                    pass
                            else:
                                category_error = edit_result.get(
                                    "error", "Unknown error"
                                )
                                try:
                                    current_app.logger.warning(
                                        f"Failed to add categories to {article_link}: {category_error}"
                                    )

                                    # Provide helpful error messages for common OAuth issues
                                    if "readapidenied" in category_error.lower():
                                        current_app.logger.error(
                                            f"OAuth permission error: The OAuth consumer does not have read/edit "
                                            f"permissions on this wiki. Ensure the OAuth consumer is registered on "
                                            f"the target wiki (not just meta.wikimedia.org) with 'Edit existing pages' grant."
                                        )
                                    elif (
                                        "mwoauth-invalid-authorization"
                                        in category_error.lower()
                                    ):
                                        current_app.logger.error(
                                            f"OAuth authentication error: Invalid OAuth signature. Verify CONSUMER_KEY "
                                            f"and CONSUMER_SECRET match the registered OAuth consumer."
                                        )
                                except (
                                    Exception
                                ):  # pylint: disable=broad-exception-caught
                                    pass
                        else:
                            category_error = "OAuth consumer credentials not configured"
                            current_app.logger.warning(
                                f"OAuth consumer credentials not configured: "
                                f"CONSUMER_KEY={bool(consumer_key)}, "
                                f"CONSUMER_SECRET={bool(consumer_secret)}"
                            )
                    else:
                        category_error = (
                            "User does not have OAuth tokens for Wikipedia editing"
                        )
                        current_app.logger.warning(
                            f"User {user.id} does not have OAuth tokens: "
                            f"oauth_token={user.oauth_token}, oauth_token_secret={user.oauth_token_secret}"
                        )
                else:
                    # All categories already present
                    try:
                        current_app.logger.info(
                            f"All contest categories already present in {article_link}"
                        )
                    except Exception:  # pylint: disable=broad-exception-caught
                        pass
            else:
                category_error = (
                    "Could not extract category names from contest category URLs"
                )
                current_app.logger.warning(
                    f"Could not extract any category names from contest categories: {contest_categories}"
                )
        except Exception as category_err:  # pylint: disable=broad-exception-caught
            category_error = str(category_err)
            try:
                current_app.logger.error(
                    f"Category enforcement error: {category_error}"
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    # --- Create Submission Record ---
    # Create submission with fetched information
    try:
        submission = Submission(
            user_id=user.id,
            contest_id=contest_id,
            article_title=article_title,
            article_link=article_link,
            status="pending",
            article_author=article_author,
            article_created_at=article_created_at,
            article_word_count=article_word_count,
            article_page_id=article_page_id,
            article_size_at_start=article_size_at_start,
            article_expansion_bytes=article_expansion_bytes,
            template_added=template_added,
            categories_added=categories_added,
            category_error=category_error,
        )

        submission.save()

        # Debug: Log what was saved
        try:
            current_app.logger.info(
                f"Submission saved: id={submission.id}, "
                f"author={submission.article_author}, "
                f"word_count={submission.article_word_count}"
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # Logging failure shouldn't break the flow
            pass

        return (
            jsonify(
                {
                    "message": "Submission created successfully",
                    "submissionId": submission.id,
                    "contest_id": contest_id,
                    "article_title": article_title,
                    "article_author": article_author,
                    "article_word_count": article_word_count,
                    "article_created_at": article_created_at,
                    "article_expansion_bytes": article_expansion_bytes,
                    "template_added": template_added,
                    "template_error": template_error,
                    "categories_added": categories_added,
                    "category_error": category_error,
                }
            ),
            201,
        )

    except IntegrityError as e:
        # Handle database integrity errors (e.g., duplicate submissions)
        # Rollback the session on integrity error
        db.session.rollback()
        # Log the actual error for debugging
        error_str = str(e)
        error_orig = str(e.orig) if hasattr(e, "orig") else ""
        full_error = f"{error_str} | Original: {error_orig}"
        current_app.logger.error(f"Integrity error creating submission: {full_error}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        # Check if it's a duplicate submission error
        if (
            "unique_user_contest_article_submission" in error_orig
            or "unique_user_contest_article_submission" in error_str
        ):
            return (
                jsonify(
                    {"error": "You have already submitted this article to this contest"}
                ),
                400,
            )
        # Return detailed error for debugging
        return (
            jsonify(
                {
                    "error": "Failed to create submission: duplicate entry or constraint violation",
                    "details": full_error,
                    "traceback": traceback.format_exc() if current_app.debug else None,
                }
            ),
            400,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Handle any other unexpected errors
        # Rollback the session on any error
        db.session.rollback()
        # Log error for debugging
        error_str = str(e)
        error_type = type(e).__name__
        full_error = f"{error_type}: {error_str}"
        current_app.logger.error(f"Error creating submission: {full_error}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        # Return detailed error for debugging
        return (
            jsonify(
                {
                    "error": "Failed to create submission",
                    "details": full_error,
                    "error_type": error_type,
                    "traceback": traceback.format_exc() if current_app.debug else None,
                }
            ),
            500,
        )


# ------------------------------------------------------------------------
# GET CONTEST SUBMISSIONS
# ------------------------------------------------------------------------


@contest_bp.route("/<int:contest_id>/submissions", methods=["GET"])
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
    contest, error_response = validate_contest_submission_access(
        contest_id, user, Contest
    )
    if error_response:
        return error_response

    # Get submissions with user information via JOIN
    submissions = (
        db.session.query(Submission, User.username, User.email)
        .join(User, Submission.user_id == User.id)
        .filter(Submission.contest_id == contest_id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )

    # Build response data with user and contest information
    submissions_data = []
    for submission, username, email in submissions:
        submission_data = submission.to_dict(include_user_info=True)
        submission_data.update(
            {"username": username, "email": email, "contest_name": contest.name}
        )
        submissions_data.append(submission_data)

    return jsonify(submissions_data), 200


# ------------------------------------------------------------------------
# ORGANIZER MANAGEMENT ENDPOINTS
# ------------------------------------------------------------------------


@contest_bp.route("/<int:contest_id>/organizers", methods=["GET"])
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


@contest_bp.route("/<int:contest_id>/organizers", methods=["POST"])
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


@contest_bp.route("/<int:contest_id>/organizers/<username>", methods=["DELETE"])
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


# ------------------------------------------------------------------------
# CONTEST REQUEST ROUTES (For Non-Privileged Users)
# ------------------------------------------------------------------------

@contest_bp.route("/requests", methods=["POST"])
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


@contest_bp.route("/requests", methods=["GET"])
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


@contest_bp.route("/requests/<int:request_id>/approve", methods=["POST"])
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


@contest_bp.route("/requests/<int:request_id>/reject", methods=["POST"])
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
