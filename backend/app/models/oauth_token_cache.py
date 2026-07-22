"""
OAuth Token Cache Model for WikiEval Application

Provides database-backed temporary storage for OAuth request tokens.
This replaces the in-memory dict that failed across multiple Gunicorn workers
(each worker has its own memory space, so tokens cached in one worker are
invisible to others).

The table is auto-created at startup via db.create_all() — no Alembic migration needed.
Entries are cleaned up on read and should not live longer than ~10 minutes.
"""

from datetime import datetime, timezone

from app.database import db
from app.models.base_model import BaseModel


class OAuthTokenCache(BaseModel):
    """
    Temporary cache for OAuth 1.0a request tokens.

    Stores the request_token_secret so the callback handler can retrieve it
    even when the Flask session cookie is lost during the cross-site redirect
    to/from Wikimedia.

    Attributes:
        token: The OAuth request token key (primary key)
        secret: The OAuth request token secret
        created_at: When this entry was created (for expiry)
    """

    __tablename__ = "oauth_token_cache"

    # The request token key serves as the natural primary key
    token = db.Column(db.String(255), primary_key=True)
    secret = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Maximum age in seconds before an entry is considered stale
    MAX_AGE_SECONDS = 600  # 10 minutes

    @classmethod
    def store(cls, token_key: str, token_secret: str) -> None:
        """
        Store or overwrite an OAuth request token and its secret.
        
        Parameters:
        	token_key (str): The request token key.
        	token_secret (str): The secret associated with the request token.
        """
        entry = db.session.get(cls, token_key)
        if entry:
            entry.secret = token_secret
            entry.created_at = datetime.now(timezone.utc)
        else:
            entry = cls(token=token_key, secret=token_secret)
            db.session.add(entry)
        db.session.commit()

    @classmethod
    def retrieve_and_delete(cls, token_key: str) -> str | None:
        """
        Retrieve the secret for *token_key* and delete the entry.

        Returns the secret string, or None if not found / expired.
        """
        entry = db.session.get(cls, token_key)
        if entry is None:
            return None

        # Check expiry
        age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
        if age > cls.MAX_AGE_SECONDS:
            db.session.delete(entry)
            db.session.commit()
            return None

        secret = entry.secret
        db.session.delete(entry)
        db.session.commit()
        return secret

    @classmethod
    def cleanup_expired(cls) -> int:
        """
        Delete all cache entries older than the maximum permitted age.
        
        Returns:
        	int: The number of deleted entries.
        """
        from sqlalchemy import delete  # noqa: C812 — local import to keep module top clean
        from datetime import timedelta  # noqa: C812

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=cls.MAX_AGE_SECONDS)
        result = db.session.execute(
            delete(cls).where(cls.created_at < cutoff)
        )
        db.session.commit()
        return result.rowcount

    def __repr__(self) -> str:
        """Return a concise string representation containing the first 10 characters of the token."""
        return f"<OAuthTokenCache {self.token[:10]}...>"
