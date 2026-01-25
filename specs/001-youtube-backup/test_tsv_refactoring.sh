#!/bin/bash
#
# Test script for TSV refactoring and new features
#
# Tests:
# - TSV location (videos/videos.tsv, playlists/playlists.tsv)
# - TSV column order (title first, path+id last)
# - Caption count (not boolean)
# - Caption language filtering
# - Comments download
# - Symlink separator (underscore)
# - Video renaming with git mv
#

set -e  # Exit on error

DEMO_DIR="/tmp/tsv-refactoring-demo"
REPO_DIR="$DEMO_DIR/my-archive"

echo "========================================"
echo "TSV Refactoring Test Demo"
echo "========================================"
echo

# Cleanup
echo "Cleaning up previous test..."
rm -rf "$DEMO_DIR"
mkdir -p "$DEMO_DIR"

# Step 1: Create archive
echo "Step 1: Creating archive..."
cd "$DEMO_DIR"
annextube create-dataset my-archive
cd my-archive

# Step 2: Create config with new defaults
echo
echo "Step 2: Creating config with new settings..."
echo "Note: Set YOUTUBE_API_KEY environment variable before running"

cat > .annextube/config.toml << 'EOF'
# Test config for TSV refactoring
# API key read from YOUTUBE_API_KEY environment variable

[[sources]]
url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
type = "playlist"
enabled = true

[components]
videos = false       # Just track URLs
metadata = true
comments = true      # NEW: Download comments
captions = true
thumbnails = true
caption_languages = "en.*"  # NEW: Only English captions

[organization]
video_path_pattern = "{date}_{sanitized_title}"  # NEW: No video_id
playlist_prefix_width = 4
playlist_prefix_separator = "_"  # NEW: Underscore separator

[filters]
limit = 3  # Just a few videos for testing
EOF

echo "Config created with:"
echo "  - video_path_pattern: {date}_{sanitized_title} (no video_id)"
echo "  - caption_languages: en.* (English only)"
echo "  - playlist_prefix_separator: _ (underscore)"
echo "  - comments: true"

# Step 3: Backup playlist
echo
echo "Step 3: Backing up playlist (limit 3 videos)..."
# Note: This will fail without a real API key, but we can check the structure
annextube backup \
  --output-dir . \
  https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf \
  || echo "Backup failed (expected without API key)"

# Step 4: Verify TSV structure
echo
echo "Step 4: Verifying TSV structure..."

if [ -f "videos/videos.tsv" ]; then
  echo "✓ videos/videos.tsv found in correct location"
  echo "  Header:"
  head -n 1 videos/videos.tsv
  echo "  Columns should be: title, channel, published, duration, views, likes, comments, captions, path, video_id"
else
  echo "✗ videos/videos.tsv not found"
fi

if [ -f "playlists/playlists.tsv" ]; then
  echo "✓ playlists/playlists.tsv found in correct location"
  echo "  Header:"
  head -n 1 playlists/playlists.tsv
  echo "  Columns should be: title, channel, video_count, total_duration, last_updated, path, playlist_id"
else
  echo "✗ playlists/playlists.tsv not found"
fi

# Step 5: Verify symlink separator
echo
echo "Step 5: Verifying playlist symlink naming..."
echo "Playlist symlinks (should use underscore separator):"
ls -la playlists/*/ 2>/dev/null | grep "^l" | head -n 3 || echo "No symlinks found"
echo "  Expected format: 0001_2020-01-10_video-title (underscore after index)"

# Step 6: Verify video paths (no video_id)
echo
echo "Step 6: Verifying video directory names..."
echo "Video directories (should NOT contain video_id):"
ls -d videos/*/ 2>/dev/null | head -n 3 || echo "No videos found"
echo "  Expected format: YYYY-MM-DD_video-title (no ID)"

# Step 7: Verify caption files (English only)
echo
echo "Step 7: Verifying caption language filtering..."
echo "Caption files (should be English only):"
find videos -name "*.vtt" 2>/dev/null | head -n 5 || echo "No captions found"
echo "  Expected: Only en.* language codes"

# Step 8: Verify comments.json
echo
echo "Step 8: Verifying comments download..."
echo "Comments files:"
find videos -name "comments.json" 2>/dev/null | head -n 3 || echo "No comments found"

# Step 9: Test video renaming
echo
echo "Step 9: Testing video renaming (change path pattern)..."
echo "Changing config to include video_id in path..."

cat > .annextube/config.toml << 'EOF'
api_key = "YOUR_API_KEY_HERE"

[[sources]]
url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
type = "playlist"
enabled = true

[components]
videos = false
metadata = true
comments = true
captions = true
thumbnails = true
caption_languages = "en.*"

[organization]
video_path_pattern = "{date}_{video_id}_{sanitized_title}"  # CHANGED: Include video_id
playlist_prefix_width = 4
playlist_prefix_separator = "_"

[filters]
limit = 3
EOF

echo "Re-running backup to test renaming..."
annextube backup \
  --output-dir . \
  https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf \
  || echo "Backup failed (expected without API key)"

echo
echo "Video directories after path pattern change:"
ls -d videos/*/ 2>/dev/null | head -n 3 || echo "No videos found"
echo "  Expected: Now includes video_id in path"

echo
echo "Git log (should show 'git mv' renames):"
git log --oneline --all -n 10 2>/dev/null || echo "No git history"

# Summary
echo
echo "========================================"
echo "Test Summary"
echo "========================================"
echo
echo "Verify the following manually:"
echo "1. ✓ videos/videos.tsv exists with title-first column order"
echo "2. ✓ playlists/playlists.tsv exists with title-first column order"
echo "3. ✓ TSV has 'captions' column (count) not 'has_captions' (boolean)"
echo "4. ✓ TSV has 'path' column not 'file_path'/'folder_name'"
echo "5. ✓ TSV has video_id/playlist_id as last column"
echo "6. ✓ Playlist symlinks use underscore separator (0001_...)"
echo "7. ✓ Video paths don't include video_id by default"
echo "8. ✓ Only English captions downloaded (en.* filter)"
echo "9. ✓ comments.json files created"
echo "10. ✓ Videos renamed with git mv when path pattern changed"
echo
echo "Test directory: $REPO_DIR"
echo
