# WikiEval Project Documentation

Complete technical documentation for the WikiEval platform – a web-based system for organizing and managing Wikipedia editing contests (Edit-a-thons).



## Project Overview

**WikiEval** is a platform that enables users to create, participate in, and manage Wikipedia editing contests. It provides comprehensive features for contest management, submission tracking, leaderboards, and role-based access control.

### Key Capabilities

1. **Contest Management** – Create, configure, and manage Wikipedia editing contests
2. **User Authentication** – Secure login/logout with JWT tokens and role-based access control
3. **Submission Tracking** – Submit and review Wikipedia edits for contests
4. **Leaderboards** – Real-time ranking of participants based on edit quality and quantity
5. **Admin Controls** – Contest creators and jury members can review submissions and assign scores
6. **Toolforge Integration** – Deployable on Wikimedia's Toolforge platform with OAuth authentication



## Technology Stack

### Backend
- **Framework:** Python Flask (application factory pattern)
- **ORM:** SQLAlchemy
- **Authentication:** JWT (HTTP-only cookies) + CSRF protection via `X-CSRF-TOKEN` header
- **OAuth:** OAuth 1.0a for Wikimedia/Toolforge integration

### Frontend
- **Technologies:** HTML5, CSS3, Vanilla JavaScript
- **Alternative:** Vue.js 3 (modern implementation)

### Database
- **Production:** MySQL (recommended for Toolforge)
- **Development:** MySQL (default) or SQLite (quick testing)

### Deployment
- **Local:** Flask development server
- **Production:** Wikimedia Toolforge platform



## Project Structure
```
wikicontest/
├── backend/                        # Flask backend application
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── user.py                 # User model and database operations
│   │   ├── contest.py              # Contest model and database operations
│   │   └── submission.py           # Submission model and database operations
│   ├── routes/                     # API route handlers
│   │   ├── user_routes.py          # User-related API endpoints
│   │   ├── contest_routes.py       # Contest-related API endpoints
│   │   └── submission_routes.py    # Submission-related API endpoints
│   ├── middleware/                 # Authentication and authorization
│   │   └── auth.py                 # JWT middleware and role-based access
│   ├── app.py                      # App factory + blueprint registration
│   ├── config.py                   # Centralized configuration
│   ├── utils.py                    # Reusable helpers (responses, validation)
│   ├── database.py                 # SQLAlchemy initialization
│   ├── requirements.txt            # Python dependencies
│   ├── init_db.py                  # Database initialization script
│   ├── setup.py                    # Environment setup helper
│   ├── toolforge_app.py            # Toolforge-specific Flask application
│   ├── toolforge_config.toml       # Toolforge configuration
│   ├── toolforge_requirements.txt  # Toolforge dependencies
│   ├── deploy_to_toolforge.sh      # Toolforge deployment script
│   └── TOOLFORGE_DEPLOYMENT.md     # Toolforge deployment guide
├── frontend/                       # Frontend application
│   ├── index.html                  # Main HTML page
│   └── app.js                      # Frontend JavaScript logic
└── README.md                       # Quick start and setup guide
```



## Database Configuration

### Local Development

**Default Database:** MySQL (recommended)
```env
DATABASE_URL=mysql+pymysql://<user>:<password>@localhost/wikicontest
```

**Alternative:** SQLite for quick testing
```env
DATABASE_URL=sqlite:///wikicontest.db
```

### Toolforge Production

**Database:** MySQL (required for production)
```toml
SQLALCHEMY_DATABASE_URI = "mysql://username:password@tools-db/database_name"
```

- **Host:** `tools-db` (Toolforge's MySQL server)
- **Purpose:** Production-grade performance and reliability



## Database Schema

### User Model (`backend/models/user.py`)
```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Purpose:** Manages user accounts, authentication, and role-based permissions.

### Contest Model (`backend/models/contest.py`)
```python
class Contest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    allowed_submission_type = db.Column(db.String(20), default="both")
```

**Purpose:** Manages contest information, timing, and creator relationships.

### Submission Model (`backend/models/submission.py`)
```python
class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    article_title = db.Column(db.String(200), nullable=False)
    edit_summary = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    score = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Purpose:** Tracks user submissions, scores, and approval status for each contest.



## Backend Architecture

### Core Application Files

#### `backend/app.py` – Application Factory

The main Flask application entry point using the factory pattern.

**Features:**
- Centralized configuration via `config.py`
- SQLAlchemy ORM initialization
- JWT authentication with HTTP-only cookies
- CSRF protection via `X-CSRF-TOKEN` header
- CORS configuration
- Blueprint registration (`user`, `contest`, `submission`)
- Health check endpoints and error handlers

#### `backend/toolforge_app.py` – Toolforge Production Server

Toolforge-specific Flask application for production deployment.

**Features:**
- OAuth 1.0a authentication with Wikimedia
- TOML configuration file support
- Toolforge-specific routing
- Jinja2 template rendering
- Production-ready error handling



## API Routes

**Base URL:** `/api`

### User Routes (`backend/routes/user_routes.py`)

#### `POST /api/user/register` (Public)
Register a new user account.

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "role": "string (optional)"
}
```

**Response:** `201 Created`
```json
{
  "message": "User registered successfully",
  "userId": 1,
  "username": "string"
}
```

#### `POST /api/user/login` (Public)
Authenticate and receive JWT token in HTTP-only cookie.

**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "message": "Login successful",
  "userId": 1,
  "username": "string"
}
```

Sets JWT cookie and CSRF token cookie.

#### `POST /api/user/logout` (Authenticated + CSRF)
Clear authentication cookies and log out.

**Headers Required:**
```
X-CSRF-TOKEN: <value from csrf_access_token cookie>
```

**Response:** `200 OK`
```json
{
  "message": "Logged out successfully"
}
```

#### `GET /api/user/dashboard` (Authenticated)
Retrieve user dashboard data.

**Response:** `200 OK`
```json
{
  "totals": { ... },
  "perContestScores": [ ... ],
  "submissions": [ ... ],
  "createdContests": [ ... ],
  "juryContests": [ ... ]
}
```

#### `GET /api/user/all` (Admin Only)
Retrieve list of all users.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "username": "string",
    "email": "string",
    "role": "string"
  }
]
```

#### `GET /api/user/profile` (Authenticated)
Retrieve current user profile.

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "string",
  "email": "string",
  "role": "string"
}
```

#### `PUT /api/user/profile` (Authenticated)
Update current user profile.

**Request Body:**
```json
{
  "username": "string",
  "email": "string"
}
```

**Response:** `200 OK`
```json
{
  "message": "Profile updated successfully"
}
```

### Contest Routes (`backend/routes/contest_routes.py`)

#### `GET /api/contest/` (Public)
Retrieve all contests categorized by status.

**Response:** `200 OK`
```json
{
  "current": [ ... ],
  "upcoming": [ ... ],
  "past": [ ... ]
}
```

#### `POST /api/contest/` (Authenticated)
Create a new contest.

**Request Body (Required):**
```json
{
  "name": "string",
  "project_name": "string",
  "jury_members": ["username1", "username2"]
}
```

**Request Body (Optional):**
```json
{
  "code_link": "string",
  "description": "string",
  "start_date": "ISO 8601 datetime",
  "end_date": "ISO 8601 datetime",
  "rules": "string",
  "marks_setting_accepted": 10,
  "marks_setting_rejected": 0
}
```

**Response:** `201 Created`
```json
{
  "message": "Contest created successfully",
  "contestId": 1
}
```

#### `GET /api/contest/<id>` (Public)
Retrieve details for a specific contest.

**Response:** `200 OK`
```json
{
  "id": 1,
  "title": "string",
  "description": "string",
  "start_date": "ISO 8601 datetime",
  "end_date": "ISO 8601 datetime",
  "created_by": 1
}
```

#### `GET /api/contest/<id>/leaderboard` (Public)
Retrieve leaderboard for a specific contest.

**Response:** `200 OK`
```json
[
  {
    "rank": 1,
    "username": "string",
    "score": 100,
    "submissions": 10
  }
]
```

#### `DELETE /api/contest/<id>` (Admin or Creator)
Delete a contest and all associated submissions.

**Response:** `200 OK`
```json
{
  "message": "Contest deleted successfully"
}
```

#### `POST /api/contest/<id>/submit` (Authenticated)
Submit an edit for a contest.

**Request Body:**
```json
{
  "article_title": "string",
  "article_link": "string"
}
```

**Response:** `201 Created`
```json
{
  "message": "Submission created successfully",
  "submissionId": 1,
  "contest_id": 1,
  "article_title": "string"
}
```

#### `GET /api/contest/<id>/submissions` (Admin, Jury, or Creator)
Retrieve all submissions for a specific contest.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "article_title": "string",
    "status": "pending",
    "score": 0,
    "submitted_at": "ISO 8601 datetime"
  }
]
```

### Submission Routes (`backend/routes/submission_routes.py`)

#### `GET /api/submission/` (Admin Only)
Retrieve all submissions across all contests.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "contest_id": 1,
    "user_id": 1,
    "article_title": "string",
    "status": "pending"
  }
]
```

#### `GET /api/submission/<id>` (Permission Required)
Retrieve details for a specific submission.

**Response:** `200 OK`
```json
{
  "id": 1,
  "contest_id": 1,
  "user_id": 1,
  "article_title": "string",
  "edit_summary": "string",
  "status": "pending",
  "score": 0,
  "user": { ... }
}
```

#### `PUT /api/submission/<id>` (Jury or Admin)
Update submission status and recalculate score.

**Request Body:**
```json
{
  "status": "accepted" | "rejected"
}
```

**Response:** `200 OK`
```json
{
  "message": "Submission updated successfully",
  "status": "accepted",
  "score": 10
}
```

#### `GET /api/submission/user/<user_id>` (Self or Admin)
Retrieve submissions for a specific user.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "contest_id": 1,
    "article_title": "string",
    "status": "pending"
  }
]
```

#### `GET /api/submission/contest/<contest_id>` (Admin, Jury, or Creator)
Retrieve submissions for a specific contest.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "article_title": "string",
    "status": "pending"
  }
]
```

#### `GET /api/submission/pending` (Authenticated)
Retrieve submissions the current user can judge.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "contest_id": 1,
    "article_title": "string",
    "status": "pending"
  }
]
```

#### `GET /api/submission/stats` (Authenticated)
Retrieve submission statistics for current user.

**Response:** `200 OK`
```json
{
  "total": 10,
  "pending": 3,
  "approved": 5,
  "rejected": 2
}
```

### Utility Routes

#### `GET /api/cookie` (Authenticated)
Verify authentication and retrieve current user information.

**Response:** `200 OK`
```json
{
  "userId": 1,
  "username": "string",
  "email": "string"
}
```



## Authentication and Security

### JWT Authentication

- **Storage:** HTTP-only cookies (not accessible via JavaScript)
- **Token Type:** Access tokens with configurable expiration
- **Automatic Refresh:** Handled by Flask-JWT-Extended

### CSRF Protection

For state-changing requests (POST, PUT, DELETE), include the CSRF token:

**Header:**
```
X-CSRF-TOKEN: <value from csrf_access_token cookie>
```

### Role-Based Access Control

**Roles:**
- `user` – Standard user permissions
- `admin` – Full system access
- `jury` – Can review and score submissions for assigned contests

**Middleware:** `backend/middleware/auth.py`
- Validates JWT tokens
- Enforces role-based permissions
- Provides current user context to routes



## Frontend Architecture

### `frontend/index.html`

Main HTML structure and UI components.

**Features:**
- Responsive design using CSS Grid and Flexbox
- Modal dialogs for forms
- Dynamic content loading
- User authentication interface
- Contest management interface
- Leaderboard display

### `frontend/app.js`

Frontend JavaScript logic and API communication.

**Features:**
- API client for backend communication
- User authentication state management
- Contest creation and participation workflows
- Real-time UI updates
- Form validation and submission handling
- Error handling and user feedback



## Deployment Options

### Local Development

1. **Start Backend:**
```bash
   cd backend
   python app.py
```

2. **Access Application:**
   - Frontend: `http://localhost:5000`
   - API: `http://localhost:5000/api`

3. **Database:** MySQL (default) or SQLite (if configured)

### Toolforge Production

1. **Backend:** `python backend/toolforge_app.py`
2. **Frontend:** Served by Flask with Jinja2 templates
3. **Database:** MySQL on Toolforge (recommended)
4. **Authentication:** OAuth 1.0a with Wikimedia accounts
5. **URL:** `https://wikicontest.toolforge.org`



## Security Features

1. **JWT Authentication** – Secure token-based authentication in HTTP-only cookies
2. **Password Hashing** – bcrypt for secure password storage
3. **Role-Based Access Control** – User/Admin/Jury permission system
4. **CORS Protection** – Cross-origin request security
5. **CSRF Protection** – Token-based CSRF validation
6. **OAuth Integration** – Wikimedia account authentication for Toolforge
7. **Input Validation** – Server-side validation for all user inputs



## User Capabilities

### Regular Users

- Register and log in to the platform
- View available contests (current, upcoming, past)
- Submit Wikipedia edits for active contests
- Track submission status and scores
- View leaderboards and rankings

### Contest Creators

- Create new editing contests
- Configure contest parameters (title, description, dates, rules)
- Assign jury members
- Review contest submissions
- View detailed contest analytics

### Jury Members

- Review submissions for assigned contests
- Accept or reject submissions
- Assign scores based on contest rules

### Administrators

- Manage all users and contests
- Review all submissions across the platform
- Update scores and statuses
- Access system-wide analytics and reporting



## Development Workflow

1. **Setup:** Run `python backend/setup.py` to initialize the environment
2. **Database:** Run `python backend/init_db.py` to create database tables
3. **Testing:** Run `python backend/test_app.py` to verify functionality
4. **Development:** Use `python backend/app.py` for local development server
5. **Deployment:** Use `bash backend/deploy_to_toolforge.sh` for Toolforge deployment



## Future Enhancements

- Real-time notifications for submission updates
- Advanced analytics and reporting dashboards
- Integration with Wikipedia API for automated edit validation
- Enhanced mobile-responsive design
- Automated scoring algorithms based on edit quality
- Contest templates and presets for common contest types
- Multi-language support for international contests



## External Integrations

- **Wikimedia OAuth** – User authentication via Wikimedia accounts
- **Wikipedia API** – Potential integration for edit validation and metrics
- **Toolforge Platform** – Hosting and deployment infrastructure
- **MySQL Database** – Production database on Toolforge (recommended)
- **SQLite Database** – Development and testing database



This documentation provides a comprehensive overview of the WikiEval platform's architecture, features, and capabilities for organizing and managing Wikipedia editing contests.