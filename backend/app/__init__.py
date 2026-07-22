"""
WikiEval Flask Application
Main application entry point for the Python Flask backend

This module initializes the Flask application with all necessary configurations,
extensions, and route blueprints. It serves as the central hub for the WikiEval
platform, handling both API endpoints and static file serving.

Architecture:
- Modular design with separate blueprints for different features
- JWT-based authentication with cookie storage
- CORS enabled for frontend communication
- Database integration with SQLAlchemy ORM
- Comprehensive error handling and logging

Author: WikiEval Development Team
Version: 1.0.0
"""
# pylint: disable=too-many-lines

# Standard library imports
import os
from datetime import timedelta
from urllib.parse import urlparse, parse_qs, unquote

# Third-party imports
from flask import Flask, request, jsonify, send_from_directory, current_app
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt_identity, jwt_required
from flask_jwt_extended.exceptions import JWTDecodeError, NoAuthorizationError
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text as sql_text

# Local imports
from app.database import db
from app.extensions import limiter

# Import models to ensure they are registered with SQLAlchemy
# This is required for database migrations and table creation
from app.models.user import User  # pylint: disable=unused-import
from app.models.contest import Contest  # pylint: disable=unused-import
from app.models.submission import Submission  # pylint: disable=unused-import
from app.models.oauth_token_cache import OAuthTokenCache  # pylint: disable=unused-import
from app.routes.auth_routes import auth_bp  # pylint: disable=unused-import
from app.routes.oauth_routes import oauth_bp  # pylint: disable=unused-import
from app.routes.profile_routes import profile_bp  # pylint: disable=unused-import
from app.routes.trusted_member_routes import trusted_bp  # pylint: disable=unused-import
from app.routes.contest_crud_routes import contest_crud_bp  # pylint: disable=unused-import
from app.routes.contest_submission_routes import contest_sub_bp  # pylint: disable=unused-import
from app.routes.contest_organizer_routes import contest_org_bp  # pylint: disable=unused-import
from app.routes.contest_request_routes import contest_req_bp  # pylint: disable=unused-import
from app.routes.contest_outreach_routes import contest_outreach_bp  # pylint: disable=unused-import
from app.routes.contest_crawl_routes import contest_crawl_bp  # pylint: disable=unused-import
from app.routes.submission_routes import submission_bp  # pylint: disable=unused-import
from app.routes.system_routes import system_bp  # pylint: disable=unused-import
from app.routes.mediawiki_proxy_routes import mediawiki_proxy_bp  # pylint: disable=unused-import
from app.utils import (
    extract_page_title_from_url,
    build_mediawiki_revisions_api_params,
    get_latest_revision_author,
    get_article_reference_count,
)
from app.services.mediawiki import MediaWikiClient
from app.utils.errors import safe_error_response
from app.utils.url_validation import validate_wiki_url

# ---------------------------------------------------------------------------
# CONFIGURATION SETUP
# ---------------------------------------------------------------------------

# Load environment variables from .env file
# This allows for easy configuration management across different environments
load_dotenv()

# Strip trailing whitespace/newlines from all environment variables.
# Toolforge `toolforge envvars create` may inject values with trailing newlines,
# which causes string comparisons like `== 'true'` to silently fail.
for _key in list(os.environ):
    os.environ[_key] = os.environ[_key].strip()

def create_app():
    """
    Create and configure a Flask application instance.
    
    Raises:
        RuntimeError: If required secret keys are missing in production.
    
    Returns:
        Flask: The fully configured application instance.
    """
    # Initialize Flask application
    flask_app = Flask(__name__)

    # Disable strict_slashes to prevent 308 redirects (e.g., /api/contest → /api/contest/).
    # These redirects cause problems when the app is behind a reverse proxy because
    # the Location header points to the backend domain instead of the frontend domain,
    # and following them in the proxy can crash the Node.js process.
    flask_app.url_map.strict_slashes = False

    # Wrap with ProxyFix so Flask reads X-Forwarded-Proto / X-Forwarded-Host
    # from the Node.js frontend proxy. This ensures request.scheme == 'https'
    # and request.host == 'wikieval.toolforge.org', which is critical for:
    #   - Building correct OAuth callback URLs
    #   - Setting session cookies with the right domain (frontend domain, not backend)
    flask_app.wsgi_app = ProxyFix(
        flask_app.wsgi_app,
        x_for=1,    # X-Forwarded-For
        x_proto=1,  # X-Forwarded-Proto  (http → https)
        x_host=1,   # X-Forwarded-Host   (backend host → frontend host)
        x_prefix=1  # X-Forwarded-Prefix
    )

    # ------------------------------------------------------------------------
    # SECURITY CONFIGURATION
    # ------------------------------------------------------------------------

    # Secret keys for session management and JWT signing
    # These should be different in production and stored securely
    # CRITICAL: Require environment variables - no insecure defaults
    secret_key = os.getenv('SECRET_KEY')
    jwt_secret_key = os.getenv('JWT_SECRET_KEY')

    is_production = os.getenv('FLASK_ENV', 'development') == 'production'
    if is_production:
        # In production with multiple Gunicorn workers, every worker MUST share
        # the same secret keys — otherwise session cookies signed by one worker
        # cannot be verified by another, breaking OAuth flows and JWT auth.
        missing = []
        if not secret_key:
            missing.append('SECRET_KEY')
        if not jwt_secret_key:
            missing.append('JWT_SECRET_KEY')
        if missing:
            raise RuntimeError(
                f"Missing required environment variable(s) in production: {', '.join(missing)}. "
                f"Generate with: toolforge envvars create SECRET_KEY \"$(openssl rand -hex 32)\""
            )
    else:
        # Development only: generate temporary secrets if not set (with warning)
        if not secret_key or not jwt_secret_key:
            import secrets
            if not secret_key:
                secret_key = secrets.token_urlsafe(48)
                print("WARNING: SECRET_KEY not set in environment. Generated temporary key.")
                print("   Set SECRET_KEY in environment for production!")
            if not jwt_secret_key:
                jwt_secret_key = secrets.token_urlsafe(48)
                print("WARNING: JWT_SECRET_KEY not set in environment. Generated temporary key.")
                print("   Set JWT_SECRET_KEY in environment for production!")
    flask_app.config['SECRET_KEY'] = secret_key
    flask_app.config['JWT_SECRET_KEY'] = jwt_secret_key

    # --- Session Configuration for OAuth Flow ---
    # Sessions need to persist across redirects to external OAuth providers
    flask_app.config['SESSION_PERMANENT'] = True  # Make sessions persistent
    flask_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 30 min timeout
    flask_app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
    # SameSite=None is required so the session cookie is sent back when Wikimedia
    # redirects the user to our callback URL (a cross-site top-level navigation).
    # IMPORTANT: SameSite=None REQUIRES Secure=True — browsers reject it otherwise.
    flask_app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    # With ProxyFix, request.scheme is now 'https' in production, so Secure=True is safe.
    flask_app.config['SESSION_COOKIE_SECURE'] = is_production
    flask_app.config['SESSION_COOKIE_DOMAIN'] = None  # Let Flask derive from request host
    flask_app.config['SESSION_COOKIE_PATH'] = '/'  # Available for all paths

    # JWT Token Configuration
    # JWT token expiration time (4 hours for security)
    flask_app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=4)

    # JWT Cookie Configuration for secure token storage
    flask_app.config['JWT_TOKEN_LOCATION'] = ['cookies']  # Store tokens in HTTP-only cookies
    # Mirror the session's secure flag — True in production (HTTPS), False for localhost
    flask_app.config['JWT_COOKIE_SECURE'] = is_production
    # Lax allows same-site cookies and top-level cross-site navigations
    flask_app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
    flask_app.config['JWT_COOKIE_DOMAIN'] = None  # Derived from request host via ProxyFix
    flask_app.config['JWT_COOKIE_CSRF_PROTECT'] = is_production  # CSRF only in production (SPA frontend can't read HTTP-only CSRF cookie)
    flask_app.config['JWT_CSRF_IN_COOKIES'] = True  # Include CSRF token in cookies

    # ------------------------------------------------------------------------
    # OAUTH 1.0a CONFIGURATION (Wikimedia OAuth 1.0a)
    # ------------------------------------------------------------------------

    # OAuth 1.0a configuration from environment variables
    # These values are loaded from .env file for Wikimedia OAuth 1.0a authentication
    # The mwoauth library uses these credentials to authenticate users via OAuth 1.0a protocol
    flask_app.config['OAUTH_MWURI'] = os.getenv(
        'OAUTH_MWURI', 'https://meta.wikimedia.org/w/index.php'
    )
    flask_app.config['CONSUMER_KEY'] = os.getenv('CONSUMER_KEY', '')
    flask_app.config['CONSUMER_SECRET'] = os.getenv('CONSUMER_SECRET', '')
    # Set to True if OAuth consumer was registered with "oob" (out-of-band) callback
    # Most web apps should use False and register with a proper callback URL
    flask_app.config['OAUTH_USE_OOB'] = os.getenv('OAUTH_USE_OOB', 'False').strip().lower() == 'true'
    # Frontend URL for post-OAuth redirect (e.g. https://wikieval.toolforge.org)
    flask_app.config['FRONTEND_URL'] = os.getenv('FRONTEND_URL', '')
    # Custom callback path for OAuth (e.g. /oauth/callback for Toolforge)
    # When set, overrides the default blueprint path (/api/user/oauth/callback)
    flask_app.config['OAUTH_CALLBACK_PATH'] = os.getenv('OAUTH_CALLBACK_PATH', None)

    # ------------------------------------------------------------------------
    # DATABASE CONFIGURATION
    # ------------------------------------------------------------------------

    # Database connection string
    # Uses config.py to get auto-detected Toolforge URL
    from app.config import get_config
    config_obj = get_config()
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = config_obj.SQLALCHEMY_DATABASE_URI

    # Disable SQLAlchemy event system for better performance
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ------------------------------------------------------------------------
    # EXTENSION INITIALIZATION
    # ------------------------------------------------------------------------

    # Initialize database with the app
    db.init_app(flask_app)

    # Auto-create the OAuth token cache table if it doesn't exist.
    # This is safe to call on every startup — create_all only creates missing tables.
    # Wrapped in try/except so a DB outage doesn't prevent the app from starting.
    with flask_app.app_context():
        try:
            db.create_all()
        except Exception as db_err:  # pylint: disable=broad-exception-caught
            print(f"WARNING: db.create_all() failed on startup: {db_err}")
            print("The application will start but database operations may fail.")

    # Initialize JWT manager for token handling
    JWTManager(flask_app)

    # Configure CORS for frontend communication
    # Allows requests from frontend development servers and production
    # Get allowed origins from environment or use defaults
    allowed_origins = os.getenv('CORS_ORIGINS', '').split(',')
    if not allowed_origins or allowed_origins == ['']:
        # Development defaults
        allowed_origins = ['http://localhost:5173']

    # Always ensure the frontend domain is allowed (prevents CORS issues
    # when CORS_ORIGINS env var is not explicitly set on the backend tool).
    # Uses FRONTEND_URL which is already configured for OAuth redirects.
    frontend_url = flask_app.config.get('FRONTEND_URL', '').strip()
    if frontend_url and frontend_url not in allowed_origins:
        allowed_origins.append(frontend_url)

    CORS(flask_app, origins=allowed_origins, supports_credentials=True)

    # ---------------------------------------------------------------------------
    # RATE LIMITING
    # ---------------------------------------------------------------------------
    limiter.init_app(flask_app)

    # ---------------------------------------------------------------------------
    # BLUEPRINT REGISTRATION
    # ---------------------------------------------------------------------------
    # All user blueprints share the /api/user prefix (same URL paths as before)
    for bp in [auth_bp, oauth_bp, profile_bp, trusted_bp]:
        flask_app.register_blueprint(bp, url_prefix='/api/user')
    # All contest blueprints share the /api/contest prefix (same URL paths as before)
    for bp in [contest_crud_bp, contest_sub_bp, contest_org_bp, contest_req_bp,
               contest_outreach_bp, contest_crawl_bp]:
        flask_app.register_blueprint(bp, url_prefix='/api/contest')
    flask_app.register_blueprint(submission_bp, url_prefix='/api/submission')
    # System/auth/frontend endpoints and MediaWiki proxy endpoints were previously
    # defined directly on the app; they now live in blueprints with no URL prefix
    # so their endpoint paths and methods are unchanged.
    flask_app.register_blueprint(system_bp)
    flask_app.register_blueprint(mediawiki_proxy_bp)

    return flask_app

# Create the application instance
app = create_app()

# ---------------------------------------------------------------------------
# MODEL REGISTRATION
# ---------------------------------------------------------------------------

# Import models to ensure they are registered with SQLAlchemy
# This is required for database migrations and table creation
# Models are imported at top of file

# ---------------------------------------------------------------------------
# ROUTE BLUEPRINT REGISTRATION
# ---------------------------------------------------------------------------

# Import route blueprints for modular organization
# Each blueprint handles a specific domain of functionality
# Blueprints are imported at top of file

# ---------------------------------------------------------------------------
# ERROR HANDLERS
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(_error):
    """
    Handle 404 Not Found errors.

    This handler catches all requests to non-existent endpoints and
    returns a consistent JSON error response.
    """
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(_error):
    """
    Handle internal server errors with a generic JSON response.
    
    Returns:
        tuple: A JSON error response and HTTP status code 500.
    """
    db.session.rollback()
    try:
        current_app.logger.error(
            "Internal server error: %s", traceback.format_exc()
        )
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(429)
def ratelimit_handler(exc):
    """
    Return a consistent JSON response when flask-limiter blocks a request.
    """
    return jsonify({'error': 'Rate limit exceeded. Try again later.'}), 429

# ---------------------------------------------------------------------------
# APPLICATION STARTUP
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    # This file can be run directly, but main.py is the recommended entry point.
    # Database migrations are handled by Alembic - run 'alembic upgrade head' before starting.
    # Debug mode is controlled by environment variable (FLASK_DEBUG) for security
    # Default to False for production safety
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    if debug_mode:
        print("WARNING: Debug mode is enabled. Disable in production!")
    app.run(
        debug=debug_mode,  # Controlled by FLASK_DEBUG environment variable
        host='0.0.0.0',    # Allow connections from any IP
        port=5000          # Default Flask development port
    )
