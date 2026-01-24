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
--log-level LEVEL      Set logging level: debug, info, warning, error (default: info)
--json                 Output in JSON format instead of human-readable
--quiet                Suppress non-error output
--help                 Show help message and exit
--version              Show version and exit
```

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

### 1. create-dataset

Initialize a new YouTube archive repository.

**Usage**:
```bash
annextube create-dataset [OPTIONS] PATH
```

**Arguments**:
- `PATH`: Path to create repository (required)

**Options**:
```
--git-config PATTERN=RULE   Configure git tracking pattern (repeatable)
                            Example: --git-config "*.json=git" --git-config "*.mp4=annex"
--subdataset-pattern PATTERN Subdataset path pattern with '//' separator
                            Example: "videos/{year}//{month}"
--description TEXT          Repository description
```

**Output** (human-readable):
```
Initialized YouTube archive repository at: /path/to/repo
Git-annex backend: URL (for video URLs)
Tracking configuration:
  - *.json, *.tsv, *.md, *.vtt → git
  - *.mp4, *.webm, *.jpg, *.png → git-annex
```

**Output** (JSON):
```json
{
  "status": "success",
  "path": "/path/to/repo",
  "git_annex_backend": "URL",
  "tracking_config": {
    "git": ["*.json", "*.tsv", "*.md", "*.vtt"],
    "annex": ["*.mp4", "*.webm", "*.jpg", "*.png"]
  }
}
```

**Exit codes**:
- `0`: Repository created successfully
- `2`: Invalid path or arguments
- `4`: Git/git-annex initialization failed
- `5`: Filesystem error (permissions, exists, etc.)

---

### 2. backup

Backup a YouTube channel, playlist, or video(s).

**Usage**:
```bash
annextube backup [OPTIONS] URL
```

**Arguments**:
- `URL`: YouTube channel, playlist, or video URL (required)

**Options**:
```
--filter NAME              Apply named filter from .config/filters.json
--date-start DATE          Start date for filtering (ISO 8601)
--date-end DATE            End date for filtering (ISO 8601)
--license TYPE             Filter by license: standard, creativeCommon
--download-videos          Download video files (default: metadata only)
--no-comments              Skip comment fetching
--no-captions              Skip caption fetching
--no-thumbnails            Skip thumbnail fetching
--output-dir PATH          Repository path (default: current directory)
```

**Output** (human-readable):
```
Backing up channel: Rick Astley (UCuAXFkgsw1L7xaCfnd5JJOw)
  Videos found: 42
  Playlists found: 5
  Applying filter: date-start=2024-01-01

Progress: [████████████████████] 42/42 videos (100%)

Summary:
  Videos tracked: 42
  Videos downloaded: 0 (metadata only)
  Comments fetched: 1,234
  Captions downloaded: 84 (2 languages avg)
  Duration: 2m 34s

Repository updated: /path/to/repo
```

**Output** (JSON):
```json
{
  "status": "success",
  "source": {
    "type": "channel",
    "id": "UCuAXFkgsw1L7xaCfnd5JJOw",
    "name": "Rick Astley",
    "url": "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw"
  },
  "summary": {
    "videos_found": 42,
    "videos_tracked": 42,
    "videos_downloaded": 0,
    "comments_fetched": 1234,
    "captions_downloaded": 84,
    "duration_seconds": 154
  },
  "repository_path": "/path/to/repo"
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

Run incremental update on existing archive.

**Usage**:
```bash
annextube update [OPTIONS] [SOURCE]
```

**Arguments**:
- `SOURCE`: Channel/playlist URL to update (optional; updates all if omitted)

**Options**:
```
--output-dir PATH          Repository path (default: current directory)
--force                    Force re-fetch even if no changes detected
--force-date DATE          Force update for videos published after DATE
```

**Output** (human-readable):
```
Updating archive: /path/to/repo
  Checking 3 sources for updates...

Channel: Rick Astley
  New videos: 2
  Updated comments: 5 videos
  Updated captions: 1 video

Progress: [████████████████████] 8/8 items (100%)

Summary:
  New videos: 2
  Updated metadata: 6 videos
  New comments: 145
  Updated captions: 2
  Duration: 1m 12s
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

**Options**:
```
--output-dir PATH          Repository path (default: current directory)
--videos-file PATH         Output path for videos.tsv (default: videos.tsv)
--playlists-file PATH      Output path for playlists.tsv (default: playlists.tsv)
```

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

**Options**:
```
--output-dir PATH          Repository path (default: current directory)
--web-dir PATH             Web interface output dir (default: web/)
--base-url URL             Base URL for absolute links (optional)
```

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

### Create new archive and backup channel
```bash
# Initialize repository
annextube create-dataset ~/youtube-archive

# Backup channel (metadata only)
annextube backup --output-dir ~/youtube-archive https://www.youtube.com/@RickAstleyYT

# Export TSV files
annextube export --output-dir ~/youtube-archive

# Generate web interface
annextube generate-web --output-dir ~/youtube-archive
```

### Incremental updates
```bash
# Daily cron job
annextube update --output-dir ~/youtube-archive

# Force re-fetch recent videos
annextube update --output-dir ~/youtube-archive --force-date 2026-01-20
```

### Filtered backups
```bash
# Creative Commons videos only
annextube backup --license creativeCommon https://www.youtube.com/@SomeChannel

# Date range filter
annextube backup --date-start 2024-01-01 --date-end 2024-12-31 https://www.youtube.com/@SomeChannel
```

### CI/CD usage (JSON output)
```bash
# JSON output for parsing
annextube update --output-dir ~/youtube-archive --json > update-result.json

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
