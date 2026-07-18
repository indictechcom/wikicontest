"""
Configuration Management for WikiContest Application

This module provides centralized configuration management for different
environments (development, testing, production). It uses environment variables
and provides sensible defaults for all configuration options.

Usage:
    from config import Config, DevelopmentConfig, ProductionConfig

    # Use appropriate config class based on environment
    config = DevelopmentConfig() if DEBUG else ProductionConfig()
"""

import os
from datetime import timedelta


class Config:
    """
    Base configuration class with common settings.

    This class contains all the default configuration values that are
    shared across all environments. Environment-specific classes can
    override these values as needed.
    """

    # -------------------------------------------------------------------------
    # SECURITY SETTINGS
    # -------------------------------------------------------------------------

    # Secret keys for session management and JWT signing
    # WARNING: These defaults should NEVER be used in production
    SECRET_KEY = os.getenv('SECRET_KEY', 'wikicontest-dev-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'wikicontest-jwt-secret-key')

    # JWT token configuration
    # 24-hour token validity provides balance between security and UX
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_COOKIE_SECURE = False  # Set to True in production with HTTPS
    # CSRF protection prevents cross-site request forgery attacks
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_IN_COOKIES = True

    # -------------------------------------------------------------------------
    # DATABASE SETTINGS
    # -------------------------------------------------------------------------

    # Database connection string
    # For development: uses SQLite (no password needed)
    # For production: DATABASE_URL must be set in environment
    # CRITICAL: No default password - use SQLite for development or require DATABASE_URL
    database_url = os.getenv('DATABASE_URL')

    # Detect Toolforge ToolsDB environment
    toolforge_db_user = os.getenv('TOOL_TOOLSDB_USER')
    toolforge_db_password = os.getenv('TOOL_TOOLSDB_PASSWORD')
    toolforge_db_name = os.getenv('TOOL_TOOLSDB_DBNAME', 'wikicontest')

    # Auto-configure for Toolforge if environment variables are present
    if toolforge_db_user and toolforge_db_password and not database_url:
        # Construct ToolsDB connection string
        # Format: mysql+pymysql://sXXXXX:password@tools.db.svc.wikimedia.cloud:3306/sXXXXX__dbname
        tool_db_name = f"{toolforge_db_user}__{toolforge_db_name}"
        database_url = f"mysql+pymysql://{toolforge_db_user}:{toolforge_db_password}@tools.db.svc.wikimedia.cloud:3306/{tool_db_name}"
        print(f"Detected Toolforge environment. Using ToolsDB: {tool_db_name}")

    if not database_url:
        # Development fallback: use SQLite (no password, easier setup)
        database_url = 'sqlite:///wikicontest_dev.db'
        print("WARNING: DATABASE_URL not set. Using SQLite for development.")
        print("Set DATABASE_URL in environment for production!")
    SQLALCHEMY_DATABASE_URI = database_url

    # SQLAlchemy settings
    # Disable modification tracking to reduce memory overhead
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before use
        'pool_recycle': 300,    # Recycle connections every 5 minutes
    }

    # -------------------------------------------------------------------------
    # CORS SETTINGS
    # -------------------------------------------------------------------------

    # Allowed origins for CORS
    # Supports common local development setups
    CORS_ORIGINS = [
        'http://localhost:3000',  # React development server
        'http://localhost:5173',  # Vite development server
        'http://localhost:5000'   # Flask development server
    ]

    # Enable credentials (cookies, authorization headers) in CORS requests
    CORS_SUPPORTS_CREDENTIALS = True

    # -------------------------------------------------------------------------
    # APPLICATION SETTINGS
    # -------------------------------------------------------------------------

    # Application metadata
    APP_NAME = 'WikiContest'
    APP_VERSION = '1.0.0'
    APP_DESCRIPTION = 'A platform for hosting and participating in collaborative online competitions'

    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'

    # Logging settings
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/app.log'

    # -------------------------------------------------------------------------
    # OAUTH CONFIGURATION (Wikimedia OAuth 1.0a)
    # -------------------------------------------------------------------------

    # OAuth base URI for Wikimedia
    # Points to Meta-Wiki for centralized authentication across Wikimedia projects
    OAUTH_MWURI = os.getenv('OAUTH_MWURI', 'https://meta.wikimedia.org/w/index.php')

    # OAuth consumer credentials
    # These should be obtained from: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
    # Empty defaults ensure explicit configuration is required
    CONSUMER_KEY = os.getenv('CONSUMER_KEY', '')
    CONSUMER_SECRET = os.getenv('CONSUMER_SECRET', '')

class DevelopmentConfig(Config):
    """
    Development environment configuration.

    This configuration is optimized for development with debug features
    enabled and more verbose logging.
    """

    # Enable debug mode
    # Provides detailed error pages and auto-reloading
    DEBUG = True

    # More verbose logging for development
    # Helps diagnose issues during active development
    LOG_LEVEL = 'DEBUG'

    # Allow all origins in development
    # Simplifies local testing with various tools and ports
    CORS_ORIGINS = ['*']

    # Database URI is inherited from Config, handling Toolforge detection natively


class TestingConfig(Config):
    """
    Testing environment configuration.

    This configuration is optimized for running tests with a separate
    test database and minimal external dependencies.
    """

    # Testing settings
    TESTING = True
    DEBUG = False

    # Use in-memory SQLite database for tests
    # Provides fast, isolated test environment that resets between test runs
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Disable CSRF protection for easier testing
    # Simplifies test setup without compromising production security
    JWT_COOKIE_CSRF_PROTECT = False

    # Minimal CORS for testing
    # Only allow necessary test client connections
    CORS_ORIGINS = ['http://localhost:3000']


class ProductionConfig(Config):
    """
    Production environment configuration.

    This configuration is optimized for production deployment with
    security features enabled and performance optimizations.
    """

    # Production settings
    # Disable debug mode to prevent information leakage
    DEBUG = False
    TESTING = False

    # Enhanced security for production
    JWT_COOKIE_SECURE = True  # Require HTTPS
    JWT_COOKIE_CSRF_PROTECT = True

    # Production database URI is inherited from Config

    # Production CORS origins (should be set via environment variable)
    # Parse comma-separated list from environment for flexibility
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []

    # Production logging
    # Reduce log verbosity to focus on actionable issues
    LOG_LEVEL = 'WARNING'

    # Performance optimizations
    # Larger connection pool handles higher concurrent load
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 20,
        'max_overflow': 30,
    }


# Configuration mapping for easy access
# Provides dictionary-based lookup for configuration classes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(environment=None):
    """
    Get configuration class for the specified environment.

    Args:
        environment (str): Environment name ('development', 'testing', 'production')

    Returns:
        Config: Configuration class instance
    """
    # Auto-detect environment from FLASK_ENV if not explicitly provided
    if environment is None:
        environment = os.getenv('FLASK_ENV', 'default')

    # Return requested config or fall back to default (development)
    return config.get(environment, config['default'])
