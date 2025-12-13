#!/usr/bin/env python3
"""
Helper script for running Alembic migrations.

This script provides a convenient way to run Alembic commands with the Flask
application context properly configured.

Usage:
    python scripts/migrate.py <command> [args...]

Examples:
    python scripts/migrate.py current
    python scripts/migrate.py upgrade head
    python scripts/migrate.py revision --autogenerate -m "Add new column"
    python scripts/migrate.py downgrade -1
"""

import sys
import os
import subprocess

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

def main():
    """
    Run Alembic command with proper environment setup.
    """
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate.py <alembic_command> [args...]")
        print("\nCommon commands:")
        print("  current              - Show current revision")
        print("  history              - Show migration history")
        print("  upgrade head         - Apply all pending migrations")
        print("  downgrade -1         - Rollback one revision")
        print("  revision --autogenerate -m 'message' - Create new migration")
        print("\nFor more information, see: alembic/README.md")
        sys.exit(1)
    
    # Get the alembic command and arguments
    alembic_args = sys.argv[1:]
    
    # Change to backend directory to ensure alembic.ini is found
    os.chdir(backend_dir)
    
    # Run alembic command
    try:
        result = subprocess.run(['alembic'] + alembic_args, check=False)
        sys.exit(result.returncode)
    except FileNotFoundError:
        print("Error: Alembic not found. Make sure:")
        print("  1. Virtual environment is activated")
        print("  2. Dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error running Alembic: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

