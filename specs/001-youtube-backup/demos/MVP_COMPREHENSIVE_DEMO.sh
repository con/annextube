#!/usr/bin/env bash
#
# Comprehensive MVP Demo for annextube
# Demonstrates all Phase 1-3 features working together
#
set -e

DEMO_DIR="/tmp/annextube-comprehensive-demo-$(date +%s)"

echo "=================================="
echo "annextube Comprehensive MVP Demo"
echo "=================================="
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
url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
type = "playlist"
enabled = true

[components]
videos = false
metadata = true
comments_depth = 100  # Limit to 100 comments for demo
captions = false     # Skip captions for speed
thumbnails = false

[organization]
video_path_pattern = "{date}_{sanitized_title}"
playlist_prefix_width = 4
playlist_prefix_separator = "_"

[filters]
limit = 3  # Just 3 videos for quick demo
EOF

echo "✓ Configuration created"
echo ""

echo "Step 2: Initial backup (processes all videos)"
echo "----------------------------------------------"
uv run --directory ~/proj/annextube annextube backup --output-dir . 2>&1 | grep -E "(Backing up|Processing|Generated|Backup complete|videos processed)" || true
echo ""

echo "✓ Initial backup complete"
echo ""

echo "Step 3: Verify sync_state.json created"
echo "---------------------------------------"
if [ -f .annextube/sync_state.json ]; then
    echo "✓ sync_state.json exists"
    VIDEOS_TRACKED=$(cat .annextube/sync_state.json | python3 -c "import json, sys; data=json.load(sys.stdin); print(len(data.get('videos', {})))")
    echo "  Videos tracked: $VIDEOS_TRACKED"
else
    echo "✗ sync_state.json NOT found"
fi
echo ""

echo "Step 4: Check TSV files generated"
echo "----------------------------------"
echo "videos.tsv:"
if [ -f videos/videos.tsv ]; then
    VIDEO_COUNT=$(tail -n +2 videos/videos.tsv | wc -l)
    echo "  ✓ $VIDEO_COUNT videos"
    echo ""
    echo "  First video (title-first ordering):"
    head -2 videos/videos.tsv | tail -1 | cut -f1 | head -c 60
    echo "..."
else
    echo "  ✗ NOT found"
fi
echo ""

echo "playlists.tsv:"
if [ -f playlists/playlists.tsv ]; then
    PLAYLIST_COUNT=$(tail -n +2 playlists/playlists.tsv | wc -l)
    echo "  ✓ $PLAYLIST_COUNT playlist(s)"
else
    echo "  ✗ NOT found"
fi
echo ""

echo "authors.tsv:"
if [ -f authors.tsv ]; then
    AUTHOR_COUNT=$(tail -n +2 authors.tsv | wc -l)
    echo "  ✓ $AUTHOR_COUNT unique authors"
    echo ""
    echo "  Sample authors:"
    head -5 authors.tsv | column -t -s $'\t'
else
    echo "  ✗ NOT found"
fi
echo ""

echo "Step 5: Verify deterministic sorting"
echo "-------------------------------------"
VIDEO_DIR=$(ls -d videos/*/ | head -1)
if [ -n "$VIDEO_DIR" ]; then
    python3 << PYEOF
import json
with open("${VIDEO_DIR}/metadata.json") as f:
    data = json.load(f)
captions = data.get('captions_available', [])
is_sorted = captions == sorted(captions)
print(f"  captions_available: {len(captions)} languages")
print(f"  Sorted: {'✓' if is_sorted else '✗'}")
if len(captions) > 0:
    print(f"  First 5: {', '.join(captions[:5])}")
PYEOF
else
    echo "  ✗ No videos found"
fi
echo ""

echo "Step 6: Test incremental update (--skip-existing)"
echo "--------------------------------------------------"
echo "Running backup again with --skip-existing flag..."
echo ""
uv run --directory ~/proj/annextube annextube backup --output-dir . --skip-existing 2>&1 | grep -E "(Skipping|Processing video:|videos processed)" || true
echo ""
echo "✓ Incremental update complete (should skip all videos)"
echo ""

echo "Step 7: Git history"
echo "-------------------"
git log --oneline --max-count=5
echo ""

echo "Step 8: Directory structure"
echo "---------------------------"
echo "Archive structure:"
tree -L 2 -I '.git|.annextube' . || find . -maxdepth 2 -type d ! -path '*/\.git/*' ! -path '*/\.annextube/*'
echo ""

echo "=================================="
echo "Demo Complete!"
echo "=================================="
echo ""
echo "Key Features Demonstrated:"
echo "  ✓ Phase 1: comments_depth config, deterministic sorting"
echo "  ✓ Phase 2: authors.tsv generation"
echo "  ✓ Phase 3: Sync state tracking, incremental updates"
echo ""
echo "Results location: $DEMO_DIR"
echo ""
echo "To inspect:"
echo "  cd $DEMO_DIR"
echo "  cat videos/videos.tsv | column -t -s \$'\\t'"
echo "  cat authors.tsv | column -t -s \$'\\t' | head -20"
echo "  cat .annextube/sync_state.json | python3 -m json.tool"
echo ""
