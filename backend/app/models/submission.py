"""
Submission Model for WikiContest Application
Defines the Submission table and related functionality
"""

from datetime import datetime, timezone
import json
from app.database import db
from app.models.base_model import BaseModel


# ------------------------------------------------------------------------====
# SUBMISSION MODEL
# ------------------------------------------------------------------------====

class Submission(BaseModel):
    """
    Submission model representing user submissions to contests

    Attributes:
        id: Primary key, auto-incrementing integer
        user_id: Foreign key to users table
        contest_id: Foreign key to contests table
        article_title: Title of the submitted article
        article_link: URL link to the submitted article
        status: Status of the submission (pending, accepted, rejected)
        score: Score awarded to the submission
        submitted_at: Timestamp when submission was made
    """

    __tablename__ = "submissions"


    # ------------------------------------------------------------------------
    # Database Columns - Core Fields
    # ------------------------------------------------------------------------

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign keys - link to user and contest
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    contest_id = db.Column(db.Integer, db.ForeignKey("contests.id"), nullable=False)

    # Article identification
    article_title = db.Column(db.String(500), nullable=False)
    article_link = db.Column(db.String(1000), nullable=False)


    # ------------------------------------------------------------------------
    # Database Columns - Article Metadata (from MediaWiki API)
    # ------------------------------------------------------------------------

    # Author from latest revision at submission time (most recent editor)
    article_author = db.Column(db.String(200), nullable=True)

    # When the article was originally created on Wikipedia
    article_created_at = db.Column(db.DateTime, nullable=True)

    # Article size in bytes (MediaWiki calls this "size", not word count)
    article_word_count = db.Column(db.Integer, nullable=True)

    # MediaWiki internal page identifier
    article_page_id = db.Column(db.String(50), nullable=True)

    # Article size in bytes at contest start date
    article_size_at_start = db.Column(db.Integer, nullable=True)

    # Bytes added/removed between contest start and submission time
    # Can be negative if article was reduced in size
    article_expansion_bytes = db.Column(db.Integer, nullable=True)

    # Image count
    image_count = db.Column(db.Integer, nullable=True)

    # Infobox count
    infobox_count = db.Column(db.Integer, nullable=True)

    # Reference Analysis Metrics
    ref_new_count = db.Column(db.Integer, nullable=True, default=0)
    ref_reused_count = db.Column(db.Integer, nullable=True, default=0)

    # Link counts for future scoring evaluation
    # Number of other mainspace articles that link to this article
    incoming_links = db.Column(db.Integer, nullable=True)
    
    # Number of mainspace articles this article links to
    outgoing_links = db.Column(db.Integer, nullable=True)

    # Template enforcement tracking
    # True if template was automatically added to the article during submission
    template_added = db.Column(db.Boolean, nullable=True, default=False)

    # Category enforcement tracking
    # JSON array of category names that were automatically added to the article
    categories_added = db.Column(db.Text, nullable=True)
    # Error message if category attachment failed
    category_error = db.Column(db.Text, nullable=True)

    # Submission status and scoring
    # pending | accepted | rejected | auto_rejected
    status = db.Column(db.String(20), nullable=False, default="pending")

    # Total score awarded to this submission
    score = db.Column(db.Integer, default=0, nullable=False)

    # Individual parameter scores (stored as JSON) for multi-parameter scoring
    # Example: {"Quality": 8, "Sources": 7, "Neutrality": 9, "Formatting": 6}
    parameter_scores = db.Column(db.Text, nullable=True)

    # Automated evaluation details (for automated scoring contests)
    # Reason for rejection (if status is rejected) or success message
    evaluation_reason = db.Column(db.Text, nullable=True)
    
    # Score breakdown as JSON (for accepted submissions in automated contests)
    # Example: {"base_points": 10, "bytes_points": 5.2, "links_points": 3, ...}
    score_breakdown = db.Column(db.Text, nullable=True)


    # ------------------------------------------------------------------------
    # Database Columns - Review Metadata
    # ------------------------------------------------------------------------

    # Who reviewed this submission (jury member or organizer)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # When the review was completed (UTC)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Jury's comment or feedback on the submission
    review_comment = db.Column(db.Text, nullable=True)


    # ------------------------------------------------------------------------
    # Database Columns - Metadata
    # ------------------------------------------------------------------------

    # When the submission was created (UTC)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


    # ------------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------------

    # Many-to-one: Submission belongs to a user (submitter)
    submitter = db.relationship(
        "User", foreign_keys=[user_id], back_populates="submissions"
    )

    # Many-to-one: Submission reviewed by a user (jury member)
    # Uses separate relationship to avoid conflicts with submitter
    reviewer = db.relationship(
        "User",
        foreign_keys=[reviewed_by],
        primaryjoin="Submission.reviewed_by == User.id",
        back_populates="reviewed_submissions",
        overlaps="submissions",
    )

    # Many-to-one: Submission belongs to a contest
    contest = db.relationship("Contest", back_populates="submissions")


    # ------------------------------------------------------------------------
    # Database Constraints
    # ------------------------------------------------------------------------

    # Prevent duplicate submissions: same user + contest + article combination
    # Users can submit multiple articles to a contest, but not the same article twice
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "contest_id",
            "article_link",
            name="unique_user_contest_article_submission",
        ),
    )


    # ------------------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------------------

    def __init__(
        self,
        user_id,
        contest_id,
        article_title,
        article_link,
        status="pending",
        article_author=None,
        article_created_at=None,
        article_word_count=None,
        article_page_id=None,
        article_size_at_start=None,
        article_expansion_bytes=None,
        template_added=False,
        categories_added=None,
        category_error=None,
        image_count=None,
        infobox_count=None,
        ref_new_count=0,
        ref_reused_count=0,
        incoming_links=None,
        outgoing_links=None,
    ):
        """
        Initialize a new Submission instance

        Args:
            user_id: ID of the user making the submission
            contest_id: ID of the contest being submitted to
            article_title: Title of the submitted article
            article_link: URL to the submitted article
            status: Initial status (defaults to 'pending')
            article_author: Author from latest revision at submission time (optional, fetched from MediaWiki API)
            article_created_at: When article was created (optional, fetched from MediaWiki API)
            article_word_count: Word count/size of article in bytes (optional, fetched from MediaWiki API)
            article_page_id: MediaWiki page ID (optional, fetched from MediaWiki API)
            article_size_at_start: Article size in bytes at contest start (optional)
            article_expansion_bytes: Bytes added between contest start and submission time (optional)
            template_added: Whether template was automatically added to article (optional)
            categories_added: List of category names that were automatically added (optional, stored as JSON)
            category_error: Error message if category attachment failed (optional)
            image_count: Number of images in the article (optional)
            infobox_count: Number of infoboxes in the article (optional)
            ref_new_count: Number of new references added to the article (optional)
            ref_reused_count: Number of reused references in the article (optional)
            incoming_links: Number of other mainspace articles that link to this article (optional)
            outgoing_links: Number of mainspace articles this article links to (optional)
        """
        # Set required fields
        self.user_id = user_id
        self.contest_id = contest_id
        self.article_title = article_title
        self.article_link = article_link
        self.status = status
        self.score = 0

        # Set article metadata (fetched from MediaWiki API)
        self.article_author = article_author
        self.article_created_at = article_created_at
        self.article_word_count = article_word_count
        self.article_page_id = article_page_id
        self.article_size_at_start = article_size_at_start
        self.article_expansion_bytes = article_expansion_bytes
        self.template_added = template_added
        # Set category tracking
        # Store categories_added as JSON string if it's a list, otherwise store as-is
        if categories_added is not None:
            if isinstance(categories_added, list):
                self.categories_added = json.dumps(categories_added)
            else:
                self.categories_added = categories_added
        else:
            self.categories_added = None
        self.category_error = category_error
        self.image_count = image_count
        self.infobox_count = infobox_count
        self.ref_new_count = ref_new_count
        self.ref_reused_count = ref_reused_count
        self.incoming_links = incoming_links
        self.outgoing_links = outgoing_links
        self.reviewed_by = None
        self.reviewed_at = None
        self.review_comment = None
        self.parameter_scores = None


    # ------------------------------------------------------------------------
    # STATUS CHECKS
    # ------------------------------------------------------------------------

    def is_pending(self):
        """
        Check if submission is pending

        Returns:
            bool: True if submission is pending, False otherwise
        """
        return self.status == "pending"


    def is_accepted(self):
        """
        Check if submission is accepted

        Returns:
            bool: True if submission is accepted, False otherwise
        """
        return self.status == "accepted"


    def is_rejected(self):
        """
        Check if submission is rejected

        Returns:
            bool: True if submission is rejected, False otherwise
        """
        return self.status == "rejected"


    # ------------------------------------------------------------------------
    # CATEGORIES ADDED MANAGEMENT
    # ------------------------------------------------------------------------

    def get_categories_added(self):
        """
        Get categories_added as list.

        Returns:
            list or None: List of category names that were added, or None if empty
        """
        if not self.categories_added:
            return None
        try:
            # Parse JSON string back to list
            return json.loads(self.categories_added)
        except json.JSONDecodeError:
            # Return empty list if JSON is corrupted
            return []


    # ------------------------------------------------------------------------
    # PARAMETER SCORES MANAGEMENT (Multi-Parameter Scoring)
    # ------------------------------------------------------------------------

    def set_parameter_scores(self, scores):
        """
        Set individual parameter scores

        Args:
            scores: Dict mapping parameter names to scores (0-10)
                   Example: {"Quality": 8, "Sources": 7, ...}
        """
        if scores is None:
            self.parameter_scores = None
        elif isinstance(scores, dict):
            # Store as JSON string for database
            self.parameter_scores = json.dumps(scores)
        else:
            self.parameter_scores = None


    def get_parameter_scores(self):
        """
        Get individual parameter scores

        Returns:
            dict or None: Parameter scores mapping
        """
        if not self.parameter_scores:
            return None
        try:
            # Parse JSON string back to dictionary
            return json.loads(self.parameter_scores)
        except json.JSONDecodeError:
            return None

    def get_score_breakdown(self):
        """
        Get score breakdown for automated scoring

        Returns:
            dict or None: Score breakdown with points per category
        """
        if not self.score_breakdown:
            return None
        try:
            return json.loads(self.score_breakdown)
        except json.JSONDecodeError:
            return None


    # ------------------------------------------------------------------------
    # SUBMISSION STATUS UPDATE
    # ------------------------------------------------------------------------

    def update_status(
        self,
        new_status,
        reviewer=None,
        score=None,
        comment=None,
        contest=None,
        parameter_scores=None,
    ):
        """
        Update submission status and calculate score

        Supports both simple scoring (fixed points) and multi-parameter scoring
        (weighted average of individual parameter scores)

        Args:
            new_status: New status ('accepted', 'rejected', 'pending')
            reviewer: User instance who is reviewing
            score: Manual score override (simple scoring only)
            comment: Review comment/feedback
            contest: Contest instance (fetched if not provided)
            parameter_scores: Dict of parameter scores (multi-parameter scoring)

        Returns:
            bool: True if status was changed, False if already at new_status
        """
        # No-op if status hasn't changed
        if self.status == new_status:
            return False

        # Fetch contest if not provided
        if not contest:
            contest = self.contest

        # Determine final score based on scoring system
        if (
            contest.is_multi_parameter_scoring_enabled()
            and new_status == "accepted"
            and parameter_scores
        ):
            # NEW SYSTEM: Multi-parameter scoring
            # Calculate weighted average from individual parameter scores
            final_score = contest.calculate_weighted_score(parameter_scores)
            self.set_parameter_scores(parameter_scores)
        else:
            # OLD SYSTEM: Simple fixed scoring
            if new_status == "accepted":
                # Use manual score if provided, otherwise use contest default
                final_score = (
                    score if score is not None else contest.marks_setting_accepted
                )
            elif new_status == "rejected":
                # Use contest's rejection points (usually 0)
                final_score = contest.marks_setting_rejected
            else:
                # Pending submissions have no score
                final_score = 0
            # Clear parameter scores when using simple scoring
            self.parameter_scores = None

        # Calculate score change to update user's total
        score_difference = final_score - self.score

        # Update submission fields
        self.status = new_status
        self.score = final_score
        self.reviewed_by = reviewer.id if reviewer else None
        self.reviewed_at = datetime.now(timezone.utc)
        self.review_comment = comment

        # Update user's total score across all submissions
        if score_difference != 0:
            # Ensure submitter relationship is loaded
            if self.submitter is None:
                from app.models.user import User
                self.submitter = User.query.get(self.user_id)
                if self.submitter is None:
                    raise ValueError(f"Submitter user with id {self.user_id} not found")

            # Propagate score change to user's total
            self.submitter.update_score(score_difference)

        # Persist all changes to database
        db.session.commit()
        return True


    # ------------------------------------------------------------------------
    # PERMISSION CHECKS
    # ------------------------------------------------------------------------

    def can_be_judged_by(self, user):
        """
        Check if a user can judge this submission

        Args:
            user: User instance to check

        Returns:
            bool: True if user can judge submission, False otherwise
        """
        # Admins have universal judging permission
        if user.is_admin():
            return True

        # Jury members can judge submissions in their assigned contests
        if user.is_jury_member(self.contest):
            return True

        return False

    def can_be_deleted_by(self, user):
        """
        Check if a user can delete this submission

        Args:
            user: User instance to check

        Returns:
            bool: True if user can delete submission, False otherwise
        """
        # Admin can delete all submissions
        if user.is_admin():
            return True

        # Jury members can delete submissions in their contests
        if user.is_jury_member(self.contest):
            return True

        # Contest creators can delete submissions in their contests
        if user.is_contest_creator(self.contest):
            return True

        return False


    def can_be_viewed_by(self, user):
        """
        Check if a user can view this submission

        Args:
            user: User instance to check

        Returns:
            bool: True if user can view submission, False otherwise
        """
        # Admins can view all submissions
        if user.is_admin():
            return True

        # Users can view their own submissions
        if self.user_id == user.id:
            return True

        # Jury members can view submissions in their contests
        if user.is_jury_member(self.contest):
            return True

        # Contest creators/organizers can view submissions in their contests
        if user.is_contest_creator(self.contest):
            return True

        return False


    # ------------------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------------------

    def to_dict(self, include_user_info=False):
        """
        Convert submission instance to dictionary for JSON serialization

        Args:
            include_user_info: Whether to include user information

        Returns:
            dict: Submission data
        """
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "contest_id": self.contest_id,

            # Article information
            "article_title": self.article_title,
            "article_link": self.article_link,

            # Submission status and scoring
            "status": self.status,
            "score": self.score,

            # Timestamps - add 'Z' suffix to indicate UTC timezone
            # This ensures JavaScript interprets it as UTC, not local time
            "submitted_at": (
                (self.submitted_at.isoformat() + "Z") if self.submitted_at else None
            ),

            # Article metadata (from MediaWiki API)
            "article_author": self.article_author,
            "article_created_at": (
                (self.article_created_at.isoformat() + "Z")
                if self.article_created_at
                else None
            ),
            "article_word_count": self.article_word_count,
            "article_page_id": self.article_page_id,
            "article_size_at_start": self.article_size_at_start,
            "article_expansion_bytes": self.article_expansion_bytes,
            "image_count": self.image_count,
            "infobox_count": self.infobox_count,
            "ref_new_count": self.ref_new_count,
            "ref_reused_count": self.ref_reused_count,
            "incoming_links": self.incoming_links,
            "outgoing_links": self.outgoing_links,
            "template_added": self.template_added,
            "categories_added": self.get_categories_added(),
            "category_error": self.category_error,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": (
                self.reviewed_at.isoformat() + "Z" if self.reviewed_at else None
            ),
            "review_comment": self.review_comment,
            "already_reviewed": self.reviewed_at is not None,

            # Multi-parameter scoring data
            "parameter_scores": self.get_parameter_scores(),

            # Automated evaluation details
            "evaluation_reason": self.evaluation_reason,
            "score_breakdown": self.get_score_breakdown(),
        }

        # Optionally include related user and contest information
        if include_user_info:
            data.update(
                {
                    "username": self.submitter.username,
                    "email": self.submitter.email,
                    "contest_name": self.contest.name,
                }
            )

        return data


    def __repr__(self):
        """String representation of Submission instance"""
        return f"<Submission {self.id}: {self.article_title}>"
