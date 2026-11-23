#!/bin/bash
# Build the web UI and serve it inside the fixture archives of the Chromatic
# snapshot suite (tests/chromatic/), the way a deployed archive lays it out:
# the data at the archive root, the UI under web/ beside it.
#
#   /archive/web/     single-channel archive (videos, a playlist, comments)
#   /collection/web/  multi-channel collection (channels.tsv)
#   /empty/web/       no archive data at all (the load-error state)
#
# Started by playwright.chromatic.config.ts as its webServer. Served by
# Python's http.server rather than `vite preview`: preview answers a missing
# file with index.html (HTTP 200), and the UI finds its archive by probing
# for files, so every probe would succeed.
#
# Usage: serve-chromatic-fixtures.sh [PORT]

set -euo pipefail

PORT="${1:-4173}"
FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURES="$FRONTEND_DIR/tests/chromatic/fixtures"
SITE="$FRONTEND_DIR/.tmp/chromatic-site"

cd "$FRONTEND_DIR"

rm -rf "$SITE"
mkdir -p "$SITE/empty"
cp -R "$FIXTURES/archive" "$FIXTURES/collection" "$SITE/"

# Built outside ../web, which is what the Python package ships.
npx vite build --outDir "$SITE/_web" --emptyOutDir
for archive in archive collection empty; do
    cp -R "$SITE/_web" "$SITE/$archive/web"
done
rm -rf "$SITE/_web"

# The access log (a line per probe the UI makes) goes to a file, not into the test output.
exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$SITE" \
    >"$FRONTEND_DIR/.tmp/chromatic-site.log" 2>&1
