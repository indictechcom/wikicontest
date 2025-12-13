# WikiContest Flask Backend

A Python Flask backend application for the WikiContest platform, converted from Node.js/Express to Python/Flask with SQLAlchemy ORM and MySQL database.

## Features

- **User Management**: Registration, login, logout, profile management
- **Contest Management**: Create, view, and manage contests
- **Submission System**: Submit articles to contests, review submissions
- **Role-Based Access Control**: Admin, creator, jury, and participant roles
- **JWT Authentication**: Secure token-based authentication
- **MySQL Database**: Robust database with SQLAlchemy ORM
- **RESTful API**: Clean API endpoints for frontend integration

## Project Structure

The project follows Flask best practices with a modular, organized structure:

```
backend/
├── app/                          # Main application package
│   ├── __init__.py              # Application factory (Flask app initialization)
│   ├── config.py                # Configuration management (dev/test/prod)
│   ├── database.py              # SQLAlchemy database instance
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base_model.py        # Base model with common methods
│   │   ├── user.py              # User model
│   │   ├── contest.py           # Contest model
│   │   └── submission.py        # Submission model
│   ├── routes/                  # API route blueprints
│   │   ├── user_routes.py       # User management routes
│   │   ├── contest_routes.py    # Contest management routes
│   │   └── submission_routes.py  # Submission management routes
│   ├── middleware/              # Middleware functions
│   │   └── auth.py              # JWT and permission handling
│   └── utils/                   # Utility functions
│       └── __init__.py          # Utility functions module
├── migrations/                  # Database migration scripts
│   ├── README.md
│   ├── add_article_metadata_to_submissions.py
│   ├── add_expansion_bytes_to_submissions.py
│   └── add_size_at_start_to_submissions.py
├── scripts/                     # Utility scripts
│   ├── init_db.py               # Database initialization
│   ├── backfill_article_info.py # Backfill article metadata
│   └── get_article_metadata.py  # Fetch article metadata utility
├── toolforge/                   # Toolforge deployment files
│   ├── toolforge_app.py         # Toolforge-specific Flask app
│   ├── toolforge_config.toml    # Toolforge configuration
│   ├── toolforge_index.html     # Toolforge index page
│   ├── toolforge_login.html     # Toolforge login page
│   └── toolforge_requirements.txt
├── tests/                       # Test files (pytest)
├── logs/                        # Application logs
├── main.py                      # Main entry point for running the app
├── requirements.txt             # Python dependencies
├── setup.py                     # Setup script
├── deploy_to_toolforge.sh       # Deployment script
└── README.md                    # This file
```

## Prerequisites

- Python 3.8 or higher
- MySQL 5.7 or higher (or SQLite for development)
- pip (Python package manager)

## Installation

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   
   # On Windows
   .venv\Scripts\activate
   
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up MySQL database:**
   ```sql
   CREATE DATABASE wikicontest;
   CREATE USER 'wikicontest_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON wikicontest.* TO 'wikicontest_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

5. **Configure environment variables:**
   Create a `.env` file in the backend directory:
   ```env
   DATABASE_URL=mysql+pymysql://wikicontest_user:your_password@localhost/wikicontest
   SECRET_KEY=your_secret_key_here
   JWT_SECRET_KEY=your_jwt_secret_key_here
   FLASK_ENV=development
   ```

6. **Initialize the database:**
   ```bash
   # Create tables only
   python scripts/init_db.py
   
   # Reset database (drops all tables and recreates)
   python scripts/init_db.py reset
   ```

## Running the Application

### Development Mode

1. **Start the Flask development server:**
   ```bash
   python main.py
   ```
   
   Or using Flask directly:
   ```bash
   flask run
   ```

2. **The API will be available at:**
   - Base URL: `http://localhost:5000`
   - API endpoints: `http://localhost:5000/api/`

### Production Mode

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:app"
```

## API Endpoints

### User Management
- `POST /api/user/register` - Register a new user
- `POST /api/user/login` - Login user
- `POST /api/user/logout` - Logout user
- `GET /api/user/dashboard` - Get user dashboard
- `GET /api/user/all` - Get all users (admin only)
- `GET /api/user/profile` - Get user profile
- `PUT /api/user/profile` - Update user profile
- `GET /api/user/oauth/initiate` - Initiate OAuth login
- `GET /api/user/oauth/callback` - OAuth callback handler

### Contest Management
- `GET /api/contest` - Get all contests
- `POST /api/contest` - Create a new contest
- `GET /api/contest/<id>` - Get contest by ID
- `PUT /api/contest/<id>` - Update contest
- `DELETE /api/contest/<id>` - Delete contest
- `GET /api/contest/<id>/leaderboard` - Get contest leaderboard
- `POST /api/contest/<id>/submit` - Submit to contest
- `GET /api/contest/<id>/submissions` - Get contest submissions

### Submission Management
- `GET /api/submission` - Get all submissions (admin only)
- `GET /api/submission/<id>` - Get submission by ID
- `PUT /api/submission/<id>` - Update submission status
- `GET /api/submission/user/<user_id>` - Get user submissions
- `GET /api/submission/contest/<contest_id>` - Get contest submissions
- `GET /api/submission/pending` - Get pending submissions
- `GET /api/submission/stats` - Get submission statistics
- `POST /api/submission/contest/<contest_id>/refresh-metadata` - Refresh submission metadata

### Utility Endpoints
- `GET /api/cookie` - Check authentication status
- `GET /api/health` - Health check
- `GET /api/oauth/config` - OAuth configuration check
- `GET /api/mediawiki/article-info` - Fetch article info from MediaWiki API
- `GET /api/mediawiki/preview` - Get article preview from MediaWiki API

## Database Models

### User Model
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email address
- `role`: User role (admin, user)
- `password`: Hashed password
- `score`: Total accumulated score
- `created_at`: Creation timestamp

### Contest Model
- `id`: Primary key
- `name`: Contest name
- `project_name`: Associated project name
- `created_by`: Creator username (foreign key)
- `description`: Contest description
- `start_date`: Contest start date
- `end_date`: Contest end date
- `rules`: JSON rules object
- `marks_setting_accepted`: Points for accepted submissions
- `marks_setting_rejected`: Points for rejected submissions
- `jury_members`: Comma-separated jury usernames
- `allowed_submission_type`: Type of submissions allowed
- `created_at`: Creation timestamp

### Submission Model
- `id`: Primary key
- `user_id`: User ID (foreign key)
- `contest_id`: Contest ID (foreign key)
- `article_title`: Article title
- `article_link`: Article URL
- `status`: Submission status (pending, accepted, rejected)
- `score`: Awarded score
- `submitted_at`: Submission timestamp
- `article_author`: Author from latest revision
- `article_created_at`: Article creation date
- `article_word_count`: Article size in bytes
- `article_page_id`: MediaWiki page ID
- `article_size_at_start`: Article size at contest start
- `article_expansion_bytes`: Bytes added since contest start

## Authentication & Authorization

The application uses JWT (JSON Web Tokens) for authentication with the following features:

- **JWT Tokens**: Stored in HTTP-only cookies for security
- **CSRF Protection**: Enabled for cookie-based authentication
- **Role-Based Access**: Admin, creator, jury, and participant roles
- **Permission System**: Contextual permissions based on contest relationships
- **Middleware**: Automatic authentication and authorization checks
- **OAuth 1.0a**: Wikimedia OAuth support for Toolforge deployment

### Middleware Functions

Located in `app/middleware/auth.py`:
- `require_auth`: Require valid JWT token
- `require_role`: Require specific user role
- `require_submission_permission`: Require permission for submission access
- `validate_json_data`: Validate JSON request data
- `handle_errors`: Error handling decorator

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests
pytest
```

### Code Style
The code follows Python PEP 8 standards with comprehensive comments and documentation. Linting is configured via `.pylintrc`.

### Database Migrations

The application includes custom migration scripts in the `migrations/` directory. Migrations are automatically run on application startup, or can be run manually:

```bash
# Run a specific migration
python migrations/add_article_metadata_to_submissions.py
```

For production deployments, consider using Flask-Migrate (Alembic) for more robust database schema versioning.

### Utility Scripts

Scripts in the `scripts/` directory:

- **init_db.py**: Initialize or reset the database
  ```bash
  python scripts/init_db.py          # Create tables
  python scripts/init_db.py reset    # Reset database
  ```

- **backfill_article_info.py**: Backfill article metadata for existing submissions
  ```bash
  python scripts/backfill_article_info.py
  ```

- **get_article_metadata.py**: Fetch article metadata from MediaWiki API
  ```bash
  python scripts/get_article_metadata.py "https://en.wikipedia.org/wiki/Article"
  ```

## Production Deployment

### Environment Configuration

Set production environment variables:
```env
FLASK_ENV=production
FLASK_DEBUG=False
DATABASE_URL=mysql+pymysql://user:pass@host:port/db
SECRET_KEY=your_production_secret_key
JWT_SECRET_KEY=your_production_jwt_secret
JWT_COOKIE_SECURE=True
JWT_COOKIE_SAMESITE=None
```

### Using Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:app"
```

### Using Nginx Reverse Proxy

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

For Wikimedia Toolforge deployment, see the `toolforge/` directory and `deploy_to_toolforge.sh` script.

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

1. **Database Connection Error:**
   - Check MySQL service is running
   - Verify database credentials in `.env`
   - Ensure database exists
   - Check SQLAlchemy connection string format

2. **Import Errors:**
   - Activate virtual environment
   - Install all dependencies: `pip install -r requirements.txt`
   - Ensure you're running from the backend directory
   - Check that `app/` package structure is correct

3. **JWT Token Issues:**
   - Check `JWT_SECRET_KEY` in environment variables
   - Ensure cookies are enabled in frontend
   - Verify CORS settings allow credentials
   - Check cookie domain and path settings

4. **Permission Errors:**
   - Verify user roles in database
   - Check contest relationships for contextual permissions
   - Review middleware decorators in routes

5. **Module Not Found Errors:**
   - Ensure all imports use `app.` prefix (e.g., `from app.models import User`)
   - Check that `app/__init__.py` exists and is properly configured
   - Verify Python path includes the backend directory

### Logs

Application logs are written to console by default. For production:
- Configure logging in `app/__init__.py`
- Set up log rotation
- Use proper log levels (INFO, WARNING, ERROR)

Log files are stored in the `logs/` directory (created automatically).

## Contributing

1. Follow PEP 8 style guidelines
2. Add comprehensive comments and docstrings
3. Write tests for new features
4. Update documentation for API changes
5. Use the modular structure (models, routes, middleware, utils)
6. Keep files focused and under 200 lines when possible

## License

This project is part of the WikiContest platform.
