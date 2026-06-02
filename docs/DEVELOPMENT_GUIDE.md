# WikiEval Development Guide

Comprehensive technical guide for developers working on the WikiEval platform, covering architecture, coding standards, best practices, and development workflows.



## Architecture Overview

### Backend Architecture

The backend follows a modular Flask architecture with clear separation of concerns:
```
backend/
├── app.py                     # Application factory and main entry point
├── config.py                  # Environment-based configuration management
├── utils.py                   # Reusable utility functions
├── database.py                # Database initialization and connection
├── models/                    # SQLAlchemy data models
│   ├── user.py                # User model with authentication methods
│   ├── contest.py             # Contest model with status methods
│   └── submission.py          # Submission model for contest entries
├── routes/                    # API route blueprints
│   ├── user_routes.py         # User authentication and management
│   ├── contest_routes.py      # Contest CRUD operations
│   └── submission_routes.py   # Submission handling
└── middleware/                # Authentication and security middleware
    └── auth.py                # JWT authentication decorators
```

**Key Architectural Principles:**
- Application factory pattern for flexible configuration
- Blueprint-based modular routing
- ORM-based database abstraction
- Middleware for cross-cutting concerns
- Environment-specific configuration

### Frontend Architecture

The frontend uses vanilla JavaScript with modular function organization:
```javascript
// Global state management
let currentUser = null;
let currentContests = { current: [], upcoming: [], past: [] };

// Function organization by feature:
// - Utility functions (showAlert, formatDate, etc.)
// - API communication functions
// - Authentication functions
// - Contest management functions
// - UI management functions
```

**Modern Alternative:** Vue.js 3 implementation available with component-based architecture, reactive state management, and Vue Router.



## Development Setup

### Prerequisites

- **Python:** 3.8 or higher
- **Database:** MySQL 8.0+ or PostgreSQL 12+
- **Version Control:** Git
- **Code Editor:** VS Code (recommended)
- **Node.js:** 16+ (for Vue.js frontend)

### Local Development Environment

#### Step 1: Clone and Setup Backend
```bash
git clone <repository-url>
cd wikicontest

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Step 2: Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Required environment variables:**
```env
DATABASE_URL=mysql+pymysql://user:password@localhost/wikicontest
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
CONSUMER_KEY=your-oauth-consumer-key
CONSUMER_SECRET=your-oauth-consumer-secret
```

#### Step 3: Initialize Database
```bash
python init_db.py
```

#### Step 4: Run Development Server
```bash
python app.py
```

#### Step 5: Access Application

- **Backend API:** http://localhost:5000/api
- **Frontend:** http://localhost:5000 (served by Flask)
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
from utils import handle_errors

@user_bp.route('/login', methods=['POST'])
@handle_errors
def login():
    """Handle user login."""
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

#### 1. Function Documentation

**Use JSDoc format:**
```javascript
/**
 * Create a new contest and add it to the platform.
 * 
 * This function validates the contest data, sends it to the API,
 * and updates the UI with the newly created contest.
 * 
 * @param {string} title - Contest title
 * @param {string} description - Contest description
 * @param {Date} startDate - Contest start date
 * @param {Date} endDate - Contest end date
 * @returns {Promise<Object>} Created contest data
 * @throws {Error} If validation fails or API request fails
 * 
 * @example
 * const contest = await createContest(
 *   'Edit-a-thon 2024',
 *   'Annual editing contest',
 *   new Date('2024-01-01'),
 *   new Date('2024-12-31')
 * );
 */
async function createContest(title, description, startDate, endDate) {
    // Validation
    if (!title || !description) {
        throw new Error('Title and description are required');
    }
    
    // Implementation
    const response = await apiRequest('/contest/', {
        method: 'POST',
        body: JSON.stringify({ title, description, startDate, endDate })
    });
    
    return response;
}
```

#### 2. Error Handling

**Consistent async error handling:**
```javascript
try {
    const result = await apiRequest('/endpoint');
    showAlert('Operation successful', 'success');
    return result;
} catch (error) {
    showAlert(error.message, 'error');
    console.error('Operation failed:', error);
    throw error; // Re-throw if caller needs to handle it
}
```

#### 3. State Management

**Update global state consistently:**
```javascript
// Update authentication state
function updateUserState(userData) {
    currentUser = {
        id: userData.userId,
        username: userData.username,
        email: userData.email,
        role: userData.role
    };
    
    // Persist to localStorage if needed
    localStorage.setItem('user', JSON.stringify(currentUser));
    
    // Update UI
    updateAuthUI();
}

// Clear state on logout
function clearUserState() {
    currentUser = null;
    localStorage.removeItem('user');
    updateAuthUI();
}
```



## Adding New Features

### Backend Feature Development

#### Step 1: Create a New Model

**File: `models/new_feature.py`**
```python
from database import db
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
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='new_features')
    
    def to_dict(self):
        """Convert model to dictionary."""
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

**File: `routes/new_feature_routes.py`**
```python
from flask import Blueprint, request
from models.new_feature import NewFeature
from middleware.auth import require_auth, get_current_user
from utils import create_success_response, create_error_response, handle_errors
from database import db

new_feature_bp = Blueprint('new_feature', __name__)

@new_feature_bp.route('/', methods=['GET'])
@handle_errors
def get_all_features():
    """Retrieve all features."""
    features = NewFeature.query.all()
    return create_success_response(
        'Features retrieved successfully',
        [feature.to_dict() for feature in features]
    )

@new_feature_bp.route('/', methods=['POST'])
@require_auth
@handle_errors
def create_feature():
    """Create a new feature instance."""
    current_user = get_current_user()
    data = request.get_json()
    
    # Validation
    if not data.get('name'):
        return create_error_response('Name is required', 400)
    
    # Create instance
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

@new_feature_bp.route('/<int:feature_id>', methods=['GET'])
@handle_errors
def get_feature(feature_id):
    """Retrieve a specific feature by ID."""
    feature = NewFeature.query.get(feature_id)
    
    if not feature:
        return create_error_response('Feature not found', 404)
    
    return create_success_response(
        'Feature retrieved successfully',
        feature.to_dict()
    )

@new_feature_bp.route('/<int:feature_id>', methods=['PUT'])
@require_auth
@handle_errors
def update_feature(feature_id):
    """Update a feature."""
    current_user = get_current_user()
    feature = NewFeature.query.get(feature_id)
    
    if not feature:
        return create_error_response('Feature not found', 404)
    
    # Authorization check
    if feature.user_id != current_user['id'] and current_user['role'] != 'admin':
        return create_error_response('Unauthorized', 403)
    
    data = request.get_json()
    
    # Update fields
    if 'name' in data:
        feature.name = data['name']
    if 'description' in data:
        feature.description = data['description']
    if 'status' in data:
        feature.status = data['status']
    
    db.session.commit()
    
    return create_success_response(
        'Feature updated successfully',
        feature.to_dict()
    )

@new_feature_bp.route('/<int:feature_id>', methods=['DELETE'])
@require_auth
@handle_errors
def delete_feature(feature_id):
    """Delete a feature."""
    current_user = get_current_user()
    feature = NewFeature.query.get(feature_id)
    
    if not feature:
        return create_error_response('Feature not found', 404)
    
    # Authorization check
    if feature.user_id != current_user['id'] and current_user['role'] != 'admin':
        return create_error_response('Unauthorized', 403)
    
    db.session.delete(feature)
    db.session.commit()
    
    return create_success_response('Feature deleted successfully')
```

#### Step 3: Register Blueprint

**File: `app.py`**
```python
from routes.new_feature_routes import new_feature_bp

# Register blueprint
app.register_blueprint(new_feature_bp, url_prefix='/api/new-feature')
```

#### Step 4: Create Database Migration
```bash
# Add to init_db.py or create migration
python init_db.py
```

### Frontend Feature Development

#### Step 1: Add API Functions

**File: `frontend/app.js`** (or appropriate Vue component)
```javascript
/**
 * Retrieve all features from the API.
 * 
 * @returns {Promise<Array>} Array of feature objects
 */
async function getAllFeatures() {
    try {
        const response = await apiRequest('/new-feature/');
        return response.data;
    } catch (error) {
        showAlert('Failed to load features', 'error');
        throw error;
    }
}

/**
 * Create a new feature instance.
 * 
 * @param {string} name - Feature name
 * @param {string} description - Feature description
 * @returns {Promise<Object>} Created feature data
 */
async function createNewFeature(name, description) {
    try {
        const response = await apiRequest('/new-feature/', {
            method: 'POST',
            body: JSON.stringify({ name, description })
        });
        
        showAlert('Feature created successfully!', 'success');
        return response.data;
    } catch (error) {
        showAlert(error.message, 'error');
        throw error;
    }
}

/**
 * Update an existing feature.
 * 
 * @param {number} featureId - Feature ID
 * @param {Object} updates - Fields to update
 * @returns {Promise<Object>} Updated feature data
 */
async function updateFeature(featureId, updates) {
    try {
        const response = await apiRequest(`/new-feature/${featureId}`, {
            method: 'PUT',
            body: JSON.stringify(updates)
        });
        
        showAlert('Feature updated successfully!', 'success');
        return response.data;
    } catch (error) {
        showAlert(error.message, 'error');
        throw error;
    }
}

/**
 * Delete a feature.
 * 
 * @param {number} featureId - Feature ID
 * @returns {Promise<void>}
 */
async function deleteFeature(featureId) {
    if (!confirm('Are you sure you want to delete this feature?')) {
        return;
    }
    
    try {
        await apiRequest(`/new-feature/${featureId}`, {
            method: 'DELETE'
        });
        
        showAlert('Feature deleted successfully!', 'success');
    } catch (error) {
        showAlert(error.message, 'error');
        throw error;
    }
}
```

#### Step 2: Add UI Functions
```javascript
/**
 * Display the create feature modal.
 */
function showCreateFeatureModal() {
    const modal = document.getElementById('createFeatureModal');
    const modalInstance = new bootstrap.Modal(modal);
    
    // Clear previous input
    document.getElementById('featureName').value = '';
    document.getElementById('featureDescription').value = '';
    
    modalInstance.show();
}

/**
 * Handle create feature form submission.
 */
async function handleCreateFeature() {
    const nameInput = document.getElementById('featureName');
    const descriptionInput = document.getElementById('featureDescription');
    
    const name = nameInput.value.trim();
    const description = descriptionInput.value.trim();
    
    // Validation
    if (!name) {
        showAlert('Feature name is required', 'error');
        return;
    }
    
    try {
        await createNewFeature(name, description);
        
        // Close modal
        const modal = document.getElementById('createFeatureModal');
        bootstrap.Modal.getInstance(modal).hide();
        
        // Refresh features list
        await loadFeatures();
    } catch (error) {
        // Error already handled in createNewFeature
    }
}

/**
 * Load and display all features.
 */
async function loadFeatures() {
    const container = document.getElementById('featuresContainer');
    
    try {
        const features = await getAllFeatures();
        
        if (features.length === 0) {
            container.innerHTML = '<p class="text-muted">No features found.</p>';
            return;
        }
        
        container.innerHTML = features.map(feature => `
            <div class="card mb-3">
                <div class="card-body">
                    <h5 class="card-title">${feature.name}</h5>
                    <p class="card-text">${feature.description || 'No description'}</p>
                    <button class="btn btn-sm btn-primary" onclick="editFeature(${feature.id})">
                        Edit
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteFeature(${feature.id})">
                        Delete
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<p class="text-danger">Failed to load features.</p>';
    }
}
```



## Testing Guidelines

### Backend Testing

#### Unit Tests

**File: `tests/test_new_feature.py`**
```python
import unittest
from app import create_app
from database import db
from models.new_feature import NewFeature
from models.user import User

class TestNewFeature(unittest.TestCase):
    """Test cases for NewFeature model and routes."""
    
    def setUp(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test user
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
        # Login first
        response = self.client.post('/api/user/login',
            json={'email': 'test@example.com', 'password': 'password123'}
        )
        self.assertEqual(response.status_code, 200)
        
        # Create feature
        response = self.client.post('/api/new-feature/',
            json={'name': 'Test Feature', 'description': 'Test description'}
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('Feature created successfully', response.json['message'])
        self.assertEqual(response.json['data']['name'], 'Test Feature')
    
    def test_get_all_features(self):
        """Test retrieving all features."""
        # Create test features
        feature1 = NewFeature(name='Feature 1', user_id=self.test_user.id)
        feature2 = NewFeature(name='Feature 2', user_id=self.test_user.id)
        db.session.add_all([feature1, feature2])
        db.session.commit()
        
        # Get features
        response = self.client.get('/api/new-feature/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['data']), 2)
    
    def test_update_feature(self):
        """Test feature update."""
        # Create feature
        feature = NewFeature(name='Original Name', user_id=self.test_user.id)
        db.session.add(feature)
        db.session.commit()
        
        # Login
        self.client.post('/api/user/login',
            json={'email': 'test@example.com', 'password': 'password123'}
        )
        
        # Update feature
        response = self.client.put(f'/api/new-feature/{feature.id}',
            json={'name': 'Updated Name'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['data']['name'], 'Updated Name')

if __name__ == '__main__':
    unittest.main()
```

#### Integration Tests
```python
def test_complete_feature_workflow(self):
    """Test complete feature creation workflow."""
    # Register user
    response = self.client.post('/api/user/register',
        json={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password123'
        }
    )
    self.assertEqual(response.status_code, 201)
    
    # Login
    response = self.client.post('/api/user/login',
        json={'email': 'newuser@example.com', 'password': 'password123'}
    )
    self.assertEqual(response.status_code, 200)
    
    # Create feature
    response = self.client.post('/api/new-feature/',
        json={'name': 'New Feature', 'description': 'Test'}
    )
    self.assertEqual(response.status_code, 201)
    feature_id = response.json['data']['id']
    
    # Retrieve feature
    response = self.client.get(f'/api/new-feature/{feature_id}')
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json['data']['name'], 'New Feature')
    
    # Update feature
    response = self.client.put(f'/api/new-feature/{feature_id}',
        json={'description': 'Updated description'}
    )
    self.assertEqual(response.status_code, 200)
    
    # Delete feature
    response = self.client.delete(f'/api/new-feature/{feature_id}')
    self.assertEqual(response.status_code, 200)
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

#### Browser Testing

Test in multiple browsers to ensure compatibility:
-  Chrome (latest version)
-  Firefox (latest version)
-  Safari (latest version)
-  Edge (latest version)
-  Mobile browsers (iOS Safari, Chrome Mobile)



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

**File: `config.py`**
```python
class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    
    # Security settings
    JWT_COOKIE_SECURE = True  # Require HTTPS for cookies
    JWT_COOKIE_CSRF_PROTECT = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 20
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')
    
    # Logging
    LOG_LEVEL = 'INFO'
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
python init_db.py

# 4. Collect static files (if using separate static file server)
# (Optional, depending on deployment setup)

# 5. Start production server
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app

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
from database import db
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
- Check CORS configuration in `app.py`
- Verify API URL is correct in frontend
- Ensure backend server is running
- Check browser console for specific error messages

**Configuration:**
```python
# app.py
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
console.log('Current user:', currentUser);
console.log('API response:', response);

// Network tab
// - Check request/response details
// - Verify status codes
// - Inspect headers and cookies

// Breakpoints
debugger; // Pause execution here

// Vue DevTools (if using Vue.js)
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

###

**Guidelines**

   - Fork the repository and create a feature branch
   - Write tests for new functionality
   - Follow coding standards outlined in this guide
   - Document your changes in code comments and this guide if needed
   - Submit a pull request with a clear description

**Pull Request Checklist**

   -  Code follows project coding standards
   -  All tests pass
   -  New tests added for new functionality
   -  Documentation updated if needed
   -  No sensitive data in commits
   -   Commits are well-organized with clear messages

This development guide provides the foundation for contributing to the WikiContest platform. For specific questions, refer to inline code comments or create an issue in the repository.
