#!/bin/bash
# Wrapper script to test YouTube API metadata enhancement
# This script sources .git/secrets to load YOUTUBE_API_KEY and runs the test

set -e

# Change to tools directory
cd "$(dirname "$0")"

# Source API key
if [ -f ../.git/secrets ]; then
    echo "Loading API key from .git/secrets..."
    source ../.git/secrets
else
    echo "ERROR: .git/secrets not found"
    exit 1
fi

if [ -z "$YOUTUBE_API_KEY" ]; then
    echo "ERROR: YOUTUBE_API_KEY not set in .git/secrets"
    exit 1
fi

echo "✓ API key loaded: ${YOUTUBE_API_KEY:0:20}...${YOUTUBE_API_KEY: -4}"
echo ""

# Export the variable so it's available to child processes
export YOUTUBE_API_KEY

# Run the test script with all arguments passed through
# uv run inherits environment variables from the shell
exec uv run python test_api_metadata.py "$@"
