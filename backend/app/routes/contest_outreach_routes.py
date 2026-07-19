"""
Contest outreach-dashboard routes for WikiContest Application.
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
from app.services.outreach_dashboard import (
    fetch_course_data,
    fetch_course_users,
    fetch_course_articles,
    fetch_course_uploads,
)
from app.routes._contest_helpers import validate_date_string, parse_date_or_none


# Create Flask blueprint
contest_outreach_bp = Blueprint("contest_outreach", __name__)


@contest_outreach_bp.route("/<int:contest_id>/outreach-data", methods=["GET"])
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
    contest = db.session.get(Contest, contest_id)

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


@contest_outreach_bp.route("/<int:contest_id>/outreach-users", methods=["GET"])
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
    contest = db.session.get(Contest, contest_id)

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


@contest_outreach_bp.route("/<int:contest_id>/outreach-articles", methods=["GET"])
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
    contest = db.session.get(Contest, contest_id)

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


@contest_outreach_bp.route("/<int:contest_id>/outreach-uploads", methods=["GET"])
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
    contest = db.session.get(Contest, contest_id)

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


