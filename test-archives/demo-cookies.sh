#!/bin/bash
set -e

echo "==> annextube Cookie Demo with Authentication"
echo

# Setup fake HOME under test-archives
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FAKE_HOME="$SCRIPT_DIR/fake-home-demo"
ARCHIVE_DIR="$FAKE_HOME/archive"

# Clean up previous demo if exists
rm -rf "$FAKE_HOME"
mkdir -p "$FAKE_HOME"

echo "Fake HOME: $FAKE_HOME"
echo "Archive: $ARCHIVE_DIR"
echo

# Export HOME for child processes
export HOME="$FAKE_HOME"

# Check API key
if [ -z "$YOUTUBE_API_KEY" ]; then
    echo "⚠ YOUTUBE_API_KEY not set - running without comment support"
    echo "To enable comments: export YOUTUBE_API_KEY='your-key'"
    echo
    # Continue anyway - basic functionality will work
else
    echo "✓ API key loaded"
    echo
fi

echo "==> Activating deno environment"
source /tmp/miniconda3/bin/activate
conda activate deno
echo "✓ deno $(deno --version | head -n1 | cut -d' ' -f2) activated"
echo "✓ yt-dlp $(yt-dlp --version) activated"
echo

echo "==> Step 1: Create user config with cookies"
annextube init-user-config
cat >> "$FAKE_HOME/.config/annextube/config.toml" << 'EOF'

# Cookies for testing
cookies_file = "/home/yoh/proj/annextube/.git/yt-cookies.txt"

# Enable EJS challenge solver for cookies + deno
ytdlp_extra_opts = ["--remote-components", "ejs:github"]
EOF
echo "✓ User config created with cookies + EJS challenge solver"
echo

echo "==> Step 2: Initialize archive"
annextube init "$ARCHIVE_DIR" "https://www.youtube.com/@apopyk" --videos --limit 2
echo "✓ Archive initialized"
echo

echo "==> Step 3: Backup"
cd "$ARCHIVE_DIR"
annextube backup --output-dir "$ARCHIVE_DIR"
echo

echo "==> Step 4: Results"
echo
if [ -f "$ARCHIVE_DIR/videos/videos.tsv" ]; then
    VIDEO_COUNT=$(tail -n +2 "$ARCHIVE_DIR/videos/videos.tsv" | wc -l)
    echo "✓ videos.tsv created with $VIDEO_COUNT video(s)"
    echo
    echo "Videos:"
    tail -n +2 "$ARCHIVE_DIR/videos/videos.tsv" | cut -f2,3
else
    echo "✗ No videos.tsv found"
fi
echo

echo "Video files:"
find "$ARCHIVE_DIR/videos" -name "*.mp4" -o -name "*.webm" 2>/dev/null || echo "  (none - URLs tracked by git-annex)"
echo

echo "Metadata files:"
find "$ARCHIVE_DIR/videos" -name "*.info.json" 2>/dev/null | wc -l
echo

echo "==> Step 5: Generate web interface"
annextube generate-web --output-dir "$ARCHIVE_DIR"
if [ -f "$ARCHIVE_DIR/web/index.html" ]; then
    echo "✓ Web interface generated at $ARCHIVE_DIR/web/"
    echo
    echo "To view:"
    echo "  cd $ARCHIVE_DIR/web && python3 -m http.server 8765"
else
    echo "✗ Web interface not generated"
fi
echo

echo "Archive preserved at: $ARCHIVE_DIR"
