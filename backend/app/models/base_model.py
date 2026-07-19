"""
Base Model for WikiEval Application
Contains common database operations shared by all models
"""

from app.database import db


# ------------------------------------------------------------------------====
# ABSTRACT BASE MODEL
# ------------------------------------------------------------------------====

class BaseModel(db.Model):
    """
    Base model class with common database operations

    All models should inherit from this class to get
    save() and delete() methods without code duplication
    """

    # Mark as abstract - SQLAlchemy won't create a table for this class
    # Only child classes will have their own tables
    __abstract__ = True


    # ------------------------------------------------------------------------
    # Database Persistence Methods
    # ------------------------------------------------------------------------

    def save(self):
        """
        Save model instance to database
        Adds instance to session and commits changes
        """
        # Add instance to current session (marks as pending)
        db.session.add(self)

        # Commit transaction to persist changes to database
        db.session.commit()


    def delete(self):
        """
        Delete model instance from database
        Removes instance from session and commits changes
        """
        # Mark instance for deletion in current session
        db.session.delete(self)

        # Commit transaction to execute deletion
        db.session.commit()
