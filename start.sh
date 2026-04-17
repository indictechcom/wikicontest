#!/bin/bash

# Toolforge sets $TOOL_NAME to the tool name (e.g. 'wikicontest' or 'wikicontest-backend')
if [ "$TOOL_NAME" = "wikicontest-backend" ]; then
    echo "Starting WikiContest backend service..."
    cd backend || exit 1
    # Run the Gunicorn WGSI for Python
    exec gunicorn --bind=0.0.0.0:$PORT --workers=4 --forwarded-allow-ips=* --access-logfile - --error-logfile - "wsgi:application"
else
    echo "Starting WikiContest frontend proxy server..."
    cd frontend || exit 1
    # Run the custom Node.js Express server
    exec node server.cjs
fi
