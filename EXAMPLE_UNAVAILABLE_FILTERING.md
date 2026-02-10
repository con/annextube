# Example: Unavailable Video Filtering

This document demonstrates how the unavailable video filtering feature works in incremental playlist updates.

## Scenario

You have a large "Liked videos" playlist with some unavailable videos (private, removed, or from terminated accounts).

## First Run (Initial Backup)

```bash
annextube backup --output-dir ~/my-archive https://www.youtube.com/playlist?list=LL
```

**What happens:**
1. yt-dlp fetches all videos in playlist
2. For unavailable videos, yt-dlp logs errors and returns None entries
3. Available videos are saved with `availability: "public"`
4. Unavailable videos are not saved (no video_id available from yt-dlp)

**Log output:**
```
2026-02-08 08:35:01 [ERROR] yt_dlp: ERROR: [youtube] gw6jW50g_P0: Video unavailable. This video is private
2026-02-08 08:38:27 [ERROR] yt_dlp: ERROR: [youtube] 49MXTq55Jcs: Video unavailable. This video is private
2026-02-08 08:39:14 [ERROR] yt_dlp: ERROR: [youtube] mgYdbdE9R_E: Video unavailable. This video is no longer available
```

**Result:** 3 unavailable videos tried and failed. Time wasted: ~15-30 seconds.

## Manually Marking Unavailable Videos (Optional)

If you know certain videos are unavailable, you can manually create metadata.json files for them:

```bash
mkdir -p ~/my-archive/videos/2024/01/2024-01-15_private-video
cat > ~/my-archive/videos/2024/01/2024-01-15_private-video/metadata.json <<EOF
{
  "video_id": "gw6jW50g_P0",
  "title": "Private Video (gw6jW50g_P0)",
  "availability": "private",
  "privacy_status": "non-public",
  "published_at": "2024-01-15T00:00:00",
  "description": "",
  "channel_id": "",
  "channel_name": "",
  "duration": 0,
  "view_count": 0,
  "like_count": 0,
  "comment_count": 0,
  "thumbnail_url": "",
  "license": "standard",
  "download_status": "not_downloaded",
  "tags": [],
  "categories": [],
  "captions_available": [],
  "has_auto_captions": false,
  "source_url": "https://www.youtube.com/watch?v=gw6jW50g_P0",
  "fetched_at": "2024-01-15T00:00:00"
}
EOF
```

Repeat for other unavailable videos.

## Second Run (Incremental Update)

```bash
annextube update --output-dir ~/my-archive --mode videos-incremental
```

**What happens:**
1. System loads known unavailable video IDs from metadata.json files
2. Uses two-pass approach:
   - **First pass:** `extract_flat` to get all video IDs from playlist (fast, no metadata fetching)
   - **Filter:** Remove known unavailable video IDs
   - **Second pass:** Fetch full metadata only for remaining videos
3. Skips unavailable videos entirely (no yt-dlp errors!)

**Log output:**
```
[INFO] Loaded 3 known unavailable video(s) from archive
[INFO] First pass: fetching video ID list (fast)...
[INFO] Found 100 video(s) in playlist
[INFO] Skipped 3 video(s) known to be unavailable
[INFO] Will fetch full metadata for 97 video(s)
[INFO] Fetching metadata [1/97]: ABC123...
[INFO] Fetching metadata [2/97]: DEF456...
...
[INFO] Successfully fetched metadata for 97/97 video(s)
```

**Result:** 3 unavailable videos skipped. Time saved: ~15-30 seconds per update.

## Subsequent Runs

Every subsequent run will:
- Skip the same 3 unavailable videos
- Only fetch metadata for new or updated videos
- Save time on every update

## Verifying the Feature

Check if unavailable videos are being tracked:

```bash
# Find all metadata files with non-public availability
grep -r '"availability": "private"' ~/my-archive/videos/
grep -r '"availability": "removed"' ~/my-archive/videos/
grep -r '"availability": "unavailable"' ~/my-archive/videos/
```

Check logs for skip messages:

```bash
annextube update --output-dir ~/my-archive --log-level DEBUG
```

Look for:
```
[INFO] Loaded X known unavailable video(s) from archive
[INFO] Skipped X video(s) known to be unavailable
```

## How It Works Internally

### Metadata.json Structure

Each video has a metadata.json file with availability tracking:

```json
{
  "video_id": "ABC123",
  "title": "My Video",
  "availability": "public",  // or "private", "removed", "unavailable"
  "privacy_status": "public", // or "non-public", "removed"
  ...
}
```

### Two-Pass Extraction

1. **First pass (fast):**
   ```python
   yt_dlp_opts = {"extract_flat": "in_playlist"}  # Only get IDs, no metadata
   info = ydl.extract_info(playlist_url)
   video_ids = [entry["id"] for entry in info["entries"]]
   ```

2. **Filter:**
   ```python
   unavailable_ids = load_from_metadata_files()
   videos_to_fetch = [id for id in video_ids if id not in unavailable_ids]
   ```

3. **Second pass (targeted):**
   ```python
   for video_id in videos_to_fetch:
       video_url = f"https://www.youtube.com/watch?v={video_id}"
       metadata = ydl.extract_info(video_url)  # Full metadata
   ```

## Modes That Use This Feature

✅ **Enabled:**
- `--mode videos-incremental` (default for `annextube update`)
- `--mode all-incremental`
- `--mode playlists`

❌ **Not enabled:**
- Initial backup (`annextube backup`)
- `--mode all-force` (force re-fetch everything)

## Performance Impact

For a playlist with:
- 1000 videos total
- 50 unavailable videos

**Before:**
- Time per update: ~50 minutes (1000 videos × 3 seconds)
- Wasted time on unavailable: ~4-8 minutes (50 videos × 5-10 seconds)

**After:**
- Time per update: ~47 minutes (950 videos × 3 seconds)
- Time saved: ~4-8 minutes per update

## Troubleshooting

### "No videos to fetch" message

If you see:
```
[INFO] No new videos to fetch (all known unavailable)
```

This means all videos in the playlist are marked as unavailable. To force re-check:
```bash
# Delete unavailable metadata files
find ~/my-archive/videos/ -name "metadata.json" -exec grep -l '"availability": "private"' {} \; | xargs rm

# Run update again
annextube update --output-dir ~/my-archive --mode all-force
```

### Videos still showing errors

If you still see yt-dlp errors for unavailable videos, check:
1. Are you using incremental mode? (`--mode videos-incremental`)
2. Do metadata.json files exist for those videos?
3. Is `availability` field set correctly?

### Manual cleanup

To remove all unavailable videos from archive:
```bash
# Find and list unavailable videos
find ~/my-archive/videos/ -name "metadata.json" -exec grep -l '"availability": "private"' {} \;

# Remove them (be careful!)
find ~/my-archive/videos/ -name "metadata.json" -exec grep -l '"availability": "private"' {} \; | \
  xargs -I {} dirname {} | xargs rm -rf
```
