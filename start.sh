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

# Both wikicontest and wikicontest-backend run the same Flask/Gunicorn server.
# Flask serves both the API (/api/*) and the Vue.js static files (frontend/dist/).
# The Node.js proxy (server.cjs) is no longer needed -- Flask handles everything.
if [ "$TOOL_NAME" = "wikicontest" ] || [ "$TOOL_NAME" = "wikicontest-backend" ]; then
    echo "Starting WikiContest ($TOOL_NAME) -- Flask API + static frontend..."
    cd backend || exit 1
    exec gunicorn --bind=0.0.0.0:${PORT:-8000} --workers=4 --forwarded-allow-ips=* --access-logfile - --error-logfile - "wsgi:application"
else
    echo "CRITICAL ERROR: TOOL_NAME evaluates to '$TOOL_NAME'."
    echo "Please explicitly run: toolforge envvars create TOOL_NAME \"wikicontest\" (or wikicontest-backend)"
    exit 1
fi
