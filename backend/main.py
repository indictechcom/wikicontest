#!/usr/bin/env python3
"""
Main entry point for running the WikiEval Flask application.

This script starts the Flask API server.

Note: Database migrations are handled separately by Alembic.
"""

# Local application imports
from app import app

if __name__ == '__main__':
    # Main application entry point.
    # This section runs when the script is executed directly (not imported).

    # Start the Flask server
    # Debug mode is controlled by environment variable (FLASK_DEBUG) for security
    import os
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    print("Starting WikiEval API server...")
    print("Server will be available at: http://localhost:5000")
    if debug_mode:
        print("Debug mode: ENABLED (set FLASK_DEBUG=false to disable)")
    else:
        print("Debug mode: DISABLED (set FLASK_DEBUG=true to enable)")
    app.run(
        debug=debug_mode,  # Controlled by FLASK_DEBUG environment variable
        host='0.0.0.0',    # Allow connections from any IP
        port=5000          # Default Flask development port
    )
