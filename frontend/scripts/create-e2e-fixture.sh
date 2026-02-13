#!/bin/bash
# Create E2E test fixture for archive-workflow.spec.ts
#
# Produces an archive with both 'downloaded' and 'metadata_only' videos by
# running two backup passes with different config:
#   Phase 1: videos=true, limit=3  → 3 most recent videos get 'downloaded'
#   Phase 2: videos=false, no limit → remaining 7 videos get 'tracked' → mapped to 'metadata_only'
#   Phase 3: generate-web → produces the web UI that Playwright tests against
#
# Usage:
#   bash frontend/scripts/create-e2e-fixture.sh [OUTPUT_DIR]
#   # default OUTPUT_DIR: test-archives/archive-workflow-fixture
#
# Requires: YOUTUBE_API_KEY env var (for channel metadata), network access

set -euo pipefail

FIXTURE_DIR="${1:-test-archives/archive-workflow-fixture}"
CHANNEL_URL="https://www.youtube.com/@AnnexTubeTesting"
ANNEXTUBE="${ANNEXTUBE:-python -m annextube}"

echo "=== Creating E2E fixture at $FIXTURE_DIR ==="

# Clean up any existing fixture
if [ -d "$FIXTURE_DIR" ]; then
    echo "Removing existing fixture..."
    rm -rf "$FIXTURE_DIR"
fi

# Phase 1: Init with videos enabled, limit 3
echo ""
echo "=== Phase 1: Init + backup (videos=true, limit=3) ==="
$ANNEXTUBE init "$FIXTURE_DIR" "$CHANNEL_URL" \
    --limit 3 \
    --comments-depth 0 \
    --no-captions \
    --no-thumbnails \
    --include-playlists all

$ANNEXTUBE backup --output-dir "$FIXTURE_DIR"

# Phase 2: Disable video downloading, remove limit, backup again
# This picks up the remaining videos as 'tracked' (metadata only)
echo ""
echo "=== Phase 2: Reconfigure (videos=false, no limit) + backup ==="
CONFIG_FILE="$FIXTURE_DIR/.annextube/config.toml"

# Flip videos = true → false
sed -i 's/^videos = true/videos = false/' "$CONFIG_FILE"

# Remove or comment out the limit line
sed -i 's/^limit = [0-9]*/# limit removed for phase 2/' "$CONFIG_FILE"

# Commit config change so backup sees a clean tree
git -C "$FIXTURE_DIR" add -A && git -C "$FIXTURE_DIR" commit -m "Phase 2: disable videos, remove limit"

$ANNEXTUBE backup --output-dir "$FIXTURE_DIR"

# Phase 3: Export + generate web UI
echo ""
echo "=== Phase 3: Export + generate-web ==="

# Phase 3.5: Create synthetic caption files for downloaded videos
# NOTE: @AnnexTubeTesting videos are 1-5 seconds long — cues must fit within that range
echo "--- Phase 3.5: Adding synthetic captions to downloaded videos ---"
for VIDEO_DIR in $(find "$FIXTURE_DIR/videos" -name "video.mkv" -exec dirname {} \;); do
    # Create English VTT
    cat > "$VIDEO_DIR/video.en.vtt" << 'VTTEOF'
WEBVTT

00:00:00.000 --> 00:00:01.000
Welcome to this test video

00:00:01.000 --> 00:00:02.000
This is the second caption cue

00:00:02.000 --> 00:00:03.000
And this is the searchable third cue

00:00:03.000 --> 00:00:04.000
The final caption for testing
VTTEOF

    # Create Spanish VTT
    cat > "$VIDEO_DIR/video.es.vtt" << 'VTTEOF'
WEBVTT

00:00:00.000 --> 00:00:01.000
Bienvenidos a este video de prueba

00:00:01.000 --> 00:00:02.000
Este es el segundo subtitulo

00:00:02.000 --> 00:00:03.000
Y este es el tercer subtitulo buscable

00:00:03.000 --> 00:00:04.000
El subtitulo final para pruebas
VTTEOF

    # Update metadata.json to include captions_available
    if command -v jq &>/dev/null; then
        jq '.captions_available = ["en", "es"]' "$VIDEO_DIR/metadata.json" > "$VIDEO_DIR/metadata.json.tmp" \
            && mv "$VIDEO_DIR/metadata.json.tmp" "$VIDEO_DIR/metadata.json"
    else
        # Fallback: use python if jq not available
        python3 -c "
import json, sys
with open('$VIDEO_DIR/metadata.json') as f:
    data = json.load(f)
data['captions_available'] = ['en', 'es']
with open('$VIDEO_DIR/metadata.json', 'w') as f:
    json.dump(data, f, indent=2)
"
    fi
    echo "  Added captions to: $VIDEO_DIR"
done
git -C "$FIXTURE_DIR" add -A && git -C "$FIXTURE_DIR" commit -m "Add synthetic captions for E2E tests"

$ANNEXTUBE export --output-dir "$FIXTURE_DIR"
$ANNEXTUBE generate-web --output-dir "$FIXTURE_DIR"

# Verify
echo ""
echo "=== Fixture verification ==="
VIDEOS_TSV="$FIXTURE_DIR/videos/videos.tsv"
if [ -f "$VIDEOS_TSV" ]; then
    TOTAL=$(tail -n +2 "$VIDEOS_TSV" | wc -l)
    DOWNLOADED=$(grep -c 'downloaded' "$VIDEOS_TSV" || true)
    METADATA_ONLY=$(grep -c 'metadata_only' "$VIDEOS_TSV" || true)
    echo "Total videos:    $TOTAL"
    echo "Downloaded:      $DOWNLOADED"
    echo "Metadata only:   $METADATA_ONLY"
else
    echo "ERROR: videos.tsv not found!"
    exit 1
fi

if [ -f "$FIXTURE_DIR/web/index.html" ]; then
    echo "Web UI:          OK"
else
    echo "ERROR: web/index.html not found!"
    exit 1
fi

echo ""
echo "=== Fixture ready at $FIXTURE_DIR ==="
