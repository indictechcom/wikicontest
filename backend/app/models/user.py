"""
User Model for WikiEval Application
Defines the User table and related functionality
"""

from datetime import datetime, timezone

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
    role = db.Column(
        sa.Enum('user', 'admin', 'superadmin', name='user_role_enum'),
        nullable=False,
        default="user",
    )

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

    # Account creation timestamp (UTC)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


    # ------------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------------

    # One-to-many: User has created many contests
    created_contests = db.relationship(
        "Contest",
        foreign_keys="Contest.created_by",
        back_populates="creator",
        lazy="dynamic",
    )

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
        Initialize a user with account credentials and a role.
        
        Parameters:
            username: The user's unique username.
            email: The user's unique email address.
            password: The user's plaintext password, which is hashed before storage.
            role: The user's role. Defaults to "user".
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
        Hash and store the user's password.
        
        Parameters:
            password (str): The plaintext password to hash.
        """
        # Generate secure bcrypt hash (includes salt automatically)
        self.password = generate_password_hash(password)


    def check_password(self, password):
        """
        Determine whether a plaintext password matches the stored password hash.
        
        Parameters:
            password (str): The plaintext password to verify.
        
        Returns:
            bool: `True` if the password matches, `False` otherwise.
        """
        # Verify password against stored hash (timing-safe comparison)
        return check_password_hash(self.password, password)


    # ------------------------------------------------------------------------
    # SCORE MANAGEMENT
    # ------------------------------------------------------------------------

    def update_score(self, score_change):
        """
        Update the user's total score by applying a positive or negative adjustment.
        
        Parameters:
            score_change: The number of points to add to or subtract from the user's score.
        """
        self.score += score_change

        # Note: Don't commit here - let the caller handle transaction
        # This allows multiple updates to be batched in a single commit


    # ------------------------------------------------------------------------
    # ROLE CHECKS
    # ------------------------------------------------------------------------

    def is_admin(self):
        """
        Determine whether the user has administrator-level privileges.
        
        Returns:
            bool: `True` if the user's role is `"admin"` or `"superadmin"`, `False` otherwise.
        """
        # Both admin and superadmin share admin powers
        return self.role in ('admin', 'superadmin')


    def is_superadmin(self):
        """
        Determine whether the user has the superadmin role.
        
        Returns:
        	bool: `True` if the user's role is `"superadmin"`, `False` otherwise.
        """
        return self.role == 'superadmin'


    # ------------------------------------------------------------------------
    # TRUSTED MEMBER CHECKS
    # ------------------------------------------------------------------------

    def can_create_contests(self):
        """
        Determine whether the user may create contests.
        
        Returns:
            bool: `True` for superadmins and trusted members, `False` otherwise.
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
        Determine whether the user is assigned to a contest's jury.

        Parameters:
            contest: The contest whose jury membership to check.

        Returns:
            bool: True if the user is in the contest's jury, False otherwise.
        """
        if not contest:
            return False
        return self in contest.jury_members_rel

    def is_contest_creator(self, contest):
        """
        Determine whether the user created the specified contest.

        Parameters:
            contest: Contest whose creator is checked.

        Returns:
            `True` if the user's id matches the contest's created_by FK, `False` otherwise.
        """
        if not contest:
            return False
        return self.id == contest.created_by

    def is_contest_organizer(self, contest):
        """
        Determine whether the user organizes the contest.

        Parameters:
            contest: The contest to check.

        Returns:
            bool: `True` if the user is listed as an organizer or is the contest creator when no organizers are listed, and `False` otherwise.
        """
        if not contest:
            return False
        if self in contest.organizers_rel:
            return True
        # Fallback: creator is always treated as an organizer even before
        # the junction-table backfill runs.
        return self.id == contest.created_by


    # ------------------------------------------------------------------------
    # SUBMISSION ACCESS CONTROL
    # ------------------------------------------------------------------------

    def can_access_submission(self, submission):
        """
        Determine whether the user may view or review a submission.
        
        Parameters:
            submission: The submission whose access permissions are being checked.
        
        Returns:
            bool: `True` if the user has access, `False` otherwise.
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
        Serialize the user's data for JSON responses.

        Returns:
        	dict: User data excluding the password, including trust information and the creation timestamp in ISO format when available. Superadmins are represented as trusted members.
        """
        # Superadmins are automatically treated as trusted members
        is_trusted = bool(getattr(self, 'is_trusted_member', False))
        if self.is_superadmin():
            is_trusted = True

        # Find the most recent trusted member request for this user
        latest_request = None
        if hasattr(self, 'trusted_member_requests') and self.trusted_member_requests:
            latest_request = sorted(
                self.trusted_member_requests,
                key=lambda r: r.created_at or datetime.min.replace(tzinfo=None),
                reverse=True,
            )[0]

        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "score": self.score,
            # Trusted member status (superadmins are automatically trusted)
            "is_trusted_member": is_trusted,
            "trusted_member_request_status": latest_request.status if latest_request else None,
            "trusted_member_request_reason": latest_request.reason if latest_request else None,
            # Convert datetime to ISO format string
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


    def __repr__(self):
        """String representation of User instance"""
        return f"<User {self.username}>"
