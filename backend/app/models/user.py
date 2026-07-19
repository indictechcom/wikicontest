"""
User Model for WikiEval Application
Defines the User table and related functionality
"""

from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from app.database import db
from app.models.base_model import BaseModel
import sqlalchemy as sa


# ------------------------------------------------------------------------====
# USER MODEL
# ------------------------------------------------------------------------====

class User(BaseModel):
    """
    User model representing users in the WikiEval platform

    Attributes:
        id: Primary key, auto-incrementing integer
        username: Unique username for the user
        email: Unique email address
        role: User role (superadmin, admin, user, etc.)
        password: Hashed password
        score: Total score accumulated by user
        created_at: Timestamp when user was created
    """

    __tablename__ = "users"


    # ------------------------------------------------------------------------
    # Database Columns - Core Fields
    # ------------------------------------------------------------------------

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # User identification (both indexed for fast lookups during login)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)

    # Role-based access control: 'user', 'admin', or 'superadmin'
    role = db.Column(db.String(20), nullable=False, default="user")

    # Password stored as bcrypt hash (never store plaintext)
    password = db.Column(db.String(255), nullable=False)

    # Aggregate score across all submissions
    score = db.Column(db.Integer, default=0, nullable=False)

    # OAuth tokens for MediaWiki API access
    # These are stored when user authenticates via OAuth and allow
    # the application to make edits on behalf of the user
    oauth_token = db.Column(db.String(255), nullable=True)
    oauth_token_secret = db.Column(db.String(255), nullable=True)

    # Trusted member status - allows user to create contests
    # Only trusted members (and superadmins) can create contests
    # Regular users can still submit and participate in contests
    is_trusted_member = db.Column(db.Boolean, default=False, nullable=False)

    # Track if user has requested trusted member status
    # Superadmins can view all requests and approve/reject them
    trusted_member_request = db.Column(db.Boolean, default=False, nullable=False)

    # Reason provided by user when requesting trusted member status
    # This is required when user has less than 300 edits
    # Superadmins can view this reason when reviewing requests
    trusted_member_request_reason = db.Column(db.Text, nullable=True)

    # Status of trusted member request
    # Values: 'pending' (awaiting review), 'approved' (granted), 'rejected' (denied)
    # This allows tracking the complete request lifecycle
    trusted_member_request_status = db.Column(
        sa.Enum('pending', 'approved', 'rejected', name='trusted_member_request_status_enum'),
        nullable=True
    )

    # Account creation timestamp (UTC)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


    # ------------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------------

    # One-to-many: User has created many contests
    created_contests = db.relationship("Contest", backref="creator", lazy="dynamic")

    # One-to-many: User has submitted many submissions
    submissions = db.relationship(
        "Submission",
        foreign_keys="Submission.user_id",
        back_populates="submitter",
        lazy="dynamic",
    )

    # One-to-many: User has reviewed many submissions (as jury member)
    # Separate relationship to avoid conflict with submissions relationship
    reviewed_submissions = db.relationship(
        "Submission",
        foreign_keys="Submission.reviewed_by",
        primaryjoin="User.id == Submission.reviewed_by",
        back_populates="reviewer",
        overlaps="submissions",
    )


    # ------------------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------------------

    def __init__(self, username, email, password, role="user"):
        """
        Initialize a new User instance

        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password (will be hashed)
            role: User role (defaults to 'user')
        """
        self.username = username
        self.email = email
        self.set_password(password)  # Hash password before storing
        self.role = role
        self.score = 0


    # ------------------------------------------------------------------------
    # PASSWORD MANAGEMENT
    # ------------------------------------------------------------------------

    def set_password(self, password):
        """
        Hash and set the user's password using bcrypt

        Args:
            password: Plain text password to hash
        """
        # Generate secure bcrypt hash (includes salt automatically)
        self.password = generate_password_hash(password)


    def check_password(self, password):
        """
        Check if provided password matches the user's password

        Args:
            password: Plain text password to check

        Returns:
            bool: True if password matches, False otherwise
        """
        # Verify password against stored hash (timing-safe comparison)
        return check_password_hash(self.password, password)


    # ------------------------------------------------------------------------
    # SCORE MANAGEMENT
    # ------------------------------------------------------------------------

    def update_score(self, score_change):
        """
        Update user's total score by adding/subtracting points

        Args:
            score_change: Amount to add (positive) or subtract (negative)
        """
        self.score += score_change

        # Note: Don't commit here - let the caller handle transaction
        # This allows multiple updates to be batched in a single commit


    # ------------------------------------------------------------------------
    # ROLE CHECKS
    # ------------------------------------------------------------------------

    def is_admin(self):
        """
        Check if user has admin-level privileges

        NOTE:
        - Treats both 'admin' and 'superadmin' as admin-level users
        - This simplifies permission checks: any code checking is_admin()
          automatically grants access to superadmins as well

        Returns:
            bool: True if user is admin or superadmin, False otherwise
        """
        # Both admin and superadmin share admin powers
        return self.role in ('admin', 'superadmin')


    def is_superadmin(self):
        """
        Check if user has the superadmin role (highest privilege level)

        Superadmin notes:
        - Should be created and managed carefully (use sparingly)
        - Use this when you explicitly need to target only superadmins
        - For most permission checks, use is_admin() instead

        Returns:
            bool: True if user is superadmin, False otherwise
        """
        return self.role == 'superadmin'


    # ------------------------------------------------------------------------
    # TRUSTED MEMBER CHECKS
    # ------------------------------------------------------------------------

    def can_create_contests(self):
        """
        Check if user can create contests

        Only trusted members and superadmins can create contests.
        Regular users can still submit and participate in contests.

        Returns:
            bool: True if user can create contests, False otherwise
        """
        # Superadmins are automatically allowed to create contests
        if self.is_superadmin():
            return True
        # Check trusted member status (use getattr for safety during migration)
        return bool(getattr(self, 'is_trusted_member', False))


    # ------------------------------------------------------------------------
    # CONTEST-SPECIFIC PERMISSION CHECKS
    # ------------------------------------------------------------------------

    def is_jury_member(self, contest):
        """
        Check if user is a jury member for a specific contest

        Args:
            contest: Contest instance to check

        Returns:
            bool: True if user is jury member, False otherwise
        """
        # No jury members assigned
        if not contest.jury_members:
            return False

        # Parse comma-separated list and check for username match
        jury_usernames = [
            username.strip() for username in contest.jury_members.split(",")
        ]
        return self.username in jury_usernames


    def is_contest_creator(self, contest):
        """
        Check if user created a specific contest

        Args:
            contest: Contest instance to check

        Returns:
            bool: True if user created the contest, False otherwise
        """
        return self.username == contest.created_by


    def is_contest_organizer(self, contest):
        """
        Check if user is an organizer for a specific contest

        Organizers have management permissions (edit, view submissions, etc.)
        Creator is always included in organizers list

        Args:
            contest: Contest instance to check

        Returns:
            bool: True if user is organizer, False otherwise
        """
        if not contest:
            return False

        # Get organizers list from contest
        organizers = contest.get_organizers()
        if not organizers:
            # Fallback: creator is always an organizer even if organizers field is empty
            return self.username.strip().lower() == (contest.created_by or '').strip().lower()

        # Normalize usernames for case-insensitive comparison
        username_lower = self.username.strip().lower()
        organizer_usernames = [org.strip().lower() for org in organizers]

        return username_lower in organizer_usernames


    # ------------------------------------------------------------------------
    # SUBMISSION ACCESS CONTROL
    # ------------------------------------------------------------------------

    def can_access_submission(self, submission):
        """
        Check if user can access (view/review) a specific submission

        Access is granted to:
        - Admins (universal access)
        - Submission owner
        - Jury members of the contest
        - Contest creator
        - Contest organizers

        Args:
            submission: Submission instance to check

        Returns:
            bool: True if user can access submission, False otherwise
        """
        # Admins have universal access to all submissions
        if self.is_admin():
            return True

        # Users can access their own submissions
        if submission.user_id == self.id:
            return True

        # Jury members can access submissions in their assigned contests
        if self.is_jury_member(submission.contest):
            return True

        # Contest creators can access all submissions in their contests
        if self.is_contest_creator(submission.contest):
            return True

        # Contest organizers can access submissions in contests they manage
        if self.is_contest_organizer(submission.contest):
            return True

        return False


    # ------------------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------------------

    def to_dict(self):
        """
        Convert user instance to dictionary for JSON serialization

        Returns:
            dict: User data (excludes password for security)
        """
        # Superadmins are automatically treated as trusted members
        is_trusted = bool(getattr(self, 'is_trusted_member', False))
        if self.is_superadmin():
            is_trusted = True

        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "score": self.score,
            # Trusted member status (superadmins are automatically trusted)
            "is_trusted_member": is_trusted,
            "trusted_member_request": bool(getattr(self, 'trusted_member_request', False)),
            "trusted_member_request_reason": getattr(self, 'trusted_member_request_reason', None),
            "trusted_member_request_status": getattr(self, 'trusted_member_request_status', None),
            # Convert datetime to ISO format string
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


    def __repr__(self):
        """String representation of User instance"""
        return f"<User {self.username}>"
