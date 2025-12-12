#!/usr/bin/env python3
"""
Migration script: Add allowed_submission_type column to contests table

This script adds the following column to the contests table:
- allowed_submission_type: Type of submissions allowed ('both', 'new', 'improved')
  Default value is 'both'

Usage:
    python migrations/add_allowed_submission_type_to_contests.py
"""

import os
import sys

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app import app, db
from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError, OperationalError

def run_migration():
    """
    Run the migration to add allowed_submission_type column
    """
    print("=" * 60)
    print("Migration: Add allowed_submission_type to Contests Table")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Use inspector to check if column exists (more reliable method)
            inspector = inspect(db.engine)
            try:
                contest_columns = [col['name'] for col in inspector.get_columns('contests')]
                
                if 'allowed_submission_type' in contest_columns:
                    print("[INFO] Column 'allowed_submission_type' already exists")
                    print("[SKIP] Migration not needed. Column already exists.")
                    return True
            except Exception as e:
                print(f"[WARNING] Could not check existing columns: {e}")
                # Try alternative method: query the column directly
                try:
                    db.session.execute(text("SELECT allowed_submission_type FROM contests LIMIT 1"))
                    print("[INFO] Column 'allowed_submission_type' already exists")
                    print("[SKIP] Migration not needed. Column already exists.")
                    return True
                except Exception:
                    # Column doesn't exist, proceed with migration
                    pass
            
            print("[STEP 1] Adding allowed_submission_type column...")
            try:
                # Add the column with default value 'both'
                # VARCHAR(20) to match the model definition
                # NOT NULL with default value to ensure existing rows get a value
                db.session.execute(text("""
                    ALTER TABLE contests 
                    ADD COLUMN allowed_submission_type VARCHAR(20) NOT NULL DEFAULT 'both'
                """))
                print("  [OK] allowed_submission_type column added successfully")
                
                # Commit the change
                db.session.commit()
                print("\n[SUCCESS] Migration completed successfully!")
                print("The allowed_submission_type column has been added to the contests table.")
                print("All existing contests have been set to 'both' (default value).")
                return True
                
            except Exception as e:
                print(f"\n[ERROR] Migration failed: {e}")
                db.session.rollback()
                return False
            
        except Exception as e:
            print(f"\n[ERROR] Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)

