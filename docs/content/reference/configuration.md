---
title: "Configuration Reference"
description: "Complete reference for annextube configuration options"
weight: 10
---

# Configuration Reference

This document describes all configuration options available in annextube.

## Configuration Files

### Archive Configuration

**Location**: `.annextube/config.toml` (in each archive repository)

**Scope**: Archive-specific settings (sources, components, filters, organization)

### User Configuration

**Location**: Platform-specific user config directory:
- **Linux**: `~/.config/annextube/config.toml`
- **macOS**: `~/Library/Application Support/annextube/config.toml`
- **Windows**: `%APPDATA%/annextube/config.toml`

**Scope**: User-wide settings (authentication, network, global preferences)

---

## Archive Configuration (`.annextube/config.toml`)

### `[sources]`

Define YouTube channels and playlists to archive.

```toml
[[sources]]
url = "https://www.youtube.com/@channel-name"
type = "channel"
include_playlists = "all"      # "all", "none", or list of playlist IDs
exclude_playlists = []         # List of playlist IDs to exclude
include_podcasts = "all"       # "all", "none", or "only"
```

**Fields**:
- `url` (string, required): YouTube channel or playlist URL
- `type` (string, required): `"channel"` or `"playlist"`
- `include_playlists` (string, optional): `"all"` (default), `"none"`, or list of playlist IDs
- `exclude_playlists` (list, optional): Playlist IDs to exclude
- `include_podcasts` (string, optional): `"all"` (default), `"none"`, or `"only"`

---

### `[components]`

Control which components to download and archive.

```toml
[components]
videos = true            # Download video files
metadata = true          # Save metadata.json
captions = true          # Download captions/subtitles
thumbnails = true        # Download thumbnails
comments_depth = 100     # Max comment threads to fetch (0 = none)
```

**Fields**:
- `videos` (boolean, default: `true`): Download video files (`.mkv`)
- `metadata` (boolean, default: `true`): Save `metadata.json` files
- `captions` (boolean, default: `true`): Download captions (`.vtt`)
- `thumbnails` (boolean, default: `true`): Download thumbnails (`.jpg`)
- `comments_depth` (integer, default: `100`): Max comment threads per video (0 = disable)

**Note**: `metadata = false` is not recommended - metadata is required for TSV generation and web UI.

---

### `[filters]`

Filter which videos to archive based on criteria.

```toml
[filters]
limit = 100              # Limit to N most recent videos (null = all)
date_start = "2020-01-01"  # ISO 8601 date (upload date)
date_end = "2025-12-31"    # ISO 8601 date (upload date)
license = "creativeCommon" # Filter by license ("standard" or "creativeCommon")
min_duration = 60        # Minimum duration in seconds
max_duration = 3600      # Maximum duration in seconds
min_views = 1000         # Minimum view count
tags = ["python", "tutorial"]  # Filter by tags (any match)
```

**Fields**:
- `limit` (integer, optional): Limit to N most recent videos (default: `null` = all)
- `date_start` (string, optional): Minimum upload date (ISO 8601: `YYYY-MM-DD`)
- `date_end` (string, optional): Maximum upload date (ISO 8601: `YYYY-MM-DD`)
- `license` (string, optional): `"standard"` or `"creativeCommon"`
- `min_duration` (integer, optional): Minimum duration in seconds
- `max_duration` (integer, optional): Maximum duration in seconds
- `min_views` (integer, optional): Minimum view count
- `tags` (list, optional): Filter by tags (matches any tag)

**Date filter behavior**:
- **Initial backup**: Date filters ignored (archives all videos)
- **Incremental updates**: Date filters applied (only processes videos in range)

---

### `[organization]`

Control repository organization and file naming patterns.

```toml
[organization]
video_path_pattern = "{year}/{month}/{date}_{sanitized_title}"
channel_path_pattern = "{channel_id}"
playlist_path_pattern = "{playlist_title}"
playlist_video_pattern = "{video_index:04d}_{video_path_basename}"
video_filename = "video.mkv"
```

**Fields**:
- `video_path_pattern` (string, default: hierarchical by date):
  - Available placeholders: `{year}`, `{month}`, `{day}`, `{date}`, `{video_id}`, `{sanitized_title}`, `{channel_id}`, `{channel_name}`
  - Default: `"{year}/{month}/{date}_{sanitized_title}"` (hierarchical)
  - Flat: `"{video_id}"` or `"{sanitized_title}"`

- `channel_path_pattern` (string, default: `"{channel_id}"`):
  - Used for multi-channel collections
  - Available placeholders: `{channel_id}`, `{channel_name}`

- `playlist_path_pattern` (string, default: `"{playlist_title}"`):
  - Available placeholders: `{playlist_id}`, `{playlist_title}`, `{channel_id}`, `{channel_name}`
  - Default: `"{playlist_title}"` (uses sanitized title)

- `playlist_video_pattern` (string, default: `"{video_index:04d}_{video_path_basename}"`):
  - Pattern for video symlinks in playlists
  - Available placeholders: `{video_index}`, `{video_path_basename}`, `{video_id}`
  - Default: `"0001_2026-01-15_example-video"` format

- `video_filename` (string, default: `"video.mkv"`):
  - Filename for video file within video directory

**Example paths**:

Hierarchical (default):
```
videos/2026/02/2026-02-07_example-video/
  ├── metadata.json
  ├── video.mkv
  └── thumbnail.jpg
```

Flat:
```
videos/example-video/
  ├── metadata.json
  ├── video.mkv
  └── thumbnail.jpg
```

---

### `[backup]` ⭐ NEW

Configure backup behavior for checkpoints and interruption recovery.

```toml
[backup]
checkpoint_interval = 50        # Commit every N videos (0 = disabled)
checkpoint_enabled = true       # Enable periodic commits
auto_commit_on_interrupt = true # Auto-commit partial work on Ctrl+C
```

**Fields**:

- `checkpoint_interval` (integer, default: `50`):
  - Create checkpoint commit every N videos
  - `0` = disabled (single commit at end)
  - Recommended: 25-100 depending on channel size

- `checkpoint_enabled` (boolean, default: `true`):
  - Enable/disable periodic checkpoint commits
  - `false` = single commit at end (cleaner git history)
  - `true` = checkpoint commits (safer, auto-resume)

- `auto_commit_on_interrupt` (boolean, default: `true`):
  - Auto-commit partial progress on Ctrl+C
  - `false` = leave uncommitted (requires manual recovery)
  - `true` = auto-commit (safe Ctrl+C, recommended)

**Benefits of checkpoints**:
- ✅ Zero data loss on interruption (Ctrl+C, crash, quota)
- ✅ Auto-resume via incremental mode
- ✅ Progress visible in git history
- ✅ TSVs updated incrementally (web UI works immediately)

**Trade-offs**:
- More commits in git history (minimal overhead ~1KB/commit)
- Slightly slower (TSV regeneration + commit every N videos)

**Example commit history**:
```
a1b2c3d Checkpoint: @channel (50/300 videos)
e4f5g6h Checkpoint: @channel (100/300 videos)
i7j8k9l Checkpoint: @channel (150/300 videos)
[Ctrl+C pressed]
m0n1o2p Partial backup (interrupted): @channel (173 videos)
```

**See also**: [Handling Quota Limits and Interruptions](../how-to/quota-and-interruptions) for detailed usage guide.

---

## User Configuration (`~/.config/annextube/config.toml`)

### `[user]` (Authentication)

```toml
[user]
api_key = "YOUR_YOUTUBE_API_KEY"           # YouTube Data API v3 key
cookies_file = "/path/to/cookies.txt"      # Netscape cookies file
cookies_from_browser = "firefox"           # Browser name for cookie extraction
```

**Fields**:
- `api_key` (string, optional): YouTube Data API v3 key
  - Fallback if `YOUTUBE_API_KEY` env var not set
  - Required for enhanced metadata (license, recording location, etc.)
  - Get key: [Google Cloud Console](https://console.cloud.google.com/apis/credentials)

- `cookies_file` (string, optional): Path to Netscape cookies.txt file
  - Used for authenticated requests (private/unlisted videos)
  - Extract with browser extensions (e.g., "Get cookies.txt")

- `cookies_from_browser` (string, optional): Browser name for cookie extraction
  - Supported: `"firefox"`, `"chrome"`, `"chromium"`, `"edge"`, `"safari"`
  - With profile: `"chrome:Profile 1"`, `"firefox:default-release"`
  - Automatically extracts cookies from browser's cookie store

**Note**: `YOUTUBE_API_KEY` environment variable takes precedence over config file.

---

### `[user.network]` (Network Settings)

```toml
[user.network]
proxy = "http://proxy.example.com:8080"
rate_limit = 1000000  # Bytes per second (null = unlimited)
retries = 3
timeout = 300
```

**Fields**:
- `proxy` (string, optional): HTTP/HTTPS proxy URL
- `rate_limit` (integer, optional): Download rate limit in bytes/second
- `retries` (integer, default: `3`): Number of retries on network errors
- `timeout` (integer, default: `300`): Request timeout in seconds

---

## Python API Configuration

For custom scripts using annextube as a library:

### QuotaManager Configuration

```python
from annextube.lib.quota_manager import QuotaManager

# Default: enabled, 48h max wait, 30min check interval
quota_manager = QuotaManager()

# Custom settings
quota_manager = QuotaManager(
    enabled=True,                    # Enable auto-wait
    max_wait_hours=24,               # Max 24h wait
    check_interval_seconds=900       # Check every 15 minutes
)

# Disable auto-wait (abort on quota exceeded)
quota_manager = QuotaManager(enabled=False)
```

**Parameters**:
- `enabled` (boolean, default: `True`): Enable automatic quota wait
- `max_wait_hours` (integer, default: `48`): Maximum hours to wait before aborting
- `check_interval_seconds` (integer, default: `1800`): Seconds between quota checks

**Usage with YouTube API clients**:

```python
from annextube.services.youtube_api import YouTubeAPIMetadataClient

client = YouTubeAPIMetadataClient(
    api_key="YOUR_API_KEY",
    quota_manager=quota_manager
)
```

**See also**: [Handling Quota Limits and Interruptions](../how-to/quota-and-interruptions) for usage examples.

---

## Environment Variables

### `YOUTUBE_API_KEY`

YouTube Data API v3 key (overrides config file).

```bash
export YOUTUBE_API_KEY="AIzaSy..."
annextube backup --output-dir my-archive
```

**Priority**: Environment variable > User config file > None

---

## Complete Example

### `.annextube/config.toml` (Archive)

```toml
# Data sources
[[sources]]
url = "https://www.youtube.com/@3blue1brown"
type = "channel"
include_playlists = "all"
include_podcasts = "all"

# What to download
[components]
videos = true
metadata = true
captions = true
thumbnails = true
comments_depth = 100

# Filters
[filters]
limit = 500              # Only 500 most recent videos
date_start = "2020-01-01"  # Videos from 2020 onwards
min_views = 1000         # At least 1000 views

# Organization
[organization]
video_path_pattern = "{year}/{month}/{date}_{sanitized_title}"
playlist_path_pattern = "{playlist_title}"

# Backup behavior
[backup]
checkpoint_interval = 50
checkpoint_enabled = true
auto_commit_on_interrupt = true
```

### `~/.config/annextube/config.toml` (User)

```toml
[user]
api_key = "AIzaSy..."
cookies_from_browser = "firefox"

[user.network]
rate_limit = 5000000  # 5 MB/s
timeout = 300
```

---

## Migration from Old Config

If upgrading from older annextube versions:

### Before (v0.1.x)

```toml
# No backup section
```

### After (v0.2.x)

```toml
[backup]
checkpoint_interval = 50        # NEW: Periodic checkpoints
checkpoint_enabled = true       # NEW: Enable checkpoints
auto_commit_on_interrupt = true # NEW: Auto-commit on Ctrl+C
```

**Default values** apply automatically if section is missing (backward compatible).

---

## Validation

annextube validates configuration on load and reports errors:

```bash
$ annextube backup

ERROR - Invalid config: checkpoint_interval must be >= 0
ERROR - Invalid config: date_start must be ISO 8601 format (YYYY-MM-DD)
```

---

## See Also

- [Handling Quota Limits and Interruptions](../how-to/quota-and-interruptions) - Detailed quota and checkpoint guide
- [Troubleshooting](../how-to/troubleshooting) - Common configuration issues
