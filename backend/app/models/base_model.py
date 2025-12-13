"""
Base Model for WikiContest Application
Contains common database operations shared by all models
"""

from app.database import db

class BaseModel(db.Model):
    """
    Base model class with common database operations

    All models should inherit from this class to get
    save() and delete() methods without code duplication
    """

    # Make this an abstract base class
    __abstract__ = True

    def save(self):
        """
        Save model instance to database
        Adds instance to session and commits changes
        """
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """
        Delete model instance from database
        Removes instance from session and commits changes
        """
        db.session.delete(self)
        db.session.commit()
