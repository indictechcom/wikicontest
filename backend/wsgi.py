"""
WSGI entry point for WikiEval Flask application.

This module provides the WSGI interface for production deployment
with gunicorn on Toolforge Build Service.
"""

import os
import sys

# Get the workspace root (parent of backend directory)
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add workspace root to Python path for imports
sys.path.insert(0, workspace_root)

# Import the Flask application
from app import app as application

if __name__ == '__main__':
    application.run()
