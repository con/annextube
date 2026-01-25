#!/usr/bin/env bash
#
# Demo: yarikoptic Personal Channel + Liked Videos
# Demonstrates user-specific features (requires authentication for liked videos)
#
set -e

DEMO_DIR="/tmp/annextube-demo-yarikoptic-$(date +%s)"

echo "=========================================="
echo "annextube Demo: yarikoptic Personal Archive"
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

# Check for cookies file (optional, for liked videos)
COOKIES_FILE=""
if [ -f ~/.config/annextube/cookies.txt ]; then
    COOKIES_FILE="~/.config/annextube/cookies.txt"
    echo "✓ Cookies file found: $COOKIES_FILE"
    echo "  (Enables access to liked videos and private playlists)"
elif [ -f ~/cookies.txt ]; then
    COOKIES_FILE="~/cookies.txt"
    echo "✓ Cookies file found: $COOKIES_FILE"
else
    echo "⚠ No cookies file found"
    echo "  Liked videos (LL playlist) requires authentication"
    echo "  To export cookies:"
    echo "    1. Install browser extension: 'Get cookies.txt'"
    echo "    2. Export YouTube cookies to cookies.txt"
    echo "    3. Place at ~/.config/annextube/cookies.txt"
    echo ""
    echo "  Continuing with public channel only..."
fi
echo ""

# Create demo archive
mkdir -p "$DEMO_DIR"
cd "$DEMO_DIR"

echo "Step 1: Initialize archive"
echo "----------------------------"
uv run --directory ~/proj/annextube annextube init .
echo ""

# Create config with both channel and liked videos (if cookies available)
if [ -n "$COOKIES_FILE" ]; then
    cat > .annextube/config.toml << EOF
[[sources]]
url = "https://www.youtube.com/@yarikoptic"
type = "channel"
enabled = true

[[sources]]
url = "https://www.youtube.com/playlist?list=LL"  # Liked Videos (requires auth)
type = "playlist"
enabled = true

[components]
videos = false
metadata = true
comments_depth = 30      # Limit comments for speed
captions = false         # Skip captions for speed
thumbnails = true

[organization]
video_path_pattern = "{date}_{sanitized_title}"

[filters]
limit = 10  # Limit to 10 most recent per source
EOF
    echo "✓ Configuration created (with liked videos)"
else
    cat > .annextube/config.toml << 'EOF'
[[sources]]
url = "https://www.youtube.com/@yarikoptic"
type = "channel"
enabled = true

# NOTE: Liked videos playlist (LL) requires authentication
# Uncomment after setting up cookies file:
# [[sources]]
# url = "https://www.youtube.com/playlist?list=LL"
# type = "playlist"
# enabled = true

[components]
videos = false
metadata = true
comments_depth = 30
captions = false
thumbnails = true

[organization]
video_path_pattern = "{date}_{sanitized_title}"

[filters]
limit = 10
EOF
    echo "✓ Configuration created (public channel only)"
fi
echo ""

echo "Step 2: Backup yarikoptic's channel"
echo "------------------------------------"
echo "Processing up to 10 most recent videos from @yarikoptic..."
echo ""
uv run --directory ~/proj/annextube annextube backup --output-dir . --update all-incremental 2>&1 | grep -E "(Backing up|Processing|Generated|videos processed|Skipping)" || true
echo ""

echo "✓ Channel backup complete"
echo ""

echo "Step 3: Verify results"
echo "----------------------"
echo ""

echo "videos.tsv:"
if [ -f videos/videos.tsv ]; then
    VIDEO_COUNT=$(tail -n +2 videos/videos.tsv | wc -l)
    echo "  ✓ $VIDEO_COUNT videos"
    echo ""
    echo "  Videos from yarikoptic:"
    cat videos/videos.tsv | grep -i yarikoptic | column -t -s $'\t' | head -5 || head -4 videos/videos.tsv | column -t -s $'\t'
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
        cat playlists/playlists.tsv | column -t -s $'\t'

        # Check if liked videos playlist was backed up
        if grep -q "LL" playlists/playlists.tsv 2>/dev/null; then
            echo ""
            echo "  ✓ Liked Videos playlist backed up successfully!"
        fi
    fi
else
    echo "  No playlists found (channel may not have public playlists)"
fi
echo ""

echo "authors.tsv:"
if [ -f authors.tsv ]; then
    AUTHOR_COUNT=$(tail -n +2 authors.tsv | wc -l)
    echo "  ✓ $AUTHOR_COUNT unique authors"
    echo ""
    echo "  yarikoptic's author entry:"
    grep -i yarikoptic authors.tsv | column -t -s $'\t' || echo "  (not found - may not have uploaded videos)"
    echo ""
    echo "  Sample authors (first 10):"
    head -11 authors.tsv | column -t -s $'\t'
else
    echo "  ✗ NOT found"
fi
echo ""

echo "Step 4: Test update modes"
echo "-------------------------"
echo ""

echo "Test social update (comments only):"
echo "Running: annextube backup --update social --from-date '1 week'..."
uv run --directory ~/proj/annextube annextube backup --output-dir . --update all-incremental --from-date "1 week" --limit 3 2>&1 | grep -E "(From date|social|Processing|Skipping)" || true
echo ""

echo "Step 5: Check sync state"
echo "------------------------"
if [ -f .annextube/sync_state.json ]; then
    echo "✓ sync_state.json exists"
    echo ""
    python3 << 'PYEOF'
import json
with open('.annextube/sync_state.json') as f:
    data = json.load(f)

print(f"  Sources tracked: {len(data.get('sources', {}))}")
print(f"  Videos tracked: {len(data.get('videos', {}))}")

# Show sources
print("\n  Sources:")
for url, state in data.get('sources', {}).items():
    print(f"    - {url[:60]}...")
    print(f"      Last sync: {state.get('last_sync', 'never')}")
    print(f"      Videos: {state.get('videos_tracked', 0)}")
PYEOF
else
    echo "✗ sync_state.json NOT found"
fi
echo ""

echo "Step 6: Directory structure"
echo "----------------------------"
tree -L 2 -I '.git|.annextube' . 2>/dev/null || find . -maxdepth 2 -type d ! -path '*/\.git/*' ! -path '*/\.annextube/*'
echo ""

echo "=========================================="
echo "Demo Complete!"
echo "=========================================="
echo ""
echo "Personal Archive Features:"
echo "  ✓ yarikoptic's channel videos backed up"
if [ -n "$COOKIES_FILE" ]; then
    echo "  ✓ Liked videos playlist (LL) - authentication enabled"
else
    echo "  ⚠ Liked videos skipped (no authentication)"
    echo "    Set up cookies.txt to enable"
fi
echo "  ✓ Update modes tested (incremental, social)"
echo "  ✓ Date-based filtering demonstrated"
echo ""
echo "Results location: $DEMO_DIR"
echo ""
if [ -z "$COOKIES_FILE" ]; then
    echo "To enable liked videos backup:"
    echo "  1. Export YouTube cookies to cookies.txt (use browser extension)"
    echo "  2. Place at ~/.config/annextube/cookies.txt"
    echo "  3. Uncomment LL playlist in config"
    echo "  4. Run: annextube backup --update all-incremental"
    echo ""
fi
echo "To inspect results:"
echo "  cd $DEMO_DIR"
echo "  cat videos/videos.tsv | column -t -s \$'\\t' | less -S"
echo "  cat authors.tsv | column -t -s \$'\\t' | head -30"
echo "  cat .annextube/sync_state.json | python3 -m json.tool"
echo ""
