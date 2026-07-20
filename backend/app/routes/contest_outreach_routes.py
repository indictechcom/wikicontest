"""
Contest outreach-dashboard routes for WikiEval Application.
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
    Retrieve course data from the Outreach Dashboard for a contest.
    
    Parameters:
        contest_id (int): Identifier of the contest.
    
    Returns:
        tuple: A JSON response containing the course data on success, or an error message with the corresponding HTTP status code.
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
    Fetch course user data from the Outreach Dashboard for a contest.
    
    Parameters:
        contest_id: ID of the contest.
    
    Returns:
        A JSON response containing course user data, or an error response if the
        contest or Outreach Dashboard URL is unavailable or the request fails.
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
    Retrieve Outreach Dashboard course articles for a contest.
    
    Parameters:
        contest_id: The contest identifier.
    
    Returns:
        A JSON response containing article data, or an error message with the corresponding HTTP status.
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
    Fetches course upload data from the Outreach Dashboard for a contest.
    
    Parameters:
        contest_id (int): Identifier of the contest.
    
    Returns:
        A JSON response containing upload data, or an error response with HTTP
        status 404 when the contest is missing or 400 when the dashboard URL or
        upstream data request is unavailable.
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


