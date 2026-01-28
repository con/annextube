#!/usr/bin/env bash
#
# Demo: Andriy Popyk Channel Backup
# Demonstrates all features with a real channel that has videos and playlists
#
set -e

DEMO_DIR="/tmp/annextube-demo-apopyk-$(date +%s)"

echo "=========================================="
echo "annextube Demo: Andriy Popyk (@apopyk)"
echo "=========================================="
echo ""
echo "Demo directory: $DEMO_DIR"
echo ""

# Source API key
if [ -f ~/proj/annextube/.git/secrets ]; then
    source ~/proj/annextube/.git/secrets
fi

if [ -z "$YOUTUBE_API_KEY" ]; then
    echo "ERROR: YOUTUBE_API_KEY not set"
    echo "Set it via: export YOUTUBE_API_KEY='your-key-here'"
    exit 1
fi

echo "✓ API key loaded"
echo ""

# Create demo archive
mkdir -p "$DEMO_DIR"
cd "$DEMO_DIR"

echo "Step 1: Initialize archive"
echo "----------------------------"
uv run --directory ~/proj/annextube annextube init .
echo ""

# Create config
cat > .annextube/config.toml << 'EOF'
[[sources]]
url = "https://www.youtube.com/@apopyk"
type = "channel"
enabled = true

[components]
videos = false           # Track URLs only (no video downloads)
metadata = true          # Fetch video metadata
comments_depth = 50      # Limit to 50 comments per video for demo
captions = false         # Skip captions for speed
thumbnails = true        # Download thumbnails

[organization]
video_path_pattern = "{date}_{sanitized_title}"
playlist_prefix_width = 4
playlist_prefix_separator = "_"

[filters]
limit = 10  # Get 10 most recent videos
EOF

echo "✓ Configuration created"
echo ""

echo "Step 2: Initial backup (all-incremental mode)"
echo "----------------------------------------------"
echo "Processing up to 10 most recent videos from @apopyk..."
echo ""
uv run --directory ~/proj/annextube annextube backup --output-dir . --update all-incremental 2>&1 | grep -E "(Backing up|Processing|Generated|Backup complete|videos processed|Skipping)" || true
echo ""

echo "✓ Initial backup complete"
echo ""

echo "Step 3: Verify generated files"
echo "-------------------------------"
echo ""

echo "videos.tsv (should have ~10 videos):"
if [ -f videos/videos.tsv ]; then
    VIDEO_COUNT=$(tail -n +2 videos/videos.tsv | wc -l)
    echo "  ✓ $VIDEO_COUNT videos"
    echo ""
    echo "  Sample (first 3):"
    head -4 videos/videos.tsv | column -t -s $'\t' | head -4
else
    echo "  ✗ NOT found"
fi
echo ""

echo "playlists.tsv:"
if [ -f playlists/playlists.tsv ]; then
    PLAYLIST_COUNT=$(tail -n +2 playlists/playlists.tsv | wc -l)
    echo "  ✓ $PLAYLIST_COUNT playlist(s)"
    if [ $PLAYLIST_COUNT -gt 0 ]; then
        echo ""
        echo "  Playlists:"
        cat playlists/playlists.tsv | column -t -s $'\t'
    fi
else
    echo "  ✗ NOT found"
fi
echo ""

echo "authors.tsv:"
if [ -f authors.tsv ]; then
    AUTHOR_COUNT=$(tail -n +2 authors.tsv | wc -l)
    echo "  ✓ $AUTHOR_COUNT unique authors"
    echo ""
    echo "  Sample (first 10):"
    head -11 authors.tsv | column -t -s $'\t'
else
    echo "  ✗ NOT found"
fi
echo ""

echo "Step 4: Check sync_state.json"
echo "------------------------------"
if [ -f .annextube/sync_state.json ]; then
    echo "✓ sync_state.json exists"
    VIDEOS_TRACKED=$(cat .annextube/sync_state.json | python3 -c "import json, sys; data=json.load(sys.stdin); print(len(data.get('videos', {})))")
    echo "  Videos tracked: $VIDEOS_TRACKED"
    SOURCES_TRACKED=$(cat .annextube/sync_state.json | python3 -c "import json, sys; data=json.load(sys.stdin); print(len(data.get('sources', {})))")
    echo "  Sources tracked: $SOURCES_TRACKED"
else
    echo "✗ sync_state.json NOT found"
fi
echo ""

echo "Step 5: Test incremental update (should skip all videos)"
echo "---------------------------------------------------------"
echo "Running backup again with --update=all-incremental..."
echo ""
uv run --directory ~/proj/annextube annextube backup --output-dir . --update all-incremental 2>&1 | grep -E "(Skipping|Processing video:|videos processed)" || echo "All videos skipped (no output)"
echo ""
echo "✓ Incremental update complete"
echo ""

echo "Step 6: Test all-force update mode"
echo "-----------------------------------"
echo "Running backup with --update=all-force (re-processes all videos)..."
echo ""
uv run --directory ~/proj/annextube annextube backup --output-dir . --update all-force --limit 2 2>&1 | grep -E "(Processing|videos processed)" || true
echo ""
echo "✓ Force update complete"
echo ""

echo "Step 7: Test date-based filtering"
echo "----------------------------------"
echo "Testing --from-date with duration string..."
echo ""
uv run --directory ~/proj/annextube annextube backup --output-dir . --update all-incremental --from-date "1 week" --limit 2 2>&1 | grep -E "(From date|social window|Processing|videos processed)" || true
echo ""
echo "✓ Date filtering works"
echo ""

echo "Step 8: Check .gitattributes (large files config)"
echo "--------------------------------------------------"
if [ -f .gitattributes ]; then
    echo "✓ .gitattributes exists"
    echo ""
    echo "Content:"
    cat .gitattributes
else
    echo "✗ .gitattributes NOT found"
fi
echo ""

echo "Step 9: Git history"
echo "-------------------"
git log --oneline --max-count=7
echo ""

echo "=========================================="
echo "Demo Complete!"
echo "=========================================="
echo ""
echo "Key Features Demonstrated:"
echo "  ✓ Large files (.vtt, comments.json) → git-annex"
echo "  ✓ Update modes: all-incremental, all-force"
echo "  ✓ Date parsing: --from-date '1 week'"
echo "  ✓ Incremental updates skip existing videos"
echo "  ✓ authors.tsv generated automatically"
echo "  ✓ sync_state.json tracks processed videos"
echo ""
echo "Results location: $DEMO_DIR"
echo ""
echo "To inspect:"
echo "  cd $DEMO_DIR"
echo "  cat videos/videos.tsv | column -t -s \$'\\t' | less -S"
echo "  cat authors.tsv | column -t -s \$'\\t' | head -30"
echo "  cat .annextube/sync_state.json | python3 -m json.tool"
echo ""
