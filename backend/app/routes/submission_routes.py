"""
Submission Routes for WikiContest Application
Handles submission management and review functionality
"""

import json
from urllib.parse import urlparse
from datetime import datetime

import requests
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.orm import joinedload

from app.database import db
from app.middleware.auth import (
    handle_errors,
    require_auth,
    require_submission_permission,
    validate_json_data,
)
from app.models.contest import Contest
from app.models.submission import Submission
from app.utils import (
    validate_contest_submission_access,
    extract_page_title_from_url,
    get_latest_revision_author,
    build_mediawiki_revisions_api_params,
    get_mediawiki_headers,
    get_detailed_reference_counts,
    MEDIAWIKI_API_TIMEOUT,
)

# Create blueprint
submission_bp = Blueprint("submission", __name__)


# ------------------------------------------------------------------------
# SUBMISSION RETRIEVAL ENDPOINTS
# ------------------------------------------------------------------------

@submission_bp.route("/", methods=["GET"])
@require_auth
@handle_errors
def get_all_submissions():
    """
    Get all submissions (admin only)

    Returns:
        JSON response with all submissions
    """
    user = request.current_user

    # Restrict to admins only
    if not user.is_admin():
        return jsonify({"error": "Admin access required"}), 403

    # Fetch all submissions ordered by submission date (newest first)
    submissions = Submission.query.order_by(Submission.submitted_at.desc()).all()

    submissions_data = []
    for submission in submissions:
        submission_data = submission.to_dict(include_user_info=True)
        submissions_data.append(submission_data)

    return jsonify(submissions_data), 200


@submission_bp.route("/<int:submission_id>", methods=["GET"])
@require_submission_permission("view")
@handle_errors
def get_submission_by_id(submission_id):  # pylint: disable=unused-argument
    """
    Get a specific submission by ID

    Args:
        submission_id: Submission ID

    Returns:
        JSON response with submission data
    """
    # Submission is pre-loaded by middleware and attached to request
    submission = request.current_submission

    # Get additional information
    submission_data = submission.to_dict(include_user_info=True)

    return jsonify(submission_data), 200

@submission_bp.route("/user/<int:user_id>", methods=["GET"])
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
        return jsonify({"error": "You can only view your own submissions"}), 403

    # Fetch user's submissions ordered by submission date (newest first)
    submissions = (
        Submission.query.filter_by(user_id=user_id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )

    submissions_data = []
    for submission in submissions:
        submission_data = submission.to_dict(include_user_info=True)
        submissions_data.append(submission_data)

    return jsonify(submissions_data), 200


@submission_bp.route("/contest/<int:contest_id>", methods=["GET"])
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
    _contest, error_response = validate_contest_submission_access(
        contest_id, user, Contest
    )
    if error_response:
        return error_response

    # Fetch all submissions for this contest ordered by submission date (newest first)
    submissions = (
        Submission.query.filter_by(contest_id=contest_id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )

    submissions_data = []
    for submission in submissions:
        submission_data = submission.to_dict(include_user_info=True)
        submissions_data.append(submission_data)

    return jsonify(submissions_data), 200


@submission_bp.route("/pending", methods=["GET"])
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
    pending_submissions = Submission.query.filter_by(status="pending").all()

    # Filter submissions that user can judge based on permissions
    judgeable_submissions = []
    for submission in pending_submissions:
        if submission.can_be_judged_by(user):
            submission_data = submission.to_dict(include_user_info=True)
            judgeable_submissions.append(submission_data)

    return jsonify(judgeable_submissions), 200


# ------------------------------------------------------------------------
# SUBMISSION STATISTICS
# ------------------------------------------------------------------------

@submission_bp.route("/stats", methods=["GET"])
@require_auth
@handle_errors
def get_submission_stats():
    """
    Get submission statistics for the current user

    Returns:
        JSON response with submission statistics
    """
    user = request.current_user

    # Get user's submission statistics by status
    total_submissions = Submission.query.filter_by(user_id=user.id).count()
    accepted_submissions = Submission.query.filter_by(
        user_id=user.id, status="accepted"
    ).count()
    rejected_submissions = Submission.query.filter_by(
        user_id=user.id, status="rejected"
    ).count()
    pending_submissions = Submission.query.filter_by(
        user_id=user.id, status="pending"
    ).count()

    # Get total score from all submissions
    total_score = (
        db.session.query(db.func.sum(Submission.score))
        .filter_by(user_id=user.id)
        .scalar()
        or 0
    )

    return (
        jsonify(
            {
                "total_submissions": total_submissions,
                "accepted_submissions": accepted_submissions,
                "rejected_submissions": rejected_submissions,
                "pending_submissions": pending_submissions,
                "total_score": total_score,
                "acceptance_rate": (
                    (accepted_submissions / total_submissions * 100)
                    if total_submissions > 0
                    else 0
                ),
            }
        ),
        200,
    )


# ------------------------------------------------------------------------
# METADATA REFRESH ENDPOINT
# ------------------------------------------------------------------------

@submission_bp.route("/contest/<int:contest_id>/refresh-metadata", methods=["POST"])
@require_auth
@handle_errors
def refresh_metadata(contest_id):
    """
    Refresh article metadata (word count, author, etc.) for all submissions in a contest.

    This endpoint fetches the latest metadata from MediaWiki API for all submissions
    in the specified contest and updates the database with the current values.

    For automated scoring contests, this also evaluates each submission and updates
    status (accepted/rejected) and score based on the automated criteria.

    Args:
        contest_id: The ID of the contest to refresh submissions for

    Returns:
        JSON response with refresh results
    """
    user = request.current_user

    # Validate contest access and permissions
    contest, error_response = validate_contest_submission_access(
        contest_id, user, Contest
    )
    if error_response:
        return error_response

    # Check if this is an automated scoring contest
    is_automated = False
    try:
        is_automated = contest.get_scoring_mode() == "automated"
        current_app.logger.info(f"Contest {contest_id} scoring mode: {contest.get_scoring_mode()}, is_automated: {is_automated}")
    except Exception as e:
        current_app.logger.warning(f"Failed to check scoring mode: {str(e)}")

    # Get all submissions for this contest
    # For automated contests, limit batch size to prevent timeout
    # Each submission requires multiple API calls which can be slow
    query = Submission.query.filter_by(contest_id=contest_id)
    
    # Limit to 50 submissions per refresh for automated contests to prevent timeout
    if is_automated:
        query = query.limit(50)
    
    submissions = query.all()

    if not submissions:
        return (
            jsonify(
                {
                    "message": "No submissions found for this contest",
                    "updated": 0,
                    "failed": 0,
                    "total": 0,
                }
            ),
            200,
        )

    updated = 0
    failed = 0

    # --- Helper Functions for Metadata Refresh ---

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

            response = requests.get(api_url, params=api_params, headers=headers, timeout=MEDIAWIKI_API_TIMEOUT)

            if response.status_code != 200:
                return None

            data = response.json()

            if "error" in data:
                return None

            # Handle API response format
            pages = data.get("query", {}).get("pages", [])
            if not pages:
                return None

            page_data = pages[0]
            is_missing = page_data.get("missing", False)
            page_id = str(page_data.get("pageid", ""))

            # Check if page exists
            if is_missing or not page_id or page_id == "-1":
                return None

            # --- Get Revision Information ---
            # With rvdir='older', revisions[0] is the newest (latest) revision
            revisions = page_data.get("revisions", [])
            if not revisions or len(revisions) == 0:
                return None

            # Get latest revision (newest) for current size and author
            latest_revision = revisions[0]
            # Current size from latest revision (used for expansion bytes calculation on refresh)
            current_size = latest_revision.get("size", 0)

            # Extract author from latest revision (newest revision at submission time)
            # Use shared utility function to extract author from latest revision
            # This gets the author who made the most recent edit at submission time
            article_author = get_latest_revision_author(revisions)

            # Get latest revision timestamp
            latest_revision_timestamp = latest_revision.get("timestamp", "")

            # Get oldest revision (creation) for creation date (for historical reference)
            if len(revisions) > 1:
                oldest_revision = revisions[-1]
            else:
                oldest_revision = revisions[0]

            return {
                "article_author": article_author,  # Author from latest revision at submission time
                "article_created_at": oldest_revision.get("timestamp", ""),
                # Current size from API (used for expansion bytes calculation, not stored as article_word_count)
                "current_size": current_size,
                "article_page_id": page_id,
                # Latest revision metadata (kept for backward compatibility)
                "latest_revision_author": article_author,  # Same as article_author now
                "latest_revision_timestamp": latest_revision_timestamp,
            }

        except Exception:  # pylint: disable=broad-exception-caught
            return None

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
            current_size = article_info.get("current_size")

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
                    f"Failed to calculate expansion for submission {submission_item.id}: {str(exp_error)}"
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    # --- Process Each Submission ---
    # Refresh metadata for each submission
    for submission in submissions:
        info = fetch_article_info(submission.article_link)

        if info:
            # Update submission with latest metadata
            # Do NOT update article_author - it should remain fixed at submission time
            # Only update if it's not already set (for backward compatibility with old submissions)
            if info.get("article_author") and not submission.article_author:
                submission.article_author = info["article_author"]
            if info.get("article_created_at") and not submission.article_created_at:
                # Parse ISO 8601 timestamp string to datetime object
                timestamp_str = info["article_created_at"]
                if isinstance(timestamp_str, str):
                    # MediaWiki API returns timestamps in ISO 8601 format with 'Z' suffix
                    # Replace 'Z' with '+00:00' for UTC timezone, then parse
                    timestamp_str = timestamp_str.replace("Z", "+00:00")
                    try:
                        submission.article_created_at = datetime.fromisoformat(
                            timestamp_str
                        )
                    except (ValueError, AttributeError):
                        # If parsing fails, set to None
                        submission.article_created_at = None
                elif isinstance(timestamp_str, datetime):
                    # Already a datetime object
                    submission.article_created_at = timestamp_str
                else:
                    submission.article_created_at = None
            
            # For crawler-imported submissions (no article_word_count), fetch it from API
            # This is needed for automated evaluation
            if not submission.article_word_count and info.get("current_size"):
                submission.article_word_count = info["current_size"]
            
            if info.get("article_page_id"):
                submission.article_page_id = info["article_page_id"]

            # Calculate expansion bytes on refresh
            # Expansion bytes = current size - size at submission time
            # This shows how much the article has changed since submission
            # When refreshing metadata, ONLY update expansion bytes
            # Do NOT update: article_author, article_word_count, article_size_at_start
            # These should remain fixed at submission time
            calculate_expansion_bytes(submission, info)

            # Update detailed reference counts on refresh
            try:
                ref_counts = get_detailed_reference_counts(submission.article_link)
                submission.ref_new_count = int(ref_counts.get("new", 0) or 0)
                submission.ref_reused_count = int(ref_counts.get("reused", 0) or 0)
            except Exception as ref_error:  # pylint: disable=broad-exception-caught
                try:
                    current_app.logger.warning(
                        "Failed to refresh reference counts for submission %s: %s",
                        submission.id,
                        str(ref_error),
                    )
                except Exception:  # pylint: disable=broad-exception-caught
                    pass

            # --- Automated Scoring Evaluation ---
            # For automated contests, fetch additional metrics and evaluate
            if is_automated:
                current_app.logger.info(f"Evaluating submission {submission.id} in automated mode")
                try:
                    # Fetch incoming/outgoing links
                    from app.utils import (
                        get_article_incoming_links,
                        get_article_outgoing_links,
                        get_article_image_count,
                        get_article_infobox_count,
                    )
                    
                    incoming = get_article_incoming_links(submission.article_link) or 0
                    outgoing = get_article_outgoing_links(submission.article_link) or 0
                    images = get_article_image_count(submission.article_link) or 0
                    infoboxes = get_article_infobox_count(submission.article_link) or 0
                    
                    current_app.logger.info(f"Submission {submission.id}: incoming={incoming}, outgoing={outgoing}, images={images}, infoboxes={infoboxes}")
                    
                    # Update submission with link counts
                    submission.incoming_links = incoming
                    submission.outgoing_links = outgoing
                    submission.image_count = images
                    submission.infobox_count = infoboxes
                    
                    # Evaluate submission against automated criteria
                    submission_data = {
                        "article_word_count": submission.article_word_count,
                        "incoming_links": incoming,
                        "outgoing_links": outgoing,
                        "ref_new_count": submission.ref_new_count,
                        "ref_reused_count": submission.ref_reused_count,
                        "image_count": images,
                        "infobox_count": infoboxes,
                    }
                    
                    current_app.logger.info(f"Submission {submission.id} data for evaluation: {submission_data}")
                    
                    is_eligible, final_score, reason, breakdown = contest.evaluate_automated_submission(submission_data)
                    
                    current_app.logger.info(f"Submission {submission.id} result: eligible={is_eligible}, score={final_score}, reason={reason}")
                    
                    # Update submission status, score, and evaluation details
                    if is_eligible:
                        submission.status = "accepted"
                        submission.score = int(round(final_score))
                        submission.evaluation_reason = reason
                        submission.score_breakdown = json.dumps(breakdown) if breakdown else None
                    else:
                        submission.status = "rejected"
                        submission.score = 0
                        submission.evaluation_reason = reason
                        submission.score_breakdown = None
                    
                    current_app.logger.info(
                        "Automated evaluation for submission %s: %s - %s",
                        submission.id,
                        submission.status,
                        reason,
                    )
                    
                except Exception as eval_error:  # pylint: disable=broad-exception-caught
                    current_app.logger.error(
                        "Failed to evaluate submission %s: %s",
                        submission.id,
                        str(eval_error),
                    )
                    import traceback
                    current_app.logger.error(traceback.format_exc())

            updated += 1
        else:
            failed += 1

    # Commit all changes to database
    try:
        db.session.commit()
    except Exception:  # pylint: disable=broad-exception-caught
        db.session.rollback()
        return jsonify({"error": "Failed to save updates to database"}), 500

    return (
        jsonify(
            {
                "message": f"Refreshed metadata for {updated} submissions",
                "updated": updated,
                "failed": failed,
                "total": len(submissions),
            }
        ),
        200,
    )


# ------------------------------------------------------------------------
# SUBMISSION REVIEW ENDPOINT
# ------------------------------------------------------------------------

@submission_bp.route("/<int:submission_id>/review", methods=["PUT"])
@require_auth
@handle_errors
@validate_json_data(["status"])
def review_submission(submission_id):
    user = request.current_user
    data = request.validated_data

    # Load submission with related data
    submission = Submission.query.options(
        joinedload(Submission.submitter),
        joinedload(Submission.contest),
    ).get_or_404(submission_id)
    contest = submission.contest

    # --- Permission Checks ---
    if not submission.can_be_judged_by(user):
        return jsonify({"error": "Not allowed to review this submission"}), 403

    # Ensure submission hasn't already been reviewed
    if submission.reviewed_at:
        return jsonify({"error": "Submission already reviewed"}), 400

    # Extract and validate status
    status = data.get("status")
    comment = data.get("comment")

    if status not in ["accepted", "rejected"]:
        return jsonify({"error": "Invalid status"}), 400

    # --- Multi-Parameter Scoring Mode ---
    if contest.is_multi_parameter_scoring_enabled():
        scoring_config = contest.get_scoring_parameters()

        if status == "accepted":
            # For accepted submissions, require parameter scores
            parameter_scores = data.get("parameter_scores")

            if not parameter_scores:
                return (
                    jsonify({"error": "Parameter scores required for this contest"}),
                    400,
                )

            if not isinstance(parameter_scores, dict):
                return jsonify({"error": "Parameter scores must be an object"}), 400

            # Validate all required parameters are provided
            required_params = [p["name"] for p in scoring_config.get("parameters", [])]

            for param_name in required_params:
                if param_name not in parameter_scores:
                    return (
                        jsonify({"error": f"Missing score for: {param_name}"}),
                        400,
                    )

                param_score = parameter_scores[param_name]

                # Validate score is numeric
                if not isinstance(param_score, (int, float)):
                    return (
                        jsonify({"error": f"Invalid score for {param_name}"}),
                        400,
                    )

                # Validate score is within range (0-10)
                if param_score < 0 or param_score > 10:
                    return (
                        jsonify(
                            {
                                "error": f"Score for {param_name} must be between 0 and 10"
                            }
                        ),
                        400,
                    )

            try:
                # Final score is calculated INSIDE update_status
                submission.update_status(
                    new_status=status,
                    reviewer=user,
                    comment=comment,
                    contest=contest,
                    parameter_scores=parameter_scores,
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                db.session.rollback()
                print(f"Review error (multi-parameter): {str(e)}")
                return jsonify({"error": "Internal server error"}), 500

        else:
            # Rejected submissions get min_score
            min_score = scoring_config.get("min_score", 0)

            try:
                submission.update_status(
                    new_status=status,
                    reviewer=user,
                    score=min_score,
                    comment=comment,
                    contest=contest,
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                db.session.rollback()
                print(f"Review error (rejected, multi): {str(e)}")
                return jsonify({"error": "Internal server error"}), 500

    # --- Simple Scoring Mode ---
    else:
        if status == "accepted":
            # For accepted submissions, require score within configured range
            score = data.get("score")

            if score is None:
                return jsonify({"error": "Score required"}), 400

            max_score = contest.marks_setting_accepted

            if not isinstance(score, int):
                return jsonify({"error": "Score must be an integer"}), 400

            # Validate score is within configured range
            if score < 0 or score > max_score:
                return (
                    jsonify({"error": f"Score must be between 0 and {max_score}"}),
                    400,
                )
        else:
            # Rejected submissions get configured rejection score
            score = contest.marks_setting_rejected

        try:
            submission.update_status(
                new_status=status,
                reviewer=user,
                score=score,
                comment=comment,
                contest=contest,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            db.session.rollback()
            print(f"Review error (simple): {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    return (
        jsonify(
            {
                "message": "Submission reviewed successfully",
                "submission": submission.to_dict(include_user_info=True),
            }
        ),
        200,
    )
