#!/usr/bin/env python3
"""
Main entry point for running the WikiContest Flask application.

This script initializes the database and starts the Flask development server.
For production, use a WSGI server like gunicorn or uwsgi.

Usage:
    python main.py
"""

# Third-party imports should come before local imports
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError, OperationalError

# Local application imports
from app import app, db

def migrate_database():
    """
    Run database migrations to add new columns if they don't exist.
    This ensures the database schema matches the current model definitions.
    """
    try:
        # Get table inspector to check existing columns
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('submissions')]

        # Check which columns need to be added
        columns_to_add = []
        if 'article_author' not in columns:
            columns_to_add.append(('article_author', 'VARCHAR(200) NULL'))
        if 'article_created_at' not in columns:
            columns_to_add.append(('article_created_at', 'VARCHAR(50) NULL'))
        if 'article_word_count' not in columns:
            columns_to_add.append(('article_word_count', 'INT NULL'))
        if 'article_page_id' not in columns:
            columns_to_add.append(('article_page_id', 'VARCHAR(50) NULL'))

        # Add missing columns
        if columns_to_add:
            print("📦 Running database migration: Adding article metadata columns...")
            for col_name, col_type in columns_to_add:
                try:
                    db.session.execute(
                        text(f"ALTER TABLE submissions ADD COLUMN {col_name} {col_type}")
                    )
                    print(f"  ✓ Added column: {col_name}")
                except (ProgrammingError, OperationalError) as error:
                    # Column might already exist or there's a SQL/database error
                    print(f"  ⚠ Could not add column {col_name}: {error}")

            db.session.commit()
            print("✓ Database migration completed")
        else:
            print("✓ Database schema is up to date")

    except (OperationalError, SQLAlchemyError) as error:
        # If table doesn't exist yet, db.create_all() will handle it
        # Or if there's a database connection/query error
        print(f"⚠ Migration check skipped (table may not exist yet): {error}")
        db.session.rollback()

if __name__ == '__main__':
    # Main application entry point.
    # This section runs when the script is executed directly (not imported).
    # It initializes the database tables and starts the Flask development server.

    # Initialize database tables
    # This creates all tables defined in the models if they don't exist
    with app.app_context():
        db.create_all()
        print("✓ Database tables initialized successfully")

        # Run migrations to add new columns to existing tables
        migrate_database()

    # Start the Flask development server
    # Debug mode is enabled for development (disable in production)
    print("🚀 Starting WikiContest API server...")
    print("📡 Server will be available at: http://localhost:5000")
    print("🔧 Debug mode: ENABLED")

    app.run(
        debug=True,        # Enable debug mode for development
        host='0.0.0.0',    # Allow connections from any IP
        port=5000          # Default Flask development port
    )

