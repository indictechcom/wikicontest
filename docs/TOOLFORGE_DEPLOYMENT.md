# Toolforge Deployment Guide (Build Service)

This guide covers deploying WikiContest to Wikimedia Toolforge using the Build Service with Docker support.

## Prerequisites

- Toolforge account with access to Build Service
- OAuth consumer registered on Meta-Wiki
- ToolsDB database provisioned

## Deployment Steps

### 1. Prepare Your Tool

```bash
# SSH into Toolforge
ssh <your-username>@login.toolforge.org

# Become your tool user
become wikicontest

# Create required directories
mkdir -p $HOME/www/python/src
```

### 2. Configure Build Service

```bash
# Enable Build Service
webservice build start
```

### 3. Set Environment Variables

```bash
# Set OAuth credentials
toolforge env set CONSUMER_KEY "your-consumer-key"
toolforge env set CONSUMER_SECRET "your-consumer-secret"
toolforge env set SECRET_KEY "$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
toolforge env set JWT_SECRET_KEY "$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
toolforge env set FLASK_ENV "production"
toolforge env set DEBUG "False"
toolforge env set CORS_ORIGINS "https://wikicontest.toolforge.org"
toolforge env set OAUTH_CALLBACK_PATH "/oauth/callback"
toolforge env set OAUTH_USE_OOB "True"
```

### 4. Deploy Your Code

```bash
# From your local machine - push to Toolforge
git push toolforge main:main

# Or use the Build Service web interface at:
# https://toolforge.org/
```

### 5. Run Database Migrations

```bash
# SSH into Toolforge
ssh <your-username>@login.toolforge.org
become wikicontest

# Start a shell in your webservice
webservice build shell

# Run migrations
cd /app
flask db upgrade

# Exit shell
exit
```

### 6. Verify Deployment

```bash
# Check webservice status
webservice status

# View logs
webservice build logs

# Test the application
curl https://wikicontest.toolforge.org/api/health
```

## ToolsDB Configuration

ToolsDB credentials are automatically injected by Toolforge:

- `TOOL_TOOLSDB_USER`: Your tool database username
- `TOOL_TOOLSDB_PASSWORD`: Your tool database password
- `TOOL_TOOLSDB_DBNAME`: Database name (defaults to tool name)

The application automatically detects these and constructs the connection string.

## OAuth Consumer Registration

To register your OAuth consumer on Meta-Wiki:

1. Go to: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
2. Fill in the form:
   - **Application name**: WikiContest (or your tool name)
   - **OAuth version**: 1.0a
   - **Callback URL**: `https://wikicontest.toolforge.org/oauth/callback`
   - **Allow consumer to specify a callback**: No
   - **Grants**: Basic rights
   - **Rights**: Read user identity
3. Copy the consumer key and secret to your Toolforge environment variables

## Troubleshooting

### Build Failures

```bash
# View build logs
toolforge build logs

# Check build configuration
cat .gitlab-ci.yml
```

### Database Connection Issues

```bash
# Check ToolsDB credentials
toolforge env list

# Test database connection
webservice build shell
flask db check
```

### OAuth Callback Issues

Ensure your OAuth consumer is configured with:
- Callback URL: `https://wikicontest.toolforge.org/oauth/callback`
- OAuth version: 1.0a
- Rights: Basic rights

## Updates and Maintenance

### Update Application

```bash
# Push new code
git push toolforge main:main

# Build Service automatically rebuilds and deploys
```

### Run New Migrations

```bash
webservice build shell
flask db upgrade
exit
```

### Rollback

```bash
# Revert to previous commit
git revert HEAD
git push toolforge main:main
```

## Additional Resources

- [Toolforge Build Service Documentation](https://wikitech.wikimedia.org/wiki/Toolforge:Build_Service)
- [ToolsDB Documentation](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Database)
- [Wikimedia OAuth Documentation](https://www.mediawiki.org/wiki/OAuth/For_Developers)
