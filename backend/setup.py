#!/usr/bin/env python3
"""
Setup script for WikiEval Flask Application
Automates the setup process for development and production environments
"""

# -------------------------------------------------------------------------
# IMPORTS
# -------------------------------------------------------------------------

import os
import sys
import subprocess
import shutil
from pathlib import Path

# -------------------------------------------------------------------------
# UTILITY FUNCTIONS
# -------------------------------------------------------------------------

def run_command(command, description):
    """
    Run a command and handle errors
    
    Args:
        command: Command to run
        description: Description of what the command does
    """
    print(f" {description}...")
    try:
        # Capture output for error reporting without cluttering console
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f" {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        # Display stderr to help diagnose installation issues
        print(f" {description} failed: {e.stderr}")
        return False

# -------------------------------------------------------------------------
# PREREQUISITE CHECKS
# -------------------------------------------------------------------------

def check_python_version():
    """
    Check if Python version is compatible
    
    Returns:
        bool: True if Python version is compatible
    """
    print(" Checking Python version...")
    version = sys.version_info
    # Python 3.8+ required for modern syntax and library compatibility
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f" Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    
    print(f" Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

# -------------------------------------------------------------------------
# VIRTUAL ENVIRONMENT SETUP
# -------------------------------------------------------------------------

def create_virtual_environment():
    """
    Create Python virtual environment
    
    Returns:
        bool: True if virtual environment created successfully
    """
    venv_path = Path("venv")
    
    # Skip creation if virtual environment already exists
    if venv_path.exists():
        print(" Virtual environment already exists")
        return True
    
    return run_command("python -m venv venv", "Creating virtual environment")

def activate_virtual_environment():
    """
    Provide instructions for activating virtual environment
    """
    print("\n To activate the virtual environment:")
    # Platform-specific activation instructions
    if os.name == 'nt':  # Windows
        print("   venv\\Scripts\\activate")
    else:  # Unix/Linux/macOS
        print("   source venv/bin/activate")

# -------------------------------------------------------------------------
# DEPENDENCY INSTALLATION
# -------------------------------------------------------------------------

def install_dependencies():
    """
    Install Python dependencies
    
    Returns:
        bool: True if dependencies installed successfully
    """
    requirements_file = Path("requirements.txt")
    
    # Verify requirements file exists before attempting installation
    if not requirements_file.exists():
        print(" requirements.txt not found")
        return False
    
    return run_command("pip install -r requirements.txt", "Installing dependencies")

# -------------------------------------------------------------------------
# ENVIRONMENT CONFIGURATION
# -------------------------------------------------------------------------

def setup_environment_file():
    """
    Setup environment configuration file
    
    Returns:
        bool: True if environment file setup successfully
    """
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    # Avoid overwriting existing configuration
    if env_file.exists():
        print(" .env file already exists")
        return True
    
    if not env_example.exists():
        print(" .env.example not found")
        return False
    
    try:
        # Copy template to create initial environment configuration
        shutil.copy(env_example, env_file)
        print(" Created .env file from .env.example")
        print(" Please update .env file with your database credentials")
        return True
    except Exception as e:
        print(f" Failed to create .env file: {e}")
        return False

# -------------------------------------------------------------------------
# DATABASE INITIALIZATION
# -------------------------------------------------------------------------

def initialize_database():
    """
    Initialize database with tables and sample data
    
    Returns:
        bool: True if database initialized successfully
    """
    print(" Initializing database...")
    
    # Check if init_db.py exists
    init_script = Path("init_db.py")
    if not init_script.exists():
        print(" init_db.py not found")
        return False
    
    # Run database initialization
    # Seed data helps with development and testing
    if run_command("python init_db.py seed", "Initializing database with sample data"):
        print(" Database initialized successfully")
        return True
    else:
        # Non-fatal error - can be done manually later
        print(" Database initialization failed, but you can run it manually later")
        return True

# -------------------------------------------------------------------------
# DIRECTORY STRUCTURE
# -------------------------------------------------------------------------

def create_directories():
    """
    Create necessary directories
    
    Returns:
        bool: True if directories created successfully
    """
    # Required directories for logs and file uploads
    directories = ['logs', 'uploads']
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            try:
                # Create directory with parent directories if needed
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f" Created directory: {directory}")
            except Exception as e:
                print(f" Failed to create directory {directory}: {e}")
                return False
        else:
            print(f" Directory already exists: {directory}")
    
    return True

# -------------------------------------------------------------------------
# USER GUIDANCE
# -------------------------------------------------------------------------

def print_next_steps():
    """
    Print next steps for the user
    """
    print("\n" + "="*60)
    print(" Setup completed successfully!")
    print("="*60)
    print("\n Next steps:")
    # Step 1: Activate virtual environment
    print("1. Activate the virtual environment:")
    activate_virtual_environment()
    # Step 2: Configure database credentials
    print("\n2. Update database credentials in .env file")
    # Step 3: Start the application
    print("\n3. Start the Flask application:")
    print("   python app.py")
    # Step 4: Access web interface
    print("\n4. Open your browser and go to:")
    print("   http://localhost:5000")
    # Step 5: Verify API is working
    print("\n5. Test the API endpoints:")
    print("   http://localhost:5000/api/health")
    # Additional resources
    print("\n For more information, see README.md")
    # Troubleshooting tips
    print("\n If you encounter issues:")
    print("   - Check MySQL is running")
    print("   - Verify database credentials in .env")
    print("   - Check logs for error messages")

# -------------------------------------------------------------------------
# MAIN SETUP ORCHESTRATION
# -------------------------------------------------------------------------

def main():
    """
    Main setup function
    """
    print(" WikiEval Flask Application Setup")
    print("="*50)
    
    # Check prerequisites
    # Exit early if Python version is incompatible
    if not check_python_version():
        sys.exit(1)
    
    # Setup steps
    # Executed in order - each step builds on previous ones
    steps = [
        ("Creating virtual environment", create_virtual_environment),
        ("Installing dependencies", install_dependencies),
        ("Setting up environment file", setup_environment_file),
        ("Creating directories", create_directories),
        ("Initializing database", initialize_database),
    ]
    
    # Track which steps failed for final report
    failed_steps = []
    
    for description, step_function in steps:
        if not step_function():
            failed_steps.append(description)
    
    # Final status report
    if failed_steps:
        print(f"\n Setup completed with {len(failed_steps)} failed steps:")
        for step in failed_steps:
            print(f"   - {step}")
        print("\nPlease check the errors above and run the setup again.")
        sys.exit(1)
    else:
        # Success - show user what to do next
        print_next_steps()

# -------------------------------------------------------------------------
# SCRIPT ENTRY POINT
# -------------------------------------------------------------------------

if __name__ == '__main__':
    main()