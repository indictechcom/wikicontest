# Critical Issues Report - WikiContest

**Generated:** $(date)  
**Status:**  CRITICAL - Immediate Action Required

## Executive Summary

This report identifies **6 critical security and configuration issues** that must be addressed before production deployment. These issues pose significant security risks including:

- Hardcoded secrets that could compromise authentication
- Unauthenticated endpoints exposing sensitive user data
- OAuth credentials exposed in repository
- Production debug mode enabled
- Weak default passwords

---

## 🔴 CRITICAL ISSUE #1: Hardcoded Secrets

**Severity:** CRITICAL  
**File:** `backend/app/__init__.py`  
**Lines:** 83-84

### Problem
Default secret keys are hardcoded with weak values (`'rohank10'`). If environment variables are not set, the application will use these insecure defaults.

### Code Location
```python
flask_app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'rohank10')
flask_app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'rohank10')
```

### Impact
- **Authentication bypass:** Weak secrets can be brute-forced
- **Session hijacking:** Compromised JWT tokens
- **Data integrity:** Tampered session data

### Fix Required
1. Remove hardcoded defaults
2. Require environment variables to be set
3. Generate secure random secrets if not provided (with warning)

### Recommended Fix
```python
# Option 1: Fail if not set (recommended for production)
SECRET_KEY = os.getenv('SECRET_KEY')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
if not SECRET_KEY or not JWT_SECRET_KEY:
    raise ValueError("SECRET_KEY and JWT_SECRET_KEY must be set in environment")

# Option 2: Generate with warning (development only)
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_urlsafe(48)
    print("WARNING: Generated temporary SECRET_KEY. Set SECRET_KEY in environment for production!")
```

---

## 🔴 CRITICAL ISSUE #2: Unauthenticated Debug Endpoint

**Severity:** CRITICAL  
**File:** `backend/app/__init__.py`  
**Lines:** 356-432

### Problem
The `/api/debug/user-role/<username>` endpoint is accessible without authentication and exposes sensitive user information including:
- User ID
- Email address
- Role information
- Internal database structure

### Code Location
```python
@app.route('/api/debug/user-role/<username>', methods=['GET'])
def debug_user_role(username):
    # No @require_auth decorator!
    # Exposes: id, username, email, role
```

### Impact
- **Information disclosure:** User emails and roles exposed
- **User enumeration:** Attackers can check if usernames exist
- **Privilege escalation:** Role information helps plan attacks

### Fix Required
1. Add `@require_auth` and `@require_role('admin')` decorators
2. OR remove the endpoint entirely if not needed
3. OR restrict to localhost/development only

### Recommended Fix
```python
@app.route('/api/debug/user-role/<username>', methods=['GET'])
@require_auth
@require_role('admin')  # Only admins can access
@handle_errors
def debug_user_role(username):
    # ... existing code ...
```

**OR** Remove entirely if not needed in production.

---

## 🔴 CRITICAL ISSUE #3: OAuth Secrets in Repository

**Severity:** CRITICAL  
**File:** `backend/toolforge/toolforge_config.toml`  
**Lines:** 19-20

### Problem
OAuth consumer key and secret are hardcoded in a configuration file that may be committed to version control.

### Code Location
```toml
CONSUMER_KEY = "3f383c834a07a181723f1a1de566f7cf"
CONSUMER_SECRET = "62c40e0fde2377613d1f82b9b7aabc9fe2a73b30"
```

### Impact
- **Account compromise:** If repository is public, OAuth credentials are exposed
- **Unauthorized access:** Attackers can impersonate the application
- **Data breach:** Access to user OAuth tokens

### Fix Required
1. **IMMEDIATELY:** Revoke and regenerate OAuth consumer credentials
2. Move secrets to environment variables or secure secret management
3. Add `toolforge_config.toml` to `.gitignore` if not already
4. Use `.env.example` with placeholder values

### Recommended Fix
1. Revoke current OAuth consumer at: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
2. Create new OAuth consumer
3. Store credentials in environment variables:
   ```bash
   export CONSUMER_KEY="new_key_here"
   export CONSUMER_SECRET="new_secret_here"
   ```
4. Update code to read from environment only
5. Add to `.gitignore`:
   ```
   backend/toolforge/toolforge_config.toml
   *.toml
   ```

---

## 🟠 CRITICAL ISSUE #4: Debug Mode in Production Code

**Severity:** HIGH  
**Files:** 
- `backend/app/__init__.py:978`
- `backend/main.py:24`

### Problem
Debug mode is hardcoded to `True` in the application startup code. This should be controlled by environment variables.

### Code Location
```python
# backend/app/__init__.py:978
app.run(
    debug=True,        #  Hardcoded!
    host='0.0.0.0',
    port=5000
)
```

### Impact
- **Information leakage:** Detailed error pages expose internal structure
- **Performance:** Auto-reload enabled in production
- **Security:** Debug toolbar may expose sensitive data

### Fix Required
1. Use environment variable to control debug mode
2. Default to `False` for production safety
3. Only enable in development explicitly

### Recommended Fix
```python
# backend/app/__init__.py
if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(
        debug=debug_mode,  # Controlled by environment
        host='0.0.0.0',
        port=5000
    )
```

---

## 🟠 CRITICAL ISSUE #5: Default Database Password

**Severity:** MEDIUM-HIGH  
**File:** `backend/app/config.py`  
**Line:** 54

### Problem
Default database connection string includes weak default password `'password'`.

### Code Location
```python
SQLALCHEMY_DATABASE_URI = os.getenv(
    'DATABASE_URL',
    'mysql+pymysql://root:password@localhost/wikicontest'  #  Weak default
)
```

### Impact
- **Database compromise:** If environment variable not set, uses weak password
- **Data breach:** Unauthorized database access

### Fix Required
1. Remove default password (require DATABASE_URL to be set)
2. OR use SQLite for development (no password needed)
3. Document requirement in README

### Recommended Fix
```python
# Option 1: Require DATABASE_URL (recommended)
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
if not SQLALCHEMY_DATABASE_URI:
    raise ValueError("DATABASE_URL must be set in environment")

# Option 2: Use SQLite for development
SQLALCHEMY_DATABASE_URI = os.getenv(
    'DATABASE_URL',
    'sqlite:///wikicontest_dev.db'  # No password needed
)
```

---

## 🟡 CRITICAL ISSUE #6: Missing Error Handler on Update Route

**Severity:** MEDIUM  
**File:** `backend/app/routes/contest_routes.py`  
**Line:** 690

### Problem
The `update_contest` route has `@require_auth` but is missing `@handle_errors` decorator, which could lead to inconsistent error handling.

### Code Location
```python
@contest_bp.route("/<int:contest_id>", methods=["PUT"])
@require_auth
#  Missing @handle_errors
def update_contest(contest_id):
```

### Impact
- **Inconsistent error responses:** Different error format than other routes
- **Information leakage:** Unhandled exceptions may expose internal details
- **Poor user experience:** Generic 500 errors instead of helpful messages

### Fix Required
Add `@handle_errors` decorator for consistency.

### Recommended Fix
```python
@contest_bp.route("/<int:contest_id>", methods=["PUT"])
@require_auth
@handle_errors  # Add this
def update_contest(contest_id):
```

---

## Priority Action Items

### Immediate (Before Any Production Deployment)

1.  **Fix hardcoded secrets** - Remove `'rohank10'` defaults
2.  **Secure debug endpoint** - Add authentication or remove
3.  **Revoke OAuth credentials** - Generate new ones, move to env vars
4.  **Disable debug mode** - Use environment variable

### High Priority (Before Next Release)

5.  **Fix database password default** - Require DATABASE_URL
6.  **Add error handler** - Fix update_contest route

### Additional Recommendations

- Review all endpoints for missing authentication
- Add security headers (HSTS, CSP, X-Frame-Options)
- Implement rate limiting on authentication endpoints
- Add input validation on all user inputs
- Regular security audits

---

## Testing Checklist

After fixes are applied, verify:

- [ ] No hardcoded secrets in codebase
- [ ] All sensitive endpoints require authentication
- [ ] Debug mode disabled in production
- [ ] OAuth credentials in environment variables only
- [ ] Database connection requires explicit configuration
- [ ] All routes have consistent error handling

---

## Notes

- These issues were identified without affecting working features
- All fixes should be backward compatible where possible
- Test thoroughly after each fix
- Consider security audit before production deployment
