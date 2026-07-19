# Toolforge Deployment Guide: WikiEval

WikiEval is deployed as a **single tool** on Wikimedia Toolforge using the Build Service.
Flask (Gunicorn) serves both the REST API (`/api/*`) and the Vue.js static frontend from `frontend/dist/`.

The Node.js buildpack builds the Vue.js app during the container image build phase (`postinstall` in root `package.json`), and the Python buildpack runs Gunicorn at runtime.

**URL:** `https://WikiEval.toolforge.org`

## Architecture

```
Browser
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  WikiEval.toolforge.org  (single Toolforge tool) │
│                                                     │
│  Gunicorn (4 workers)                               │
│  ├── Flask routes: /api/*, /oauth/*                 │
│  └── Static files: frontend/dist/  (Vue.js SPA)     │
│                                                     │
│  ToolsDB: s57509__WikiEval                       │
└─────────────────────────────────────────────────────┘
```

No separate frontend proxy, no Node.js runtime at request time, no CORS issues.

## Prerequisites

- Wikimedia developer account with Toolforge access
- SSH access to `login.toolforge.org`
- OAuth consumer registered at https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
  - Callback URL: `https://WikiEval.toolforge.org/oauth/callback`

## Step 1: Create the Tool

From the Toolforge bastion:

```bash
# Create the tool (if it doesn't exist already)
# This is done via https://toolsadmin.wikimedia.org/
# Tool name: WikiEval
```

## Step 2: Configure Environment Variables

```bash
become WikiEval

# Tool identity
toolforge envvars create FLASK_ENV "production"

# OAuth credentials (from Special:OAuthConsumerRegistration)
toolforge envvars create CONSUMER_KEY "your-consumer-key"
toolforge envvars create CONSUMER_SECRET "your-consumer-secret"
toolforge envvars create OAUTH_USE_OOB "True"
toolforge envvars create OAUTH_CALLBACK_PATH "/oauth/callback"

# Security keys (generate with: openssl rand -hex 32)
toolforge envvars create SECRET_KEY "$(openssl rand -hex 32)"
toolforge envvars create JWT_SECRET_KEY "$(openssl rand -hex 32)"

# Frontend URL (used for OAuth redirects and User-Agent headers)
toolforge envvars create FRONTEND_URL "https://WikiEval.toolforge.org"

# Database — ToolsDB credentials from replica.my.cnf
TOOL_DB_USER=$(grep -Po '(?<=user = ).*' ~/replica.my.cnf)
TOOL_DB_PASS=$(grep -Po '(?<=password = ).*' ~/replica.my.cnf | tr -d "'")
toolforge envvars create TOOL_TOOLSDB_USER "$TOOL_DB_USER"
toolforge envvars create TOOL_TOOLSDB_PASSWORD "$TOOL_DB_PASS"
toolforge envvars create TOOL_TOOLSDB_DBNAME "WikiEval"
```

> **Note:** `toolforge envvars create` may inject values with trailing newlines.
> The application strips whitespace from all env vars at startup to handle this.

## Step 3: Build and Deploy

```bash
# Build the container image (installs Node.js + Python, builds frontend)
toolforge build start https://github.com/Agamya-Samuel/WikiEval.git --ref ft/toolforge

# Start the service
toolforge webservice --mount none buildservice start
```

## Step 4: Initialize the Database

```bash
# Run Alembic migrations to create the database schema
cd backend
alembic upgrade head
```

## Step 5: Verify

```bash
# Check service status
toolforge webservice status

# View logs
toolforge webservice logs

# Test from the bastion
curl -s https://WikiEval.toolforge.org/api/health
```

Expected response:
```json
{"message":"WikiEval API is running","status":"healthy","version":"1.0.0"}
```

## How It Works

The `Procfile` runs Gunicorn directly:

```
web: cd backend && exec gunicorn --bind=0.0.0.0:${PORT:-8000} --workers=4 --forwarded-allow-ips=* --access-logfile - --error-logfile - "wsgi:application"
```

The Node.js buildpack runs during the **build phase** only (via `postinstall` in root `package.json`):
1. Installs frontend dependencies (`cd frontend && npm install`)
2. Builds the Vue.js SPA (`npm run build` → `frontend/dist/`)
3. The built files are baked into the container image

At **runtime**, Gunicorn starts Flask which:
- Serves API endpoints via blueprints (`/api/user/*`, `/api/contest/*`, `/api/submission/*`)
- Serves the Vue.js SPA from `frontend/dist/` for all other routes
- Handles Vue Router history mode by returning `index.html` for unknown paths

## Rebuilding After Code Changes

```bash
become WikiEval

# Pull latest code and rebuild
toolforge build start https://github.com/Agamya-Samuel/WikiEval.git --ref ft/toolforge

# Restart the service to use the new image
toolforge webservice stop
toolforge webservice --mount none buildservice start
```

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `FLASK_ENV` | Yes | Set to `production` |
| `CONSUMER_KEY` | Yes | OAuth consumer key from Meta-Wiki |
| `CONSUMER_SECRET` | Yes | OAuth consumer secret |
| `OAUTH_USE_OOB` | Yes | Set to `True` if consumer uses oob callback |
| `OAUTH_CALLBACK_PATH` | Yes | Set to `/oauth/callback` |
| `SECRET_KEY` | Yes | Flask secret key (random hex) |
| `JWT_SECRET_KEY` | Yes | JWT signing key (random hex) |
| `FRONTEND_URL` | Yes | `https://WikiEval.toolforge.org` |
| `TOOL_TOOLSDB_USER` | Yes | ToolsDB username from `replica.my.cnf` |
| `TOOL_TOOLSDB_PASSWORD` | Yes | ToolsDB password from `replica.my.cnf` |
| `TOOL_TOOLSDB_DBNAME` | Yes | Database name (`WikiEval`) |
| `DATABASE_URL` | No | Full MySQL URI (auto-constructed from ToolsDB vars if unset) |

## Troubleshooting

### OAuth redirect goes to localhost
The `FRONTEND_URL` env var is missing or set to a development URL. Set it to `https://WikiEval.toolforge.org`.

### "oauth_callback must be set to oob"
`OAUTH_USE_OOB` is not evaluating to `True`. This is usually caused by a trailing newline in the env var value. The app strips whitespace at startup, but if you set the value before the fix was deployed, re-set it:
```bash
toolforge envvars delete OAUTH_USE_OOB
toolforge envvars create OAUTH_USE_OOB "True"
```

### Frontend shows blank page
The Vue.js build may have failed during image creation. Check build logs:
```bash
toolforge build logs
```

### Database connection errors
Verify ToolsDB credentials match `~/replica.my.cnf` on the tool account.

## Pre-Deployment Checklist

- [ ] All functions have proper documentation
- [ ] Error handling is comprehensive
- [ ] Security measures are in place (input validation, authentication)
- [ ] Database queries are optimized (no N+1 queries)
- [ ] Frontend validation is complete
- [ ] Unit tests pass successfully
- [ ] Integration tests pass successfully
- [ ] No sensitive data in code (secrets in environment variables)

## Production Configuration

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

## Post-Deployment Verification

- [ ] Application loads successfully
- [ ] Health check endpoint responds
- [ ] User authentication works
- [ ] Database connections are stable
- [ ] API endpoints return expected responses
- [ ] Error logging is functional
- [ ] SSL/HTTPS is working correctly
