#!/bin/bash
set -e

echo "==> Testing Hierarchical Video Structure with @apopyk Channel"
echo

# Setup environment
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MINICONDA_DIR="$SCRIPT_DIR/miniconda3"
FAKE_HOME="$SCRIPT_DIR/fake-home-hierarchical-test"
ARCHIVE_DIR="$FAKE_HOME/apopyk-archive"

# Clean up previous test
rm -rf "$FAKE_HOME"
mkdir -p "$FAKE_HOME"

echo "Archive directory: $ARCHIVE_DIR"
echo

# Export HOME and activate environment
export HOME="$FAKE_HOME"
source "$MINICONDA_DIR/bin/activate"
conda activate deno
echo "✓ deno $(deno --version | head -n1 | cut -d' ' -f2) activated"
echo "✓ yt-dlp $(yt-dlp --version) activated"
echo

# Check API key
if [ -z "$YOUTUBE_API_KEY" ]; then
    echo "⚠ YOUTUBE_API_KEY not set - running without comment support"
    echo
else
    echo "✓ API key loaded"
    echo
fi

echo "==> Step 1: Create user config with cookies"
annextube init-user-config
cat >> "$FAKE_HOME/.config/annextube/config.toml" << 'EOF'

# Cookies for testing
cookies_file = "/home/yoh/proj/annextube/.git/yt-cookies.txt"

# Enable EJS challenge solver for cookies + deno
ytdlp_extra_opts = ["--remote-components", "ejs:github"]
EOF
echo "✓ User config created"
echo

echo "==> Step 2: Initialize archive with hierarchical pattern (default)"
# Using default pattern which is now {year}/{month}/{date}_{sanitized_title}
annextube init "$ARCHIVE_DIR" "https://www.youtube.com/@apopyk" --videos --limit 3
echo "✓ Archive initialized with hierarchical video paths"
echo

echo "==> Step 3: Backup"
cd "$ARCHIVE_DIR"
annextube backup --output-dir "$ARCHIVE_DIR"
echo

echo "==> Step 4: Verify hierarchical structure"
echo
echo "Directory tree:"
if command -v tree &> /dev/null; then
    tree -d "$ARCHIVE_DIR/videos" -L 3
else
    find "$ARCHIVE_DIR/videos" -type d | sort
fi
echo

echo "==> Step 5: Results"
if [ -f "$ARCHIVE_DIR/videos/videos.tsv" ]; then
    VIDEO_COUNT=$(tail -n +2 "$ARCHIVE_DIR/videos/videos.tsv" | wc -l)
    echo "✓ videos.tsv created with $VIDEO_COUNT video(s)"
    echo

    # Show video paths
    echo "Video directories:"
    find "$ARCHIVE_DIR/videos" -type d -mindepth 3 | while read dir; do
        # Extract year/month/date_title from path
        rel_path="${dir#$ARCHIVE_DIR/videos/}"
        echo "  $rel_path"
    done
else
    echo "✗ No videos.tsv found"
fi
echo

echo "Archive preserved at: $ARCHIVE_DIR"
echo "You can inspect the hierarchical structure with:"
echo "  cd $ARCHIVE_DIR/videos && ls -la"
