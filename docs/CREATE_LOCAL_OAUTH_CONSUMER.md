# Create Local OAuth Consumer - Step by Step

Complete guide to creating a separate OAuth consumer for local development.



## Problem

Your current OAuth consumer is registered for Toolforge production:
- **Callback URL:** `https://wikicontest.toolforge.org/oauth/callback`
- **Environment:** Production (Toolforge)
- **Problem:** This won't work for localhost development!



## Solution: Create a NEW OAuth Consumer

You need a separate OAuth consumer specifically for local development with a localhost callback URL.



## Step-by-Step Registration

### Step 1: Navigate to OAuth Registration

Visit: **https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration**

Click **"Propose an OAuth 1.0a consumer"** (or similar button)



### Step 2: Complete the Registration Form

Fill out each field carefully:

#### Application Name
```
WikiContest Local Development
```
**Note:** Use a different name from your Toolforge consumer to distinguish between environments.

#### Consumer Version
```
1.0
```

#### OAuth Protocol Version
```
OAuth 1.0a
```
 **Must match:** Your code uses OAuth 1.0a protocol.

#### Application Description
```
Local development instance of WikiContest for testing and development purposes
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
 **IMPORTANT:** Must be set to "No" to allow other users to test your application!

#### Applicable Grants / Permissions
```
☑ Basic rights (user rights)
```
Select the permissions your application needs. For WikiContest, basic rights are typically sufficient.



### Step 3: Submit and Save Credentials

After clicking **"Propose consumer"**, you'll receive:

- **Consumer Key:** (e.g., `3f383c834a07a181723f1a1de566f7cf`)
- **Consumer Secret:** (e.g., `62c40e0fde2377613d1f82b9b7aabc9fe2a73b30`)

 **CRITICAL:** Copy BOTH credentials immediately! The consumer secret is only displayed once. If you lose it, you'll need to create a new consumer.

**Save them to a secure location temporarily.**



### Step 4: Update Your Configuration

Open `backend/.env` and update the OAuth credentials:
```env
# OAuth Configuration for Local Development
OAUTH_MWURI=https://meta.wikimedia.org/w/index.php
CONSUMER_KEY=your-new-local-consumer-key-here
CONSUMER_SECRET=your-new-local-consumer-secret-here

# OAuth Callback Configuration
OAUTH_USE_OOB=False
```

Replace `your-new-local-consumer-key-here` and `your-new-local-consumer-secret-here` with your actual credentials from Step 3.



### Step 5: Restart Flask Server

Stop your Flask server if it's running (`Ctrl+C`), then restart it:
```bash
cd backend
python app.py
```

Verify the server starts successfully on `http://localhost:5000`.



### Step 6: Test OAuth Authentication

1. **Open your browser** and navigate to: `http://localhost:5000`
2. **Click "Login"** or "Login with Wikimedia"
3. **Authorize the application:**
   - You'll be redirected to Wikimedia
   - Log in with your Wikimedia account (if not already logged in)
   - Click **"Allow"** to authorize the application
4. **Verify redirect:**
   - After authorization, you should be redirected to: `http://localhost:5000/api/user/oauth/callback`
   - The application processes the callback and logs you in
   - You should be redirected to the home page with an active session



## Why You Need Separate Consumers

OAuth consumers are environment-specific because callback URLs are fixed and cannot be changed after registration.

| Environment                                           | Consumer | Callback URL       |
|-|-|--|
| **Local Development**                                 | WikiContest Local Development | `http://localhost:5000/api/user/oauth/callback` |
| **Production (Toolforge)**                            | WikiContest                   | `https://wikicontest.toolforge.org/oauth/callback` |

**Benefits of separation:**
- Test OAuth flows safely without affecting production
- Different callback URLs for different environments
- Separate credentials for better security
- Independent consumer management



## Troubleshooting

### Error: "Invalid redirect URI" or "Callback URL mismatch"

**Cause:** The callback URL in your OAuth consumer registration doesn't match what the application is sending.

**Solution:**
1. Verify your consumer registration at: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
2. Ensure the callback URL is EXACTLY: `http://localhost:5000/api/user/oauth/callback`
3. Check there are no typos (extra spaces, wrong protocol, wrong port)
4. If incorrect, you must create a new consumer with the correct callback URL



### Error: "Owner-only consumer"

**Cause:** The OAuth consumer is set to "Owner-only: Yes", which restricts access to only the consumer owner.

**Solution:**
1. Create a new OAuth consumer
2. Set **"Owner-only"** to **"No"** during registration
3. Update your `.env` file with the new credentials



### Still Redirecting to Toolforge

**Cause:** Your `.env` file is using Toolforge consumer credentials instead of local development credentials.

**Solution:**
1. Verify `CONSUMER_KEY` and `CONSUMER_SECRET` in `backend/.env`
2. Ensure they match the credentials from your **local development consumer** (not Toolforge)
3. Restart Flask server after updating `.env`



### OAuth Callback Returns 404

**Cause:** The callback route is not properly registered or Flask server is not running.

**Solution:**
1. Verify Flask server is running on `http://localhost:5000`
2. Check that the user blueprint is registered:
```python
   app.register_blueprint(user_bp, url_prefix='/api/user')
```
3. Confirm the callback route exists in `routes/user_routes.py`:
```python
   @user_bp.route('/oauth/callback', methods=['GET'])
   def oauth_callback():
       # OAuth callback handler
```



### Error: "oauth_callback must be set to oob"

**Cause:** Your OAuth consumer was registered with "out-of-band" (oob) authentication instead of a callback URL.

**Solution:**
1. Create a new OAuth consumer
2. Ensure you provide a callback URL: `http://localhost:5000/api/user/oauth/callback`
3. Do NOT select "out-of-band" authentication



### Consumer Not Approved Yet

**Cause:** New OAuth consumers may require approval by Wikimedia administrators.

**Solution:**
- Most consumers with basic rights are approved automatically within a few minutes
- Check your consumer status at: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
- If approval is delayed, you may need to contact Wikimedia administrators



## Verification Checklist

After completing all steps, verify:

- [ ] OAuth consumer registered with correct callback URL
- [ ] Consumer credentials saved securely
- [ ] `.env` file updated with local consumer credentials
- [ ] `OAUTH_USE_OOB=False` in `.env`
- [ ] Flask server restarted successfully
- [ ] OAuth login redirects to Wikimedia
- [ ] OAuth callback redirects back to localhost
- [ ] User successfully authenticated and logged in



## Summary

**Key Points:**
- Create a **separate** OAuth consumer for local development
- Use callback URL: `http://localhost:5000/api/user/oauth/callback`
- Set "Owner-only" to "No" for testing with multiple users
- Save credentials immediately (consumer secret shown only once)
- Update `.env` with local consumer credentials
- Keep Toolforge consumer separate for production use

**Environment Comparison:**

| Setting                     | Local Development             | Production (Toolforge) |
|--|-||
| **Consumer Name**           | WikiContest Local Development | WikiContest            |
| **Callback URL**            |`http://localhost:5000/api/user/oauth/callback`|`https://wikicontest.toolforge.org/oauth/callback`                                                          |
| **Protocol**                | HTTP                          | HTTPS                  |
| **Config File**             | `.env`                        | `config.toml`          |
| **OAUTH_CALLBACK_PATH**     | Not set (uses default)        | `/oauth/callback`      |



## Related Documentation

- **OAuth 1.0a Local Development Setup Guide** - General OAuth setup instructions
- **OAuth Callback URL for Local Development** - Detailed callback URL reference
- **OAuth Configuration for Toolforge Deployment** - Production OAuth setup