#!/bin/bash
# Test script for container build and basic functionality

set -euo pipefail

CONTAINER_ENGINE="${CONTAINER_ENGINE:-podman}"

echo "Testing annextube container with $CONTAINER_ENGINE"
echo "================================================="

# Build container
echo "Building container..."
$CONTAINER_ENGINE build -t annextube:test -f Containerfile .

# Test 1: Version check
echo ""
echo "Test 1: Verify annextube version"
$CONTAINER_ENGINE run --rm annextube:test --version

# Test 2: Help output
echo ""
echo "Test 2: Verify help command"
$CONTAINER_ENGINE run --rm annextube:test --help | head -5

# Test 3: Check dependencies
echo ""
echo "Test 3: Verify dependencies installed"
$CONTAINER_ENGINE run --rm annextube:test bash -c "
  git --version && \
  git-annex version && \
  yt-dlp --version && \
  deno --version && \
  ffmpeg -version | head -1
"

# Test 4: Init in temporary directory
echo ""
echo "Test 4: Initialize test archive"
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

$CONTAINER_ENGINE run --rm -v "$TEMP_DIR":/archive annextube:test init

if [ -f "$TEMP_DIR/.annextube/config.toml" ]; then
    echo "[ok] Archive initialized successfully"
else
    echo "[FAIL] Archive initialization failed"
    exit 1
fi

echo ""
echo "================================================="
echo "All tests passed!"
echo ""
echo "To use the container:"
echo "  $CONTAINER_ENGINE run -it --rm -v \$PWD:/archive annextube:test backup"
