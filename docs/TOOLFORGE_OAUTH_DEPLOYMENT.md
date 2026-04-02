# OAuth Configuration for Toolforge Deployment

This guide explains how to configure OAuth authentication when deploying your application to Toolforge.



## Quick Summary

When deploying to Toolforge, you need to update **three configuration settings**:

1. **OAuth Consumer Credentials** – Use the Toolforge consumer (not local development consumer)
2. **Callback Path** – Set `OAUTH_CALLBACK_PATH = "/oauth/callback"`
3. **Callback URL** – Ensure your Toolforge consumer uses: `https://wikicontest.toolforge.org/oauth/callback`



## Environment Differences: Local vs. Production

### Local Development (Current Setup)

- **Consumer Key:** ``
- **Consumer Secret:** ``
- **Callback URL:** `http://localhost:5000/api/user/oauth/callback`
- **OAUTH_CALLBACK_PATH:** Not set (uses default)

### Toolforge Production (Required Setup)

- **Consumer Key:** ``
- **Consumer Secret:** ``
- **Callback URL:** `https://wikicontest.toolforge.org/oauth/callback`
- **OAUTH_CALLBACK_PATH:** `/oauth/callback` (must be set)



## Step-by-Step Configuration

### Step 1: Verify Your Toolforge OAuth Consumer

Your Toolforge OAuth consumer should already be registered with the following details:

- **Consumer Key:** ``
- **Callback URL:** `https://wikicontest.toolforge.org/oauth/callback`
- **Status:** Approved  
- **Owner-only:** No  

**Verify your consumer at:**  
https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/update/

### Step 2: Update Configuration File

On Toolforge, use `config.toml` (not `.env`) for configuration. Add the following OAuth settings:
```toml
# OAuth Configuration for Toolforge
OAUTH_MWURI = "https://meta.wikimedia.org/w/index.php"
CONSUMER_KEY = ""
CONSUMER_SECRET = ""

# OAuth Callback Path - CRITICAL for Toolforge!
# This tells the application to use /oauth/callback instead of /api/user/oauth/callback
OAUTH_CALLBACK_PATH = "/oauth/callback"

# OAuth Callback Type
OAUTH_USE_OOB = false
```

### Step 3: Understand How the Code Works

The application automatically detects the callback path based on your configuration.

**Code reference: `backend/routes/user_routes.py` (lines 376-382)**
```python
custom_callback_path = current_app.config.get('OAUTH_CALLBACK_PATH', None)
if custom_callback_path:
    # Use custom callback path (e.g., /oauth/callback for Toolforge)
    callback_url = f"{scheme}://{host}{custom_callback_path}"
else:
    # Use default blueprint route path (for localhost)
    callback_url = f"{scheme}://{host}/api/user/oauth/callback"
```

**When `OAUTH_CALLBACK_PATH = "/oauth/callback"` is set:**
- Builds: `https://wikicontest.toolforge.org/oauth/callback`  
- Matches your Toolforge OAuth consumer registration  

**When `OAUTH_CALLBACK_PATH` is not set (local development):**
- Builds: `http://localhost:5000/api/user/oauth/callback`  
- Matches your local OAuth consumer registration  

### Step 4: Route Handling

The route `/oauth/callback` is already configured in `backend/app.py` (line 284):
```python
@app.route('/oauth/callback', methods=['GET'])
def oauth_callback():
    # Redirects to /api/user/oauth/callback with query parameters
    # This handles the Toolforge callback URL
```

This route redirects to the blueprint handler, so the actual OAuth processing happens at `/api/user/oauth/callback`. No code changes are required.



## Complete Toolforge Configuration

### File: `config.toml` (Location: `$HOME/www/python/src/config.toml` on Toolforge)
```toml
# Security (generate new keys for production!)
SECRET_KEY = "your-generated-secret-key-here"
JWT_SECRET_KEY = "your-generated-jwt-secret-key-here"

# Database
SQLALCHEMY_DATABASE_URI = "mysql://username:password@tools-db/database_name"
SQLALCHEMY_TRACK_MODIFICATIONS = false

# JWT Configuration
JWT_ACCESS_TOKEN_EXPires = 86400

# Debug mode (set to false for production)
DEBUG = false

# OAuth Configuration - TOOLFORGE SETTINGS
OAUTH_MWURI = "https://meta.wikimedia.org/w/index.php"
CONSUMER_KEY = ""
CONSUMER_SECRET = ""

# OAuth Callback Path - MUST BE SET FOR TOOLFORGE
OAUTH_CALLBACK_PATH = "/oauth/callback"

# OAuth Callback Type
OAUTH_USE_OOB = false
```



## Configuration File Locations

### Local Development

**File:** `backend/.env`
```env
CONSUMER_KEY=
CONSUMER_SECRET=
# OAUTH_CALLBACK_PATH is not set (uses default)
```

### Toolforge Production

**File:** `$HOME/www/python/src/config.toml`
```toml
CONSUMER_KEY = ""
CONSUMER_SECRET = ""
OAUTH_CALLBACK_PATH = "/oauth/callback"  # MUST SET THIS!
```

### Code Changes

**No code changes are needed!** The application already handles both environments:

-   Detects `OAUTH_CALLBACK_PATH` from configuration
-   Uses custom path if set, otherwise uses default `/api/user/oauth/callback`
-   Route `/oauth/callback` already exists in `app.py`

Simply update the configuration file for your target environment.



## Pre-Deployment Checklist

Before deploying to Toolforge, verify the following:

- [ ] OAuth consumer registered with callback: `https://wikicontest.toolforge.org/oauth/callback`
- [ ] `config.toml` contains Toolforge consumer credentials
- [ ] `config.toml` has `OAUTH_CALLBACK_PATH = "/oauth/callback"`
- [ ] `OAUTH_USE_OOB = false` in configuration
- [ ] Route `/oauth/callback` exists in `app.py` (already present)
- [ ] Test OAuth login flow after deployment



## Verification and Testing

### Check Callback URL in Logs

When a user clicks "Login with Wikimedia" on Toolforge:

1. Check Flask logs for: `Using OAuth callback URL: https://wikicontest.toolforge.org/oauth/callback`
2. Verify this matches your OAuth consumer registration

### Test the OAuth Flow

1. Navigate to: https://wikicontest.toolforge.org
2. Click **"Login with Wikimedia"**
3. Verify redirect to Wikimedia for authentication
4. Verify redirect back to Toolforge after authentication
5. Confirm successful login



## Troubleshooting

### Error: "oauth_callback must be set to oob"

**Cause:** `OAUTH_CALLBACK_PATH` is not set in the configuration file.

**Solution:** Add `OAUTH_CALLBACK_PATH = "/oauth/callback"` to `config.toml`.

### Error: "Invalid redirect URI"

**Cause:** The callback URL doesn't match the registered OAuth consumer callback.

**Solution:** Verify your consumer registration uses: `https://wikicontest.toolforge.org/oauth/callback`

### Error: "OAuth session expired"

**Cause:** Session cookies are not persisting correctly.

**Solution:** The cache fallback mechanism should handle this. If the issue persists, verify your session configuration settings.



## Summary

### Local Development

- **Consumer:** ``
- **OAUTH_CALLBACK_PATH:** Not set (uses default)
- **Callback URL:** `http://localhost:5000/api/user/oauth/callback`

### Toolforge Production

- **Consumer:** ``
- **OAUTH_CALLBACK_PATH:** `/oauth/callback` (must be set)
- **Callback URL:** `https://wikicontest.toolforge.org/oauth/callback`

**Important:** No code changes are required. Only update the configuration file for your deployment environment.