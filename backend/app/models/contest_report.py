"""
Contest Report Model for WikiContest Application
Stores generated contest reports and their metadata
FIXED: Proper inheritance from BaseModel for created_at/updated_at
"""

from datetime import datetime
from app.database import db
from app.models.base_model import BaseModel


class ContestReport(BaseModel):
    """
    Contest Report model representing generated reports for contests

    Attributes:
        id: Primary key, auto-incrementing integer
        contest_id: Foreign key to contests table
        report_type: Type of report ('csv' or 'pdf')
        status: Generation status ('pending', 'processing', 'completed', 'failed')
        file_path: Path to generated report file
        generated_by: Foreign key to users table (who requested the report)
        error_message: Error message if generation failed
        report_metadata: JSON containing report parameters (top_n, filters, etc.)
        created_at: Timestamp when report generation was requested (from BaseModel)
        updated_at: Timestamp when report status was last updated (from BaseModel)
    """

    __tablename__ = "contest_reports"

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    contest_id = db.Column(db.Integer, db.ForeignKey("contests.id"), nullable=False)
    generated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Report configuration
    report_type = db.Column(db.String(20), nullable=False)  # 'csv' or 'pdf'
    status = db.Column(db.String(20), default='pending', nullable=False)

    # File storage
    file_path = db.Column(db.String(500), nullable=True)

    # Error handling
    error_message = db.Column(db.Text, nullable=True)

    # Report parameters (stored as JSON string)
    report_metadata = db.Column(db.Text, nullable=True)

    # Relationships
    contest = db.relationship("Contest", backref="reports")
    generator = db.relationship("User", backref="generated_reports")

    def __init__(self, contest_id, report_type, generated_by, report_metadata=None):
        """
        Initialize a new ContestReport instance

        IMPORTANT: Don't manually set created_at/updated_at
        They are automatically handled by BaseModel

        Args:
            contest_id: ID of the contest
            report_type: Type of report ('csv' or 'pdf')
            generated_by: ID of user requesting the report
            report_metadata: Optional dict of report parameters
        """
        # Call parent __init__ to set created_at/updated_at
        super().__init__()

        self.contest_id = contest_id
        self.report_type = report_type
        self.generated_by = generated_by
        self.status = 'pending'

        # Store report_metadata as JSON string
        if report_metadata:
            import json
            self.report_metadata = json.dumps(report_metadata)
        else:
            self.report_metadata = None

    def get_metadata(self):
        """
        Get report metadata as dictionary

        Returns:
            dict or None: Report parameters
        """
        if not self.report_metadata:
            return None
        try:
            import json
            return json.loads(self.report_metadata)
        except Exception:
            return None

    def is_completed(self):
        """Check if report generation is completed"""
        return self.status == 'completed'

    def is_failed(self):
        """Check if report generation failed"""
        return self.status == 'failed'

    def is_processing(self):
        """Check if report is currently being generated"""
        return self.status == 'processing'

    def to_dict(self):
        """
        Convert report instance to dictionary for JSON serialization

        NOTE: created_at and updated_at come from BaseModel

        Returns:
            dict: Report data
        """
        return {
            'id': self.id,
            'contest_id': self.contest_id,
            'report_type': self.report_type,
            'status': self.status,
            'file_path': self.file_path if self.is_completed() else None,
            'error_message': self.error_message if self.is_failed() else None,
            'report_metadata': self.get_metadata(),
            'generated_by': self.generated_by,
            #  These come from BaseModel - should work now
            'created_at': self.created_at.isoformat() if hasattr(self, 'created_at') and self.created_at else None,
            'updated_at': self.updated_at.isoformat() if hasattr(self, 'updated_at') and self.updated_at else None,
        }

    def __repr__(self):
        """String representation of ContestReport instance"""
        return f"<ContestReport {self.id}: {self.report_type} for Contest {self.contest_id}>"