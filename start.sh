#!/usr/bin/env bash

# Auto-detect tool name if running inside Toolforge and env var isn't explicitly set
if [ -z "$TOOL_NAME" ]; then
    if [ -n "$TOOL_DIR" ]; then
        TOOL_NAME=$(basename "$TOOL_DIR")
    elif [ -n "$TOOL_DATA_DIR" ]; then
        TOOL_NAME=$(basename "$TOOL_DATA_DIR")
    fi
    export TOOL_NAME
fi

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
