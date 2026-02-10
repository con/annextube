# Unavailable Video Filtering - Implementation Summary

## Overview

Implemented efficient filtering of known unavailable videos in incremental playlist updates to avoid wasting time re-attempting to fetch videos that are private, removed, or from terminated accounts.

## Problem Solved

When running incremental updates on playlists (especially large ones like "Liked videos"), the system was repeatedly attempting to fetch metadata for videos known to be unavailable, wasting 5-10 seconds per video on network timeouts and error handling.

Example from user's log:
```
2026-02-08 08:35:01 [ERROR] yt_dlp: ERROR: [youtube] gw6jW50g_P0: Video unavailable. This video is private
2026-02-08 08:38:27 [ERROR] yt_dlp: ERROR: [youtube] 49MXTq55Jcs: Video unavailable. This video is private
2026-02-08 08:39:14 [ERROR] yt_dlp: ERROR: [youtube] mgYdbdE9R_E: Video unavailable. This video is no longer available
```

These same errors would repeat on every subsequent run.

## Solution

Implemented a two-pass extraction approach for incremental playlist updates:

1. **First pass:** Use `extract_flat` to quickly get all video IDs from playlist (no metadata fetching)
2. **Filter:** Load known unavailable video IDs from existing metadata.json files and skip them
3. **Second pass:** Fetch full metadata only for videos not in the unavailable set

This avoids the repeated failed attempts entirely, saving significant time on every update.

## Changes Made

### 1. New Method: `YouTubeService._load_unavailable_videos()`

**File:** `annextube/services/youtube.py`

Scans the archive's `videos/` directory for metadata.json files and returns a set of video IDs with `availability` in `['private', 'removed', 'unavailable']`.

### 2. Enhanced Method: `YouTubeService.get_playlist_videos()`

**File:** `annextube/services/youtube.py`

Added two new parameters:
- `repo_path: Path | None = None` - Path to archive repository
- `incremental: bool = False` - Enable filtering of unavailable videos

When `incremental=True` and unavailable videos exist:
- Uses two-pass approach (extract_flat + individual fetches)
- Filters out known unavailable videos before fetching metadata
- Logs statistics on how many videos are skipped

When `incremental=False` (initial backup, forced updates):
- Uses original single-pass approach for full metadata extraction
- No filtering applied

### 3. Integration: `Archiver.backup_playlist()`

**File:** `annextube/services/archiver.py`

Updated to pass `repo_path` and `incremental` flag to `get_playlist_videos()`:

```python
incremental = self.update_mode in ["videos-incremental", "all-incremental", "playlists"]
all_videos = self.youtube.get_playlist_videos(
    playlist_url,
    limit=limit,
    repo_path=self.repo_path,
    incremental=incremental
)
```

### 4. Comprehensive Tests

**File:** `tests/unit/test_unavailable_video_filtering.py`

Added 6 unit tests covering:
- Loading unavailable videos from archive
- Two-pass approach for incremental mode
- Single-pass approach for non-incremental mode
- Edge cases (empty repo, nonexistent repo, corrupted metadata)

All tests pass with no regressions in existing tests (132 total unit tests pass).

### 5. Documentation

**Files:**
- `.specify/specs/unavailable-video-filtering.md` - Technical specification
- `EXAMPLE_UNAVAILABLE_FILTERING.md` - User-friendly example and usage guide

## Performance Impact

For a playlist with 100 videos and 10 unavailable:
- **Time saved per update:** 50-100 seconds
- **Efficiency gain:** 10% fewer metadata fetches

For a playlist with 1000 videos and 50 unavailable:
- **Time saved per update:** 4-8 minutes
- **Efficiency gain:** 5% fewer metadata fetches

## Usage

The feature is automatically enabled for incremental update modes:
```bash
annextube update --mode videos-incremental  # Default
annextube update --mode all-incremental
annextube update --mode playlists
```

Not enabled for initial backups or forced updates:
```bash
annextube backup  # Initial backup
annextube update --mode all-force  # Force re-fetch everything
```

## Verification

Run tests:
```bash
uv run pytest tests/unit/test_unavailable_video_filtering.py -v
```

Check logs for skip messages:
```bash
annextube update --output-dir ~/archive --log-level INFO
```

Look for:
```
[INFO] Loaded X known unavailable video(s) from archive
[INFO] Skipped X video(s) known to be unavailable
```

## Files Modified

1. `annextube/services/youtube.py` - Core implementation
2. `annextube/services/archiver.py` - Integration
3. `tests/unit/test_unavailable_video_filtering.py` - Tests

## Files Added

1. `.specify/specs/unavailable-video-filtering.md` - Specification
2. `EXAMPLE_UNAVAILABLE_FILTERING.md` - Usage guide
3. `CHANGES_SUMMARY.md` - This file

## Type Safety & Code Quality

- All type hints correct (mypy passes)
- All linting passes (ruff passes)
- All tests pass (132/132 unit tests)
- No regressions in existing functionality

## Future Enhancements

Possible improvements for future versions:
1. CLI flag to force re-check unavailable videos
2. Track timestamp when video became unavailable
3. Differentiate temporary vs permanent unavailability
4. Add statistics showing time saved by filtering
