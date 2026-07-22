"""
Trusted Member Request Model for WikiEval Application
Tracks user requests for trusted-member (contest creator) status.
"""

from datetime import datetime, timezone

from app.database import db
from app.models.base_model import BaseModel
import sqlalchemy as sa


class TrustedMemberRequest(BaseModel):
    """
    Request model for users seeking trusted-member status.

    Attributes:
        id: Primary key
        user_id: FK to users.id — the requester
        reason: User-provided justification
        status: pending / approved / rejected
        reviewed_by: FK to users.id — the superadmin who handled the request
        reviewed_at: When the request was handled
        created_at: When the request was submitted
        updated_at: When the request was last updated
    """

    __tablename__ = "trusted_member_requests"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=True)

    status = db.Column(
        sa.Enum('pending', 'approved', 'rejected',
                name='trusted_member_request_status_enum'),
        nullable=False,
        default='pending',
    )

    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    requester = db.relationship("User", foreign_keys=[user_id], backref="trusted_member_requests")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self):
        return (
            f"<TrustedMemberRequest {self.id}: user={self.user_id} "
            f"status={self.status}>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.requester.username if self.requester else None,
            "reason": self.reason,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewer_username": self.reviewer.username if self.reviewer else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
