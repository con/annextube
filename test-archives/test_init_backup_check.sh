#!/bin/bash
# Minimal script to test init, backup, and check on apopyk and datalad channels

set -e  # Exit on error

# Default limit
LIMIT=${1:-10}

echo "Testing with limit=$LIMIT"
echo "========================================"
echo

# Channels to test
declare -A CHANNELS
CHANNELS[apopyk]="https://www.youtube.com/@apopyk"
CHANNELS[datalad]="https://youtube.com/c/datalad"

# Clean up old test repos
for channel in "${!CHANNELS[@]}"; do
    if [ -d "$channel" ]; then
        echo "Cleaning up old $channel directory..."
        chmod -R u+w "$channel" 2>/dev/null || true
        rm -rf "$channel"
    fi
done

echo

# Test each channel
for channel in "${!CHANNELS[@]}"; do
    url="${CHANNELS[$channel]}"
    echo "========================================"
    echo "Testing: $channel ($url)"
    echo "========================================"
    echo

    # Step 1: Init
    echo "Step 1: annextube init"
    echo "----------------------"
    annextube init "$channel" "$url" --no-videos --comments 10 --captions --thumbnails --limit "$LIMIT" --include-playlists all
    echo

    # Step 2: Backup
    echo "Step 2: annextube backup"
    echo "----------------------"
    cd "$channel"
    annextube backup
    cd ..
    echo

    # Step 3: Check
    echo "Step 3: annextube check"
    echo "----------------------"
    annextube check --output-dir "$channel" || echo "⚠ Check found issues (see above)"
    echo

    # Quick stats
    echo "Quick stats:"
    echo "  Videos: $(ls $channel/videos 2>/dev/null | wc -l)"
    echo "  Playlists: $(ls $channel/playlists 2>/dev/null | wc -l)"
    echo "  Captions: $(find $channel -name '*.vtt' 2>/dev/null | wc -l)"
    echo "  Comments: $(find $channel -name 'comments.json' 2>/dev/null | wc -l)"
    echo "  Thumbnails: $(find $channel -name 'thumbnail.jpg' 2>/dev/null | wc -l)"
    echo "  Git commits: $(cd $channel && git rev-list --count HEAD)"
    echo

done

echo "========================================"
echo "All tests completed successfully!"
echo "========================================"
echo
echo "Test archives available at:"
for channel in "${!CHANNELS[@]}"; do
    echo "  - $(pwd)/$channel/"
done
