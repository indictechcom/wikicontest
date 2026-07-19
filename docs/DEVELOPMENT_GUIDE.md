# WikiEval Development Guide

Comprehensive technical guide for developers working on the WikiEval platform, covering architecture, coding standards, best practices, and development workflows.



## Architecture Overview

### Backend Architecture

The backend follows a modular Flask architecture with clear separation of concerns:
```
backend/
├── main.py                    # Application entry point
├── app/
│   ├── __init__.py            # Application factory
│   ├── config.py              # Environment-based configuration
│   ├── database.py            # SQLAlchemy database instance
│   ├── models/                # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base_model.py      # Base model with common methods
│   │   ├── user.py            # User model
│   │   ├── contest.py         # Contest model
│   │   ├── submission.py      # Submission model
│   │   └── ...
│   ├── routes/                # API route blueprints
│   │   ├── user_routes.py     # User authentication and management
│   │   ├── contest_routes.py  # Contest CRUD operations
│   │   └── submission_routes.py # Submission handling
│   ├── middleware/            # Authentication and security middleware
│   │   └── auth.py            # JWT and permission handling
│   └── utils/                 # Utility functions
│       ├── __init__.py
│       ├── validation.py
│       └── ...
├── alembic/                   # Database migration environment
├── scripts/                   # Utility scripts
└── ...
```

**Key Architectural Principles:**
- Application factory pattern for flexible configuration
- Blueprint-based modular routing
- ORM-based database abstraction
- Middleware for cross-cutting concerns
- Environment-specific configuration

### Frontend Architecture

The frontend is a Vue.js 3 single-page application using the Composition API:
```javascript
// Global state management via composables
import { useStore } from '@/store'

const store = useStore()

// Reactive state
const currentUser = store.user
const currentContests = store.contests

// API communication via centralized service
import api from '@/services/api'
const contests = await api.get('/contest')
```

**Key Architectural Principles:**
- Component-based UI with Vue 3 Composition API
- Centralized API service layer (`src/services/api.js`)
- Composable state management (`src/store/index.js`)
- Vue Router for client-side navigation
- Vite for build tooling and HMR



## Development Setup

### Prerequisites

- **Python:** 3.8 or higher
- **Database:** MySQL 8.0+ or SQLite (development)
- **Version Control:** Git
- **Code Editor:** VS Code (recommended)
- **Node.js:** 16+ (for Vue.js frontend)

### Local Development Environment

#### Step 1: Clone and Setup Backend
```bash
git clone <repository-url>
cd WikiEval

# Backend setup
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

#### Step 2: Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
```

**Required environment variables:**
```env
DATABASE_URL=mysql+pymysql://user:password@localhost/WikiEval
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
```

For OAuth configuration, see [OAUTH_LOCAL_SETUP.md](OAUTH_LOCAL_SETUP.md).


#### Step 3: Initialize Database
```bash
# Apply Alembic migrations
python -m alembic upgrade head
```

#### Step 4: Run Development Server
```bash
python main.py
```

#### Step 5: Access Application

- **Backend API:** http://localhost:5000/api
- **Frontend (Vite dev server):** http://localhost:5173
- **Vue.js Dev Server (if using Vue):** http://localhost:5173



## Coding Standards

### Python Backend Standards

#### 1. Code Organization

**Best Practices:**
- Use descriptive, meaningful function and variable names
- Add comprehensive docstrings for all public functions
- Group related functionality in modules
- Use type hints where appropriate for better code clarity

**Example:**
```python
from typing import Optional, Dict, Any

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user by their email address.

    Args:
        email: The user's email address

    Returns:
        User dictionary if found, None otherwise
    """
    user = User.query.filter_by(email=email).first()
    return user.to_dict() if user else None
```

#### 2. Error Handling

**Use decorators for route functions:**
```python
from app.middleware.auth import require_auth, get_current_user
from app.utils import create_success_response, create_error_response
from app.utils.validation import validate_json

@user_bp.route('/login', methods=['POST'])
@validate_json
def login():
    """Handle user login."""
    data = request.get_json()
    # Function implementation
    pass
```

**Manual error handling for complex operations:**
```python
try:
    result = perform_operation()
    return create_success_response("Operation successful", result)
except SpecificException as e:
    return create_error_response(f"Operation failed: {str(e)}", 400)
except Exception as e:
    return create_error_response("Unexpected error occurred", 500)
```

#### 3. Database Operations

**Use SQLAlchemy ORM methods:**
```python
# Query operations
user = User.query.filter_by(email=email).first()
if not user:
    return create_error_response("User not found", 404)

# Bulk operations
users = User.query.filter(User.role == 'admin').all()
```

**Use transactions for multiple operations:**
```python
db.session.begin()
try:
    # Multiple database operations
    user = User(username='test', email='test@example.com')
    db.session.add(user)

    contest = Contest(title='New Contest', created_by=user.id)
    db.session.add(contest)

    db.session.commit()
except Exception:
    db.session.rollback()
    raise
```

#### 4. API Response Format

**Consistent response structure:**
```python
# Success responses
return create_success_response(
    message="Operation completed successfully",
    data={'id': 1, 'name': 'Example'},
    status_code=200
)

# Error responses
return create_error_response(
    message="Validation failed",
    status_code=400,
    details={'field': 'error description'}
)
```

### JavaScript Frontend Standards

#### 1. Component Documentation

**Use JSDoc format:**
```vue
<script setup>
/**
 * Contest listing page with filtering and search.
 *
 * @example
 * <Contests />
 */
const contests = ref([])
const loading = ref(false)
</script>
```

#### 2. Error Handling

**Consistent async error handling in composables:**
```javascript
// src/composables/useContests.js
export function useContests() {
  const loading = ref(false)
  const error = ref(null)

  async function fetchContests() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/contest')
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  return { fetchContests, loading, error }
}
```

#### 3. State Management

**Use composable store pattern:**
```javascript
// src/store/index.js
export function useStore() {
  const user = ref(null)
  const contests = ref([])

  function setUser(userData) {
    user.value = userData
  }

  function clearUser() {
    user.value = null
  }

  return { user, contests, setUser, clearUser }
}
```



## Adding New Features

### Backend Feature Development

#### Step 1: Create a New Model

**File: `app/models/new_feature.py`**
```python
from app.database import db
from datetime import datetime

class NewFeature(db.Model):
    """Model for new feature entities."""

    __tablename__ = 'new_features'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='new_features')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'user_id': self.user_id
        }

    def __repr__(self):
        return f'<NewFeature {self.name}>'
```

#### Step 2: Create Route Blueprint

**File: `app/routes/new_feature_routes.py`**
```python
from flask import Blueprint, request
from app.models.new_feature import NewFeature
from app.middleware.auth import require_auth, get_current_user
from app.utils import create_success_response, create_error_response
from app.database import db

new_feature_bp = Blueprint('new_feature', __name__)

@new_feature_bp.route('/', methods=['GET'])
def get_all_features():
    """Retrieve all features."""
    features = NewFeature.query.all()
    return create_success_response(
        'Features retrieved successfully',
        [feature.to_dict() for feature in features]
    )

@new_feature_bp.route('/', methods=['POST'])
@require_auth
def create_feature():
    """Create a new feature instance."""
    current_user = get_current_user()
    data = request.get_json()

    if not data.get('name'):
        return create_error_response('Name is required', 400)

    new_feature = NewFeature(
        name=data['name'],
        description=data.get('description'),
        user_id=current_user['id']
    )

    db.session.add(new_feature)
    db.session.commit()

    return create_success_response(
        'Feature created successfully',
        new_feature.to_dict(),
        201
    )
```

#### Step 3: Register Blueprint

**File: `app/__init__.py`**
```python
from app.routes.new_feature_routes import new_feature_bp

# Register blueprint
app.register_blueprint(new_feature_bp, url_prefix='/api/new-feature')
```

#### Step 4: Create Database Migration
```bash
# Generate migration
python -m alembic revision --autogenerate -m "Add new_feature table"

# Apply migration
python -m alembic upgrade head
```

### Frontend Feature Development

#### Step 1: Add API Functions

**File: `frontend/src/services/new-feature.js`**
```javascript
import api from './api'

export async function getAllFeatures() {
    const response = await api.get('/new-feature/')
    return response.data
}

export async function createNewFeature(name, description) {
    const response = await api.post('/new-feature/', {
        name,
        description
    })
    return response.data
}

export async function updateFeature(featureId, updates) {
    const response = await api.put(`/new-feature/${featureId}`, updates)
    return response.data
}

export async function deleteFeature(featureId) {
    await api.delete(`/new-feature/${featureId}`)
}
```

#### Step 2: Add Vue Components

**File: `frontend/src/views/NewFeature.vue`**
```vue
<template>
  <div class="new-feature">
    <h1>New Feature</h1>
    <button @click="createFeature">Create Feature</button>
  </div>
</template>

<script setup>
import { useStore } from '@/store'
import { createNewFeature } from '@/services/new-feature'

const store = useStore()

async function createFeature() {
    await createNewFeature('Feature Name', 'Description')
}
</script>
```

#### Step 3: Add Routes

**File: `frontend/src/router/index.js`**
```javascript
{
    path: '/new-feature',
    name: 'NewFeature',
    component: () => import('@/views/NewFeature.vue'),
    meta: { requiresAuth: true }
}
```



## Testing Guidelines

### Backend Testing

#### Unit Tests

**File: `tests/test_new_feature.py`**
```python
import unittest
from app import create_app
from app.database import db
from app.models.new_feature import NewFeature
from app.models.user import User

class TestNewFeature(unittest.TestCase):
    """Test cases for NewFeature model and routes."""

    def setUp(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.test_user = User(
            username='testuser',
            email='test@example.com'
        )
        self.test_user.set_password('password123')
        db.session.add(self.test_user)
        db.session.commit()

    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_create_new_feature(self):
        """Test feature creation."""
        response = self.client.post('/api/user/login',
            json={'email': 'test@example.com', 'password': 'password123'}
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/api/new-feature/',
            json={'name': 'Test Feature', 'description': 'Test description'}
        )

        self.assertEqual(response.status_code, 201)

    def test_get_all_features(self):
        """Test retrieving all features."""
        feature1 = NewFeature(name='Feature 1', user_id=self.test_user.id)
        feature2 = NewFeature(name='Feature 2', user_id=self.test_user.id)
        db.session.add_all([feature1, feature2])
        db.session.commit()

        response = self.client.get('/api/new-feature/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['data']), 2)

if __name__ == '__main__':
    unittest.main()
```

### Frontend Testing

#### Manual Testing Checklist

**Feature Testing:**
- [ ] Feature list loads correctly
- [ ] Create feature modal opens and closes properly
- [ ] Feature creation succeeds with valid input
- [ ] Feature creation fails with invalid input
- [ ] Feature update works correctly
- [ ] Feature deletion works with confirmation
- [ ] Error messages display appropriately
- [ ] Success messages display appropriately

**User Experience Testing:**
- [ ] Responsive design works on mobile devices
- [ ] All buttons are clickable and functional
- [ ] Forms validate input before submission
- [ ] Loading indicators appear during API calls
- [ ] Navigation works correctly



## Deployment Process

### Development to Production Checklist

#### 1. Code Review

- [ ] All functions have proper documentation
- [ ] Error handling is comprehensive
- [ ] Security measures are in place (input validation, authentication)
- [ ] Database queries are optimized (no N+1 queries)
- [ ] Frontend validation is complete
- [ ] Unit tests pass successfully
- [ ] Integration tests pass successfully
- [ ] No sensitive data in code (secrets in environment variables)

#### 2. Production Configuration

Set production environment variables in `.env`:
```env
FLASK_ENV=production
FLASK_DEBUG=False
DATABASE_URL=mysql+pymysql://user:pass@host:port/db
SECRET_KEY=<generate-secure-key>
JWT_SECRET_KEY=<generate-secure-key>
JWT_COOKIE_SECURE=True
JWT_COOKIE_SAMESITE=None
```

#### 3. Deployment Steps
```bash
# 1. Set environment variables
export FLASK_ENV=production
export DATABASE_URL=mysql://user:password@host/database
export SECRET_KEY=your-production-secret-key
export JWT_SECRET_KEY=your-production-jwt-key

# 2. Install production dependencies
pip install -r requirements.txt
pip install gunicorn

# 3. Run database migrations
python -m alembic upgrade head

# 4. Build frontend
cd frontend && npm run build

# 5. Start production server
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 main:app

# Or use a process manager like systemd or supervisord
```

#### 4. Post-Deployment Verification

- [ ] Application loads successfully
- [ ] Health check endpoint responds
- [ ] User authentication works
- [ ] Database connections are stable
- [ ] API endpoints return expected responses
- [ ] Error logging is functional
- [ ] SSL/HTTPS is working correctly


## Deployment

For production deployment to Wikimedia Toolforge, see [TOOLFORGE_DEPLOYMENT.md](TOOLFORGE_DEPLOYMENT.md).



## Debugging Guide

### Common Issues and Solutions

#### 1. Authentication Issues

**Problem:** "Missing Authorization Header" or "Unauthorized"

**Solution:**
- Verify JWT cookie is being set correctly
- Check CSRF token handling in requests
- Ensure `JWT_COOKIE_SECURE` matches your environment (False for HTTP, True for HTTPS)
- Check browser DevTools → Application → Cookies

**Debugging:**
```python
# Add logging to auth middleware
import logging
logger = logging.getLogger(__name__)

@require_auth
def protected_route():
    logger.debug(f"Request cookies: {request.cookies}")
    logger.debug(f"JWT present: {'access_token_cookie' in request.cookies}")
    # Rest of function
```

#### 2. Database Connection Issues

**Problem:** "Database connection failed" or "OperationalError"

**Solution:**
- Verify `DATABASE_URL` environment variable
- Check database server is running
- Verify database credentials are correct
- Ensure database exists and user has proper permissions

**Debugging:**
```python
# Test database connection
from app.database import db
from app import create_app

app = create_app()
with app.app_context():
    try:
        db.session.execute('SELECT 1')
        print("Database connection successful")
    except Exception as e:
        print(f"Database connection failed: {e}")
```

#### 3. Frontend API Errors

**Problem:** CORS error or "Network request failed"

**Solution:**
- Check CORS configuration in `app/__init__.py`
- Verify API URL is correct in frontend
- Ensure backend server is running
- Check browser console for specific error messages

**Configuration:**
```python
# app/__init__.py
from flask_cors import CORS

CORS(app,
     origins=['http://localhost:5173', 'https://your-domain.com'],
     supports_credentials=True,
     allow_headers=['Content-Type', 'X-CSRF-TOKEN'])
```

#### 4. Contest Creation Issues

**Problem:** Contest not appearing in correct category (current/upcoming/past)

**Solution:**
- Verify date fields are properly formatted (ISO 8601)
- Check timezone handling
- Validate date comparison logic in backend

**Debugging:**
```python
# Check date parsing
from datetime import datetime

def debug_contest_dates(contest):
    now = datetime.utcnow()
    print(f"Now: {now}")
    print(f"Start: {contest.start_date}")
    print(f"End: {contest.end_date}")
    print(f"Is current: {contest.start_date <= now <= contest.end_date}")
```

### Debugging Tools

#### Backend Debugging
```python
# Enable detailed logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Use Flask debug mode (development only!)
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Add debug prints in routes
@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    print(f"Login attempt for: {data.get('email')}")
    # Rest of function
```

#### Frontend Debugging
```javascript
// Use browser developer tools

// Console logging
console.log('Current user:', currentUser)
console.log('API response:', response)

// Network tab
// - Check request/response details
// - Verify status codes
// - Inspect headers and cookies

// Breakpoints
debugger; // Pause execution here

// Vue DevTools
// - Inspect component state
// - Track events
// - Time-travel debugging
```



## Additional Resources

### Documentation

- **Flask:** https://flask.palletsprojects.com/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **Flask-JWT-Extended:** https://flask-jwt-extended.readthedocs.io/
- **Bootstrap 5:** https://getbootstrap.com/docs/5.0/
- **Vue.js:** https://vuejs.org/guide/
- **Vite:** https://vitejs.dev/guide/

### Best Practices

#### General Principles

1. **Follow RESTful API design principles**
   - Use appropriate HTTP methods (GET, POST, PUT, DELETE)
   - Return meaningful status codes
   - Use plural nouns for resource endpoints

2. **Use meaningful names**
   - Variables: `user_data`, `contest_list`, `submission_count`
   - Functions: `create_contest()`, `get_user_by_id()`, `validate_email()`
   - Classes: `User`, `Contest`, `SubmissionValidator`

3. **Add comprehensive error handling**
   - Catch specific exceptions
   - Provide meaningful error messages
   - Log errors for debugging

4. **Write tests for new functionality**
   - Unit tests for individual functions
   - Integration tests for workflows
   - Aim for >80% code coverage

5. **Document all public functions**
   - Use docstrings (Python) or JSDoc (JavaScript)
   - Include parameter types and return values
   - Provide usage examples

6. **Keep functions small and focused**
   - Single responsibility principle
   - Aim for <50 lines per function
   - Extract complex logic into helper functions

7. **Use consistent code formatting**
   - Python: Follow PEP 8
   - JavaScript: Use consistent indentation (2 or 4 spaces)
   - Use linters (pylint, ESLint)



## Contributing

### Guidelines

- Fork the repository and create a feature branch
- Write tests for new functionality
- Follow coding standards outlined in this guide
- Document your changes in code comments and this guide if needed
- Submit a pull request with a clear description

**Pull Request Checklist**

- Code follows project coding standards
- All tests pass
- New tests added for new functionality
- Documentation updated if needed
- No sensitive data in commits
- Commits are well-organized with clear messages

This development guide provides the foundation for contributing to the WikiEval platform. For specific questions, refer to inline code comments or create an issue in the repository.
