# OAuth 1.0a Registration Guide for Wiki Evaluation Tool

## Purpose

This document provides a technical, step-by-step guide for registering an OAuth 1.0a consumer application on Wikimedia Meta-Wiki for use with the WikiContest evaluation tool. It is based on the project's existing implementation (`backend/app/routes/user_routes.py`, `backend/app/config.py`, `docs/OAUTH_LOCAL_SETUP.md`) and the Wikimedia OAuth consumer registration form.


## Pre-requisites

- A Wikimedia account with permission to register OAuth consumers
- Access to the registration page: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
- A Wikimedia project to associate the consumer with (typically Meta-Wiki)


## Step 1: Navigate to the Registration Form

Visit: `https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration`

Click the link to propose a new OAuth consumer.


## Step 2: Complete the Registration Form

Fill in each field as described below.

| Field | Value | Notes |
|-------|-------|-------|
| **Application name** | `WikiContest` or `WikiContest Evaluation Tool` | Must be unique across Wikimedia OAuth consumers. |
| **Application description** | `A platform for hosting and participating in collaborative online Wikipedia article competitions, with automated evaluation and jury review workflows.` | Be specific about your tool's purpose. |
| **OAuth "callback" URL** | `https://wikicontest.toolforge.org/oauth/callback` | **Must match exactly** the URL your application uses for OAuth callbacks. See Redirect URI section below. |
| **Contact email** | Your valid email address | Used by Wikimedia administrators for consumer approval communications. |
| **Consumer version** | `1.0` | Leave at default unless you have a specific reason to change. |
| **Owner-only** | `No` | Must be `No` to allow any Wikimedia user to authorize the application. |
| **Applicable project** | `Meta-wiki` | Select the Wikimedia project the consumer is associated with. |
| **Allow consumer to specify callback in requests** | `No` | Leave unchecked for security. Prevents the application from dynamically setting callback URLs. |
| **RSA key** | Leave empty | Not required unless you need RSA-SHA1 signing. The project uses HMAC-SHA1. |

### Important Form Notes

1. **OAuth Protocol Version**: The registration form defaults to **OAuth 1.0a** (not OAuth 2.0). Wikimedia uses OAuth 1.0a exclusively.
2. **Grant Types**: After saving, you will configure specific grants/permissions on the next screen.
3. **Terms**: You must agree to the Wikimedia OAuth terms of use.


## Step 3: Configure Applicable Grants (Scopes)

After proposing the consumer, you will be taken to a grants selection screen. Wikimedia OAuth 1.0a uses "grants" instead of OAuth 2.0 "scopes." Select the following grants based on your application's needs.

### Required Grants for WikiContest

| Grant | Checkbox | Required | Purpose |
|-------|----------|----------|---------|
| **Basic rights** | ☑ | Yes | Allows read access to user identity (username, user ID) and basic user info. This is the minimum required for login. |
| **Edit existing pages** | ☑ | Recommended | Allows the application to make edits to MediaWiki pages on behalf of the user. Required for template enforcement and automated editing features. |
| **Upload new files** | ☑ | Optional | Allows file uploads to Wikimedia Commons. Required if your tool needs to upload images or files. |
| **Create, edit, and move pages** | ☑ | Recommended | Allows creating new pages, editing existing ones, and moving pages. Required for full article management. |
| **View your watchlist** | ☑ | Optional | Allows the application to read the user's watchlist. |
| **Edit your preferences** | ☑ | Optional | Allows modifying user preferences. |
| **Send email to other users** | ☐ | No | Not required for basic evaluation functionality. |
| **View deleted pages, revisions, and log entries** | ☐ | No | Not required unless your tool needs to review deleted content. |
| **Block and unblock users** | ☐ | No | Not required for regular evaluation. |

### Grant Selection Strategy

- **Minimum**: Select only `Basic rights` for a read-only evaluation tool.
- **Recommended**: Select `Basic rights`, `Edit existing pages`, `Create, edit, and move pages`, and `View your watchlist`.
- **Full feature set**: Select all grants if your tool performs comprehensive MediaWiki editing on behalf of users.

**Important**: Grants with a warning icon (⚠️) are high-risk permissions. Wikimedia administrators may manually review consumers requesting these grants. Approval may take longer.


## Step 4: Redirect URI Configuration

### What is a Redirect URI?

In Wikimedia OAuth 1.0a, the "callback URL" serves the same purpose as the redirect URI in OAuth 2.0. It is the URL on your application server where Wikimedia sends the user after they authorize the consumer. The callback URL must match **exactly** what is registered.

### For Local Development

| Component | Value |
|-----------|-------|
| Protocol | `http://` |
| Host | `localhost` |
| Port | `5000` |
| Path | `/api/user/oauth/callback` |
| Full URL | `http://localhost:5000/api/user/oauth/callback` |

**Critical rules:**
- Must use `http://`, not `https://`
- Must use `localhost`, not `127.0.0.1`
- Must include the port `:5000` if your Flask server runs on port 5000
- Must include the exact path `/api/user/oauth/callback` (no trailing slash)
- Must match exactly the value configured in `backend/app/config.py` and `backend/.env`

### For Production (Toolforge)

| Component | Value |
|-----------|-------|
| Protocol | `https://` |
| Host | `wikicontest.toolforge.org` |
| Path | `/oauth/callback` |
| Full URL | `https://wikicontest.toolforge.org/oauth/callback` |

### Custom Callback Path Override

If you need a different callback path (e.g., for Toolforge), you can set the `OAUTH_CALLBACK_PATH` environment variable in your `.env` file:

```env
# Toolforge custom callback path
OAUTH_CALLBACK_PATH=/oauth/callback
```

The application will construct the full callback URL as:
```
{scheme}://{host}{OAUTH_CALLBACK_PATH}
```

If `OAUTH_CALLBACK_PATH` is not set, the default `/api/user/oauth/callback` is used.


## Step 5: Submit and Save Credentials

After completing the form and selecting grants:

1. Click **"Propose consumer"**
2. You will be shown your **Consumer Key** and **Consumer Secret**
3. **Copy both immediately** — the Consumer Secret is only displayed once
4. Store them securely in your `backend/.env` file:

```env
# OAuth 1.0a Configuration
OAUTH_MWURI=https://meta.wikimedia.org/w/index.php
CONSUMER_KEY=your-consumer-key-here
CONSUMER_SECRET=your-consumer-secret-here

# OAuth Callback Configuration
OAUTH_USE_OOB=False
OAUTH_CALLBACK_PATH=
```

**Security warnings:**
- Never commit the Consumer Secret to version control
- Treat it like a password
- If lost, you must create a new consumer (it cannot be recovered)


## Step 6: Standard OAuth 1.0a Authorization Flow

Wikimedia uses **OAuth 1.0a**, not OAuth 2.0. The standard flow consists of three steps: **Request Token**, **User Authorization**, and **Access Token**.

### Step 6a: Request Token

When a user clicks "Login with Wikimedia," the application:

1. Reads `CONSUMER_KEY` and `CONSUMER_SECRET` from `.env` via `app/config.py`
2. Builds the callback URL: `http://localhost:5000/api/user/oauth/callback` (or your production URL)
3. Calls `mwoauth.initiate(mw_uri, consumer_token, callback=callback_url)` (`user_routes.py:522`)
4. Receives a `request_token` (with `key` and `secret`) from Wikimedia
5. Stores the token in Flask `session` and in `OAuthTokenCache` for redundancy
6. Redirects the user to Wikimedia's authorization URL

**Key code reference:**
```python
# backend/app/routes/user_routes.py:517-526
consumer_token = mwoauth.ConsumerToken(consumer_key, consumer_secret)
redirect_url, request_token = mwoauth.initiate(
    mw_uri,
    consumer_token,
    callback=callback_param  # callback_url or "oob"
)
session['request_token'] = request_token.key
session['request_secret'] = request_token.secret
```

### Step 6b: User Authorization

1. The user is redirected to `https://meta.wikimedia.org/w/index.php?title=Special:OAuth/authorize&oauth_token=...`
2. The user logs in with their Wikimedia account (if not already logged in)
3. The user sees an authorization prompt showing:
   - Application name
   - Application description
   - Requested permissions (grants)
4. The user clicks **"Allow"** to grant access
5. Wikimedia redirects the user back to the registered callback URL with query parameters:
   - `oauth_token`: The request token
   - `oauth_verifier`: A verification code

### Step 6c: Access Token Exchange

When Wikimedia redirects to `/api/user/oauth/callback`, the application:

1. Extracts `oauth_token` and `oauth_verifier` from query parameters
2. Retrieves the stored `request_token` and `request_secret` from session (or DB cache as fallback)
3. Validates that `oauth_token` matches the stored request token
4. Calls `mwoauth.complete(mw_uri, consumer_token, request_token, response_qs)` (`user_routes.py:658-663`)
5. Receives an `access_token` (with `key` and `secret`)
6. Calls `mwoauth.identify(mw_uri, consumer_token, access_token)` (`user_routes.py:666`) to get the user's Wikimedia identity
7. Creates or updates the local `User` record, storing the OAuth tokens for future MediaWiki API use
8. Creates a JWT access token via `create_access_token(identity=str(user.id))`
9. Sets the JWT in an HTTP-only cookie
10. Redirects the user to the frontend with `?oauth_success=true`

**Key code reference:**
```python
# backend/app/routes/user_routes.py:643-706
consumer_token = mwoauth.ConsumerToken(consumer_key, consumer_secret)
request_token = mwoauth.RequestToken(request_token_key, request_secret)
access_token = mwoauth.complete(mw_uri, consumer_token, request_token, response_qs)
identity = mwoauth.identify(mw_uri, consumer_token, access_token)
```

### Step 6d: Token Storage

The application stores the OAuth tokens in the `User` model:

```python
# backend/app/routes/user_routes.py:692-700
user.oauth_token = access_token.key
user.oauth_token_secret = access_token.secret
user.save()
```

These stored tokens are later used for:
- Making authenticated MediaWiki API calls on behalf of the user
- Template enforcement (editing pages to add contest templates)
- Any other MediaWiki actions requiring user authentication


## Step 7: Configure the Application

Update your `backend/.env` with the credentials:

```env
# OAuth 1.0a Configuration
OAUTH_MWURI=https://meta.wikimedia.org/w/index.php
CONSUMER_KEY=your-new-consumer-key-here
CONSUMER_SECRET=your-new-consumer-secret-here

# OAuth Callback Configuration
OAUTH_USE_OOB=False
OAUTH_CALLBACK_PATH=
```

For production/Toolforge, add:
```env
FRONTEND_URL=https://wikicontest.toolforge.org
```


## Step 8: Test the Flow

1. Start the Flask server: `cd backend && python main.py`
2. Navigate to `http://localhost:5000`
3. Click **"Login"** → **"Login with Wikimedia"**
4. Authorize the application on Wikimedia
5. Verify you are redirected back and logged in


## Important Notes

### Separate Consumers per Environment

OAuth consumers are environment-specific because callback URLs are fixed and cannot be changed after registration. Maintain separate consumers for:
- **Local Development**: `http://localhost:5000/api/user/oauth/callback`
- **Production (Toolforge)**: `https://wikicontest.toolforge.org/oauth/callback`

### OAuth 1.0a vs OAuth 2.0

This implementation uses **OAuth 1.0a**, not OAuth 2.0. Key differences:
- No "authorization code" or "implicit" grant types in the OAuth 2.0 sense
- Uses 3-legged OAuth: Request Token → User Authorization → Access Token
- All requests are signed with HMAC-SHA1 or RSA-SHA1
- No bearer tokens; uses token key + secret pairs

### Token Cache for Multi-Worker Deployments

The application uses `OAuthTokenCache` (database-backed) to store request tokens temporarily. This handles cases where Flask session cookies don't persist across the external redirect to Wikimedia, or when multiple Gunicorn workers are running:

```python
# backend/app/routes/user_routes.py:537
OAuthTokenCache.store(request_token.key, request_token.secret)
```

### Out-of-Band (OOB) Fallback

If your OAuth consumer was registered with `oob` instead of a callback URL, set `OAUTH_USE_OOB=True` in `.env`. The user will then manually enter a verification code. This is less user-friendly and not recommended for web applications.


## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `oauth_callback must be set to oob` | Consumer registered with "oob" | Register new consumer with callback URL, or set `OAUTH_USE_OOB=True` |
| `Invalid redirect URI` or `Callback URL mismatch` | Callback URL doesn't match registration | Verify exact URL match including protocol, host, port, and path |
| `OAuth not configured` | Missing `CONSUMER_KEY` or `CONSUMER_SECRET` | Set both in `backend/.env` |
| OAuth callback returns 404 | Route not registered | Ensure `user_bp` is registered with `url_prefix='/api/user'` |
| Session expired | Session cookies not persisting | Check cookie settings, ensure `session.permanent = True` |
| Consumer not approved | New consumers may require manual approval | Wait for approval or contact Wikimedia admins |


## Summary

1. **Register** at https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
2. **Fill** the form with application details and exact callback URL
3. **Select** required grants (Basic rights minimum, Edit existing pages recommended)
4. **Submit** and copy Consumer Key + Consumer Secret
5. **Configure** `backend/.env` with credentials
6. **Test** the full OAuth 1.0a flow: Request Token → Authorization → Access Token
7. **Verify** the access token is stored and JWT cookie is set correctly
