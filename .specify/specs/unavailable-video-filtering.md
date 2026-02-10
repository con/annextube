# Unavailable Video Filtering for Incremental Playlist Updates

## Problem

When running incremental updates on playlists (especially large ones like "Liked videos"), the system wastes time re-attempting to fetch metadata for videos that are already known to be unavailable:
- Private videos
- Removed videos
- Videos from terminated accounts

These same videos are attempted again on every run, wasting significant time as yt-dlp tries to fetch them, fails, and logs errors.

## Solution

Implemented a two-pass approach for incremental playlist updates that:

1. **Tracks unavailable videos**: Records when a video is discovered to be unavailable in metadata.json with `availability` field set to 'private', 'removed', or 'unavailable'
2. **Skips on subsequent runs**: Uses a two-pass extraction approach:
   - First pass: `extract_flat` to get just video IDs (fast, no metadata fetching)
   - Filter out known unavailable videos by checking existing metadata.json files
   - Second pass: Fetch full metadata only for videos not in unavailable set
3. **Default behavior**: Only enabled in incremental modes (`videos-incremental`, `all-incremental`, `playlists`)
4. **Metadata persistence**: Availability status is stored in metadata.json's `availability` field

## Implementation Details

### New Method: `YouTubeService._load_unavailable_videos()`

Scans the archive's `videos/` directory for metadata.json files and returns a set of video IDs with `availability` in `['private', 'removed', 'unavailable']`.

```python
def _load_unavailable_videos(self, repo_path: Path) -> set[str]:
    """Load video IDs of known unavailable videos from archive."""
```

### Modified Method: `YouTubeService.get_playlist_videos()`

Added two new parameters:
- `repo_path: Path | None = None`: Path to archive repository (for incremental mode)
- `incremental: bool = False`: If True, skip videos known to be unavailable

When `incremental=True` and unavailable videos are found:
1. Loads unavailable video IDs from metadata.json files
2. Uses two-pass approach (extract_flat + individual fetches)
3. Skips known unavailable videos in second pass
4. Logs how many videos are skipped

### Modified: `Archiver.backup_playlist()`

Now passes `repo_path` and `incremental` flag when calling `get_playlist_videos()`:

```python
incremental = self.update_mode in ["videos-incremental", "all-incremental", "playlists"]
all_videos = self.youtube.get_playlist_videos(
    playlist_url,
    limit=limit,
    repo_path=self.repo_path,
    incremental=incremental
)
```

## Usage

The feature is automatically enabled for incremental update modes:
- `annextube update --mode videos-incremental` (default)
- `annextube update --mode all-incremental`
- `annextube update --mode playlists`

For initial backups or forced updates, the standard single-pass approach is used:
- `annextube backup` (initial backup)
- `annextube update --mode all-force`

## Performance Impact

For a playlist with N videos and U unavailable videos:

**Before:**
- Single pass: N full metadata fetches (including U failed attempts)
- Time per unavailable video: ~5-10 seconds (network timeout + error handling)
- Wasted time per run: U × 5-10 seconds

**After (incremental mode):**
- First pass: 1 fast playlist extraction (extract_flat)
- Second pass: (N - U) full metadata fetches
- Time saved per run: U × 5-10 seconds

For a playlist with 100 videos and 10 unavailable:
- Time saved: 50-100 seconds per update

## Tests

Added comprehensive unit tests in `tests/unit/test_unavailable_video_filtering.py`:
- Test loading unavailable videos from archive
- Test two-pass approach for incremental mode
- Test single-pass approach for non-incremental mode
- Test handling of corrupted metadata files
- Test edge cases (empty repo, nonexistent repo)

All tests pass and no regressions in existing tests.

## Future Enhancements

Possible improvements:
1. Add CLI flag to force re-check unavailable videos (e.g., `--recheck-unavailable`)
2. Track timestamp when video became unavailable for pruning old entries
3. Differentiate between temporarily unavailable (network errors) and permanently unavailable (deleted/private)
4. Add statistics to show how much time was saved by skipping unavailable videos

## Related Files

- `annextube/services/youtube.py`: Core implementation
- `annextube/services/archiver.py`: Integration with backup logic
- `tests/unit/test_unavailable_video_filtering.py`: Unit tests
- `annextube/models/video.py`: Video model with `availability` field (already existed)
