# WikiEval Toolforge Deployment Guide

This guide provides step-by-step instructions for deploying the WikiEval Flask application to Wikimedia Toolforge.



## Prerequisites

Before you begin, ensure you have:

- A Toolforge account
- SSH access to Toolforge
- Basic knowledge of Python and Flask
- Node.js and npm installed locally (for building the frontend)



## Deployment Steps

### Step 1: Create Your Tool Account

1. Follow the [Toolforge quickstart guide](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Quickstart) to create your tool
2. SSH into Toolforge:
```bash
   ssh <your-username>@login.toolforge.org
```
3. Switch to your tool user:
```bash
   become wikicontest
```

### Step 2: Build the Vue.js Frontend

Build the Vue.js frontend for production **on your local machine** before deploying:

1. **Build the frontend:**
```bash
   cd frontend
   npm install
   npm run build
```
   
   This creates a `dist/` directory containing optimized production files.

2. **Verify the build:**
```bash
   ls -la dist/
```
   
   You should see `index.html` and an `assets/` directory with JavaScript and CSS files.

### Step 3: Prepare the Application Structure

1. **Run the deployment script (recommended):**
```bash
   cd backend
   chmod +x deploy_to_toolforge.sh
   ./deploy_to_toolforge.sh
```

2. **Or manually create the directory structure:**
```bash
   mkdir -p $HOME/www/python/src
   mkdir -p $HOME/www/python/src/models
   mkdir -p $HOME/www/python/src/routes
   mkdir -p $HOME/www/python/src/middleware
```

**Note:** Flask will automatically serve the Vue.js frontend from the `frontend/dist/` directory.

### Step 4: Set Up the Python Virtual Environment

1. **Start a Kubernetes shell:**
```bash
   webservice python3.13 shell
```

2. **Create and activate the virtual environment:**
```bash
   python3 -m venv $HOME/www/python/venv
   source $HOME/www/python/venv/bin/activate
   pip install --upgrade pip
```

3. **Install Python dependencies:**
```bash
   pip install -r $HOME/www/python/src/requirements.txt
```

4. **Exit the Kubernetes shell:**
```bash
   exit
```

### Step 5: Configure OAuth

1. **Register an OAuth consumer:**
   - Navigate to: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
   - **Callback URL:** `https://wikicontest.toolforge.org/oauth/callback`
   - **Contact email:** Your Wikimedia account email
   - **Grant settings:** Request authorization for specific permissions (Basic rights)
   - Save your **Consumer Key** and **Consumer Secret**

2. **Generate security keys:**
```bash
   python3 -c "import secrets; print('SECRET_KEY = \"' + secrets.token_urlsafe(48) + '\"')"
   python3 -c "import secrets; print('JWT_SECRET_KEY = \"' + secrets.token_urlsafe(48) + '\"')"
```

3. **Create the configuration file:**
```bash
   nano $HOME/www/python/src/config.toml
```

4. **Add your configuration:**
```toml
   GREETING = "Welcome to  on Toolforge!"
   
   # Security (use generated keys from step 2)
   SECRET_KEY = "your-generated-secret-key"
   JWT_SECRET_KEY = "your-generated-jwt-secret-key"
   
   # Database
   SQLALCHEMY_DATABASE_URI = "sqlite:///wikicontest.db"
   SQLALCHEMY_TRACK_MODIFICATIONS = false
   
   # JWT Configuration
   JWT_ACCESS_TOKEN_EXPIRES = 86400
   
   # Debug mode
   DEBUG = false
   
   # OAuth Configuration
   OAUTH_MWURI = "https://meta.wikimedia.org/w/index.php"
   CONSUMER_KEY = "your-consumer-key-from-oauth-registration"
   CONSUMER_SECRET = "your-consumer-secret-from-oauth-registration"
   
   # OAuth Callback Path - REQUIRED for Toolforge
   OAUTH_CALLBACK_PATH = "/oauth/callback"
   
   # OAuth Callback Type
   OAUTH_USE_OOB = false
```

### Step 6: Secure Your Configuration

Set proper file permissions to protect sensitive data:
```bash
# Make config file readable only by the tool user
chmod u=rw,go= $HOME/www/python/src/config.toml
```

### Step 7: Start the Webservice
```bash
webservice python3.13 start
```

### Step 8: Verify Your Deployment

Test your deployment by accessing these URLs:

1. **Main application:** https://wikicontest.toolforge.org/
2. **API health check:** https://wikicontest.toolforge.org/api/health
3. **OAuth login:** https://wikicontest.toolforge.org/login



## File Structure on Toolforge
```
$HOME/
├── uwsgi.log
├── error.log
└── www/
    └── python/
        ├── src/
        │   ├── app.py                 # Main Flask application
        │   ├── config.toml            # Configuration file (secure)
        │   ├── requirements.txt       # Python dependencies
        │   ├── models/
        │   │   ├── user.py            # User model
        │   │   ├── contest.py         # Contest model
        │   │   └── submission.py      # Submission model
        │   ├── routes/
        │   │   ├── user_routes.py     # User API routes
        │   │   ├── contest_routes.py  # Contest API routes
        │   │   └── submission_routes.py # Submission API routes
        │   └── middleware/
        │       └── auth.py            # Authentication middleware
        └── venv/                      # Python virtual environment
```

**Note:** The Vue.js frontend is built locally and deployed as static files. Flask automatically serves the production build from the `frontend/dist/` directory.



## Frontend Technology Stack

The WikiEval frontend uses modern web technologies:

- **Vue.js 3** – Progressive JavaScript framework
- **Vue Router** – Client-side routing
- **Vite** – Modern build tool
- **Axios** – HTTP client for API requests
- **Bootstrap 5** – CSS framework

### Frontend Deployment Approach

The frontend is built locally using `npm run build`, and the production files are served by Flask from the `frontend/dist/` directory. This approach provides:

- Optimized production builds with minification
- Seamless integration with Toolforge's Python webservice
- Compatibility with MediaWiki/Toolforge infrastructure
- Simple updates and deployments



## Troubleshooting

### Common Issues

#### Webservice Won't Start

Check the log files for errors:
```bash
tail -n 50 $HOME/uwsgi.log
tail -n 50 $HOME/error.log
```

#### Import Errors

Verify your virtual environment is properly set up:
```bash
webservice python3.13 shell
source $HOME/www/python/venv/bin/activate
pip list
```

#### OAuth Errors

If OAuth authentication fails:

- Verify `CONSUMER_KEY` and `CONSUMER_SECRET` in `config.toml`
- Ensure the callback URL matches exactly: `https://wikicontest.toolforge.org/oauth/callback`
- Confirm your OAuth consumer is approved on Meta-Wiki
- Verify `OAUTH_CALLBACK_PATH = "/oauth/callback"` is set in `config.toml`

#### Database Errors

Check if the database file exists:
```bash
ls -la $HOME/www/python/src/
```

### Useful Commands
```bash
# Restart the webservice
webservice restart

# Stop the webservice
webservice stop

# Check webservice status
webservice status

# View logs in real-time
tail -f $HOME/uwsgi.log

# Test database connection
webservice python3.13 shell
python3 -c "from app import app, db; app.app_context().push(); print('Database OK')"
```



## Security Considerations

Follow these security best practices:

1. **Never commit secrets** – Keep `config.toml` out of version control
2. **File permissions** – Ensure `config.toml` is only readable by the tool user (`chmod u=rw,go=`)
3. **OAuth secrets** – Keep consumer key and secret secure
4. **Database security** – Store SQLite file in a secure location with proper permissions



## Production Optimizations

Consider these optimizations for production use:

1. **Enable caching** – Use Redis for session storage
2. **Database optimization** – Add proper indexing to improve query performance
3. **Static files** – Consider using a CDN for better frontend performance
4. **Monitoring** – Set up proper logging and monitoring for your application



## Updates and Maintenance

### Updating Code
```bash
# Copy new files to the server
cp new_file.py $HOME/www/python/src/

# Restart the webservice
webservice restart
```

### Updating Dependencies
```bash
# Enter the Kubernetes shell
webservice python3.13 shell

# Activate virtual environment
source $HOME/www/python/venv/bin/activate

# Update dependencies
pip install -r $HOME/www/python/src/requirements.txt

# Exit and restart
exit
webservice restart
```



## Additional Resources

- [Toolforge Documentation](https://wikitech.wikimedia.org/wiki/Help:Toolforge)
- [Toolforge Python Guide](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Python)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Vue.js Documentation](https://vuejs.org/)
- [Vite Documentation](https://vitejs.dev/)
- [OAuth Documentation](https://www.mediawiki.org/wiki/OAuth)



## Getting Help

If you encounter issues:

- **Toolforge IRC:** #wikimedia-cloud on Libera.Chat
- **Toolforge Mailing List:** cloud@lists.wikimedia.org
- **Phabricator:** #Cloud-Services project



## Important Notes

- This deployment uses SQLite for simplicity. For production use with many concurrent users, consider migrating to MySQL or PostgreSQL.
- Remember to set `OAUTH_CALLBACK_PATH = "/oauth/callback"` in your `config.toml` – this is required for OAuth to work correctly on Toolforge.