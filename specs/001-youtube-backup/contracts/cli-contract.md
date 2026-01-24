# CLI Contract: annextube

**Version**: 1.0.0
**Date**: 2026-01-24
**Purpose**: Define command-line interface contract for annextube CLI

## Overview

The annextube CLI follows Unix philosophy and Constitution Principle II (Multi-Interface Exposure):
- Accepts input via stdin and/or command-line arguments
- Outputs primary results to stdout
- Outputs errors and warnings to stderr
- Supports both JSON and human-readable formats
- Meaningful exit codes (0 for success, non-zero for errors)
- Idempotent operations (same command with same inputs produces same result)
- Progress indication for long-running operations (when TTY detected)

## Global Options

All commands support these global options:

```
--config PATH          Configuration file path (default: .annextube/config.toml or ~/.config/annextube/config.toml)
--log-level LEVEL      Set logging level: debug, info, warning, error (default: info)
--json                 Output in JSON format instead of human-readable
--quiet                Suppress non-error output
--help                 Show help message and exit
--version              Show version and exit
```

**Config File Search Order**:
1. `--config PATH` if specified
2. `.annextube/config.toml` in current directory (local dataset config)
3. `~/.config/annextube/config.toml` (global user config)
4. Default values

**Working Directory Context**: Commands operate on the current directory's git-annex repository by default. The `.annextube/config.toml` file defines channels, filters, and behavior.

## Exit Codes

```
0   Success
1   General error
2   Invalid arguments
3   Network error (YouTube API/connection failed)
4   Git/git-annex error
5   Filesystem error (permissions, disk full, etc.)
6   Configuration error
7   Data validation error
```

## Commands

### 1. init

Initialize a new YouTube archive repository in the current directory.

**Usage**:
```bash
annextube init [OPTIONS]
```

**Arguments**: None (operates in current directory)

**Options**:
```
--git-config PATTERN=RULE   Configure git tracking pattern (repeatable)
                            Example: --git-config "*.json=git" --git-config "*.mp4=annex"
--subdataset-pattern PATTERN Subdataset path pattern with '//' separator
                            Example: "videos/{year}//{month}"
--description TEXT          Repository description
```

**What this does**:
- Initializes git repository in current directory
- Initializes git-annex with URL backend
- Creates `.annextube/config.toml` template with common settings
- Configures .gitattributes for file tracking rules
- Creates basic directory structure (videos/, playlists/, channels/)

**Output** (human-readable):
```
Initialized YouTube archive repository in current directory
Git-annex backend: URL (for video URLs)
Tracking configuration:
  - *.json, *.tsv, *.md, *.vtt → git
  - *.mp4, *.webm, *.jpg, *.png → git-annex

Template configuration created: .annextube/config.toml
Edit this file to configure channels, playlists, and filters.

Next steps:
  1. Edit .annextube/config.toml to add channels/playlists
  2. Run: annextube backup
```

**Output** (JSON):
```json
{
  "status": "success",
  "path": ".",
  "git_annex_backend": "URL",
  "config_file": ".annextube/config.toml",
  "tracking_config": {
    "git": ["*.json", "*.tsv", "*.md", "*.vtt"],
    "annex": ["*.mp4", "*.webm", "*.jpg", "*.png"]
  }
}
```

**Exit codes**:
- `0`: Repository created successfully
- `2`: Directory already initialized (use --force to reinitialize)
- `4`: Git/git-annex initialization failed
- `5`: Filesystem error (permissions, etc.)

**Config Template** (`.annextube/config.toml`):
```toml
# annextube configuration
# Edit this file to configure your archive

# YouTube Data API v3 key (required for metadata, comments, playlists)
# Get from: https://console.cloud.google.com/apis/credentials
api_key = "YOUR_API_KEY_HERE"

# Channels to archive (can add multiple)
[[sources]]
url = "https://www.youtube.com/@YourChannel"
type = "channel"  # or "playlist"
enabled = true

# Example: Liked Videos playlist (HIGH PRIORITY test case)
# [[sources]]
# url = "https://www.youtube.com/playlist?list=LL"  # Liked Videos special ID
# type = "playlist"
# enabled = true

# Example: Add more sources
# [[sources]]
# url = "https://youtube.com/c/datalad"
# type = "channel"
# enabled = true

# [[sources]]
# url = "https://www.youtube.com/playlist?list=PLxxx..."
# type = "playlist"
# enabled = true

# What to backup (components)
[components]
videos = false       # Download video files (default: track URLs only)
metadata = true      # Fetch video metadata
comments = true      # Fetch comments
captions = true      # Fetch captions
thumbnails = true    # Download thumbnails

# Filters (optional)
# date_start = "2024-01-01"
# date_end = "2024-12-31"
# license = "creativeCommon"  # or "standard"
# limit = 10  # For testing: limit to N most recent videos (by upload date, newest first)

# Organization (optional)
[organization]
# hierarchy = "videos/{year}/{video_id}/"  # Custom path template
# use_symlinks = true  # Symlink videos in multiple playlists

# Rate limiting (optional)
[rate_limit]
sleep_interval = 1.0  # Seconds between requests
max_sleep_interval = 5.0
```

---

### 2. backup

Backup YouTube channels/playlists configured in `.annextube/config.toml`, or a specific URL.

**Usage**:
```bash
# Backup all sources from config
annextube backup [OPTIONS]

# Backup specific URL (not in config)
annextube backup [OPTIONS] URL
```

**Arguments**:
- `URL`: YouTube channel, playlist, or video URL (optional - if omitted, backs up all enabled sources from config)

**Options**:
```
--source NAME              Backup only specific named source from config
--date-start DATE          Override date filter from config (ISO 8601)
--date-end DATE            Override date filter from config (ISO 8601)
--license TYPE             Override license filter: standard, creativeCommon
--limit N                  Limit to N most recent videos by upload date (for testing, deterministic ordering)
--download-videos          Download video files (overrides config)
--no-download-videos       Track URLs only (overrides config)
--no-comments              Skip comment fetching (overrides config)
--no-captions              Skip caption fetching (overrides config)
--no-thumbnails            Skip thumbnail fetching (overrides config)
```

**Behavior**:
- **With config**: Backs up all enabled sources from `.annextube/config.toml`
- **With URL**: Backs up specific URL (uses config filters/components as defaults)
- **Operates in current directory**: Requires git-annex repository (run `annextube init` first)

**Output** (human-readable - backing up from config):
```
Loading config: .annextube/config.toml
Found 3 enabled sources

Backing up [1/3]: https://www.youtube.com/@RickAstleyYT
  Channel: Rick Astley (UCuAXFkgsw1L7xaCfnd5JJOw)
  Videos found: 42 (limiting to 10 via config.filters.limit)

  Progress: [████████████████████] 10/10 videos (100%)

  Summary:
    Videos tracked: 10 (URL-only via git-annex --relaxed)
    Comments fetched: 234
    Captions downloaded: 20 (2 languages avg)

Backing up [2/3]: https://youtube.com/c/datalad
  Channel: DataLad (UCxxx...)
  Videos found: 156
  Playlists found: 8

  Progress: [████████████████████] 156/156 videos (100%)

  Summary:
    Videos tracked: 156 (URL-only)
    Comments fetched: 3,421
    Captions downloaded: 312

Backing up [3/3]: https://www.youtube.com/@repronim
  Channel: ReproNim (UCyyy...)
  Videos found: 67

  Progress: [████████████████████] 67/67 videos (100%)

  Summary:
    Videos tracked: 67 (URL-only)
    Comments fetched: 892
    Captions downloaded: 134

Total summary:
  Sources processed: 3
  Videos tracked: 233
  Comments fetched: 4,547
  Captions downloaded: 466
  Duration: 8m 23s
```

**Output** (JSON - backing up from config):
```json
{
  "status": "success",
  "config_file": ".annextube/config.toml",
  "sources_processed": 3,
  "sources": [
    {
      "url": "https://www.youtube.com/@RickAstleyYT",
      "type": "channel",
      "id": "UCuAXFkgsw1L7xaCfnd5JJOw",
      "name": "Rick Astley",
      "videos_tracked": 10,
      "comments_fetched": 234,
      "captions_downloaded": 20
    },
    {
      "url": "https://youtube.com/c/datalad",
      "type": "channel",
      "id": "UCxxx...",
      "name": "DataLad",
      "videos_tracked": 156,
      "comments_fetched": 3421,
      "captions_downloaded": 312
    },
    {
      "url": "https://www.youtube.com/@repronim",
      "type": "channel",
      "id": "UCyyy...",
      "name": "ReproNim",
      "videos_tracked": 67,
      "comments_fetched": 892,
      "captions_downloaded": 134
    }
  ],
  "summary": {
    "videos_tracked": 233,
    "comments_fetched": 4547,
    "captions_downloaded": 466,
    "duration_seconds": 503
  }
}
```

**Exit codes**:
- `0`: Backup completed successfully
- `2`: Invalid URL or arguments
- `3`: Network error (YouTube API failed)
- `4`: Git-annex error
- `5`: Filesystem error

---

### 3. update

Run incremental update on existing archive (fetch new videos, comments, captions).

**Usage**:
```bash
# Update all sources from config
annextube update [OPTIONS]

# Update specific source
annextube update [OPTIONS] --source NAME
```

**Arguments**: None (operates on current directory)

**Options**:
```
--source NAME              Update only specific named source from config
--force                    Force re-fetch even if no changes detected
--force-date DATE          Force update for videos published after DATE
```

**Behavior**:
- Loads sources from `.annextube/config.toml`
- Checks for new videos published since last sync
- Fetches updated comments and captions
- Skips already-processed content via yt-dlp archive file

**Output** (human-readable):
```
Loading config: .annextube/config.toml
Checking 3 sources for updates...

Source [1/3]: Rick Astley
  Last sync: 2026-01-20 10:00:00
  New videos: 2
  Updated comments: 5 videos
  Updated captions: 1 video

Source [2/3]: DataLad
  Last sync: 2026-01-20 10:00:00
  New videos: 0
  Updated comments: 2 videos

Source [3/3]: ReproNim
  Last sync: 2026-01-20 10:00:00
  New videos: 1
  Updated comments: 1 video

Progress: [████████████████████] 11/11 items (100%)

Summary:
  Sources checked: 3
  New videos: 3
  Updated comments: 8 videos (290 new comments)
  Updated captions: 1 video
  Duration: 1m 45s
```

**Output** (JSON):
```json
{
  "status": "success",
  "sources_checked": 3,
  "summary": {
    "new_videos": 2,
    "updated_metadata": 6,
    "new_comments": 145,
    "updated_captions": 2,
    "duration_seconds": 72
  },
  "repository_path": "/path/to/repo"
}
```

**Exit codes**:
- `0`: Update completed successfully
- `3`: Network error
- `4`: Git-annex error
- `6`: Configuration error (no sources configured)

---

### 4. export

Export metadata to TSV files.

**Usage**:
```bash
annextube export [OPTIONS]
```

**Arguments**: None (operates on current directory)

**Options**:
```
--videos-file PATH         Output path for videos.tsv (default: videos.tsv)
--playlists-file PATH      Output path for playlists.tsv (default: playlists.tsv)
```

**Behavior**:
- Reads all metadata from current repository
- Generates videos.tsv and playlists.tsv in repository root

**Output** (human-readable):
```
Exporting metadata...
  Videos: 42 entries → videos.tsv
  Playlists: 5 entries → playlists.tsv

Export complete.
```

**Output** (JSON):
```json
{
  "status": "success",
  "exports": {
    "videos": {
      "file": "videos.tsv",
      "count": 42
    },
    "playlists": {
      "file": "playlists.tsv",
      "count": 5
    }
  }
}
```

**Exit codes**:
- `0`: Export completed successfully
- `5`: Filesystem error
- `7`: Data validation error

---

### 5. generate-web

Generate static web interface for browsing archive.

**Usage**:
```bash
annextube generate-web [OPTIONS]
```

**Arguments**: None (operates on current directory)

**Options**:
```
--web-dir PATH             Web interface output dir (default: web/)
--base-url URL             Base URL for absolute links (for publishing)
```

**Behavior**:
- Reads metadata from current repository
- Generates static Svelte-based web UI in web/ directory
- Works offline via file:// protocol

**Output** (human-readable):
```
Generating web interface...
  Loading metadata: 42 videos, 5 playlists
  Building index...
  Generating pages...
  Copying assets...

Web interface generated: /path/to/repo/web/
  Open: file:///path/to/repo/web/index.html
```

**Output** (JSON):
```json
{
  "status": "success",
  "web_directory": "/path/to/repo/web/",
  "entry_point": "file:///path/to/repo/web/index.html",
  "statistics": {
    "videos": 42,
    "playlists": 5,
    "pages_generated": 48
  }
}
```

**Exit codes**:
- `0`: Web interface generated successfully
- `5`: Filesystem error
- `7`: Data validation error

---

## Idempotency

All commands are idempotent:

| Command | Idempotent Behavior |
|---------|-------------------|
| `create-dataset` | Error if repository exists; safe to re-run with `--force` (not implemented in v1) |
| `backup` | Skip already-tracked videos (via yt-dlp archive file); update metadata if changed |
| `update` | Only fetch new/changed content; safe to run repeatedly |
| `export` | Regenerate TSV files from current data; deterministic output |
| `generate-web` | Regenerate web interface from current data; deterministic output |

## Progress Indication

When stdout is a TTY (terminal), long-running commands display progress:

```
Progress: [████████████░░░░░░░░] 42/100 videos (42%) - ETA: 2m 15s
```

When stdout is piped or `--quiet` is used, progress is suppressed.

## Machine-Parseable Output

All commands support `--json` for machine-readable output:

**Success response**:
```json
{
  "status": "success",
  "command": "backup",
  "timestamp": "2026-01-24T12:00:00Z",
  "summary": { ... },
  ...
}
```

**Error response**:
```json
{
  "status": "error",
  "command": "backup",
  "timestamp": "2026-01-24T12:00:00Z",
  "error": {
    "code": 3,
    "message": "Network error: Failed to fetch channel metadata",
    "details": "YouTube API returned 403 Forbidden"
  }
}
```

## Logging

Structured logging to stderr:

**Human-readable format** (default):
```
[2026-01-24 12:00:00] INFO: Starting backup for channel UCuAXFkgsw1L7xaCfnd5JJOw
[2026-01-24 12:00:05] DEBUG: Fetching channel metadata...
[2026-01-24 12:00:10] WARNING: Video dQw4w9WgXcQ has no comments (disabled)
[2026-01-24 12:00:15] ERROR: Network timeout fetching playlist PLxyz...
```

**JSON format** (`--json`):
```json
{"timestamp": "2026-01-24T12:00:00Z", "level": "INFO", "message": "Starting backup for channel UCuAXFkgsw1L7xaCfnd5JJOw", "trace_id": "abc123"}
{"timestamp": "2026-01-24T12:00:05Z", "level": "DEBUG", "message": "Fetching channel metadata...", "trace_id": "abc123"}
{"timestamp": "2026-01-24T12:00:10Z", "level": "WARNING", "message": "Video dQw4w9WgXcQ has no comments (disabled)", "trace_id": "abc123"}
{"timestamp": "2026-01-24T12:00:15Z", "level": "ERROR", "message": "Network timeout fetching playlist PLxyz...", "trace_id": "abc123"}
```

## Examples

### Typical Workflow (Config-Based)

```bash
# 1. Create archive directory and initialize
mkdir my-youtube-archive
cd my-youtube-archive
annextube init

# 2. Edit config to add sources
vim .annextube/config.toml
# Add channels/playlists to [[sources]] sections

# 3. Backup all configured sources
annextube backup

# 4. Export metadata for browsing
annextube export

# 5. Generate web interface
annextube generate-web

# 6. Open in browser
xdg-open web/index.html  # Linux
# or: open web/index.html  # macOS
```

### Quick Test Setup (Single Channel)

```bash
# Initialize and backup single channel for testing
mkdir test-archive
cd test-archive
annextube init

# Edit .annextube/config.toml:
#   [[sources]]
#   url = "https://www.youtube.com/@RickAstleyYT"
#   type = "channel"
#
#   [filters]
#   limit = 10

annextube backup
```

### Ad-hoc Backup (Without Config)

```bash
# Initialize repository
mkdir archive
cd archive
annextube init

# Backup specific URL directly (uses default config settings)
annextube backup --limit 10 https://www.youtube.com/@RickAstleyYT
```

### Test with Recommended Channels

```bash
# Initialize once
mkdir test-archive && cd test-archive
annextube init

# Edit .annextube/config.toml to add test channels:
# [[sources]]
# url = "https://www.youtube.com/@RickAstleyYT"
# [filters]
# limit = 10  # Quick testing

# [[sources]]
# url = "https://youtube.com/c/datalad"  # Playlist testing

# [[sources]]
# url = "https://www.youtube.com/@repronim"

# [[sources]]
# url = "https://www.youtube.com/@apopyk"

# [[sources]]
# url = "https://www.youtube.com/@centeropenneuro"

# Backup all
annextube backup
```

### Incremental Updates

```bash
# Navigate to archive directory
cd ~/my-youtube-archive

# Daily update (fetch new videos/comments/captions)
annextube update

# Force re-fetch recent videos
annextube update --force-date 2026-01-20

# Daily cron job
0 2 * * * cd ~/my-youtube-archive && /usr/bin/annextube update
```

### Filtered Backups

```bash
# Set filters in config (.annextube/config.toml):
# [filters]
# license = "creativeCommon"
# date_start = "2024-01-01"
# date_end = "2024-12-31"
# limit = 10

# Then backup (uses config filters)
annextube backup

# Or override config with CLI flags
annextube backup --license creativeCommon --limit 10

# Ad-hoc URL with filters
annextube backup --date-start 2024-01-01 https://www.youtube.com/@SomeChannel
```

### CI/CD Usage (JSON Output)

```bash
# In GitHub Actions / cron
cd $ARCHIVE_DIR

# JSON output for parsing
annextube update --json > update-result.json

# Check exit code
if [ $? -eq 0 ]; then
  echo "Update successful"
else
  echo "Update failed"
  exit 1
fi
```

## Version History

**v1.0.0** (2026-01-24): Initial CLI contract
- Commands: create-dataset, backup, update, export, generate-web
- JSON output support
- Idempotent operations
- Meaningful exit codes
