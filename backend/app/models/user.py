"""
User Model for WikiContest Application
Defines the User table and related functionality
"""

from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from app.database import db
from app.models.base_model import BaseModel

class User(BaseModel):
    """
    User model representing users in the WikiContest platform

    Attributes:
        id: Primary key, auto-incrementing integer
        username: Unique username for the user
        email: Unique email address
        role: User role (admin, user, etc.)
        password: Hashed password
        score: Total score accumulated by user
        created_at: Timestamp when user was created
    """

    __tablename__ = 'users'

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # User identification fields
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)

    # User role and authentication
    role = db.Column(db.String(20), nullable=False, default='user')
    password = db.Column(db.String(255), nullable=False)

    # User score tracking
    score = db.Column(db.Integer, default=0, nullable=False)

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    created_contests = db.relationship('Contest', backref='creator', lazy='dynamic')
    submissions = db.relationship('Submission', backref='submitter', lazy='dynamic')

    def __init__(self, username, email, password, role='user'):
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
        self.set_password(password)
        self.role = role
        self.score = 0

    def set_password(self, password):
        """
        Hash and set the user's password

        Args:
            password: Plain text password to hash
        """
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """
        Check if provided password matches the user's password

        Args:
            password: Plain text password to check

        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(self.password, password)

    def to_dict(self):
        """
        Convert user instance to dictionary for JSON serialization

        Returns:
            dict: User data without password
        """
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'score': self.score,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def update_score(self, score_change):
        """
        Update user's total score

        Args:
            score_change: Amount to add/subtract from current score
        """
        self.score += score_change
        db.session.commit()

    def is_admin(self):
        """
        Check if user has admin role

        Returns:
            bool: True if user is admin, False otherwise
        """
        return self.role == 'admin'

    def is_jury_member(self, contest):
        """
        Check if user is a jury member for a specific contest

        Args:
            contest: Contest instance to check

        Returns:
            bool: True if user is jury member, False otherwise
        """
        if not contest.jury_members:
            return False

        jury_usernames = [username.strip() for username in contest.jury_members.split(',')]
        return self.username in jury_usernames

    def is_contest_creator(self, contest):
        """
        Check if user created a specific contest

        Args:
            contest: Contest instance to check

        Returns:
            bool: True if user created contest, False otherwise
        """
        return self.username == contest.created_by

    def can_access_submission(self, submission):
        """
        Check if user can access a specific submission

        Args:
            submission: Submission instance to check

        Returns:
            bool: True if user can access submission, False otherwise
        """
        # Admin can access all submissions
        if self.is_admin():
            return True

        # User can access their own submissions
        if submission.user_id == self.id:
            return True

        # Jury members can access submissions in their contests
        if self.is_jury_member(submission.contest):
            return True

        # Contest creators can access submissions in their contests
        if self.is_contest_creator(submission.contest):
            return True

        return False

    def __repr__(self):
        """String representation of User instance"""
        return f'<User {self.username}>'
