#!/bin/bash
#
# Setup script for E2E tests
# Copies test fixture archive to the correct location for frontend to load
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_ARCHIVE="$FRONTEND_DIR/tests/fixtures/test-archive"
WEB_DIR="$(cd "$FRONTEND_DIR/.." && pwd)/web"

echo "Setting up E2E test environment..."
echo "Frontend dir: $FRONTEND_DIR"
echo "Test archive: $TEST_ARCHIVE"
echo "Web dir: $WEB_DIR"

# Ensure web directory exists
if [ ! -d "$WEB_DIR" ]; then
  echo "Error: web/ directory not found. Run 'npm run build' first."
  exit 1
fi

# Create symlinks for test data (so frontend can load from ../videos, ../playlists)
echo "Creating symlinks for test data..."
cd "$WEB_DIR"

# Remove old symlinks/directories if they exist
[ -L videos ] && rm videos
[ -L playlists ] && rm playlists

# Create new symlinks
ln -sf "$TEST_ARCHIVE/videos" videos
ln -sf "$TEST_ARCHIVE/playlists" playlists

echo "Test archive setup complete!"
echo "Run 'npm run test:e2e' to start E2E tests"
