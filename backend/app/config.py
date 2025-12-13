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
    
    # =========================================================================
    # SECURITY SETTINGS
    # =========================================================================
    
    # Secret keys for session management and JWT signing
    SECRET_KEY = os.getenv('SECRET_KEY', 'wikicontest-dev-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'wikicontest-jwt-secret-key')
    
    # JWT token configuration
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_COOKIE_SECURE = False  # Set to True in production with HTTPS
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_IN_COOKIES = True
    
    # =========================================================================
    # DATABASE SETTINGS
    # =========================================================================
    
    # Database connection string
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 
        'mysql+pymysql://root:password@localhost/wikicontest'
    )
    
    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before use
        'pool_recycle': 300,    # Recycle connections every 5 minutes
    }
    
    # =========================================================================
    # CORS SETTINGS
    # =========================================================================
    
    # Allowed origins for CORS
    CORS_ORIGINS = [
        'http://localhost:3000',  # React development server
        'http://localhost:5173',  # Vite development server
        'http://localhost:5000'   # Flask development server
    ]
    
    CORS_SUPPORTS_CREDENTIALS = True
    
    # =========================================================================
    # APPLICATION SETTINGS
    # =========================================================================
    
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
    
    # =========================================================================
    # OAUTH CONFIGURATION (Wikimedia OAuth 1.0a)
    # =========================================================================
    
    # OAuth base URI for Wikimedia
    OAUTH_MWURI = os.getenv('OAUTH_MWURI', 'https://meta.wikimedia.org/w/index.php')
    
    # OAuth consumer credentials
    # These should be obtained from: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
    CONSUMER_KEY = os.getenv('CONSUMER_KEY', '')
    CONSUMER_SECRET = os.getenv('CONSUMER_SECRET', '')


class DevelopmentConfig(Config):
    """
    Development environment configuration.
    
    This configuration is optimized for development with debug features
    enabled and more verbose logging.
    """
    
    # Enable debug mode
    DEBUG = True
    
    # More verbose logging for development
    LOG_LEVEL = 'DEBUG'
    
    # Allow all origins in development
    CORS_ORIGINS = ['*']
    
    # Development database (can be SQLite for easier setup)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 
        'sqlite:///wikicontest_dev.db'
    )


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
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF protection for easier testing
    JWT_COOKIE_CSRF_PROTECT = False
    
    # Minimal CORS for testing
    CORS_ORIGINS = ['http://localhost:3000']


class ProductionConfig(Config):
    """
    Production environment configuration.
    
    This configuration is optimized for production deployment with
    security features enabled and performance optimizations.
    """
    
    # Production settings
    DEBUG = False
    TESTING = False
    
    # Enhanced security for production
    JWT_COOKIE_SECURE = True  # Require HTTPS
    JWT_COOKIE_CSRF_PROTECT = True
    
    # Production database (should be set via environment variable)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    
    # Production CORS origins (should be set via environment variable)
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []
    
    # Production logging
    LOG_LEVEL = 'WARNING'
    
    # Performance optimizations
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 20,
        'max_overflow': 30,
    }


# Configuration mapping for easy access
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
    if environment is None:
        environment = os.getenv('FLASK_ENV', 'default')
    
    return config.get(environment, config['default'])
