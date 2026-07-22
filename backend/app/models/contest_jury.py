"""
Contest Jury Junction Model for WikiEval Application
Links contests to jury members via a many-to-many relationship.
"""

from datetime import datetime, timezone

from app.database import db
from app.models.base_model import BaseModel


class ContestJury(BaseModel):
    """
    Junction model linking contests to jury members.

    Attributes:
        contest_id: FK to contests.id (part of composite PK)
        user_id: FK to users.id (part of composite PK)
        created_at: When this jury membership was created
    """

    __tablename__ = "contest_jury"

    contest_id = db.Column(
        db.Integer, db.ForeignKey("contests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"),
        primary_key=True,
    )
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self):
        return f"<ContestJury contest={self.contest_id} user={self.user_id}>"
