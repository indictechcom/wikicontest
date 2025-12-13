# WikiContest Backend Architecture

This document describes the architecture and design decisions of the WikiContest Flask backend.

## Overview

The WikiContest backend is built using Flask with a modular, package-based structure following Flask best practices. The application uses SQLAlchemy for database operations, JWT for authentication, and follows the application factory pattern.

## Directory Structure

```
backend/
├── app/                    # Main application package
│   ├── __init__.py        # Application factory
│   ├── config.py          # Configuration classes
│   ├── database.py        # SQLAlchemy instance
│   ├── models/            # Database models
│   ├── routes/            # API route blueprints
│   ├── middleware/        # Middleware functions
│   └── utils/             # Utility functions
├── migrations/            # Database migration scripts
├── scripts/               # Utility scripts
├── toolforge/             # Toolforge deployment files
├── tests/                 # Test files
└── logs/                  # Application logs
```

## Application Factory Pattern

The application uses Flask's application factory pattern, defined in `app/__init__.py`. This pattern provides:

- **Multiple Instances**: Create multiple app instances with different configurations
- **Testing**: Easier testing with isolated app contexts
- **Flexibility**: Configure the app differently for different environments

### Usage

```python
from app import create_app

app = create_app()
```

## Configuration Management

Configuration is managed in `app/config.py` with three configuration classes:

- **Config**: Base configuration with common settings
- **DevelopmentConfig**: Development environment settings
- **TestingConfig**: Testing environment settings
- **ProductionConfig**: Production environment settings

Configuration is loaded from environment variables, with sensible defaults for development.

## Database Layer

### SQLAlchemy Setup

The database instance is created in `app/database.py` and initialized with the Flask app:

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
```

### Models

All models inherit from `BaseModel` (defined in `app/models/base_model.py`), which provides:
- `save()`: Save instance to database
- `delete()`: Delete instance from database

Models are organized by domain:
- `User`: User accounts and authentication
- `Contest`: Contest information
- `Submission`: User submissions to contests

### Relationships

Models define relationships using SQLAlchemy's `relationship()`:
- User → Contests (one-to-many)
- User → Submissions (one-to-many)
- Contest → Submissions (one-to-many)

## Routing Architecture

### Blueprints

Routes are organized into blueprints for modularity:

- **user_bp**: User management (`/api/user/*`)
- **contest_bp**: Contest management (`/api/contest/*`)
- **submission_bp**: Submission management (`/api/submission/*`)

### Route Registration

Blueprints are registered in `app/__init__.py`:

```python
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(contest_bp, url_prefix='/api/contest')
app.register_blueprint(submission_bp, url_prefix='/api/submission')
```

## Middleware

Middleware functions are defined in `app/middleware/auth.py`:

- **require_auth**: Require valid JWT token
- **require_role**: Require specific user role (admin, etc.)
- **require_submission_permission**: Contextual permission checking
- **validate_json_data**: Validate JSON request payload
- **handle_errors**: Error handling decorator

### Usage Example

```python
from app.middleware.auth import require_auth, require_role

@route('/admin')
@require_auth
@require_role('admin')
def admin_route():
    pass
```

## Authentication & Authorization

### JWT Authentication

The application uses Flask-JWT-Extended for JWT authentication:
- Tokens stored in HTTP-only cookies
- CSRF protection enabled
- 24-hour token expiration

### Role-Based Access Control

Roles:
- **admin**: Full system access
- **user**: Standard user access
- **creator**: Contest creator permissions
- **jury**: Jury member permissions (contextual)

### Permission System

Permissions are contextual based on:
- User role
- Contest relationships (creator, jury member)
- Submission ownership

## Error Handling

### Global Error Handlers

Defined in `app/__init__.py`:
- `404`: Not Found handler
- `500`: Internal Server Error handler

### Route-Level Error Handling

Routes use the `@handle_errors` decorator for consistent error handling.

## Database Migrations

### Custom Migration Scripts

Migrations are custom Python scripts in `migrations/`:
- Check if columns exist before adding
- Use SQLAlchemy's `text()` for raw SQL
- Idempotent (safe to run multiple times)

### Automatic Migrations

Migrations run automatically on application startup via `migrate_database()` function.

## Utility Functions

Utility functions are organized in `app/utils/`:
- MediaWiki API helpers
- URL parsing utilities
- Date/time validation
- Permission checking utilities

## Testing Structure

Tests should be organized in `tests/` directory:
- Unit tests for models
- Integration tests for routes
- Test fixtures and helpers

## Logging

Logging is configured in the application factory:
- Console output for development
- File logging for production (in `logs/` directory)
- Configurable log levels

## Security Considerations

### Authentication
- JWT tokens in HTTP-only cookies
- CSRF protection
- Secure cookie settings for production

### Database
- Parameterized queries (SQLAlchemy ORM)
- Connection pooling
- SQL injection prevention

### Input Validation
- JSON schema validation
- Type checking
- Sanitization where needed

## Performance Optimizations

### Database
- Connection pooling
- Query optimization
- Indexed columns

### Caching
- Session caching
- Query result caching (where applicable)

## Deployment

### Development
- Flask development server
- Debug mode enabled
- Hot reload

### Production
- Gunicorn WSGI server
- Multiple workers
- Reverse proxy (Nginx)
- Environment-specific configuration

### Toolforge
- Specialized deployment in `toolforge/` directory
- OAuth 1.0a integration
- Toolforge-specific configuration

## Code Organization Principles

1. **Separation of Concerns**: Models, routes, middleware, and utilities are separated
2. **DRY (Don't Repeat Yourself)**: Common functionality in base classes and utilities
3. **Single Responsibility**: Each module has a clear, single purpose
4. **Modularity**: Blueprints and packages for easy extension
5. **Testability**: Application factory pattern enables easy testing

## Future Improvements

- Consider Flask-Migrate (Alembic) for database migrations
- Add comprehensive test coverage
- Implement API rate limiting
- Add request/response logging middleware
- Consider adding a service layer for business logic
- Implement caching layer (Redis)
- Add API documentation (Swagger/OpenAPI)

