"""
Access control utilities for WikiContest Application.

Provides shared permission checking functions used by multiple route handlers.
"""

from __future__ import annotations

from typing import Tuple, Optional

from flask import jsonify
from app.database import db
from app.models.contest import Contest

__all__ = ["validate_contest_submission_access"]


def validate_contest_submission_access(contest_id, user, Contest) -> tuple:
    contest = db.session.get(Contest, contest_id)

    if not contest:
        return None, (jsonify({"error": "Contest not found"}), 404)

    if hasattr(user, "is_admin") and callable(getattr(user, "is_admin")):
        if user.is_admin():
            return contest, None

    if getattr(user, "username", None) == getattr(contest, "created_by", None):
        return contest, None

    try:
        from app.models.user import User
    except Exception:
        User = None

    if User is not None and hasattr(user, "is_jury_member"):
        try:
            if user.is_jury_member(contest):
                return contest, None
        except Exception:
            pass

    jury_members_raw = getattr(contest, "jury_members", "") or ""
    jury_usernames = [u.strip() for u in jury_members_raw.split(",") if u.strip()]
    if getattr(user, "username", None) in jury_usernames:
        return contest, None

    return None, (jsonify({"error": "Permission denied"}), 403)