"""
Contest Model for WikiEval Application
Defines the Contest table and related functionality
"""

import json
from datetime import datetime, date

from app.database import db
from app.models.base_model import BaseModel
from app.models.contest_mixin import ContestMixin


# ------------------------------------------------------------------------
# CONTEST MODEL
# ------------------------------------------------------------------------

class Contest(BaseModel, ContestMixin):
    """
    Contest model representing contests in the WikiEval platform

    Attributes:
        id: Primary key, auto-incrementing integer
        name: Name of the contest
        project_name: Name of the associated project (e.g., 'Wikimedia')
        created_by: Username of the user who created the contest
        description: Description of the contest
        start_date: Start date of the contest
        end_date: End date of the contest
        rules: JSON string containing contest rules
        marks_setting_accepted: Points awarded for accepted submissions
        marks_setting_rejected: Points awarded for rejected submissions
        jury_members: Comma-separated list of jury member usernames
        created_at: Timestamp when contest was created
    """

    __tablename__ = "contests"

    # ------------------------------------------------------------------------
    # Database Columns - Core Fields
    # ------------------------------------------------------------------------

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Contest basic information
    name = db.Column(db.String(200), nullable=False)
    project_name = db.Column(db.String(100), nullable=False)

    # Contest creator (foreign key to users.username)
    created_by = db.Column(
        db.String(50), db.ForeignKey("users.username"), nullable=False
    )

    # Contest details
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    # ------------------------------------------------------------------------
    # Database Columns - Scoring & Rules
    # ------------------------------------------------------------------------

    # Contest rules (stored as JSON string)
    rules = db.Column(db.Text, nullable=True)

    # Simple scoring: fixed points for accepted/rejected submissions
    marks_setting_accepted = db.Column(db.Integer, default=0, nullable=False)
    marks_setting_rejected = db.Column(db.Integer, default=0, nullable=False)

    # Multi-parameter scoring configuration (stored as JSON string)
    scoring_parameters = db.Column(db.Text, nullable=True)

    # Automated scoring configuration (stored as JSON string)
    # Contains eligibility criteria and evaluation parameters
    automated_settings = db.Column(db.Text, nullable=True)

    # Submission type restriction: 'new', 'expansion', or 'both'
    allowed_submission_type = db.Column(db.String(20), default="both", nullable=False)

    # ------------------------------------------------------------------------
    # Database Columns - Article Requirements
    # ------------------------------------------------------------------------

    # Minimum byte count required for article submissions
    min_byte_count = db.Column(db.Integer, nullable=False)

    # Minimum reference count (external links) required for submissions
    # Default 0 means no requirement
    min_reference_count = db.Column(db.Integer, nullable=False, default=0)

    # Optional MediaWiki categories (stored as JSON array of URLs)
    # If set, articles must belong to at least one of these categories
    categories = db.Column(db.Text, nullable=True)

    # ------------------------------------------------------------------------
    # Database Columns - People Management
    # ------------------------------------------------------------------------

    # Jury members who can review submissions (comma-separated usernames)
    jury_members = db.Column(db.Text, nullable=True)

    # Template link for contest (URL to Wiki template page)
    # Used to enforce template attachment on submitted articles
    template_link = db.Column(db.Text, nullable=True)

    # Outreach Dashboard URL (base URL for Outreach Dashboard course)
    # Used to link contest with Outreach Dashboard course data
    outreach_dashboard_url = db.Column(db.Text, nullable=True)

    # Contest organizers who can manage the contest (comma-separated usernames)
    # Creator is always included as an organizer
    organizers = db.Column(db.Text, nullable=True)

    # ------------------------------------------------------------------------
    # Database Columns - Metadata
    # ------------------------------------------------------------------------

    # Timestamp when contest was created (UTC)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # ------------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------------

    # One-to-many: Contest has many submissions
    # lazy='dynamic' returns a query object instead of loading all submissions
    submissions = db.relationship(
        "Submission", back_populates="contest", lazy="dynamic"
    )

    # ------------------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------------------

    def __init__(self, name, project_name, created_by, **kwargs):
        """
        Initialize a contest with required details and optional configuration.
        
        Parameters:
            name: Contest name.
            project_name: Associated project name.
            created_by: Username of the contest creator.
            **kwargs: Optional dates, scoring settings, submission requirements, links,
                categories, rules, jury members, and organizers.
        """
        # Set required fields
        self.name = name
        self.project_name = project_name
        self.created_by = created_by

        # Set optional basic attributes with defaults
        self.description = kwargs.get("description")
        self.start_date = kwargs.get("start_date")
        self.end_date = kwargs.get("end_date")
        self.marks_setting_accepted = kwargs.get("marks_setting_accepted", 0)
        self.marks_setting_rejected = kwargs.get("marks_setting_rejected", 0)
        self.allowed_submission_type = kwargs.get("allowed_submission_type", "both")

        # Set scoring configuration (handles validation internally)
        self.set_scoring_parameters(kwargs.get("scoring_parameters"))

        # Set automated scoring configuration (handles validation internally)
        self.set_automated_settings(kwargs.get("automated_settings"))

        # Set article requirements
        self.min_byte_count = kwargs.get("min_byte_count", 0)
        self.min_reference_count = kwargs.get("min_reference_count", 0)

        # Set template link (optional)
        self.template_link = kwargs.get("template_link")

        # Set Outreach Dashboard URL (optional)
        self.outreach_dashboard_url = kwargs.get("outreach_dashboard_url")

        # Set complex fields using setter methods (handle JSON/list conversion)
        self.set_categories(kwargs.get("categories", []))
        self.set_rules(kwargs.get("rules", {}))
        self.set_jury_members(kwargs.get("jury_members", []))
        # Set organizers (creator is automatically added by set_organizers)
        self.set_organizers(kwargs.get("organizers", []), creator_username=created_by)

        # Initialize scoring mode cache (per-instance, request-scoped)
        self._scoring_mode_cache = None

    # Note: set_rules, get_rules, set_jury_members, get_jury_members,
    # set_categories, and get_categories are inherited from ContestMixin

    # ------------------------------------------------------------------------
    # ARTICLE VALIDATION
    # ------------------------------------------------------------------------

    def validate_byte_count(self, byte_count):
        """
        Determine whether an article meets the contest's minimum byte-count requirement.
        
        Parameters:
            byte_count (int or None): The article's byte count, or None if it could not be determined.
        
        Returns:
            tuple: A boolean indicating validity and an error message, or None when the article is valid.
        """
        # Handle case where MediaWiki API failed to fetch article size
        if byte_count is None:
            return (
                False,
                "Article byte count could not be determined. Please ensure the article exists and try again.",
            )

        # Validate against minimum requirement (always enforced)
        if byte_count < self.min_byte_count:
            return (
                False,
                f"Article byte count ({byte_count}) is below the minimum required ({self.min_byte_count} bytes)",
            )

        # Validation passed
        return True, None

    def validate_reference_count(self, reference_count):
        """
        Validate whether an article meets the contest's minimum reference requirement.
        
        Parameters:
            reference_count (int or None): Number of references in the article.
        
        Returns:
            tuple: `(True, None)` if the requirement is met; otherwise, `(False, error_message)`.
        """
        # If no minimum requirement is set (min_reference_count = 0), always pass
        if self.min_reference_count == 0:
            return True, None

        # Handle case where MediaWiki API failed to fetch reference count
        if reference_count is None:
            return (
                False,
                "Article reference count could not be determined. Please ensure the article exists and try again.",
            )

        # Validate against minimum requirement
        if reference_count < self.min_reference_count:
            return (
                False,
                f"Article reference count ({reference_count}) is below the "
                f"minimum required ({self.min_reference_count} references)",
            )

        # Validation passed
        return True, None

    # ------------------------------------------------------------------------
    # CONTEST STATUS CHECKS
    # ------------------------------------------------------------------------

    def is_active(self):
        """
        Determine whether the contest is currently active.
        
        Returns:
        	bool: `True` if today falls between the contest's start and end dates, inclusive, `False` otherwise.
        """
        # Cannot be active without dates
        if not self.start_date or not self.end_date:
            return False

        # Check if today falls within contest period
        today = date.today()
        return self.start_date <= today <= self.end_date

    def is_upcoming(self):
        """
        Determine whether the contest is scheduled to start in the future.
        
        Returns:
        	bool: `True` if the start date is after today, `False` otherwise.
        """
        # Cannot be upcoming without start date
        if not self.start_date:
            return False

        # Check if start date is in the future
        today = date.today()
        return self.start_date > today

    def is_past(self):
        """
        Determine whether the contest has ended.
        
        Returns:
        	bool: `True` if the end date is before today, `False` otherwise.
        """
        # Cannot be past without end date
        if not self.end_date:
            return False

        # Check if end date has passed
        today = date.today()
        return self.end_date < today

    def get_status(self):
        """
        Determine the contest's lifecycle status from its start and end dates.
        
        Returns:
            str: ``"current"``, ``"upcoming"``, ``"past"``, or ``"unknown"``.
        """
        # Determine status based on date checks
        if self.is_active():
            return "current"
        if self.is_upcoming():
            return "upcoming"
        if self.is_past():
            return "past"
        # Fallback for contests without proper dates
        return "unknown"

    # ------------------------------------------------------------------------
    # STATISTICS & QUERIES
    # ------------------------------------------------------------------------

    def get_submission_count(self):
        """
        Count the submissions associated with this contest.
        
        Returns:
            int: The number of submissions.
        """
        # Count submissions using the dynamic relationship query
        return self.submissions.count()

    def get_leaderboard(self):
        """
        Build a score-ranked leaderboard for the contest.
        
        Returns:
        	list: Dictionaries containing each user's ID, username, and total score, ordered by descending total score.
        """
        # Import here to avoid circular imports between models
        from app.models.user import User
        from app.models.submission import Submission

        # Aggregate total scores per user for this contest
        leaderboard_query = (
            db.session.query(
                User.id,
                User.username,
                db.func.sum(Submission.score).label("total_score"),
            )
            .join(Submission)
            .filter(Submission.contest_id == self.id)
            .group_by(User.id, User.username)
            .order_by(db.func.sum(Submission.score).desc())
            .all()
        )

        # Format results as list of dictionaries
        return [
            {
                "user_id": row.id,
                "username": row.username,
                "total_score": row.total_score or 0,
            }
            for row in leaderboard_query
        ]

    # ------------------------------------------------------------------------
    # SCORING PARAMETERS (Multi-Parameter Scoring System)
    # ------------------------------------------------------------------------

    def set_scoring_parameters(self, params):
        """
        Set the contest's scoring parameters and validate enabled parameter weights.
        
        Parameters:
            params (dict or None): Scoring configuration, including parameter weights when multi-parameter scoring is enabled.
        
        Raises:
            ValueError: If enabled parameter weights do not sum to 100.
        """
        # Invalidate scoring mode cache
        self._scoring_mode_cache = None
        if params is None:
            self.scoring_parameters = None
        elif isinstance(params, dict):
            # Validate that parameter weights sum to 100 (if enabled)
            # This validation is specific to Contest model
            if params.get("enabled") and "parameters" in params:
                total_weight = sum(p.get("weight", 0) for p in params["parameters"])
                if total_weight != 100:
                    raise ValueError(
                        f"Parameter weights must sum to 100, got {total_weight}"
                    )
            # Store as JSON string (use parent class logic)
            self.scoring_parameters = json.dumps(params)
        else:
            self.scoring_parameters = None

    # Note: get_scoring_parameters is inherited from ContestMixin

    def set_automated_settings(self, settings):
        """Update the contest's automated scoring settings."""
        self._scoring_mode_cache = None
        super().set_automated_settings(settings)

    def is_multi_parameter_scoring_enabled(self):
        """
        Determine whether multi-parameter scoring is enabled.
        
        Returns:
        	bool: `True` if enabled, `False` otherwise.
        """
        params = self.get_scoring_parameters()
        if not isinstance(params, dict):
            return False
        return params.get("enabled", False)

    def calculate_weighted_score(self, parameter_scores):
        """
        Calculate the contest score from weighted parameter scores.
        
        Parameters:
            parameter_scores (dict): Mapping of parameter names to scores on a 0-10 scale.
        
        Returns:
            int: Weighted score clamped to the configured minimum and maximum, or the accepted mark when multi-parameter scoring is disabled.
        """
        # Fall back to simple scoring if multi-parameter is disabled
        if not self.is_multi_parameter_scoring_enabled():
            return self.marks_setting_accepted

        # Extract scoring configuration
        scoring_config = self.get_scoring_parameters()
        max_score = scoring_config.get("max_score", 100)
        min_score = scoring_config.get("min_score", 0)
        parameters = scoring_config.get("parameters", [])

        # Calculate weighted average of parameter scores
        weighted_sum = 0.0
        for param in parameters:
            param_name = param["name"]
            weight = param["weight"] / 100.0  # Convert percentage to decimal
            score = parameter_scores.get(param_name, 0)  # Default to 0 if missing
            weighted_sum += score * weight

        # Scale weighted average (0-10) to final score range
        # Example: weighted_sum=8.5, max=100 → 8.5 * (100/10) = 85
        final_score = int(weighted_sum * (max_score / 10))

        # Clamp score between configured min and max bounds
        return max(min(final_score, max_score), min_score)

    # ------------------------------------------------------------------------
    # ORGANIZERS MANAGEMENT (Comma-Separated Storage)
    # ------------------------------------------------------------------------

    # Note: set_organizers and get_organizers are inherited from ContestMixin
    # The mixin version already handles creator_username parameter correctly

    def add_organizer(self, username):
        """
        Add a user to the contest's organizer list.
        
        Parameters:
            username (str): Username to add as an organizer.
        
        Returns:
            tuple: `(True, None)` on success, or `(False, error_message)` if the username is invalid or already an organizer.
        """
        username = username.strip()
        if not username:
            return False, "Invalid username"

        # Check for duplicate
        current_organizers = self.get_organizers()
        if username in current_organizers:
            return False, f"{username} is already an organizer"

        # Add to list and persist
        current_organizers.append(username)
        self.set_organizers(current_organizers, self.created_by)

        return True, None

    def remove_organizer(self, username):
        """
        Remove an organizer while preserving the contest creator and at least one organizer.
        
        Parameters:
            username (str): Username of the organizer to remove.
        
        Returns:
            tuple: `(True, None)` if removed; otherwise, `(False, error_message)`.
        """
        username = username.strip()
        if not username:
            return False, "Invalid username"

        # Verify user is actually an organizer
        current_organizers = self.get_organizers()
        if username not in current_organizers:
            return False, f"{username} is not an organizer"

        # Prevent removing the contest creator
        if username == self.created_by:
            return False, "Cannot remove the contest creator from organizers"

        # Prevent removing the last organizer (contest must have at least one)
        if len(current_organizers) <= 1:
            return False, "Cannot remove the last organizer"

        # Remove from list and persist
        current_organizers.remove(username)
        self.set_organizers(current_organizers, self.created_by)

        return True, None

    def is_organizer(self, username):
        """
        Determine whether a username belongs to the contest's organizers.
        
        Returns:
            bool: `True` if the username is an organizer, `False` otherwise.
        """
        if not username:
            return False

        username = username.strip()
        return username in self.get_organizers()

    def can_change_scoring_system(self):
        """
        Determine whether the contest's scoring system can be changed.
        
        Returns:
            tuple: A boolean and an explanatory reason; the reason is `None` when changes are allowed.
        """
        from app.models.submission import Submission

        # Check if any submissions have been reviewed
        reviewed_count = (
            Submission.query.filter(Submission.contest_id == self.id)
            .filter(Submission.status.in_(["accepted", "rejected"]))
            .count()
        )

        if reviewed_count > 0:
            return (
                False,
                f"Cannot change scoring system: {reviewed_count} submissions have already been reviewed",
            )

        return True, None

    # Internal cache for get_scoring_mode (per-instance, request-scoped)
    _scoring_mode_cache = None

    def get_scoring_mode(self):
        """
        Determine which scoring mode is configured for the contest.
        
        Returns:
        	str: The configured scoring mode: `"automated"`, `"multi_parameter"`, or `"simple"`.
        """
        if self._scoring_mode_cache is not None:
            return self._scoring_mode_cache
        # Check for automated scoring mode first
        automated = self.get_automated_settings()
        if automated and automated.get("enabled") is True:
            self._scoring_mode_cache = "automated"
            return "automated"
        # Then check for multi-parameter scoring
        params = self.get_scoring_parameters()
        if params and params.get("enabled") is True:
            self._scoring_mode_cache = "multi_parameter"
            return "multi_parameter"
        self._scoring_mode_cache = "simple"
        return "simple"

    # ------------------------------------------------------------------------
    # AUTOMATED EVALUATION ENGINE
    # ------------------------------------------------------------------------

    def evaluate_automated_submission(self, submission_data):
        """
        Evaluate a submission using the contest's automated eligibility and scoring criteria.
        
        Parameters:
            submission_data (dict): Submission metrics, including article size, link counts,
                reference counts, image count, and infobox count.
        
        Returns:
            tuple: A tuple of eligibility status, final score, reason, and scoring breakdown.
                The breakdown is `None` when automated scoring is disabled or eligibility
                requirements are not met.
        """
        automated = self.get_automated_settings()
        if not automated or not automated.get("enabled"):
            return False, 0, "Automated scoring not enabled for this contest", None

        eligibility = automated.get("eligibility", {})
        evaluation = automated.get("evaluation", {})

        # --- ELIGIBILITY CHECKS ---
        reasons = []

        # Check minimum byte count (article_word_count stores bytes)
        # NOTE: min_bytes is read from the common contest field (self.min_byte_count)
        # instead of from automated_settings.eligibility.min_bytes (which has no UI
        # and always defaults to 0). This ensures crawled articles are validated
        # against the same threshold that manual submissions use.
        # See PR #198 Comment #13 for full context on this unification.
        min_bytes = self.min_byte_count or 0
        actual_bytes = submission_data.get("article_word_count") or 0
        if min_bytes > 0 and actual_bytes < min_bytes:
            reasons.append(f"Article size ({actual_bytes} bytes) below minimum ({min_bytes} bytes)")

        # Check minimum incoming links
        min_incoming = eligibility.get("min_incoming_links", 0)
        actual_incoming = submission_data.get("incoming_links") or 0
        if min_incoming > 0 and actual_incoming < min_incoming:
            reasons.append(f"Incoming links ({actual_incoming}) below minimum ({min_incoming})")

        # Check minimum outgoing links
        min_outgoing = eligibility.get("min_outgoing_links", 0)
        actual_outgoing = submission_data.get("outgoing_links") or 0
        if min_outgoing > 0 and actual_outgoing < min_outgoing:
            reasons.append(f"Outgoing links ({actual_outgoing}) below minimum ({min_outgoing})")

        # Check minimum references
        # NOTE: min_references is read from the common contest field
        # (self.min_reference_count) for the same reason as min_bytes above.
        min_refs = self.min_reference_count or 0
        actual_refs = (submission_data.get("ref_new_count") or 0) + (submission_data.get("ref_reused_count") or 0)
        if min_refs > 0 and actual_refs < min_refs:
            reasons.append(f"Total references ({actual_refs}) below minimum ({min_refs})")

        # If any eligibility check failed, return rejected
        if reasons:
            return False, 0, "; ".join(reasons), None

        # --- SCORE CALCULATION ---
        score = 0.0
        breakdown = {}

        # Points per accepted article (base points)
        base_points = float(evaluation.get("points_per_accepted", 0))
        score += base_points
        breakdown["base_points"] = base_points

        # Points per byte
        points_per_byte = float(evaluation.get("points_per_byte", 0))
        bytes_points = round(actual_bytes * points_per_byte, 2)
        score += bytes_points
        breakdown["bytes_points"] = bytes_points
        breakdown["bytes_count"] = actual_bytes

        # Points per incoming link
        points_per_incoming = float(evaluation.get("points_per_incoming_link", 0))
        incoming_points = round(actual_incoming * points_per_incoming, 2)
        score += incoming_points
        breakdown["incoming_links_points"] = incoming_points
        breakdown["incoming_links_count"] = actual_incoming

        # Points per outgoing link
        points_per_outgoing = float(evaluation.get("points_per_outgoing_link", 0))
        outgoing_points = round(actual_outgoing * points_per_outgoing, 2)
        score += outgoing_points
        breakdown["outgoing_links_points"] = outgoing_points
        breakdown["outgoing_links_count"] = actual_outgoing

        # Points per new reference
        points_per_new_ref = float(evaluation.get("points_per_new_reference", 0))
        new_refs = submission_data.get("ref_new_count") or 0
        new_ref_points = round(new_refs * points_per_new_ref, 2)
        score += new_ref_points
        breakdown["new_references_points"] = new_ref_points
        breakdown["new_references_count"] = new_refs

        # Points per reused reference
        points_per_reused_ref = float(evaluation.get("points_per_reused_reference", 0))
        reused_refs = submission_data.get("ref_reused_count") or 0
        reused_ref_points = round(reused_refs * points_per_reused_ref, 2)
        score += reused_ref_points
        breakdown["reused_references_points"] = reused_ref_points
        breakdown["reused_references_count"] = reused_refs

        # Points per infobox
        points_per_infobox = float(evaluation.get("points_per_infobox", 0))
        infobox_count = submission_data.get("infobox_count") or 0
        infobox_points = round(infobox_count * points_per_infobox, 2)
        score += infobox_points
        breakdown["infobox_points"] = infobox_points
        breakdown["infobox_count"] = infobox_count

        # Points per image
        points_per_image = float(evaluation.get("points_per_image", 0))
        image_count = submission_data.get("image_count") or 0
        image_points = round(image_count * points_per_image, 2)
        score += image_points
        breakdown["image_points"] = image_points
        breakdown["image_count"] = image_count

        # Round score to 2 decimal places
        final_score = round(score, 2)

        return True, final_score, f"Eligible. Score: {final_score}", breakdown

    # ------------------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------------------

    def to_dict(self):
        """
        Convert the contest to a JSON-serializable dictionary.
        
        Returns:
            dict: Contest fields, configuration settings, organizer information,
                serialized dates, scoring data, automated settings, submission count,
                and status.
        """
        #  Get scoring parameters with proper fallback
        scoring_params = self.get_scoring_parameters()

        #  Ensure it's never None for frontend
        if scoring_params is None:
            scoring_params = {"enabled": False}

        return {
            "id": self.id,
            "name": self.name,
            "project_name": self.project_name,
            "created_by": self.created_by,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "rules": self.get_rules(),
            "marks_setting_accepted": self.marks_setting_accepted,
            "marks_setting_rejected": self.marks_setting_rejected,
            "allowed_submission_type": self.allowed_submission_type,
            "min_byte_count": self.min_byte_count,
            "min_reference_count": self.min_reference_count,
            "categories": self.get_categories(),
            "jury_members": self.get_jury_members(),
            "organizers": self.get_organizers(),
            "template_link": self.template_link,
            "outreach_dashboard_url": self.outreach_dashboard_url,
            "created_at": (
                (self.created_at.isoformat() + "Z") if self.created_at else None
            ),
            #  CRITICAL FIX: Explicitly add scoring_parameters
            "scoring_parameters": scoring_params,
            # Automated scoring settings
            "automated_settings": self.get_automated_settings(),
            # Computed fields
            "submission_count": self.get_submission_count(),
            "status": self.get_status(),
        }

    def __repr__(self):
        """Provide a concise representation of the contest."""
        return f"<Contest {self.name}>"
