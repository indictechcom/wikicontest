"""
Database configuration for WikiContest Application
Separate module to avoid circular imports
"""

from flask_sqlalchemy import SQLAlchemy

# Create SQLAlchemy instance
db = SQLAlchemy()
