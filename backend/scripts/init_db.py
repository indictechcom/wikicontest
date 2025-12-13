#!/usr/bin/env python3
"""
Database initialization script for WikiContest Flask Application
"""

import os
import sys
from datetime import datetime, date, timedelta

# Add the parent directory (backend) to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app import app, db
from app.models.user import User
from app.models.contest import Contest
from app.models.submission import Submission

def create_tables():
    """
    Create all database tables
    """
    print("Creating database tables...")
    
    with app.app_context():
        try:
            db.create_all()
            print("[OK] Database tables created successfully!")
        except Exception as e:
            print(f"[ERROR] Error creating tables: {e}")
            return False
    
    return True

# Note: Sample/demo data seeding has been removed to keep this script
# production-friendly. Developers can add their own seed scripts separately
# if needed.

def reset_database():
    """
    Drop all tables and recreate them
    """
    print("Resetting database...")
    
    with app.app_context():
        try:
            db.drop_all()
            print("[OK] Dropped all tables")
            db.create_all()
            print("[OK] Recreated all tables")
        except Exception as e:
            print(f"[ERROR] Error resetting database: {e}")
            return False
    
    return True

def main():
    """
    Main function to initialize database
    """
    print("WikiContest Database Initialization")
    print("=" * 40)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'reset':
            if reset_database():
                print("[OK] Database reset completed!")
            else:
                print("[ERROR] Database reset failed!")
                sys.exit(1)
        elif command == 'seed':
            if create_tables() and seed_sample_data():
                print("[OK] Database initialization with sample data completed!")
            else:
                print("[ERROR] Database initialization failed!")
                sys.exit(1)
        else:
            print(f"Unknown command: {command}")
            print("Available commands: reset")
            sys.exit(1)
    else:
        # Default: just create tables
        if create_tables():
            print("[OK] Database initialization completed!")
        else:
            print("[ERROR] Database initialization failed!")
            sys.exit(1)

if __name__ == '__main__':
    main()