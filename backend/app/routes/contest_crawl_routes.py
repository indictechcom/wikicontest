"""
Contest category-crawl routes for WikiEval Application.

Handles importing articles from a MediaWiki category into a contest as pending
submissions. Extracted from the original monolithic contest_routes.py.
Registered at /api/contest along with the other contest blueprints.
"""

from datetime import datetime, timezone
import os
import traceback

# ---------------------------------------------------------------------------
# Category crawler rate-limiting constants (PR #198 Comment #6)
# ---------------------------------------------------------------------------
# Maximum articles that can ever be imported in a single crawl request.
# Keeps the value configurable on the server without touching code:
#   export MAX_CRAWL_LIMIT=3000
_MAX_CRAWL_LIMIT: int = int(os.environ.get("MAX_CRAWL_LIMIT", "2000"))

# Default when the caller omits the `limit` field in the request body.
_DEFAULT_CRAWL_LIMIT: int = 500

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.middleware.auth import require_auth, require_role, handle_errors, validate_json_data
from app.models.contest import Contest
from app.models.submission import Submission
from app.models.user import User
from app.models.contest_request import ContestRequest
from app.utils import (
    crawl_category_articles,
)
from app.utils.url_validation import validate_wiki_url
from app.routes._contest_helpers import validate_date_string, parse_date_or_none


# Create Flask blueprint
contest_crawl_bp = Blueprint("contest_crawl", __name__)


@contest_crawl_bp.route("/<int:contest_id>/crawl-category", methods=["POST"])
@require_auth
@handle_errors
@validate_json_data(["category_url"])
def crawl_category_for_contest(contest_id):
    """
    Crawls a Wikipedia category and imports its articles as pending submissions for a contest.
    
    Parameters:
        contest_id (int): Identifier of the contest receiving the submissions.
    
    Returns:
        tuple: A Flask JSON response and HTTP status code indicating the crawl result.
    """
    try:
        user = request.current_user
        data = request.get_json()

        # Fetch contest
        contest = db.session.get(Contest, contest_id)
        if not contest:
            return jsonify({"error": "Contest not found"}), 404

        # Check if contest uses automated scoring
        try:
            scoring_mode = contest.get_scoring_mode()
        except Exception as e:
            current_app.logger.error(f"Error getting scoring mode: {str(e)}")
            scoring_mode = "simple"

        if scoring_mode != "automated":
            return jsonify({
                "error": (
                    f"Category crawling is only available for automated scoring contests. "
                    f"Current mode: {scoring_mode}"
                )
            }), 400

        # Permission check: jury member or superadmin only
        jury_members = contest.get_jury_members() if hasattr(contest, "get_jury_members") else []
        is_jury_member = user.username in jury_members if jury_members else False
        is_superadmin = getattr(user, "role", None) == "superadmin"

        if not (is_jury_member or is_superadmin):
            return jsonify({"error": "You do not have permission to crawl categories for this contest"}), 403

        # Get parameters
        category_url = data.get("category_url")

        # Enforce rate limiting: cap imports per request to prevent server
        # overload and MediaWiki API timeouts (PR #198 Comment #6).
        # Default: 500  |  Hard cap: MAX_CRAWL_LIMIT (default 2000, env-configurable)
        try:
            requested_limit = int(data.get("limit", _DEFAULT_CRAWL_LIMIT))
            limit = min(max(requested_limit, 1), _MAX_CRAWL_LIMIT)
        except (ValueError, TypeError):
            limit = _DEFAULT_CRAWL_LIMIT

        # Optional cmcontinue token from a previous crawl batch.
        # When present the crawler resumes from this position in the category
        # instead of starting from the beginning (supports "Import Next Batch").
        continue_from = data.get("continue_from") or None

        # Crawl the category
        result = crawl_category_articles(
            category_url,
            limit=limit,
            continue_from=continue_from,
        )

        if not result:
            return jsonify({
                "error": "Failed to crawl category. Please check the category URL."
            }), 400

        articles = result.get("articles", [])
        imported = []
        skipped = 0

        # Get existing article links for this contest to avoid duplicates
        existing_links = set(
            row[0]
            for row in db.session.query(Submission.article_link)
            .filter_by(contest_id=contest_id)
            .all()
        )

        # Create submissions for each article
        for article in articles:
            article_url = article.get("url")
            article_title = article.get("title")

            # Skip if already submitted
            if article_url in existing_links:
                skipped += 1
                continue

            # Create pending submission
            submission = Submission(
                user_id=user.id,
                contest_id=contest_id,
                article_title=article_title,
                article_link=article_url,
                status="pending",
            )

            try:
                submission.save()
                imported.append(article_title)
                existing_links.add(article_url)
            except IntegrityError:
                db.session.rollback()
                skipped += 1
            except Exception as e:
                current_app.logger.error(f"Error creating submission for {article_title}: {str(e)}")
                db.session.rollback()
                skipped += 1

        return jsonify({
            "message": f"Successfully imported {len(imported)} articles from category",
            "total_imported": len(imported),
            "skipped": skipped,
            "category": result.get("category"),
            "wiki_base": result.get("wiki_base"),
            "articles": imported[:100],
            # Pagination: pass next_continue back to the client so it can
            # request the next batch with "Import Next Batch" (Option B).
            "has_more": result.get("has_more", False),
            "next_continue": result.get("next_continue"),
        }), 200


    except Exception as e:
        current_app.logger.error(f"crawl_category_for_contest error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500
