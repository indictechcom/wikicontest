#!/bin/bash
# WikiEval Toolforge Deployment Script
# This script helps deploy the WikiEval application to Toolforge

set -e

echo "🚀 WikiEval Toolforge Deployment Script"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "toolforge_app.py" ]; then
    echo " Error: toolforge_app.py not found. Please run this script from the backend directory."
    exit 1
fi

echo "📋 Step 1: Create Toolforge directory structure"
echo "Creating required directories..."

# Create the required directory structure
mkdir -p $HOME/www/python/src
mkdir -p $HOME/www/python/src/templates
mkdir -p $HOME/www/python/src/static
mkdir -p $HOME/www/python/src/models
mkdir -p $HOME/www/python/src/routes
mkdir -p $HOME/www/python/src/middleware

echo " Directory structure created"

echo ""
echo "📋 Step 2: Copy application files"
echo "Copying files to Toolforge structure..."

# Copy main application file
cp toolforge_app.py $HOME/www/python/src/app.py
echo " Copied app.py"

# Copy requirements file
cp toolforge_requirements.txt $HOME/www/python/src/requirements.txt
echo " Copied requirements.txt"

# Copy configuration template
cp toolforge_config.toml $HOME/www/python/src/config.toml
echo " Copied config.toml"

# Copy templates
cp toolforge_index.html $HOME/www/python/src/templates/index.html
cp toolforge_login.html $HOME/www/python/src/templates/login.html
echo " Copied templates"

# Copy models
cp models/*.py $HOME/www/python/src/models/
echo " Copied models"

# Copy routes
cp routes/*.py $HOME/www/python/src/routes/
echo " Copied routes"

# Copy middleware
cp middleware/*.py $HOME/www/python/src/middleware/
echo " Copied middleware"

# Copy frontend JavaScript
cp ../frontend/app.js $HOME/www/python/src/static/app.js
echo " Copied frontend JavaScript"

echo ""
echo "📋 Step 3: Set up virtual environment"
echo "Starting Kubernetes shell to create virtual environment..."

# Create virtual environment in Kubernetes shell
echo "Run the following commands in the Kubernetes shell:"
echo ""
echo "webservice python3.13 shell"
echo "python3 -m venv \$HOME/www/python/venv"
echo "source \$HOME/www/python/venv/bin/activate"
echo "pip install --upgrade pip"
echo "pip install -r \$HOME/www/python/src/requirements.txt"
echo "exit"
echo ""

echo "📋 Step 4: Configure OAuth"
echo "1. Register a new OAuth consumer at: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration"
echo "2. Use callback URL: https://wikicontest.toolforge.org/oauth-callback"
echo "3. Update config.toml with your OAuth consumer key and secret"
echo "4. Generate secret keys:"
echo "   python3 -c \"import secrets; print('SECRET_KEY = \"' + secrets.token_urlsafe(48) + '\"')\""
echo "   python3 -c \"import secrets; print('JWT_SECRET_KEY = \"' + secrets.token_urlsafe(48) + '\"')\""
echo ""

echo "📋 Step 5: Set file permissions"
echo "Setting secure file permissions..."

# Set secure permissions for config file
chmod u=rw,go= $HOME/www/python/src/config.toml
echo " Set secure permissions for config.toml"

echo ""
echo "📋 Step 6: Start the webservice"
echo "Run the following command to start your webservice:"
echo ""
echo "webservice python3.13 start"
echo ""

echo "📋 Step 7: Test your deployment"
echo "Once started, visit: https://wikicontest.toolforge.org/"
echo ""

echo "🎉 Deployment preparation complete!"
echo ""
echo "Next steps:"
echo "1. Follow the virtual environment setup instructions above"
echo "2. Configure OAuth as described"
echo "3. Start the webservice"
echo "4. Test your application"
echo ""
echo "For troubleshooting, check:"
echo "- \$HOME/uwsgi.log"
echo "- \$HOME/error.log"
echo ""
echo "Good luck with your deployment! 🚀"
