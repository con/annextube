# annextube Web UI Testing Procedure

This document describes how to test the annextube web UI end-to-end to verify all features work correctly.

## Quick Start

```bash
# 1. Create or use existing test archive
cd /path/to/test-archive

# 2. Start the server
annextube serve --port 8080 &

# 3. Run automated tests
cd /path/to/annextube
uv run python tests/e2e/test_web_ui.py

# 4. Stop the server when done
pkill -f "annextube serve"
```

## Creating a Fresh Test Archive

```bash
# Create archive directory
mkdir -p ~/test-archives/my-test-archive
cd ~/test-archives/my-test-archive

# Initialize repository
annextube init

# Edit config to add a channel and enable playlists
nano .annextube/config.toml

# Add to config:
[[sources]]
url = "https://www.youtube.com/@YourChannel"
type = "channel"
enabled = true
include_playlists = "all"  # Auto-discover all playlists

# Set video limit for testing (optional)
[filters]
limit = 10  # Only fetch 10 most recent videos

# Run backup
annextube backup

# Generate web UI
annextube generate-web

# Export TSV files
annextube export
```

## Manual Testing Checklist

### 1. Web UI Loads

- [ ] Navigate to `http://localhost:8080/web/`
- [ ] Page loads without redirect loop
- [ ] Video count is displayed correctly
- [ ] Filter panel is visible

### 2. Download Status Filters

- [ ] Click "Downloaded" checkbox
- [ ] Videos with downloaded content are shown
- [ ] Click "Tracked" checkbox
- [ ] Videos with URL-only tracking are shown
- [ ] Uncheck both - all videos shown

### 3. Video Playback

- [ ] Click on a video thumbnail
- [ ] Video player loads
- [ ] Video duration is displayed correctly
- [ ] Click on timeline to seek
- [ ] Video jumps to clicked position
- [ ] Video plays smoothly

### 4. Captions

- [ ] Open video with captions
- [ ] Caption tracks are available in video player
- [ ] Select a caption language
- [ ] Captions display correctly

### 5. Playlists

- [ ] Playlist filter section is visible
- [ ] Playlist names are human-readable (not `{PLxxxxx}`)
- [ ] Click playlist filter
- [ ] Only videos from that playlist are shown
- [ ] Playlist video count is correct

### 6. Search

- [ ] Type in search box
- [ ] Results filter as you type
- [ ] Search finds videos by title
- [ ] Search finds videos by channel name

### 7. Date Range

- [ ] Select "Last Week" preset
- [ ] Videos filtered to last week
- [ ] Custom date range works
- [ ] "All Time" shows all videos

## Automated Test Coverage

The `test_web_ui.py` script tests:

1. **Main Page Load**: Page loads, title correct, video count shown
2. **Download Status Filters**: Downloaded/Tracked checkboxes filter correctly
3. **Video Playback**: Player loads, seeking works, Range requests functional
4. **Playlists**: Playlist section exists and is accessible

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8080
lsof -ti:8080

# Kill it
kill $(lsof -ti:8080)

# Or use different port
annextube serve --port 8081
```

### Videos Show "Not Downloaded"

Check if videos are tracked or downloaded:

```bash
# Check symlink target
ls -la videos/*/video.mkv | head -3

# URL-only (tracked):
# → .git/annex/objects/.../URL--yt&...

# Downloaded (content present):
# → .git/annex/objects/.../SHA256--...
```

### Playlists Have Broken Names

If playlists show `{PLxxxxx}` names instead of titles:

1. Check `.annextube/config.toml`:
   ```toml
   playlist_path_pattern = "{playlist_id}"  # Should be single braces
   ```

2. Delete broken playlists and re-run:
   ```bash
   rm -rf playlists/{PL*}
   annextube backup --update=playlists
   ```

### Range Requests Not Working

Video seeking doesn't work:

1. Verify server has Range support:
   ```bash
   curl -I -H "Range: bytes=0-1023" http://localhost:8080/videos/.../video.mkv
   # Should return: HTTP/1.0 206 Partial Content
   ```

2. Check server logs for errors
3. Ensure using `annextube serve`, not standard Python http.server

## Testing After Changes

Whenever you make changes to:

### Backend (Python Code)

```bash
# 1. Update test archive
cd /path/to/test-archive
annextube backup --update=all-incremental

# 2. Regenerate exports
annextube export

# 3. Restart server
pkill -f "annextube serve"
annextube serve --regenerate &

# 4. Run tests
uv run python tests/e2e/test_web_ui.py
```

### Frontend (Svelte Code)

```bash
# 1. Rebuild frontend
cd frontend
npm run build

# 2. Regenerate web UI in archive
cd /path/to/test-archive
annextube generate-web

# 3. Restart server
pkill -f "annextube serve"
annextube serve &

# 4. Test in browser
open http://localhost:8080/web/
```

### Configuration Format

```bash
# 1. Delete old test archive
rm -rf ~/test-archives/my-test-archive

# 2. Create fresh archive with new config format
# (follow "Creating a Fresh Test Archive" above)

# 3. Run full test suite
uv run python tests/e2e/test_web_ui.py
```

## CI/CD Integration

Add to GitHub Actions:

```yaml
- name: Run E2E Tests
  run: |
    # Create test archive
    annextube init --output-dir test-archive

    # Backup sample channel (with limit)
    cd test-archive
    # ... configure and backup ...

    # Start server in background
    annextube serve --port 8080 &
    SERVER_PID=$!

    # Run tests
    cd ..
    uv run python tests/e2e/test_web_ui.py --url http://localhost:8080

    # Cleanup
    kill $SERVER_PID
```

## Performance Testing

For larger archives:

```bash
# Test with many videos
[filters]
limit = 1000

# Monitor performance
time annextube backup
time annextube export
time annextube generate-web

# Check web UI responsiveness
# - Initial load time
# - Filter response time
# - Search latency
```

## Snapshot Testing

Save known-good state:

```bash
# After successful test run
cd /path/to/test-archive
tar czf ../test-archive-baseline.tar.gz .

# Later, restore for testing
tar xzf test-archive-baseline.tar.gz -C test-archive-restored
```
