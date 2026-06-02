# -*- coding: utf-8 -*-
#
# WikiEval Flask Application for Toolforge
#
# Copyright (C) 2024 WikiEval Contributors
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

# -------------------------------------------------------------------------
# IMPORTS
# -------------------------------------------------------------------------

import os
import sys
import tomllib
from flask import Flask, request, jsonify, send_from_directory, render_template, session, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from datetime import datetime, timedelta
import secrets

# -------------------------------------------------------------------------
# APPLICATION INITIALIZATION
# -------------------------------------------------------------------------

# Initialize Flask app
app = Flask(__name__)

# Load configuration from TOML file
# Configuration file contains environment-specific settings
__dir__ = os.path.dirname(__file__)
config_path = os.path.join(__dir__, 'config.toml')

if os.path.exists(config_path):
    # Load production/deployment configuration from TOML
    with open(config_path, 'rb') as f:
        app.config.update(tomllib.load(f))
else:
    # Default configuration for development
    # Uses ephemeral secrets and SQLite for easy local setup
    app.config.update({
        'SECRET_KEY': secrets.token_urlsafe(48),
        'JWT_SECRET_KEY': secrets.token_urlsafe(48),
        'JWT_ACCESS_TOKEN_EXPIRES': 86400,  # 24 hours
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///wikicontest.db',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'GREETING': 'Welcome to WikiContest!',
        'DEBUG': False
    })

# -------------------------------------------------------------------------
# EXTENSION INITIALIZATION
# -------------------------------------------------------------------------

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# CORS configuration for Toolforge
# Restricts access to official Toolforge domain for security
CORS(app, origins=['https://wikicontest.toolforge.org'], supports_credentials=True)

# -------------------------------------------------------------------------
# MODEL AND ROUTE IMPORTS
# -------------------------------------------------------------------------

# Import models and routes
# Graceful degradation if models aren't available yet
try:
    from models.user import User
    from models.contest import Contest
    from models.submission import Submission
    from routes.user_routes import user_bp
    from routes.contest_routes import contest_bp
    from routes.submission_routes import submission_bp

    # Register blueprints
    # Blueprints organize routes into logical modules
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(contest_bp, url_prefix='/api/contest')
    app.register_blueprint(submission_bp, url_prefix='/api/submission')

    MODELS_LOADED = True
except ImportError as e:
    print(f"Warning: Could not load models/routes: {e}")
    # Track loading status to prevent errors from missing dependencies
    MODELS_LOADED = False

# -------------------------------------------------------------------------
# FRONTEND ROUTES
# -------------------------------------------------------------------------

# Frontend routes
@app.route('/')
def index():
    """Serve the main frontend page"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

# -------------------------------------------------------------------------
# API ENDPOINTS
# -------------------------------------------------------------------------

# API endpoints
@app.route('/api/cookie', methods=['GET'])
def check_cookie():
    """Check if user is authenticated via cookie"""
    # Prevent operations when models aren't available
    if not MODELS_LOADED:
        return jsonify({'error': 'Models not loaded'}), 500

    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

    try:
        # Verify JWT token exists and is valid
        verify_jwt_in_request()
        user_id = get_jwt_identity()

        # Get user details from database
        # Ensures user still exists and hasn't been deleted
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401

        # Return sanitized user data for client-side use
        return jsonify({
            'userId': user.id,
            'username': user.username,
            'email': user.email
        }), 200

    except Exception as e:
        # JWT verification failed or token expired
        return jsonify({'error': 'You are not logged in'}), 401

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Used by monitoring systems to verify service availability
    return jsonify({
        'status': 'healthy',
        'message': 'WikiContest API is running',
        'models_loaded': MODELS_LOADED
    }), 200

# -------------------------------------------------------------------------
# OAUTH ROUTES
# -------------------------------------------------------------------------

# OAuth routes for Toolforge
@app.route('/login')
def login():
    """OAuth login route"""
    if not MODELS_LOADED:
        return jsonify({'error': 'Models not loaded'}), 500

    # For now, redirect to a simple login page
    # Will be replaced with OAuth flow initiation
    return render_template('login.html')

@app.route('/logout')
def logout():
    """OAuth logout route"""
    # Clear all session data to terminate user session
    session.clear()
    return redirect(url_for('index'))

@app.route('/oauth/callback', methods=['GET'])
def oauth_callback_toolforge():
    """
    Handle OAuth callback from Wikimedia for Toolforge deployment.

    This route is at /oauth/callback to match the OAuth consumer registration.
    It redirects to the blueprint route handler at /api/user/oauth/callback
    while preserving all query parameters.
    """
    if not MODELS_LOADED:
        return jsonify({'error': 'Models not loaded'}), 500

    # Redirect to the blueprint route with all query parameters preserved
    # This ensures the OAuth callback works with the registered callback URL
    # OAuth tokens and verifiers are passed via query string
    query_string = request.query_string.decode('utf-8')
    if query_string:
        return redirect(f'/api/user/oauth/callback?{query_string}')
    else:
        return redirect('/api/user/oauth/callback')

# -------------------------------------------------------------------------
# ERROR HANDLERS
# -------------------------------------------------------------------------

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    # Return JSON for API consistency
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    # Rollback any pending database transactions on errors
    if MODELS_LOADED:
        db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# -------------------------------------------------------------------------
# DATABASE INITIALIZATION
# -------------------------------------------------------------------------

# Create database tables
def create_tables():
    """Create database tables if they don't exist"""
    # Skip if models haven't been loaded successfully
    if not MODELS_LOADED:
        return False

    try:
        # Creates all tables defined in models
        db.create_all()
        print("Database tables created successfully")
        return True
    except Exception as e:
        print(f"Error creating database tables: {e}")
        return False

# Initialize database on startup
# Ensures schema exists before handling requests
if MODELS_LOADED:
    with app.app_context():
        create_tables()

# -------------------------------------------------------------------------
# APPLICATION ENTRY POINT
# -------------------------------------------------------------------------

if __name__ == '__main__':
    # This won't run on Toolforge, but useful for local testing
    # Toolforge uses uWSGI/Gunicorn instead of Flask's dev server
    app.run(debug=True, host='0.0.0.0', port=5000)