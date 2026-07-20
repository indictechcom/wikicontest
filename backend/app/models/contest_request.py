"""
Contest Request Model for WikiEval Application
Defines the ContestRequest table for tracking contest creation requests from non-privileged users
"""

from datetime import datetime

from app.database import db
from app.models.base_model import BaseModel
from app.models.contest_mixin import ContestMixin


# ------------------------------------------------------------------------
# CONTEST REQUEST MODEL
# ------------------------------------------------------------------------

class ContestRequest(BaseModel, ContestMixin):
    """
    Contest Request model representing requests to create contests from non-privileged users
    
    Regular users (not superadmin or trusted members) can submit requests to create contests.
    Superadmins can review and approve/reject these requests.
    
    Attributes:
        id: Primary key, auto-incrementing integer
        user_id: Foreign key to users table (who made the request)
        name: Name of the requested contest
        project_name: Name of the associated project
        description: Description of the contest
        start_date: Start date of the contest
        end_date: End date of the contest
        rules: JSON string containing contest rules
        jury_members: Comma-separated list of jury member usernames
        organizers: Comma-separated list of organizer usernames
        min_byte_count: Minimum byte count required
        min_reference_count: Minimum reference count required
        categories: JSON array of category URLs
        template_link: Template link URL (optional)
        scoring_parameters: JSON string containing scoring configuration
        allowed_submission_type: Submission type restriction
        marks_setting_accepted: Points for accepted submissions
        marks_setting_rejected: Points for rejected submissions
        status: Request status ('pending', 'approved', 'rejected')
        reviewed_by: User ID of superadmin who reviewed the request
        reviewed_at: Timestamp when request was reviewed
        created_at: Timestamp when request was created
    """

    __tablename__ = "contest_requests"

    # ------------------------------------------------------------------------
    # Database Columns
    # ------------------------------------------------------------------------

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # User who made the request (foreign key to users table)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Contest information (same fields as Contest model)
    name = db.Column(db.String(200), nullable=False)
    project_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    # Rules stored as JSON string
    rules = db.Column(db.Text, nullable=True)

    # Jury members (comma-separated usernames)
    jury_members = db.Column(db.Text, nullable=True)

    # Organizers (comma-separated usernames)
    organizers = db.Column(db.Text, nullable=True)

    # Article requirements
    min_byte_count = db.Column(db.Integer, nullable=False)
    min_reference_count = db.Column(db.Integer, nullable=False, default=0)
    categories = db.Column(db.Text, nullable=False, default="[]")
    template_link = db.Column(db.Text, nullable=True)

    # Scoring configuration
    scoring_parameters = db.Column(db.Text, nullable=True)
    allowed_submission_type = db.Column(db.String(20), default="both", nullable=False)
    marks_setting_accepted = db.Column(db.Integer, default=0, nullable=False)
    marks_setting_rejected = db.Column(db.Integer, default=0, nullable=False)

    # Request status and review information
    status = db.Column(db.String(20), default="pending", nullable=False)  # pending, approved, rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)  # Optional reason for rejection

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # ------------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------------

    # Relationship to user who made the request
    requester = db.relationship("User", foreign_keys=[user_id], backref="contest_requests")

    # Relationship to user who reviewed the request
    reviewer = db.relationship("User", foreign_keys=[reviewed_by], backref="reviewed_contest_requests")

    # ------------------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------------------

    def __init__(self, user_id, name, project_name, **kwargs):
        """
        Initialize a pending contest creation request.
        
        Parameters:
            user_id: ID of the user submitting the request.
            name: Contest name.
            project_name: Name of the associated project.
            **kwargs: Optional contest details and configuration, including dates,
                submission limits, participant lists, categories, rules, scoring
                parameters, and template link.
        """
        self.user_id = user_id
        self.name = name
        self.project_name = project_name
        self.status = "pending"

        # Set optional fields
        self.description = kwargs.get("description")
        self.start_date = kwargs.get("start_date")
        self.end_date = kwargs.get("end_date")
        self.min_byte_count = kwargs.get("min_byte_count", 0)
        self.min_reference_count = kwargs.get("min_reference_count", 0)
        self.allowed_submission_type = kwargs.get("allowed_submission_type", "both")
        self.marks_setting_accepted = kwargs.get("marks_setting_accepted", 0)
        self.marks_setting_rejected = kwargs.get("marks_setting_rejected", 0)
        self.template_link = kwargs.get("template_link")

        # Set complex fields using setter methods
        self.set_rules(kwargs.get("rules", {}))
        self.set_jury_members(kwargs.get("jury_members", []))
        self.set_organizers(kwargs.get("organizers", []))
        self.set_categories(kwargs.get("categories", []))
        self.set_scoring_parameters(kwargs.get("scoring_parameters"))

    # ------------------------------------------------------------------------
    # HELPER METHODS (Inherited from ContestMixin)
    # ------------------------------------------------------------------------

    # Note: All helper methods (set_rules, get_rules, set_jury_members,
    # get_jury_members, set_organizers, get_organizers, set_categories,
    # get_categories, set_scoring_parameters, get_scoring_parameters) are
    # inherited from ContestMixin to avoid code duplication

    # ------------------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------------------

    def to_dict(self):
        """
        Serialize the contest request and its review metadata for API responses.
        
        Returns:
            dict: Contest request data with date values in ISO 8601 format and the requester's username when available.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "project_name": self.project_name,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "rules": self.get_rules(),
            "jury_members": self.get_jury_members(),
            "organizers": self.get_organizers(),
            "min_byte_count": self.min_byte_count,
            "min_reference_count": self.min_reference_count,
            "categories": self.get_categories(),
            "template_link": self.template_link,
            "scoring_parameters": self.get_scoring_parameters(),
            "allowed_submission_type": self.allowed_submission_type,
            "marks_setting_accepted": self.marks_setting_accepted,
            "marks_setting_rejected": self.marks_setting_rejected,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # Include requester username if relationship is loaded
            "requester_username": self.requester.username if self.requester else None,
        }

    def __repr__(self):
        """Return a concise string representation identifying the contest request, its name, and submitting user."""
        return f"<ContestRequest {self.id}: {self.name} by user {self.user_id}>"
