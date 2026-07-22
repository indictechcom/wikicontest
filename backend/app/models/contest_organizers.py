"""
Contest Organizers Junction Model for WikiEval Application
Links contests to organizers via a many-to-many relationship.
"""

from datetime import datetime, timezone

from app.database import db
from app.models.base_model import BaseModel


class ContestOrganizer(BaseModel):
    """
    Junction model linking contests to organizers.

    Attributes:
        contest_id: FK to contests.id (part of composite PK)
        user_id: FK to users.id (part of composite PK)
        created_at: When this organizer membership was created
    """

    __tablename__ = "contest_organizers"

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
        return f"<ContestOrganizer contest={self.contest_id} user={self.user_id}>"
