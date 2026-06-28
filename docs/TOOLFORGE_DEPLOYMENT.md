# Toolforge Deployment Guide: WikiContest

WikiContest is designed to be deployed as two separate tools on Toolforge using the exact same GitHub repository via Build Service.

The tools are:
- `wikicontest-backend`: Python Flask API and Database connection
- `wikicontest`: Node.js Vue static website and proxy-server

## 1. Setup Backend Tool (`wikicontest-backend`)

From the bastion server:
```bash
# Become the tool account
become wikicontest-backend

# Set Production Environment Variables
toolforge envvars create TOOL_NAME "wikicontest-backend"
toolforge envvars create FLASK_ENV "production"
# (Required) Add OAuth config from Special:OAuthConsumerRegistration
toolforge envvars create CONSUMER_KEY "..."
toolforge envvars create CONSUMER_SECRET "..."
toolforge envvars create OAUTH_USE_OOB "True"
toolforge envvars create SECRET_KEY "$(openssl rand -hex 32)"
toolforge envvars create JWT_SECRET_KEY "$(openssl rand -hex 32)"

# Toolforge ToolsDB config (parse replica.my.cnf for credentials)
TOOL_DB_USER=$(grep -Po '(?<=user = ).*' ~/replica.my.cnf)
TOOL_DB_PASS=$(grep -Po '(?<=password = ).*' ~/replica.my.cnf | tr -d "'")

toolforge envvars create TOOL_TOOLSDB_USER "$TOOL_DB_USER"
toolforge envvars create TOOL_TOOLSDB_PASSWORD "$TOOL_DB_PASS"
toolforge envvars create TOOL_TOOLSDB_DBNAME "wikicontest"
# CORS: always allow frontend domain (also auto-added by code, but explicit is safer)
toolforge envvars create CORS_ORIGINS "https://wikicontest.toolforge.org"

# Build and start the backend
toolforge build start https://github.com/Agamya-Samuel/wikicontest.git
toolforge webservice --mount none buildservice start
toolforge webservice restart
toolforge webservice logs
```

*Note: Once started, run `python -m app.scripts.init_db` (or Alembic) via `toolforge jobs` or SSH to initialize schemas on ToolsDB.*

## 2. Setup Frontend Tool (`wikicontest`)

From the bastion server:
```bash
# Become the tool account
become wikicontest

# Set Production Environment Variables
toolforge envvars create TOOL_NAME "wikicontest"

# Tell the frontend where the backend API lives (Defaults to this URL if unset)
toolforge envvars create BACKEND_URL "https://wikicontest-backend.toolforge.org"

# Build and start the frontend
toolforge build start https://github.com/Agamya-Samuel/wikicontest.git
toolforge webservice --mount none buildservice start
```

## How It Works
Both environments run `Procfile` -> `start.sh`.
- When `$TOOL_NAME` is `wikicontest-backend`, `start.sh` starts `gunicorn`.
- When `$TOOL_NAME` is `wikicontest`, it starts the lightweight Node.js Express server (`frontend/server.cjs`), which safely proxies `/api` calls to the backend, completely sidestepping cross-domain 3rd-party cookie policies in modern browsers.
