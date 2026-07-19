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
   - **Consumer Key** (e.g., ``)
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
   python main.py
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
| **Production/Toolforge** | `https://WikiEval.toolforge.org/oauth/callback` |

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


## URL Components

| Component    | Value                      | Notes |
|--------------|----------------------------|-------|
| **Protocol** | `http://`                  | NOT `https://` |
| **Host**     | `localhost`                | NOT `127.0.0.1` or any domain name |
| **Port**     | `5000`                     | Must match your Flask server port |
| **Path**     | `/api/user/oauth/callback` | Exact path, no trailing slash |

## Custom Port Configuration

If your Flask server runs on a different port, adjust the callback URL accordingly.

**Example for port 8000:**
```
http://localhost:8000/api/user/oauth/callback
```

**Example for port 3000:**
```
http://localhost:3000/api/user/oauth/callback
```


## Common Mistakes

### Incorrect URLs

| Wrong URL                                          | Issue                                      |
|----------------------------------------------------|--------------------------------------------|
| `https://localhost:5000/api/user/oauth/callback`   | Using `https://` instead of `http://`      |
| `http://127.0.0.1:5000/api/user/oauth/callback`    | Using IP address instead of `localhost`    |
| `http://localhost:5000/oauth/callback`             | Missing `/api/user` prefix                 |
| `http://localhost/api/user/oauth/callback`         | Missing port number (`:5000`)              |
| `http://localhost:5000/api/user/oauth/callback/`   | Extra trailing slash                       |
| `https://WikiEval.toolforge.org/oauth/callback` | Using production URL for local development |

### Correct URL
```
http://localhost:5000/api/user/oauth/callback
```


## Post-Registration Steps

After successfully registering your OAuth consumer:

1. **Copy the credentials:**
   - Consumer Key
   - Consumer Secret

2. **Update your configuration file:**

   **File: `backend/.env`**
```env
   CONSUMER_KEY=your-consumer-key-here
   CONSUMER_SECRET=your-consumer-secret-here
   OAUTH_USE_OOB=False
```

3. **Restart the Flask server:**
```bash
   cd backend
   python main.py
```

4. **Test OAuth authentication:**
   - Navigate to `http://localhost:5000`
   - Click "Login with Wikimedia"
   - Authorize the application
   - Verify successful redirect and login


## Detailed Registration Form

When completing the OAuth consumer registration form on Wikimedia Meta:

#### Application Name
```
WikiEval Local Development
```
**Note:** Use a different name from your Toolforge consumer to distinguish between environments.

#### OAuth Protocol Version
```
OAuth 1.0a
```

#### Application Description
```
Local development instance of WikiEval for testing and development purposes
```

#### OAuth "callback" URL
```
http://localhost:5000/api/user/oauth/callback
```

**CRITICAL - Must be EXACTLY:**
- **Protocol:** `http://` (NOT `https://`)
- **Host:** `localhost` (NOT `127.0.0.1` or any domain)
- **Port:** `5000` (must match your Flask server port)
- **Path:** `/api/user/oauth/callback` (exact path, no trailing slash)

#### Allow Consumer to Specify a Callback in Requests
```
☐ No (Leave unchecked)
```

#### Owner-only
```
☐ No (Leave unchecked)
```

#### Applicable Grants / Permissions
```
☑ Basic rights (user rights)
```

### Step 3: Submit and Save Credentials

After clicking **"Propose consumer"**, you'll receive:

- **Consumer Key:**
- **Consumer Secret:**

**CRITICAL:** Copy BOTH credentials immediately! The consumer secret is only displayed once. If you lose it, you'll need to create a new consumer.


## Why You Need Separate Consumers

OAuth consumers are environment-specific because callback URLs are fixed and cannot be changed after registration.

| Environment                                           | Consumer | Callback URL       |
|--|-|--|
| **Local Development**                                 | WikiEval Local Development | `http://localhost:5000/api/user/oauth/callback` |
| **Production (Toolforge)**                            | WikiEval                   | `https://WikiEval.toolforge.org/oauth/callback` |

**Benefits of separation:**
- Test OAuth flows safely without affecting production
- Different callback URLs for different environments
- Separate credentials for better security
- Independent consumer management


## Debugging Callback Issues

### Possibility 1: Consumer Registered with "oob"

Your OAuth consumer may have been registered with **"oob"** (out-of-band) authentication instead of a specific callback URL.

**Check Your Consumer Registration:**
1. Navigate to: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
2. Find your consumer and click **"Update"** or **"Manage"**
3. Check the callback URL field:

| Callback URL Value                              | Status   | Issue                          |
|-------------------------------------------------|----------|--------------------------------|
| `oob`                                           | Problem  | Consumer registered for out-of-band authentication |
| `http://localhost:5000/api/user/oauth/callback` | Correct  | Consumer properly configured for callback |
| Empty or missing                                | Problem  | No callback URL specified      |

**Solution Options:**

**Option 1: Update the Consumer (If Possible)**
1. Click **"Update"** on your consumer
2. Change **"OAuth 'callback' URL"** to: `http://localhost:5000/api/user/oauth/callback`
3. Save changes
4. Restart your Flask server

**Note:** Not all consumer settings can be modified after approval. If the callback URL field is read-only, use Option 2.

**Option 2: Use Out-of-Band Authentication**
If you cannot update the consumer, configure your application to use out-of-band authentication:

**File: `backend/.env`**
```env
OAUTH_USE_OOB=True
```

**Restart Flask:**
```bash
cd backend
python main.py
```

**How it works:**
1. Click "Login with Wikimedia"
2. You'll be redirected to Wikimedia and receive a verification code
3. Manually enter the verification code in your application
4. Authentication completes

**Limitation:** This is less user-friendly than automatic callback authentication.

### Possibility 2: Callback URL Mismatch

The callback URL your application is sending doesn't match the registered callback URL.

**What Must Match Exactly:**

| Component | Registered Value           | Application Value          | Must Match |
|-----------|----------------------------|----------------------------|------------|
| Protocol  | `http://`                  | `http://`                  | Yes        |
| Host      | `localhost`                | `localhost`                | Yes        |
| Port      | `5000`                     | `5000`                     | Yes        |
| Path      | `/api/user/oauth/callback` | `/api/user/oauth/callback` | Yes        |

**Common Mismatches:**
- **Wrong Protocol:** Registered: `http://...` Sent: `https://...`
- **Wrong Host:** Registered: `http://localhost...` Sent: `http://127.0.0.1...`
- **Wrong Port:** Registered: `http://localhost:5000...` Sent: `http://localhost:8000...`
- **Wrong Path:** Registered: `/api/user/oauth/callback` Sent: `/oauth/callback`

**How to Debug:**
1. Check Flask console logs when you click "Login with Wikimedia"
2. Look for the callback URL being used
3. Compare with your registered callback URL at: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
4. They must match exactly
5. Check for common issues:
   - Extra trailing slash: `/api/user/oauth/callback/`
   - Missing path prefix: `/oauth/callback`
   - Wrong protocol: `https://` instead of `http://`


## Owner-only Consumer

**Cause:** The OAuth consumer is set to "Owner-only: Yes", which restricts access to only the consumer owner.

**Solution:**
1. Create a new OAuth consumer
2. Set **"Owner-only"** to **"No"** during registration
3. Update your `.env` file with the new credentials


## Consumer Not Approved Yet

**Cause:** New OAuth consumers may require approval by Wikimedia administrators.

**Solution:**
- Most consumers with basic rights are approved automatically within a few minutes
- Check your consumer status at: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
- If approval is delayed, you may need to contact Wikimedia administrators


## Verification Checklist

After applying your fix, verify:

- [ ] OAuth consumer found at https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
- [ ] Callback URL is either `oob` or `http://localhost:5000/api/user/oauth/callback`
- [ ] `.env` file has correct `CONSUMER_KEY` and `CONSUMER_SECRET`
- [ ] `.env` file has `OAUTH_USE_OOB` set correctly:
  - `True` if consumer uses "oob"
  - `False` if consumer uses callback URL
- [ ] Flask server restarted after configuration changes
- [ ] OAuth login redirects properly
- [ ] Authentication completes successfully


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
