# Check Your OAuth Consumer Settings

Troubleshooting guide for the "oauth_callback must be set to 'oob'" error.

## Understanding the Error

**Error Message:** "oauth_callback must be set to 'oob'"

This error occurs when there's a mismatch between your OAuth consumer registration and the callback configuration in your application.


## Possibility 1: Consumer Registered with "oob"

Your OAuth consumer may have been registered with **"oob"** (out-of-band) authentication instead of a specific callback URL.

### Check Your Consumer Registration

1. **Navigate to OAuth Consumer Management:**
   - Visit: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration

2. **Find your consumer:**
   - Look for the consumer with key: ``
   - Click **"Update"** or **"Manage"** to view details

3. **Check the callback URL field:**
   
   | Callback URL Value                              | Status   | Issue                          |
   |-------------------------------------------------|----------|--------------------------------|
   | `oob`                                           |  Problem | Consumer registered for out-of-band authentication |
   | `http://localhost:5000/api/user/oauth/callback` |  Correct | Consumer properly configured for callback |
   | Empty or missing                                |  Problem | No callback URL specified      |

### Solution Options

#### Option 1: Update the Consumer (If Possible)

Some OAuth consumers can be updated after registration:

1. Click **"Update"** on your consumer
2. Change **"OAuth 'callback' URL"** to: `http://localhost:5000/api/user/oauth/callback`
3. Save changes
4. Restart your Flask server

**Note:** Not all consumer settings can be modified after approval. If the callback URL field is read-only, use Option 2.

#### Option 2: Use Out-of-Band Authentication

If you cannot update the consumer, configure your application to use out-of-band authentication:

**File: `backend/.env`**
```env
OAUTH_USE_OOB=True
```

**Restart Flask:**
```bash
cd backend
python app.py
```

**How it works:**
1. Click "Login with Wikimedia"
2. You'll be redirected to Wikimedia and receive a verification code
3. Manually enter the verification code in your application
4. Authentication completes

**Limitation:** This is less user-friendly than automatic callback authentication.

## Possibility 2: Callback URL Mismatch

The callback URL your application is sending doesn't match the registered callback URL.

### What Must Match Exactly

The following must be **identical** between your OAuth consumer registration and your application:

| Component | Registered Value           | Application Value          | Must Match |
|-----------|----------------------------|----------------------------|------------|
| Protocol  | `http://`                  | `http://`                  |  Yes       |
| Host      | `localhost`                | `localhost`                |  Yes       |
| Port      | `5000`                     | `5000`                     |  Yes       |
| Path      | `/api/user/oauth/callback` | `/api/user/oauth/callback` |  Yes       |
           
### Common Mismatches

 **Wrong Protocol:**
- Registered: `http://localhost:5000/api/user/oauth/callback`
- Sent: `https://localhost:5000/api/user/oauth/callback`

 **Wrong Host:**
- Registered: `http://localhost:5000/api/user/oauth/callback`
- Sent: `http://127.0.0.1:5000/api/user/oauth/callback`

 **Wrong Port:**
- Registered: `http://localhost:5000/api/user/oauth/callback`
- Sent: `http://localhost:8000/api/user/oauth/callback`

 **Wrong Path:**
- Registered: `http://localhost:5000/api/user/oauth/callback`
- Sent: `http://localhost:5000/oauth/callback`

### How to Debug

1. **Check Flask console logs** when you click "Login with Wikimedia"

2. **Look for the callback URL being used:**
```
   Using OAuth callback URL: http://localhost:5000/api/user/oauth/callback
```

3. **Compare with your registered callback URL:**
   - Go to: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
   - Find your consumer and check the callback URL
   - They must match **exactly**

4. **Check for common issues:**
   - Extra trailing slash: `/api/user/oauth/callback/` 
   - Missing path prefix: `/oauth/callback` 
   - Wrong protocol: `https://` instead of `http://` 

## Quick Fix: Enable Out-of-Band

If you need OAuth working immediately and can't update your consumer:

**File: `backend/.env`**
```env
OAUTH_USE_OOB=True
```

**Restart Flask:**
```bash
cd backend
python app.py
```

**Trade-off:**
-  Works immediately without consumer changes
-  Requires manual verification code entry (less user-friendly)

## Better Solution: Create New Consumer

For the best user experience, create a new OAuth consumer with the correct callback URL:

### Step 1: Register New Consumer

1. Visit: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
2. Click **"Propose an OAuth 1.0a consumer"**
3. Fill out the form:
   - **Application name:** WikiContest Local Development
   - **OAuth callback URL:** `http://localhost:5000/api/user/oauth/callback`
   - **Owner-only:** No
4. Submit and copy the credentials

### Step 2: Update Configuration

**File: `backend/.env`**
```env
# New consumer credentials
CONSUMER_KEY=your-new-consumer-key
CONSUMER_SECRET=your-new-consumer-secret

# Use callback (not out-of-band)
OAUTH_USE_OOB=False
```

### Step 3: Restart and Test
```bash
cd backend
python app.py
```

Test the OAuth flow - it should work smoothly without manual verification codes.


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


## Summary

**If callback URL is "oob":**
- Set `OAUTH_USE_OOB=True` in `.env` (quick fix)
- OR create new consumer with proper callback URL (better solution)

**If callback URL is set but mismatched:**
- Verify exact match between registered and sent URLs
- Check protocol, host, port, and path
- Update consumer or application configuration to match

**Recommended approach:**
- Create a new OAuth consumer specifically for local development
- Use callback URL: `http://localhost:5000/api/user/oauth/callback`
- Set `OAUTH_USE_OOB=False` in `.env`
- Keep a separate consumer for production (Toolforge)


## Related Documentation

- **Create Local OAuth Consumer - Step by Step** - Full guide to creating a new consumer
- **OAuth Callback URL for Local Development** - Detailed callback URL reference
- **OAuth 1.0a Local Development Setup Guide** - Complete OAuth setup instructions