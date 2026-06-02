# WikiEval Backend Architecture

Comprehensive documentation of the WikiEval Flask backend architecture, design patterns, and implementation details.



## Overview

The WikiEval backend is a Flask application built using modern Python best practices with a modular, package-based structure. It leverages SQLAlchemy for ORM operations, Flask-JWT-Extended for authentication, and follows the application factory pattern for flexibility and testability.

**Core Technologies:**
- **Framework:** Flask (Python web framework)
- **ORM:** SQLAlchemy (database abstraction)
- **Authentication:** Flask-JWT-Extended (JWT tokens)
- **Migrations:** Alembic (database schema versioning)
- **Validation:** Custom middleware and decorators



## Directory Structure
```
backend/
├── app/                        # Main application package
│   ├── __init__.py            # Application factory
│   ├── config.py              # Configuration classes (Dev/Test/Prod)
│   ├── database.py            # SQLAlchemy instance initialization
│   ├── models/                # Database models (User, Contest, Submission)
│   │   ├── __init__.py
│   │   ├── base_model.py      # Base model with common methods
│   │   ├── user.py            # User model
│   │   ├── contest.py         # Contest model
│   │   └── submission.py      # Submission model
│   ├── routes/                # API route blueprints
│   │   ├── __init__.py
│   │   ├── user_routes.py     # User authentication & management
│   │   ├── contest_routes.py  # Contest CRUD operations
│   │   └── submission_routes.py # Submission handling
│   ├── middleware/            # Middleware functions
│   │   ├── __init__.py
│   │   └── auth.py            # Authentication & authorization
│   └── utils/                 # Utility functions
│       ├── __init__.py
│       ├── responses.py       # Response helpers
│       ├── validators.py      # Input validation
│       └── mediawiki.py       # MediaWiki API helpers
├── alembic/                   # Alembic database migrations
│   ├── versions/              # Migration version files
│   └── env.py                 # Alembic environment config
├── scripts/                   # Utility scripts
│   ├── init_db.py            # Database initialization
│   └── seed_data.py          # Test data seeding
├── toolforge/                 # Toolforge deployment files
│   ├── toolforge_app.py      # Toolforge-specific app
│   └── config.toml.example   # Toolforge config template
├── tests/                     # Test files
│   ├── __init__.py
│   ├── test_models.py        # Model tests
│   ├── test_routes.py        # Route tests
│   └── conftest.py           # Test fixtures
├── logs/                      # Application logs (production)
├── requirements.txt           # Python dependencies
└── run.py                     # Development server entry point
```



## Application Factory Pattern

The application uses Flask's application factory pattern, implemented in `app/__init__.py`. This design pattern provides several key benefits.

### Benefits

1. **Multiple Instances:** Create multiple app instances with different configurations
2. **Testing:** Easier testing with isolated application contexts
3. **Flexibility:** Configure the app differently for different environments
4. **Modularity:** Clear separation between configuration and initialization

### Implementation

**File: `app/__init__.py`**
```python
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from app.config import config
from app.database import db

def create_app(config_name='development'):
    """
    Application factory function.
    
    Args:
        config_name: Configuration environment (development, testing, production)
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    JWTManager(app)
    CORS(app, supports_credentials=True)
    
    # Register blueprints
    from app.routes import user_bp, contest_bp, submission_bp
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(contest_bp, url_prefix='/api/contest')
    app.register_blueprint(submission_bp, url_prefix='/api/submission')
    
    # Register error handlers
    register_error_handlers(app)
    
    return app
```

### Usage
```python
from app import create_app

# Development
app = create_app('development')

# Testing
app = create_app('testing')

# Production
app = create_app('production')
```



## Configuration Management

Configuration is centralized in `app/config.py` with environment-specific classes.

### Configuration Classes

**File: `app/config.py`**
```python
import os
from datetime import timedelta

class Config:
    """Base configuration with common settings."""
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret')
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 20
    
    # JWT
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_COOKIE_SECURE = False  # Override in production
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_COOKIE_CSRF_PROTECT = True
    
    # CORS
    CORS_ORIGINS = ['http://localhost:5173']

class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root@localhost/wikicontest_dev'
    )

class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_COOKIE_CSRF_PROTECT = False  # Easier testing

class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    JWT_COOKIE_SECURE = True  # Require HTTPS
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}
```

### Environment Variables

Configuration values are loaded from environment variables with sensible defaults for development:
```env
# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key

# Database
DATABASE_URL=mysql+pymysql://user:password@localhost/wikicontest

# CORS
CORS_ORIGINS=http://localhost:5173,https://your-domain.com

# OAuth
CONSUMER_KEY=your-consumer-key
CONSUMER_SECRET=your-consumer-secret
```



## Database Layer

### SQLAlchemy Setup

The database instance is created in `app/database.py` and initialized with the Flask app.

**File: `app/database.py`**
```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
```

### Base Model

All models inherit from `BaseModel`, which provides common functionality.

**File: `app/models/base_model.py`**
```python
from app.database import db
from datetime import datetime

class BaseModel(db.Model):
    """Base model with common fields and methods."""
    
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def save(self):
        """Save instance to database."""
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        """Delete instance from database."""
        db.session.delete(self)
        db.session.commit()
    
    def to_dict(self):
        """Convert model to dictionary (override in subclasses)."""
        raise NotImplementedError
```

### Models

Models are organized by domain with clear relationships.

#### User Model

**File: `app/models/user.py`**
```python
from app.models.base_model import BaseModel
from app.database import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(BaseModel):
    """User account model."""
    
    __tablename__ = 'users'
    
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user')  # user, admin
    
    # Relationships
    contests = db.relationship('Contest', backref='creator', lazy='dynamic')
    submissions = db.relationship('Submission', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat()
        }
```

#### Contest Model

**File: `app/models/contest.py`**
```python
from app.models.base_model import BaseModel
from app.database import db

class Contest(BaseModel):
    """Contest model."""
    
    __tablename__ = 'contests'
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    submissions = db.relationship('Submission', backref='contest', lazy='dynamic')
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat()
        }
```

#### Submission Model

**File: `app/models/submission.py`**
```python
from app.models.base_model import BaseModel
from app.database import db

class Submission(BaseModel):
    """Submission model."""
    
    __tablename__ = 'submissions'
    
    contest_id = db.Column(db.Integer, db.ForeignKey('contests.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    article_title = db.Column(db.String(200), nullable=False)
    article_link = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    score = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'contest_id': self.contest_id,
            'user_id': self.user_id,
            'article_title': self.article_title,
            'article_link': self.article_link,
            'status': self.status,
            'score': self.score,
            'submitted_at': self.created_at.isoformat()
        }
```

### Database Relationships

Models define relationships using SQLAlchemy's `relationship()`:

- **User → Contests:** One-to-many (one user creates many contests)
- **User → Submissions:** One-to-many (one user makes many submissions)
- **Contest → Submissions:** One-to-many (one contest has many submissions)

**Relationship Diagram:**
```
User
├── contests (created contests)
└── submissions (user's submissions)

Contest
├── creator (relationship to User)
└── submissions (contest submissions)

Submission
├── user (relationship to User)
└── contest (relationship to Contest)
```



## Routing Architecture

### Blueprint Organization

Routes are organized into blueprints for modularity and maintainability.

**Available Blueprints:**
- `user_bp` → User authentication and management (`/api/user/*`)
- `contest_bp` → Contest CRUD operations (`/api/contest/*`)
- `submission_bp` → Submission handling (`/api/submission/*`)

### Blueprint Registration

Blueprints are registered in the application factory.

**File: `app/__init__.py`**
```python
def create_app(config_name='development'):
    # ... initialization code ...
    
    # Register blueprints
    from app.routes import user_bp, contest_bp, submission_bp
    
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(contest_bp, url_prefix='/api/contest')
    app.register_blueprint(submission_bp, url_prefix='/api/submission')
    
    return app
```

### Route Example

**File: `app/routes/user_routes.py`**
```python
from flask import Blueprint, request
from app.middleware.auth import require_auth, handle_errors
from app.models.user import User
from app.utils.responses import success_response, error_response

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
@require_auth
@handle_errors
def get_profile():
    """Get current user profile."""
    current_user = get_current_user()
    return success_response('Profile retrieved', current_user.to_dict())

@user_bp.route('/register', methods=['POST'])
@handle_errors
def register():
    """Register a new user."""
    data = request.get_json()
    
    # Validation
    if not data.get('username') or not data.get('email') or not data.get('password'):
        return error_response('Missing required fields', 400)
    
    # Create user
    user = User(
        username=data['username'],
        email=data['email']
    )
    user.set_password(data['password'])
    user.save()
    
    return success_response('User registered successfully', user.to_dict(), 201)
```



## Middleware

Middleware functions provide cross-cutting concerns like authentication, authorization, and error handling.

**File: `app/middleware/auth.py`**

### Authentication Middleware
```python
from functools import wraps
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User
from app.utils.responses import error_response

def require_auth(fn):
    """Require valid JWT token."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            return error_response('Unauthorized', 401)
    return wrapper

def get_current_user():
    """Get current authenticated user."""
    user_id = get_jwt_identity()
    return User.query.get(user_id)
```

### Authorization Middleware
```python
def require_role(*roles):
    """Require specific user role(s)."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            current_user = get_current_user()
            if current_user.role not in roles:
                return error_response('Forbidden', 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@route('/admin')
@require_auth
@require_role('admin')
def admin_route():
    pass
```

### Permission Checking
```python
def require_submission_permission(fn):
    """Require permission to access submission."""
    @wraps(fn)
    def wrapper(submission_id, *args, **kwargs):
        current_user = get_current_user()
        submission = Submission.query.get(submission_id)
        
        if not submission:
            return error_response('Submission not found', 404)
        
        # Check permission
        is_owner = submission.user_id == current_user.id
        is_admin = current_user.role == 'admin'
        is_jury = check_jury_permission(current_user, submission.contest_id)
        
        if not (is_owner or is_admin or is_jury):
            return error_response('Forbidden', 403)
        
        return fn(submission_id, *args, **kwargs)
    return wrapper
```

### Error Handling Middleware
```python
def handle_errors(fn):
    """Global error handling decorator."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as e:
            return error_response(str(e), 400)
        except Exception as e:
            # Log error
            app.logger.error(f"Unexpected error: {str(e)}")
            return error_response('Internal server error', 500)
    return wrapper
```



## Authentication & Authorization

### JWT Authentication

The application uses Flask-JWT-Extended for JWT-based authentication.

**Configuration:**
- **Storage:** HTTP-only cookies (not accessible via JavaScript)
- **CSRF Protection:** Enabled via `X-CSRF-TOKEN` header
- **Expiration:** 24 hours (configurable)
- **Refresh:** Automatic token refresh (optional)

**Login Flow:**
1. User submits credentials
2. Server validates credentials
3. Server generates JWT token
4. Token stored in HTTP-only cookie
5. Client includes cookie in subsequent requests

**File: `app/routes/user_routes.py`**
```python
from flask_jwt_extended import create_access_token, set_access_cookies

@user_bp.route('/login', methods=['POST'])
@handle_errors
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()
    
    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return error_response('Invalid credentials', 401)
    
    # Create JWT token
    access_token = create_access_token(identity=user.id)
    
    # Create response and set cookies
    response = success_response('Login successful', user.to_dict())
    set_access_cookies(response, access_token)
    
    return response
```

### Role-Based Access Control

**Roles:**
- `admin` – Full system access (manage all users, contests, submissions)
- `user` – Standard user access (create contests, submit entries)
- `creator` – Contest creator permissions (manage own contests)
- `jury` – Jury member permissions (review assigned contest submissions)

### Permission System

Permissions are contextual based on:
- **User role** (admin, user)
- **Contest relationships** (creator, jury member)
- **Submission ownership** (submission author)


## Error Handling

### Global Error Handlers

Defined in the application factory to handle common HTTP errors.

**File: `app/__init__.py`**
```python
def register_error_handlers(app):
    """Register global error handlers."""
    
    @app.errorhandler(404)
    def not_found(error):
        return error_response('Resource not found', 404)
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()  # Rollback any pending transactions
        return error_response('Internal server error', 500)
    
    @app.errorhandler(403)
    def forbidden(error):
        return error_response('Forbidden', 403)
```

### Route-Level Error Handling

Routes use the `@handle_errors` decorator for consistent error handling.

**Example:**
```python
@contest_bp.route('/', methods=['POST'])
@require_auth
@handle_errors
def create_contest():
    """Create a new contest."""
    # If any exception occurs, @handle_errors catches it
    # and returns appropriate error response
    data = request.get_json()
    
    # Validation errors raise ValueError
    if not data.get('title'):
        raise ValueError('Title is required')
    
    # Business logic
    contest = Contest(**data)
    contest.save()
    
    return success_response('Contest created', contest.to_dict(), 201)
```



## Database Migrations

The application uses **Alembic** for database schema versioning and migrations.

### Migration Workflow

1. **Modify models** in `app/models/`
2. **Generate migration** using Alembic
3. **Review migration** file
4. **Apply migration** to database

### Commands
```bash
# Generate a new migration
alembic revision --autogenerate -m "Add new field to User model"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

### Migration Files

- **Location:** `alembic/versions/`
- **Version Tracking:** Managed by `alembic_version` table
- **Structure:** Each migration has `upgrade()` and `downgrade()` functions

For detailed migration documentation, see the Alembic Usage Guide.



## Utility Functions

Utility functions are organized in `app/utils/` for reusability.

### Response Helpers

**File: `app/utils/responses.py`**
```python
from flask import jsonify

def success_response(message, data=None, status_code=200):
    """Create standardized success response."""
    response = {'success': True, 'message': message}
    if data is not None:
        response['data'] = data
    return jsonify(response), status_code

def error_response(message, status_code=400, details=None):
    """Create standardized error response."""
    response = {'success': False, 'message': message}
    if details:
        response['details'] = details
    return jsonify(response), status_code
```

### Validators

**File: `app/utils/validators.py`**
```python
from datetime import datetime

def validate_date_range(start_date, end_date):
    """Validate that end date is after start date."""
    if end_date <= start_date:
        raise ValueError('End date must be after start date')

def validate_email(email):
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError('Invalid email format')
```

### MediaWiki Helpers

**File: `app/utils/mediawiki.py`**
```python
import requests

def validate_wikipedia_article(article_title):
    """Validate that Wikipedia article exists."""
    url = f'https://en.wikipedia.org/w/api.php'
    params = {
        'action': 'query',
        'titles': article_title,
        'format': 'json'
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    pages = data['query']['pages']
    return '-1' not in pages  # -1 indicates page doesn't exist
```



## Testing Structure

Tests are organized in the `tests/` directory with clear separation by component.

### Test Organization
```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_models.py           # Model tests
├── test_user_routes.py      # User route tests
├── test_contest_routes.py   # Contest route tests
└── test_submission_routes.py # Submission route tests
```

### Test Fixtures

**File: `tests/conftest.py`**
```python
import pytest
from app import create_app
from app.database import db

@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """Create authenticated test client."""
    # Register and login
    client.post('/api/user/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    client.post('/api/user/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    return client
```

### Example Test

**File: `tests/test_user_routes.py`**
```python
def test_user_registration(client):
    """Test user registration endpoint."""
    response = client.post('/api/user/register', json={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'password123'
    })
    
    assert response.status_code == 201
    assert response.json['success'] == True
    assert 'data' in response.json

def test_user_login(client):
    """Test user login endpoint."""
    # Register first
    client.post('/api/user/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Login
    response = client.post('/api/user/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    assert response.status_code == 200
    assert response.json['success'] == True
```



## Logging

Logging is configured in the application factory with environment-specific settings.

### Configuration

**File: `app/__init__.py`**
```python
import logging
from logging.handlers import RotatingFileHandler
import os

def configure_logging(app):
    """Configure application logging."""
    if not app.debug:
        # Production logging
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/wikicontest.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('WikiContest startup')
```

### Usage
```python
from flask import current_app

# In routes
current_app.logger.info('User logged in: %s', user.username)
current_app.logger.error('Failed to create contest: %s', str(error))
current_app.logger.warning('Invalid submission attempt: %s', submission_id)
```



## Security Considerations

### Authentication Security

- **JWT tokens** stored in HTTP-only cookies (not accessible via JavaScript)
- **CSRF protection** via `X-CSRF-TOKEN` header for state-changing requests
- **Secure cookies** enabled in production (HTTPS only)
- **Token expiration** enforced (24-hour default)

### Database Security

- **Parameterized queries** via SQLAlchemy ORM (prevents SQL injection)
- **Connection pooling** for efficient resource management
- **Password hashing** using Werkzeug's bcrypt implementation
- **No raw SQL** queries in application code

### Input Validation

- **JSON schema validation** for API requests
- **Type checking** on all user inputs
- **Email validation** using regex patterns
- **URL sanitization** for external links

### CORS Configuration

- **Whitelist** of allowed origins (no wildcard in production)
- **Credentials support** enabled for cookie-based auth
- **Specific methods** and headers allowed



## Performance Optimizations

### Database Optimizations

**Connection Pooling:**
```python
SQLALCHEMY_POOL_SIZE = 10
SQLALCHEMY_MAX_OVERFLOW = 20
SQLALCHEMY_POOL_RECYCLE = 3600
```

**Query Optimization:**
- Use `lazy='dynamic'` for large relationship sets
- Add database indexes on frequently queried columns
- Use `joinedload()` to prevent N+1 queries

**Indexed Columns:**
```python
class User(BaseModel):
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
```

### Caching Strategies

- **Session caching** for frequently accessed user data
- **Query result caching** for read-heavy operations
- **Redis integration** (future enhancement)



## Deployment

### Development Environment
```bash
# Start development server
python run.py

# Features:
# - Debug mode enabled
# - Hot reload on code changes
# - Detailed error pages
# - SQLite or local MySQL
```

### Production Environment
```bash
# Use Gunicorn WSGI server
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 run:app

# Configuration:
# - Multiple workers for concurrency
# - Longer timeout for complex requests
# - Behind reverse proxy (Nginx)
# - MySQL or PostgreSQL database
```

### Toolforge Deployment

Specialized deployment for Wikimedia Toolforge platform:

- **Location:** `toolforge/` directory
- **Application:** `toolforge_app.py`
- **OAuth:** OAuth 1.0a integration with Wikimedia
- **Configuration:** TOML-based config files
- **Server:** uWSGI with Kubernetes



## Code Organization Principles

The codebase follows these key principles:

1. **Separation of Concerns** – Models, routes, middleware, and utilities are clearly separated
2. **DRY (Don't Repeat Yourself)** – Common functionality abstracted into base classes and utilities
3. **Single Responsibility** – Each module has a clear, single purpose
4. **Modularity** – Blueprints and packages enable easy extension
5. **Testability** – Application factory pattern enables easy testing with different configurations


## Future Improvements

- Consider Flask-Migrate (Alembic) for database migrations
- Add comprehensive test coverage
- Implement API rate limiting
- Add request/response logging middleware
- Consider adding a service layer for business logic
- Implement caching layer (Redis)
- Add API documentation (Swagger/OpenAPI)

