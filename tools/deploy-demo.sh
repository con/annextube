#!/bin/bash
# Deploy demo to gh-pages branch from local machine.
#
# Prerequisites:
#   - annextube installed (uv pip install -e .)
#   - git-annex installed
#   - deno installed (for yt-dlp challenge solver)
#   - YouTube cookies available (ANNEXTUBE_COOKIES_FILE or browser)
#
# Usage:
#   ./tools/deploy-demo.sh              # build + deploy
#   ./tools/deploy-demo.sh --build-only # build without pushing
#   ./tools/deploy-demo.sh --skip-build # deploy existing annextubetesting content
#
# This script:
#   1. Ensures the annextubetesting branch has content (runs setup_demo_branch.sh if needed)
#   2. Generates the web UI from that content
#   3. Deploys to gh-pages branch and pushes
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if [ ! -f "pyproject.toml" ] || [ ! -d "annextube" ]; then
    echo "Error: must be run from annextube project root"
    exit 1
fi

BUILD_ONLY=false
SKIP_BUILD=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --build-only) BUILD_ONLY=true; shift ;;
        --skip-build) SKIP_BUILD=true; shift ;;
        *)
            echo "Usage: $0 [--build-only|--skip-build]"
            exit 1
            ;;
    esac
done

ORIGINAL_BRANCH=$(git branch --show-current)

# --- Step 1: Ensure demo content exists ---
if [ "$SKIP_BUILD" = false ]; then
    echo "=== Step 1: Ensuring demo content on annextubetesting branch ==="
    if ! git show-ref --verify --quiet refs/heads/annextubetesting; then
        echo "annextubetesting branch not found, running setup_demo_branch.sh..."
        bash "$SCRIPT_DIR/setup_demo_branch.sh"
    else
        echo "annextubetesting branch exists. Run setup_demo_branch.sh manually to update content."
    fi
fi

# --- Step 2: Generate web UI ---
echo ""
echo "=== Step 2: Generating web UI from annextubetesting content ==="
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

# Export the annextubetesting content to a temp dir
git archive annextubetesting | tar -x -C "$WORK_DIR"

# Generate web UI
uv run annextube generate-web --output-dir "$WORK_DIR"

WEB_DIR="$WORK_DIR/web"
if [ ! -d "$WEB_DIR" ]; then
    echo "Error: generate-web did not produce web/ directory"
    exit 1
fi

echo "Web UI generated: $(find "$WEB_DIR" -type f | wc -l) files"

if [ "$BUILD_ONLY" = true ]; then
    echo ""
    echo "Build complete (--build-only). Web output in: $WEB_DIR"
    echo "To preview: cd $WEB_DIR && python3 -m http.server 8080"
    # Keep temp dir alive by removing the trap
    trap - EXIT
    exit 0
fi

# --- Step 3: Deploy to gh-pages ---
echo ""
echo "=== Step 3: Deploying to gh-pages ==="

# Switch to gh-pages (create orphan if needed)
git checkout gh-pages 2>/dev/null || git checkout --orphan gh-pages

# Clean working tree
git rm -rf . 2>/dev/null || true
# Use git clean instead of rm -rf * (safer, avoids matching .git)
git clean -fd 2>/dev/null || true

# Copy web output
cp -r "$WEB_DIR"/* .

# Add README
cat > README.md << 'READMEEOF'
# annextube Demo

Auto-generated from [@AnnexTubeTesting](https://www.youtube.com/@AnnexTubeTesting).

- Video metadata browsing
- Playlist navigation
- Search functionality
- Client-side static web UI (no backend required)

Source: https://github.com/con/annextube
READMEEOF

# Commit
git add -A
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "initial")
git commit -m "Deploy demo (source: $COMMIT_SHA)" || { echo "No changes to deploy"; git checkout "$ORIGINAL_BRANCH"; exit 0; }

echo ""
echo "gh-pages updated. To publish:"
echo "  git push origin gh-pages --force"
echo ""
echo "To return to your branch:"
echo "  git checkout $ORIGINAL_BRANCH"
