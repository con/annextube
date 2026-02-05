#!/bin/bash
# Ensure Playwright browsers are installed without requiring sudo.
#
# This script checks whether the required Playwright browser (chromium)
# is already installed before attempting installation. It never uses
# --with-deps (which requires sudo for system dependency installation).
#
# For system dependencies, users should run once manually:
#   npx playwright install-deps chromium
# or install the OS packages listed by:
#   npx playwright install --dry-run chromium

set -euo pipefail

BROWSER="${1:-chromium}"

# Use node to ask playwright-core for the expected executable path
# and check if it already exists on disk.
check_browser_installed() {
    node -e "
const { ${BROWSER} } = require('playwright-core');
const fs = require('fs');
try {
    const execPath = ${BROWSER}.executablePath();
    if (fs.existsSync(execPath)) {
        console.log('FOUND: ' + execPath);
        process.exit(0);
    } else {
        console.log('MISSING: ' + execPath);
        process.exit(1);
    }
} catch(e) {
    console.log('ERROR: ' + e.message);
    process.exit(1);
}
" 2>&1
}

echo "Checking if Playwright ${BROWSER} is already installed..."
if check_browser_installed; then
    echo "Playwright ${BROWSER} is already installed, skipping download."
    exit 0
fi

echo "Playwright ${BROWSER} not found, installing (without system deps)..."
npx playwright install "${BROWSER}"

# Verify installation succeeded
if check_browser_installed; then
    echo "Playwright ${BROWSER} installed successfully."
else
    echo ""
    echo "ERROR: Playwright ${BROWSER} installation failed or system dependencies are missing."
    echo ""
    echo "If you see errors about missing shared libraries, install system deps once with:"
    echo "  cd frontend && npx playwright install-deps ${BROWSER}"
    echo ""
    echo "This requires sudo but only needs to be done once per system."
    exit 1
fi
