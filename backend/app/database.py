"""
Database configuration for WikiEval Application
Separate module to avoid circular imports
"""

from flask_sqlalchemy import SQLAlchemy

# Create SQLAlchemy instance
db = SQLAlchemy()
