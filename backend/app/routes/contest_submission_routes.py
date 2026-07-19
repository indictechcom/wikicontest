"""
Contest submission routes for WikiContest Application.
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
    extract_template_name_from_url,
    check_article_has_template,
    prepend_template_to_article,
    extract_category_name_from_url,
    check_article_has_category,
    append_categories_to_article,
    fetch_article_metrics,
    MEDIAWIKI_API_TIMEOUT,
)
from app.utils.url_validation import validate_wiki_url
from app.routes._contest_helpers import validate_date_string, parse_date_or_none


# Create Flask blueprint
contest_sub_bp = Blueprint("contest_sub", __name__)


@contest_sub_bp.route("/<int:contest_id>/submit", methods=["POST"])
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
    contest = db.session.get(Contest, contest_id)
    if not contest:
        return jsonify({"error": "Contest not found"}), 404

    # --- Input Validation ---
    article_link = data["article_link"].strip()

    if not article_link:
        return jsonify({"error": "Article link is required"}), 400

    # Basic URL validation
    if not (article_link.startswith("http://") or article_link.startswith("https://")):
        return jsonify({"error": "Article link must be a valid URL"}), 400

    # --- Domain Validation Against Contest's Wiki (Automated Scoring Only) ---
    # For automated scoring contests, ensure the submitted article belongs to
    # the same wiki as the contest's configured categories. This prevents
    # cross-wiki submissions (e.g., submitting a French Wikipedia article to
    # an English Wikipedia contest).
    # This check is scoped to automated contests only — simple and
    # multi-parameter scoring modes are left untouched.
    try:
        _is_automated_contest = contest.get_scoring_mode() == "automated"
    except Exception:  # pylint: disable=broad-exception-caught
        _is_automated_contest = False

    if _is_automated_contest:
        contest_categories = contest.get_categories()
        if contest_categories:
            from urllib.parse import urlparse as _urlparse
            allowed_domains = set()
            for cat_url in contest_categories:
                parsed = _urlparse(cat_url)
                if parsed.netloc:
                    allowed_domains.add(parsed.netloc.lower())

            if allowed_domains:
                article_domain = _urlparse(article_link).netloc.lower()
                if article_domain not in allowed_domains:
                    return jsonify({
                        "error": (
                            f"The article URL belongs to '{article_domain}', but this "
                            f"contest only accepts articles from: "
                            f"{', '.join(sorted(allowed_domains))}"
                        )
                    }), 400

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
    ref_new_count = 0
    ref_reused_count = 0
    image_count = None
    infobox_count = None

    # --- Fetch Article Information from MediaWiki API ---
    # MediaWiki API fetching has deep nesting due to complex error handling
    # pylint: disable=too-many-nested-blocks
    try:
        # Extract page title from URL using shared utility function
        page_title = extract_page_title_from_url(article_link)

        if page_title:
            # Parse the article URL to extract base URL
            base_url, error = validate_wiki_url(article_link)
            if error:
                return error

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
            submission_datetime = datetime.now(timezone.utc)

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

    # --- Fetch Supplementary Metrics (Parallel) ---
    metrics = fetch_article_metrics(article_link, contest_start_date=contest.start_date if contest.start_date else None)
    article_reference_count = metrics.get("reference_count")
    ref_new_count = metrics.get("new_ref_count", 0) or 0
    ref_reused_count = metrics.get("reused_ref_count", 0) or 0
    image_count = metrics.get("image_count")
    infobox_count = metrics.get("infobox_count")
    incoming_links = metrics.get("incoming_links")
    outgoing_links = metrics.get("outgoing_links")

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
            image_count=image_count,
            infobox_count=infobox_count,
            ref_new_count=ref_new_count,
            ref_reused_count=ref_reused_count,
            incoming_links=incoming_links,
            outgoing_links=outgoing_links,
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
        # Log details server-side; return only generic message to client
        return jsonify({"error": "Failed to create submission"}), 400
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Handle any other unexpected errors
        # Rollback the session on any error
        db.session.rollback()
        # Log error for debugging (server-side only)
        current_app.logger.error(f"Error creating submission: {type(e).__name__}: {e}")
        current_app.logger.error(traceback.format_exc())
        # Return generic error to client — no internal details
        return jsonify({"error": "Failed to create submission"}), 500

@contest_sub_bp.route("/<int:contest_id>/submissions", methods=["GET"])
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

