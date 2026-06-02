# WikiEval Flask Backend

A Python Flask backend application for the WikiEval platform, converted from Node.js/Express to Python/Flask with SQLAlchemy ORM and MySQL database support.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Database Management](#database-management)
- [Authentication & Authorization](#authentication--authorization)
- [Development](#development)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)


## Overview

This backend provides a comprehensive API for managing Wikipedia article contests, including user authentication, contest creation, article submission, and jury review workflows. Built with Flask and SQLAlchemy, it offers a clean RESTful API with robust security features.

## Features

### Core Functionality
- **User Management** - Registration, login, logout, and profile management
- **Contest Management** - Create, view, update, and delete contests
- **Submission System** - Submit Wikipedia articles to contests and manage reviews
- **Role-Based Access Control** - Admin, creator, jury, and participant roles with granular permissions

### Technical Features
- **JWT Authentication** - Secure token-based authentication with HTTP-only cookies
- **MySQL Database** - Production-ready database with SQLAlchemy ORM
- **Database Migrations** - Alembic for version-controlled schema management
- **RESTful API** - Clean, documented endpoints for frontend integration
- **OAuth Support** - Wikimedia OAuth 1.0a integration for Toolforge deployment


## Project Structure

```
backend/
├── app/                          # Main application package
│   ├── __init__.py              # Application factory
│   ├── config.py                # Configuration management
│   ├── database.py              # SQLAlchemy database instance
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base_model.py        # Base model with common methods
│   │   ├── user.py              # User model
│   │   ├── contest.py           # Contest model
│   │   └── submission.py        # Submission model
│   ├── routes/                  # API route blueprints
│   │   ├── user_routes.py       # User management endpoints
│   │   ├── contest_routes.py    # Contest management endpoints
│   │   └── submission_routes.py # Submission management endpoints
│   ├── middleware/              # Middleware functions
│   │   └── auth.py              # JWT and permission handling
│   └── utils/                   # Utility functions
│       └── __init__.py
├── alembic/                     # Database migration environment
│   ├── env.py                   # Alembic environment configuration
│   ├── versions/                # Migration version files
│   ├── script.py.mako          # Migration template
│   └── README.md
├── scripts/                     # Utility scripts
│   ├── init_db.py               # Database initialization
│   ├── backfill_article_info.py # Backfill article metadata
│   └── get_article_metadata.py  # Fetch article metadata
├── toolforge/                   # Toolforge deployment files
│   ├── toolforge_app.py
│   ├── toolforge_config.toml
│   ├── toolforge_index.html
│   ├── toolforge_login.html
│   └── toolforge_requirements.txt
├── tests/                       # Test files (pytest)
├── logs/                        # Application logs
├── docs/                        # Documentation
│   ├── ALEMBIC_USAGE_GUIDE.md
│   ├── ALEMBIC_MODEL_COMPATIBILITY.md
│   ├── ALEMBIC_SETUP_VERIFICATION.md
│   └── SETUP_NEW_DATABASE.md
├── main.py                      # Application entry point
├── alembic.ini                  # Alembic configuration
├── Makefile                     # Common commands
├── requirements.txt             # Python dependencies
├── setup.py                     # Setup script
├── deploy_to_toolforge.sh       # Deployment script
└── README.md                    # This file
```

### Architecture Highlights

- **Application Factory Pattern** - Enables multiple app instances with different configurations
- **Blueprint Organization** - Routes organized by domain (users, contests, submissions)
- **Layered Configuration** - Separate configs for development, testing, and production
- **Centralized Database** - Single SQLAlchemy instance with base model inheritance

## Prerequisites

Ensure you have the following installed:

- **Python** 3.8 or higher
- **MySQL** 5.7 or higher (or SQLite for development)
- **pip** Python package manager

## Installation

### 1. Navigate to the Backend Directory

```bash
cd backend
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

**Activate the virtual environment:**

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up MySQL Database

Run the following SQL commands to create the database and user:

```sql
CREATE DATABASE wikicontest;
CREATE USER 'wikicontest_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON wikicontest.* TO 'wikicontest_user'@'localhost';
FLUSH PRIVILEGES;
```

## Configuration

### Environment Variables

Create a `.env` file in the backend directory with the following variables:

```env
# Database Configuration
DATABASE_URL=mysql+pymysql://wikicontest_user:your_password@localhost/wikicontest

# Security Keys
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# Environment
FLASK_ENV=development
```

### Database Schema Setup

This project uses **Alembic exclusively** for database schema management. All tables are created automatically through migrations.

**Apply migrations to create the database schema:**

```bash
# Apply all migrations
python -m alembic upgrade head

# Verify migrations were applied
python -m alembic current
```

**Important:** Do not use `init_db.py` or any other scripts to create tables manually. Alembic handles all schema changes.

For detailed setup instructions, see [`docs/SETUP_NEW_DATABASE.md`](docs/SETUP_NEW_DATABASE.md).

## Running the Application

### Using Makefile (Recommended)

The Makefile provides convenient commands for common tasks:

```bash
# Run the development server
make run
# or
make dev

# View all available commands
make help
```

### Manual Running

**Start the Flask development server:**

```bash
python main.py
```

**Or use Flask directly:**

```bash
flask run
```

**The API will be available at:**
- Base URL: `http://localhost:5000`
- API endpoints: `http://localhost:5000/api/`

### Production Mode

For production environments, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:app"
```

## API Documentation

### User Management Endpoints

| Method | Endpoint                   | Description            | Auth Required |
|--------|----------------------------|------------------------|---------------|
| POST   | `/api/user/register`       | Register a new user    | No            |
| POST   | `/api/user/login`          | Login user             | No            |
| POST   | `/api/user/logout`         | Logout user            | Yes           |
| GET    | `/api/user/dashboard`      | Get user dashboard     | Yes           |
| GET    | `/api/user/all`            | Get all users          | Admin only    |
| GET    | `/api/user/profile`        | Get user profile       | Yes           |
| PUT    | `/api/user/profile`        | Update user profile    | Yes           |
| GET    | `/api/user/oauth/initiate` | Initiate OAuth login   | No            |
| GET    | `/api/user/oauth/callback` | OAuth callback handler | No            |
   
### Contest Management Endpoints   
   
| Method | Endpoint                        | Description             | Auth Required      |
|--------|---------------------------------|-------------------------|--------------------|
| GET    | `/api/contest`                  | Get all contests        | No                 |
| POST   | `/api/contest`                  | Create a new contest    | Yes                |
| GET    | `/api/contest/<id>`             | Get contest by ID       | No                 |
| PUT    | `/api/contest/<id>`             | Update contest          | Creator/Admin      |
| DELETE | `/api/contest/<id>`             | Delete contest          | Creator/Admin      |
| GET    | `/api/contest/<id>/leaderboard` | Get contest leaderboard | No                 |
| POST   | `/api/contest/<id>/submit`      | Submit to contest       | Yes                |
| GET    | `/api/contest/<id>/submissions` | Get contest submissions | Creator/Jury/Admin |

### Submission Management Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET    | `/api/submission` | Get all submissions | Admin only |
| GET    | `/api/submission/<id>` | Get submission by ID | Owner/Jury/Admin |
| PUT    | `/api/submission/<id>` | Update submission status | Jury/Admin |
| GET    | `/api/submission/user/<user_id>` | Get user submissions | Owner/Admin |
| GET    | `/api/submission/contest/<contest_id>` | Get contest submissions | Creator/Jury/Admin |
| GET    | `/api/submission/pending` | Get pending submissions | Jury/Admin |
| GET    | `/api/submission/stats` | Get submission statistics | Admin only |
| POST   | `/api/submission/contest/<contest_id>/refresh-metadata` | Refresh submission metadata | Creator/Admin |

### Utility Endpoints

| Method | Endpoint                      | Description                            |
|--------|-------------------------------|----------------------------------------|
| GET    | `/api/cookie`                 | Check authentication status            |
| GET    | `/api/health`                 | Health check                           |
| GET    | `/api/oauth/config`           | OAuth configuration check              |
| GET    | `/api/mediawiki/article-info` | Fetch article info from MediaWiki API  |
| GET    | `/api/mediawiki/preview`      | Get article preview from MediaWiki API |


## Database Management

### Database Models

#### User Model
- `id` - Primary key
- `username` - Unique username
- `email` - Unique email address
- `role` - User role (admin, user)
- `password` - Hashed password
- `score` - Total accumulated score
- `created_at` - Creation timestamp

#### Contest Model
- `id` - Primary key
- `name` - Contest name
- `project_name` - Associated project name
- `created_by` - Creator username (foreign key)
- `description` - Contest description
- `start_date` - Contest start date
- `end_date` - Contest end date
- `rules` - JSON rules object
- `marks_setting_accepted` - Points for accepted submissions
- `marks_setting_rejected` - Points for rejected submissions
- `jury_members` - Comma-separated jury usernames
- `allowed_submission_type` - Type of submissions allowed
- `created_at` - Creation timestamp

#### Submission Model
- `id` - Primary key
- `user_id` - User ID (foreign key)
- `contest_id` - Contest ID (foreign key)
- `article_title` - Article title
- `article_link` - Article URL
- `status` - Submission status (pending, accepted, rejected)
- `score` - Awarded score
- `submitted_at` - Submission timestamp
- `article_author` - Author from latest revision
- `article_created_at` - Article creation date
- `article_word_count` - Article size in bytes
- `article_page_id` - MediaWiki page ID
- `article_size_at_start` - Article size at contest start
- `article_expansion_bytes` - Bytes added since contest start

### Alembic Migrations

The application uses **Alembic** for database migrations, providing robust schema versioning and management.

#### Common Alembic Commands

```bash
# Create a new migration (after modifying models)
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback to previous version
alembic downgrade -1

# View current migration status
alembic current

# View migration history
alembic history
```

#### How Alembic Works

1. **Migration Files** - Python files in `alembic/versions/` define schema changes
2. **Version Tracking** - `alembic_version` table stores current database version
3. **Migration Chain** - Each migration links to the previous one (linked list structure)
4. **Upgrade/Downgrade** - Each migration has functions to apply and reverse changes

#### Typical Migration Workflow

1. Modify your models in `app/models/`
2. Generate migration: `make migrate-create MSG="Add new field"`
3. Review the generated file in `alembic/versions/`
4. Apply migration: `make db-upgrade`
5. Test your application
6. Commit migration file to version control

**For detailed documentation:**
- [`docs/ALEMBIC_USAGE_GUIDE.md`](docs/ALEMBIC_USAGE_GUIDE.md) - Complete usage guide
- [`docs/ALEMBIC_MODEL_COMPATIBILITY.md`](docs/ALEMBIC_MODEL_COMPATIBILITY.md) - Model compatibility
- [`docs/ALEMBIC_SETUP_VERIFICATION.md`](docs/ALEMBIC_SETUP_VERIFICATION.md) - Setup verification

### Utility Scripts

Located in the `scripts/` directory:

#### init_db.py
Initialize or reset the database:

```bash
# Create tables
python scripts/init_db.py

# Reset database
python scripts/init_db.py reset
```

#### backfill_article_info.py
Backfill article metadata for existing submissions:

```bash
python scripts/backfill_article_info.py
```

#### get_article_metadata.py
Fetch article metadata from MediaWiki API:

```bash
python scripts/get_article_metadata.py "https://en.wikipedia.org/wiki/Article"
```

## Authentication & Authorization

The application implements JWT-based authentication with comprehensive security features.

### Authentication Features

- **JWT Tokens** - Stored in HTTP-only cookies for enhanced security
- **CSRF Protection** - Enabled for cookie-based authentication
- **Role-Based Access** - Admin, creator, jury, and participant roles
- **Permission System** - Contextual permissions based on contest relationships
- **Middleware** - Automatic authentication and authorization checks
- **OAuth 1.0a** - Wikimedia OAuth support for Toolforge deployment

### Middleware Functions

Located in `app/middleware/auth.py`:

- `require_auth` - Require valid JWT token
- `require_role` - Require specific user role
- `require_submission_permission` - Require permission for submission access
- `validate_json_data` - Validate JSON request data
- `handle_errors` - Error handling decorator

## Development

### Running Tests

**Using Makefile:**

```bash
# Run tests
make test

# Run tests with coverage report
make test-coverage
```

**Direct pytest commands:**

```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests
pytest
```

### Code Style

The codebase follows Python PEP 8 standards with comprehensive comments and documentation. Linting is configured via `.pylintrc`.

### Best Practices

When contributing:
- Follow PEP 8 style guidelines
- Add comprehensive comments and docstrings
- Write tests for new features
- Update documentation for API changes
- Use the modular structure (models, routes, middleware, utils)
- Keep files focused and under 200 lines when possible

## Production Deployment

### Environment Configuration

Set production environment variables in `.env`:

```env
# Environment
FLASK_ENV=production
FLASK_DEBUG=False

# Database
DATABASE_URL=mysql+pymysql://user:pass@host:port/db

# Security Keys (use strong, unique values)
SECRET_KEY=your_production_secret_key
JWT_SECRET_KEY=your_production_jwt_secret

# JWT Cookie Settings
JWT_COOKIE_SECURE=True
JWT_COOKIE_SAMESITE=None
```

### Using Gunicorn

Deploy with Gunicorn for production:

```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 worker processes
gunicorn -w 4 -b 0.0.0.0:5000 "app:app"
```

### Using Nginx Reverse Proxy

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Toolforge Deployment

For Wikimedia Toolforge deployment:
- See the `toolforge/` directory for deployment files
- Use the `deploy_to_toolforge.sh` script for automated deployment

## Project Architecture

### Application Factory Pattern

The application uses Flask's application factory pattern (`app/__init__.py`), which allows:
- Multiple app instances with different configurations
- Easier testing with isolated app contexts
- Better code organization

### Blueprint Organization

Routes are organized into blueprints:
- `user_bp`: User management endpoints
- `contest_bp`: Contest management endpoints
- `submission_bp`: Submission management endpoints

### Configuration Management

Configuration is managed in `app/config.py` with separate classes for:
- `DevelopmentConfig`: Development settings
- `TestingConfig`: Test settings
- `ProductionConfig`: Production settings

### Database Layer

- **Models**: SQLAlchemy ORM models in `app/models/`
- **Base Model**: Common functionality in `app/models/base_model.py`
- **Database Instance**: Centralized in `app/database.py`

## Troubleshooting

### Common Issues

#### Database Connection Error

**Symptoms:** Unable to connect to MySQL database

**Solutions:**
- Verify MySQL service is running
- Check database credentials in `.env`
- Ensure database exists
- Verify SQLAlchemy connection string format

#### Import Errors

**Symptoms:** `ModuleNotFoundError` or import failures

**Solutions:**
- Activate virtual environment
- Install all dependencies: `pip install -r requirements.txt`
- Ensure you're running from the backend directory
- Verify `app/` package structure is correct
- Check that all imports use `app.` prefix (e.g., `from app.models import User`)

#### JWT Token Issues

**Symptoms:** Authentication failures, token validation errors

**Solutions:**
- Check `JWT_SECRET_KEY` in environment variables
- Ensure cookies are enabled in frontend
- Verify CORS settings allow credentials
- Check cookie domain and path settings

#### Permission Errors

**Symptoms:** 403 Forbidden responses

**Solutions:**
- Verify user roles in database
- Check contest relationships for contextual permissions
- Review middleware decorators in routes

#### Module Not Found Errors

**Symptoms:** Python cannot find application modules

**Solutions:**
- Ensure all imports use `app.` prefix
- Check that `app/__init__.py` exists and is properly configured
- Verify Python path includes the backend directory

### Logging

Application logs are written to console by default.

**For production:**
- Configure logging in `app/__init__.py`
- Set up log rotation
- Use appropriate log levels (INFO, WARNING, ERROR)
- Log files are stored in the `logs/` directory (created automatically)

## Contributing

We welcome contributions to the WikiEval platform!

### Guidelines

1. **Code Style** - Follow PEP 8 style guidelines
2. **Documentation** - Add comprehensive comments and docstrings
3. **Testing** - Write tests for new features
4. **API Changes** - Update documentation when modifying endpoints
5. **Architecture** - Use the modular structure (models, routes, middleware, utils)
6. **File Size** - Keep files focused and under 200 lines when possible


## License

This project is part of the WikiEval platform.

## Additional Resources

- [Alembic Usage Guide](docs/ALEMBIC_USAGE_GUIDE.md)
- [Database Setup Guide](docs/SETUP_NEW_DATABASE.md)
- [Model Compatibility Guide](docs/ALEMBIC_MODEL_COMPATIBILITY.md)
- [Setup Verification Checklist](docs/ALEMBIC_SETUP_VERIFICATION.md)