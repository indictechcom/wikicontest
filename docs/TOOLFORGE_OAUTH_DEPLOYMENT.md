# OAuth Configuration for Toolforge Deployment

This guide covers configuring Wikimedia OAuth 1.0a for the WikiContest tool on Toolforge.

## Quick Summary

| Setting | Value |
|---|---|
| OAuth Consumer Registration | https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration |
| Callback URL | `https://wikicontest.toolforge.org/oauth/callback` |
| `OAUTH_USE_OOB` | `True` |
| `OAUTH_CALLBACK_PATH` | `/oauth/callback` |

## How the OAuth Flow Works

```
1. User clicks "Login with Wikimedia"
   → GET /api/user/oauth/login

2. Flask builds callback URL using OAUTH_CALLBACK_PATH:
   → https://wikicontest.toolforge.org/oauth/callback

3. User authorizes on Meta-Wiki
   → Meta-Wiki redirects to https://wikicontest.toolforge.org/oauth/callback

4. Flask /oauth/callback route redirects to blueprint handler:
   → /api/user/oauth/callback?oauth_verifier=...&oauth_token=...

5. Blueprint handler exchanges token, creates JWT, redirects:
   → https://wikicontest.toolforge.org/?oauth_success=true
```

The `/oauth/callback` route (in `backend/app/__init__.py`) redirects to the blueprint handler at `/api/user/oauth/callback`. This bridge exists because the OAuth consumer is registered with `/oauth/callback`, but the actual handler lives in the `user_bp` blueprint.

## Step-by-Step Setup

### 1. Register OAuth Consumer

1. Go to https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
2. Fill in application details:
   - **Application name:** WikiContest
   - **Callback URL:** `https://wikicontest.toolforge.org/oauth/callback`
3. Save and note your **Consumer Key** and **Consumer Secret**

### 2. Set Environment Variables

```bash
become wikicontest

toolforge envvars create CONSUMER_KEY "your-consumer-key"
toolforge envvars create CONSUMER_SECRET "your-consumer-secret"
toolforge envvars create OAUTH_USE_OOB "True"
toolforge envvars create OAUTH_CALLBACK_PATH "/oauth/callback"
```

### 3. Restart the Service

```bash
toolforge webservice stop
toolforge webservice --mount none buildservice start
```

### 4. Verify

```bash
curl -s https://wikicontest.toolforge.org/api/oauth/config | python3 -m json.tool
```

Expected output:
```json
{
    "oauth_configured": true,
    "use_oob": true,
    "callback_url": "https://wikicontest.toolforge.org/oauth/callback"
}
```

## Local Development

For local development, no `OAUTH_CALLBACK_PATH` or `OAUTH_USE_OOB` is needed:

```env
# backend/.env
CONSUMER_KEY=your-local-consumer-key
CONSUMER_SECRET=your-local-consumer-secret
# OAUTH_CALLBACK_PATH is not set → defaults to /api/user/oauth/callback
# OAUTH_USE_OOB is not set → defaults to False
```

Register a separate OAuth consumer for local development:
- **Callback URL:** `http://localhost:5000/api/user/oauth/callback`

## Troubleshooting

### "oauth_callback must be set to oob"

`OAUTH_USE_OOB` is not evaluating to `True`. This is usually caused by a trailing newline in the env var value (a known Toolforge quirk). Re-set it:

```bash
toolforge envvars delete OAUTH_USE_OOB
toolforge envvars create OAUTH_USE_OOB "True"
toolforge webservice stop
toolforge webservice --mount none buildservice start
```

### Redirect goes to localhost after login

`FRONTEND_URL` is not set or still has the development value:

```bash
toolforge envvars create FRONTEND_URL "https://wikicontest.toolforge.org"
toolforge webservice stop
toolforge webservice --mount none buildservice start
```

### "can't subtract offset-naive and offset-aware datetimes"

This is a timezone mismatch between Python code and MySQL. Ensure the code uses `datetime.utcnow()` (naive) consistently, not `datetime.now(timezone.utc)` (aware).
