"""
WikiContest Flask Application
Main application entry point for the Python Flask backend

This module initializes the Flask application with all necessary configurations,
extensions, and route blueprints. It serves as the central hub for the WikiContest
platform, handling both API endpoints and static file serving.

Architecture:
- Modular design with separate blueprints for different features
- JWT-based authentication with cookie storage
- CORS enabled for frontend communication
- Database integration with SQLAlchemy ORM
- Comprehensive error handling and logging

Author: WikiContest Development Team
Version: 1.0.0
"""

# Standard library imports
import os
from datetime import timedelta
from urllib.parse import urlparse, parse_qs, unquote

# Third-party imports
from flask import Flask, request, jsonify, send_from_directory, current_app
from flask_cors import CORS
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt_identity
from flask_jwt_extended.exceptions import JWTDecodeError, NoAuthorizationError
from dotenv import load_dotenv
import requests
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError, OperationalError

# Local imports
from database import db
# Import models to ensure they are registered with SQLAlchemy
# This is required for database migrations and table creation
from models.user import User  # pylint: disable=unused-import
from models.contest import Contest  # pylint: disable=unused-import
from models.submission import Submission  # pylint: disable=unused-import
from routes.user_routes import user_bp
from routes.contest_routes import contest_bp
from routes.submission_routes import submission_bp

# =============================================================================
# CONFIGURATION SETUP
# =============================================================================

# Load environment variables from .env file
# This allows for easy configuration management across different environments
load_dotenv()

def create_app():
    """
    Application factory pattern for creating Flask app instances.

    This function creates and configures the Flask application with all
    necessary extensions and settings. Using the factory pattern makes
    the application more testable and allows for different configurations
    in different environments.

    Returns:
        Flask: Configured Flask application instance
    """
    # Initialize Flask application
    flask_app = Flask(__name__)

    # =========================================================================
    # SECURITY CONFIGURATION
    # =========================================================================

    # Secret keys for session management and JWT signing
    # These should be different in production and stored securely
    flask_app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'rohank10')
    flask_app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'rohank10')

    # Session configuration for OAuth flow
    # Sessions need to persist across redirects to external OAuth providers
    flask_app.config['SESSION_PERMANENT'] = True  # Make sessions persistent
    flask_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 30 min timeout
    flask_app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
    # Allow cross-site redirects for OAuth (required for external redirects)
    flask_app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    # Set to False for localhost (True for HTTPS in production)
    flask_app.config['SESSION_COOKIE_SECURE'] = False
    flask_app.config['SESSION_COOKIE_DOMAIN'] = None  # Don't restrict domain for localhost
    flask_app.config['SESSION_COOKIE_PATH'] = '/'  # Available for all paths

    # JWT token expiration time (24 hours)
    flask_app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

    # JWT Cookie Configuration for secure token storage
    flask_app.config['JWT_TOKEN_LOCATION'] = ['cookies']  # Store tokens in HTTP-only cookies
    # False for localhost HTTP, True for production HTTPS
    flask_app.config['JWT_COOKIE_SECURE'] = False
    # Lax allows same-site cookies (works for localhost ports)
    flask_app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
    # None allows cookie to work across localhost ports
    # Set to True in production with HTTPS
    flask_app.config['JWT_COOKIE_DOMAIN'] = None
    flask_app.config['JWT_COOKIE_CSRF_PROTECT'] = True  # Enable CSRF protection
    flask_app.config['JWT_CSRF_IN_COOKIES'] = True  # Include CSRF token in cookies

    # =========================================================================
    # OAUTH 1.0a CONFIGURATION (Wikimedia OAuth 1.0a)
    # =========================================================================

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
    flask_app.config['OAUTH_USE_OOB'] = os.getenv('OAUTH_USE_OOB', 'False').lower() == 'true'

    # =========================================================================
    # DATABASE CONFIGURATION
    # =========================================================================

    # Database connection string
    # Supports MySQL, PostgreSQL, SQLite, and other SQLAlchemy-compatible databases
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:password@localhost/wikicontest'
    )

    # Disable SQLAlchemy event system for better performance
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # =========================================================================
    # EXTENSION INITIALIZATION
    # =========================================================================

    # Initialize database with the app
    db.init_app(flask_app)

    # Initialize JWT manager for token handling
    JWTManager(flask_app)

    # Configure CORS for frontend communication
    # Allows requests from frontend development servers
    CORS(flask_app, origins=[
        'http://localhost:3000',  # React development server
        'http://localhost:5173',  # Vite development server
        'http://localhost:5000'   # Flask development server
    ], supports_credentials=True)

    return flask_app

# Create the application instance
app = create_app()

# =============================================================================
# MODEL REGISTRATION
# =============================================================================

# Import models to ensure they are registered with SQLAlchemy
# This is required for database migrations and table creation
# Models are imported at top of file

# =============================================================================
# ROUTE BLUEPRINT REGISTRATION
# =============================================================================

# Import route blueprints for modular organization
# Each blueprint handles a specific domain of functionality
# Blueprints are imported at top of file

# Register blueprints with URL prefixes for API organization
# This creates a clean RESTful API structure
app.register_blueprint(user_bp, url_prefix='/api/user')  # User management endpoints
app.register_blueprint(contest_bp, url_prefix='/api/contest')  # Contest endpoints
app.register_blueprint(submission_bp, url_prefix='/api/submission')  # Submission endpoints
# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@app.route('/api/cookie', methods=['GET'])
def check_cookie():
    """
    Check if user is authenticated via JWT cookie.

    This endpoint is used by the frontend to verify if a user is currently
    logged in. It reads the JWT token from the HTTP-only cookie and returns
    the user's basic information if the token is valid.

    Returns:
        JSON: User information if authenticated, error if not
    """
    try:
        # Verify the JWT token from the cookie
        # Use optional=False to ensure token MUST be present and valid
        verify_jwt_in_request(optional=False)
        user_id = get_jwt_identity()

        # Validate user_id exists and is valid
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401

        # Get user details from database
        user = User.query.get(int(user_id))
        if not user:
            return jsonify({'error': 'User not found'}), 401

        return jsonify({
            'userId': user.id,
            'username': user.username,
            'email': user.email
        }), 200

    except (JWTDecodeError, NoAuthorizationError):
        # No token or invalid token - user is definitely not logged in
        return jsonify({'error': 'You are not logged in'}), 401
    except (SQLAlchemyError, RuntimeError, AttributeError, ValueError) as error:
        # Catch database errors, Flask context errors, or other specific errors
        # Log for debugging but don't expose error to client
        try:
            current_app.logger.debug(f'Cookie check failed: {str(error)}')
        except (AttributeError, RuntimeError):
            # Logger might not be available or Flask context missing
            pass
        return jsonify({'error': 'You are not logged in'}), 401

# =============================================================================
# FRONTEND SERVING ROUTES
# =============================================================================

@app.route('/')
def index():
    """
    Serve the main frontend page.

    Serves the Vue.js application.
    In development, serves from frontend directory (Vite dev server handles it).
    In production, serves from frontend/dist directory (built Vue.js app).
    """
    # Check if dist directory exists (production build)
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
    if os.path.exists(dist_path):
        # Production - serve built Vue.js files
        return send_from_directory(dist_path, 'index.html')
    # Development - serve Vue.js mount point (Vite dev server will handle it)
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """
    Serve static files from frontend directory.

    In production, serves from frontend/dist directory (built Vue.js app).
    In development, serves from frontend directory (Vite dev server handles Vue.js).
    """
    # Skip API routes
    if filename.startswith('api/'):
        return jsonify({'error': 'Endpoint not found'}), 404

    # Check if dist directory exists (production build)
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
    if os.path.exists(dist_path):
        # Production - serve from dist
        try:
            return send_from_directory(dist_path, filename)
        except Exception:
            # If file not found in dist, serve index.html (for Vue Router)
            if not filename.startswith('api/'):
                return send_from_directory(dist_path, 'index.html')
            raise
    # Development - serve from frontend directory
    # Vite dev server will handle Vue.js files, Flask serves other static files
    return send_from_directory('../frontend', filename)

# =============================================================================
# SYSTEM ENDPOINTS
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    This endpoint can be used by monitoring systems to check if the
    application is running and responding to requests.

    Returns:
        JSON: Application status information
    """
    return jsonify({
        'status': 'healthy',
        'message': 'WikiContest API is running',
        'version': '1.0.0'
    }), 200

@app.route('/api/oauth/config', methods=['GET'])
def oauth_config_check():
    """
    Diagnostic endpoint to check OAuth configuration.

    This helps verify that OAuth is properly configured and shows
    what callback URL will be used. Useful for troubleshooting.

    Returns:
        JSON: OAuth configuration details (without secrets)
    """
    consumer_key = app.config.get('CONSUMER_KEY', '')
    consumer_secret = app.config.get('CONSUMER_SECRET', '')
    mw_uri = app.config.get('OAUTH_MWURI', 'https://meta.wikimedia.org/w/index.php')
    use_oob = app.config.get('OAUTH_USE_OOB', False)
    custom_callback_path = app.config.get('OAUTH_CALLBACK_PATH', None)

    # Build callback URL
    # For local development: http://localhost:5000/api/user/oauth/callback
    # For Toolforge: https://wikicontest.toolforge.org/oauth/callback
    # (if OAUTH_CALLBACK_PATH is set)
    scheme = request.scheme
    host = request.host
    if custom_callback_path:
        callback_url = f"{scheme}://{host}{custom_callback_path}"
    else:
        # Default callback URL for local development
        callback_url = f"{scheme}://{host}/api/user/oauth/callback"

    # Build instruction message for callback URL
    callback_instruction = (
        f'Your OAuth consumer must be registered with this exact '
        f'callback URL: {callback_url}'
    )

    return jsonify({
        'oauth_configured': bool(consumer_key and consumer_secret),
        'consumer_key': consumer_key[:10] + '...' if consumer_key else 'NOT SET',
        'consumer_secret_set': bool(consumer_secret),
        'mw_uri': mw_uri,
        'use_oob': use_oob,
        'callback_url': callback_url,
        'custom_callback_path': custom_callback_path,
        'instructions': {
            'if_use_oob_true': 'Your OAuth consumer must be registered with "oob" (out-of-band)',
            'if_use_oob_false': callback_instruction,
            'check_registration': (
                'Go to https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration '
                'to verify your consumer settings'
            )
        }
    }), 200

@app.route('/api/mediawiki/article-info', methods=['GET'])
def mediawiki_article_info():  # pylint: disable=too-many-return-statements
    """
    Fetch comprehensive article information from MediaWiki API.

    This endpoint fetches detailed information about a MediaWiki article including:
    - Article title
    - Author (creator) of the article
    - Creation date
    - Last revision date
    - Page ID
    - Word count
    - And other metadata useful for judging

    Query Parameters:
        url (str): The full MediaWiki article URL

    Returns:
        JSON: Article information including title, author, dates, etc.

    Example:
        GET /api/mediawiki/article-info?url=https://en.wikipedia.org/wiki/Article_Title
    """
    # Get the article URL from query parameters
    article_url = request.args.get('url', '')

    if not article_url:
        return jsonify({'error': 'Article URL is required'}), 400

    try:
        # Parse the article URL to extract base URL and page title
        url_obj = urlparse(article_url)
        base_url = f"{url_obj.scheme}://{url_obj.netloc}"

        # Extract page title from URL
        page_title = ''
        if '/wiki/' in url_obj.path:
            # Standard MediaWiki URL format: /wiki/Page_Title
            page_title = unquote(url_obj.path.split('/wiki/')[1])
        elif 'title=' in url_obj.query:
            # Old-style URL: /w/index.php?title=Page_Title
            query_params = parse_qs(url_obj.query)
            page_title = unquote(query_params.get('title', [''])[0])
        else:
            # Try to extract from pathname
            parts = url_obj.path.split('/')
            page_title = unquote(parts[-1]) if parts else ''

        if not page_title:
            return jsonify({'error': 'Could not extract page title from URL'}), 400

        # Build MediaWiki API URL
        api_url = f"{base_url}/w/api.php"

        # First, get page information including revisions (for author)
        # Use formatversion=2 for better JSON structure (as shown in MediaWiki API docs)
        api_params = {
            'action': 'query',
            'titles': page_title,
            'format': 'json',
            'formatversion': '2',  # Use formatversion=2 for cleaner JSON structure
            'prop': 'info|revisions',
            'rvprop': 'timestamp|user|comment|size',
            'rvlimit': '1',  # Get first revision (creation)
            'rvdir': 'newer',  # Start from oldest
            'inprop': 'url|displaytitle',
            'redirects': 'true'  # Follow redirects
        }

        # Make request to MediaWiki API with timeout
        # MediaWiki API requires a User-Agent header to identify the application
        headers = {
            'User-Agent': (
                'WikiContest/1.0 (https://wikicontest.toolforge.org; '
                'contact@wikicontest.org) Python/requests'
            )
        }

        response = requests.get(api_url, params=api_params, headers=headers, timeout=10)

        # Check if request was successful
        if response.status_code != 200:
            return jsonify({
                'error': f'MediaWiki API returned status {response.status_code}',
                'details': response.text[:200]
            }), response.status_code

        # Parse JSON response
        data = response.json()

        # Check for API errors
        if 'error' in data:
            error_info = data['error'].get('info', 'Unknown MediaWiki API error')
            error_code = data['error'].get('code', 'unknown')
            return jsonify({
                'error': error_info,
                'code': error_code
            }), 400

        # Get page data
        # With formatversion=2, pages is an array; otherwise it's an object
        pages = data.get('query', {}).get('pages', [])
        if not pages:
            return jsonify({'error': 'No page data found in API response'}), 404

        # Handle formatversion=2 (array) or formatversion=1 (object)
        if isinstance(pages, list):
            # formatversion=2: pages is an array
            if len(pages) == 0:
                return jsonify({'error': 'Article not found'}), 404
            page_data = pages[0]
            page_id = str(page_data.get('pageid', ''))
        else:
            # formatversion=1: pages is an object with page IDs as keys
            page_id = list(pages.keys())[0]
            page_data = pages[page_id]

        # Check if page exists
        if page_id == '-1' or page_data.get('missing') is not False:
            return jsonify({'error': 'Article not found'}), 404

        # Extract article information
        article_title = page_data.get('title', page_title)
        display_title = page_data.get('displaytitle', article_title)
        page_url = page_data.get('fullurl', article_url)

        # Get revision information (first revision = creation)
        revisions = page_data.get('revisions', [])
        author = None
        article_created_at = None
        last_revision_date = None
        word_count = None

        if revisions:
            # First revision is the creation
            first_revision = revisions[0]
            author = first_revision.get('user', 'Unknown')
            article_created_at = first_revision.get('timestamp', '')
            word_count = first_revision.get('size', 0)

            # Last revision (most recent)
            if len(revisions) > 0:
                last_revision = revisions[-1]
                last_revision_date = last_revision.get('timestamp', '')

        # Return comprehensive article information
        return jsonify({
            'article_title': article_title,
            'display_title': display_title,
            'article_url': page_url,
            'author': author,
            'article_created_at': article_created_at,
            'last_revision_date': last_revision_date,
            'word_count': word_count,
            'page_id': page_id,
            'base_url': base_url
        }), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'error': (
                'Request to MediaWiki API timed out. '
                'The server may be slow or unavailable.'
            )
        }), 504
    except requests.exceptions.RequestException as error:
        return jsonify({
            'error': f'Failed to connect to MediaWiki API: {str(error)}'
        }), 502
    except ValueError as error:
        # JSON parsing error
        return jsonify({
            'error': f'Invalid response from MediaWiki API: {str(error)}'
        }), 502
    except (KeyError, TypeError, AttributeError) as error:
        # Catch data structure errors (missing keys, wrong types, missing attributes)
        return jsonify({
            'error': f'Unexpected error while fetching article information: {str(error)}'
        }), 500

@app.route('/api/mediawiki/preview', methods=['GET'])
def mediawiki_preview():  # pylint: disable=too-many-return-statements
    """
    Proxy endpoint for MediaWiki API article preview requests.

    This endpoint acts as a proxy to fetch MediaWiki article content
    from external MediaWiki sites. It solves CORS issues by making
    the request from the backend server instead of the browser.

    Query Parameters:
        url (str): The full MediaWiki article URL to fetch preview for
        page (str, optional): The page title (if URL parsing fails)

    Returns:
        JSON: MediaWiki API response with parsed article content

    Example:
        GET /api/mediawiki/preview?url=https://en.wikipedia.org/wiki/Userpage
    """
    # Get the article URL from query parameters
    article_url = request.args.get('url', '')
    page_title = request.args.get('page', '')

    if not article_url:
        return jsonify({'error': 'Article URL is required'}), 400

    try:
        # Parse the article URL to extract base URL and page title
        url_obj = urlparse(article_url)
        base_url = f"{url_obj.scheme}://{url_obj.netloc}"

        # Extract page title from URL if not provided as parameter
        if not page_title:
            if '/wiki/' in url_obj.path:
                # Standard MediaWiki URL format: /wiki/Page_Title
                # Decode URL-encoded characters (e.g., %20 -> space, %2F -> /)
                page_title = unquote(url_obj.path.split('/wiki/')[1])
            elif 'title=' in url_obj.query:
                # Old-style URL: /w/index.php?title=Page_Title
                query_params = parse_qs(url_obj.query)
                page_title = unquote(query_params.get('title', [''])[0])
            else:
                # Try to extract from pathname
                parts = url_obj.path.split('/')
                page_title = unquote(parts[-1]) if parts else ''

        if not page_title:
            return jsonify({'error': 'Could not extract page title from URL'}), 400

        # Build MediaWiki API URL
        # Use action=parse to get rendered HTML content
        api_url = f"{base_url}/w/api.php"

        # MediaWiki API request with formatversion=2 for better JSON structure
        # This matches the recommended API format
        api_params = {
            'action': 'parse',
            'page': page_title,  # MediaWiki API handles URL encoding internally
            'format': 'json',
            'formatversion': '2',  # Use formatversion=2 for cleaner JSON structure
            'prop': 'text|displaytitle',
            'redirects': 'true'  # Follow redirects
        }

        # Make request to MediaWiki API with timeout
        # Backend-to-backend requests don't have CORS restrictions
        # MediaWiki API requires a User-Agent header to identify the application
        headers = {
            'User-Agent': (
                'WikiContest/1.0 (https://wikicontest.toolforge.org; '
                'contact@wikicontest.org) Python/requests'
            )
        }

        try:
            response = requests.get(api_url, params=api_params, headers=headers, timeout=10)
        except requests.exceptions.RequestException as error:
            return jsonify({
                'error': f'Failed to connect to MediaWiki API: {str(error)}',
                'api_url': api_url,
                'page_title': page_title
            }), 502

        # Check if request was successful
        if response.status_code != 200:
            return jsonify({
                'error': f'MediaWiki API returned status {response.status_code}',
                'details': response.text[:200]  # First 200 chars of error
            }), response.status_code

        # Parse JSON response
        try:
            data = response.json()
        except ValueError as error:
            return jsonify({
                'error': f'Invalid JSON response from MediaWiki API: {str(error)}',
                'response_preview': response.text[:200]
            }), 502

        # Check for API errors
        if 'error' in data:
            error_info = data['error'].get('info', 'Unknown MediaWiki API error')
            error_code = data['error'].get('code', 'unknown')
            return jsonify({
                'error': error_info,
                'code': error_code,
                'page_title': page_title
            }), 400

        # Check if we have parsed content
        if 'parse' not in data:
            return jsonify({
                'error': 'No parse data found in MediaWiki API response',
                'page_title': page_title,
                'response_keys': (
                    list(data.keys()) if isinstance(data, dict) else 'not a dict'
                )
            }), 404

        # Check if text field exists (can be dict or string depending on formatversion)
        parse_data = data.get('parse', {})
        if 'text' not in parse_data:
            return jsonify({
                'error': 'No text content found in MediaWiki API response',
                'page_title': page_title,
                'parse_keys': (
                    list(parse_data.keys()) if isinstance(parse_data, dict) else 'not a dict'
                )
            }), 404

        # Get the HTML content
        # Handle both formatversion=1 (dict with '*') and formatversion=2
        # MediaWiki API parse action returns text as a dict with '*' key
        text_data = parse_data.get('text', {})

        if isinstance(text_data, dict):
            # Standard format: text is a dict with '*' key containing the HTML
            html_content = text_data.get('*', '')
        elif isinstance(text_data, str):
            # Fallback: if text is directly a string (shouldn't happen but handle it)
            html_content = text_data
        else:
            # No text data available
            html_content = ''

        # Get the actual page title (may differ from URL due to redirects)
        # Use safe access to avoid errors
        actual_page_title = parse_data.get('displaytitle') or parse_data.get('title', page_title)

        # Make links absolute (convert relative links to absolute)
        # This ensures images and links work correctly in the preview
        html_content = html_content.replace('href="/wiki/', f'href="{base_url}/wiki/')
        html_content = html_content.replace('href="/w/', f'href="{base_url}/w/')
        html_content = html_content.replace('src="/wiki/', f'src="{base_url}/wiki/')
        html_content = html_content.replace('src="/w/', f'src="{base_url}/w/')

        # Return the parsed content
        return jsonify({
            'htmlContent': html_content,
            'actualPageTitle': actual_page_title,
            'pageTitle': page_title,
            'baseUrl': base_url
        }), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'error': (
                'Request to MediaWiki API timed out. '
                'The server may be slow or unavailable.'
            )
        }), 504
    except requests.exceptions.RequestException as error:
        return jsonify({
            'error': f'Failed to connect to MediaWiki API: {str(error)}'
        }), 502
    except ValueError as error:
        # JSON parsing error
        return jsonify({
            'error': f'Invalid response from MediaWiki API: {str(error)}'
        }), 502
    except (KeyError, TypeError, AttributeError) as error:
        # Catch data structure errors (missing keys, wrong types, missing attributes)
        return jsonify({
            'error': f'Unexpected error while fetching article preview: {str(error)}'
        }), 500

# =============================================================================
# ERROR HANDLERS
# =============================================================================

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
    Handle 500 Internal Server errors.

    This handler catches all unhandled exceptions and returns a generic
    error response. It also rolls back any pending database transactions.
    """
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# =============================================================================
# APPLICATION STARTUP
# =============================================================================

def migrate_database():
    """
    Run database migrations to add new columns if they don't exist.
    This ensures the database schema matches the current model definitions.
    """
    try:
        # Get table inspector to check existing columns
        inspector = inspect(db.engine)

        # =====================================================================
        # Migrate submissions table: Add article metadata columns
        # =====================================================================
        try:
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
                print("✓ Submissions table migration completed")
        except (OperationalError, SQLAlchemyError, AttributeError) as error:
            # Catch database errors or missing table inspector
            # This is a broad catch but necessary for migration safety
            print(f"⚠ Submissions table migration check skipped: {error}")

        # =====================================================================
        # Migrate contests table: Add allowed_submission_type column
        # =====================================================================
        try:
            contest_columns = [col['name'] for col in inspector.get_columns('contests')]

            # Check if allowed_submission_type column exists
            if 'allowed_submission_type' not in contest_columns:
                print("📦 Running database migration: Adding allowed_submission_type to contests...")
                try:
                    db.session.execute(
                        text(
                            "ALTER TABLE contests ADD COLUMN allowed_submission_type "
                            "VARCHAR(20) NOT NULL DEFAULT 'both'"
                        )
                    )
                    db.session.commit()
                    print("  ✓ Added column: allowed_submission_type")
                    print("✓ Contests table migration completed")
                except (ProgrammingError, OperationalError) as error:
                    # Column might already exist or there's a SQL/database error
                    print(f"  ⚠ Could not add column allowed_submission_type: {error}")
                    db.session.rollback()
            else:
                print("✓ Database schema is up to date")
        except (OperationalError, SQLAlchemyError, AttributeError) as error:
            # Catch database errors or missing table inspector
            # This is a broad catch but necessary for migration safety
            print(f"⚠ Contests table migration check skipped: {error}")

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
