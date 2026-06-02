# OAuth 1.0a Local Development Setup Guide

This guide walks you through setting up OAuth 1.0a authentication for local development with Wikimedia accounts.



## Overview

OAuth 1.0a allows users to authenticate using their Wikimedia accounts. For local development, you need to register a separate OAuth consumer with a callback URL pointing to your local server.



## Step 1: Register OAuth Consumer

Register an OAuth consumer for local development on Wikimedia Meta.

1. **Navigate to OAuth Consumer Registration:**
   - Visit: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration

2. **Complete the registration form:**
   
   | Field                       | Value                                                  |
   |-----------------------------|--------------------------------------------------------|
   | **Application name**        | WikiEval Local Development (or your preferred name) |
   | **Application description** | Local development instance of WikiEval              |
   | **OAuth "callback" URL**    | `http://localhost:5000/api/user/oauth/callback`        |
   | **Contact email**           | Your email address                                     |
   | **Grant settings**          | Request authorization for "Basic rights" (or required permissions) |

   **Important:** The callback URL must match exactly, including:
   - Protocol: `http://` (not `https://`)
   - Host: `localhost`
   - Port: `5000`
   - Path: `/api/user/oauth/callback`

3. **Submit and save credentials:**
   
   After submission, you'll receive:
   - **Consumer Key** (e.g., `3f383c834a07a181723f1a1de566f7cf`)
   - **Consumer Secret** (a long hexadecimal string)
   
   Copy both values – you'll need them in the next step.



## Step 2: Configure Your Application

Update your `backend/.env` file with the OAuth credentials.

**File: `backend/.env`**
```env
# OAuth 1.0a Configuration
OAUTH_MWURI=https://meta.wikimedia.org/w/index.php
CONSUMER_KEY=your-new-consumer-key-here
CONSUMER_SECRET=your-new-consumer-secret-here

# OAuth Callback Configuration
# Set to False for local development with callback URL
OAUTH_USE_OOB=False
```

Replace `your-new-consumer-key-here` and `your-new-consumer-secret-here` with the credentials from Step 1.



## Step 3: Test OAuth Authentication

Verify that OAuth authentication is working correctly.

1. **Start the Flask server:**
```bash
   cd backend
   python app.py
```

2. **Open your browser and navigate to:**
```
   http://localhost:5000
```

3. **Initiate OAuth login:**
   - Click the **"Login"** button
   - Click **"Login with Wikimedia"**

4. **Authorize the application:**
   - You'll be redirected to Wikimedia
   - Log in with your Wikimedia account (if not already logged in)
   - Click **"Allow"** to authorize the application

5. **Verify successful authentication:**
   - After authorization, you'll be redirected to: `http://localhost:5000/api/user/oauth/callback`
   - The application processes the OAuth callback and logs you in
   - You'll be redirected to the home page with an active session



## Troubleshooting

### Error: "oauth_callback must be set to oob"

**Cause:** Your OAuth consumer was registered with "oob" (out-of-band) authentication instead of a callback URL.

**Solution:** Register a new OAuth consumer with the callback URL set to: `http://localhost:5000/api/user/oauth/callback`



### Error: "Invalid redirect URI" or "Callback URL mismatch"

**Cause:** The callback URL in your OAuth consumer registration doesn't match the URL your application is using.

**Solution:**

1. Verify your OAuth consumer registration at: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
2. Ensure the callback URL is exactly: `http://localhost:5000/api/user/oauth/callback`
3. If the URL doesn't match, either:
   - Update the OAuth consumer registration to use the correct URL, **OR**
   - Update `OAUTH_CALLBACK_PATH` in your `.env` file to match the registered URL



### Error: "OAuth not configured"

**Cause:** Missing `CONSUMER_KEY` or `CONSUMER_SECRET` in your `.env` file.

**Solution:** Verify that both `CONSUMER_KEY` and `CONSUMER_SECRET` are set in your `backend/.env` file.



### OAuth Callback Returns 404

**Cause:** The route `/api/user/oauth/callback` is not accessible or not properly registered.

**Solution:**

1. Ensure the Flask server is running on `http://localhost:5000`
2. Verify the user blueprint is registered in your Flask app:
```python
   app.register_blueprint(user_bp, url_prefix='/api/user')
```
3. Confirm the callback route exists in `routes/user_routes.py`:
```python
   @user_bp.route('/oauth/callback', methods=['GET'])
   def oauth_callback():
       # OAuth callback handler
```



## Important Notes

### Separate OAuth Consumers

You should maintain separate OAuth consumers for different environments:

| Environment | Callback URL |
|-------------|-------------|
| **Local Development** | `http://localhost:5000/api/user/oauth/callback` |
| **Production/Toolforge** | `https://wikicontest.toolforge.org/oauth/callback` |

This separation ensures:
- Local testing doesn't affect production authentication
- Different callback URLs can be used for each environment
- Better security by isolating credentials

### OAuth Consumer Approval

- New OAuth consumers requesting basic rights are typically approved automatically
- Approval may take a few minutes to process
- Consumers requesting elevated permissions may require manual administrator approval
- Check your OAuth consumer status at: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration

### Testing Strategy

Create a dedicated OAuth consumer for local development to:
- Avoid conflicts with production OAuth settings
- Test authentication flows safely
- Maintain separate credentials for security

---

## Summary

**Quick Setup Checklist:**

- [ ] Register OAuth consumer on Wikimedia Meta
- [ ] Set callback URL to `http://localhost:5000/api/user/oauth/callback`
- [ ] Copy Consumer Key and Consumer Secret
- [ ] Update `backend/.env` with OAuth credentials
- [ ] Set `OAUTH_USE_OOB=False` in `.env`
- [ ] Start Flask server and test OAuth login flow

For production deployment to Toolforge, refer to the **OAuth Configuration for Toolforge Deployment** guide.