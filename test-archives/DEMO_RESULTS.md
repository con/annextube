# Cookie Demo Results - Metadata Collection Working ✅

## Important Correction

**Video downloads:** ❌ **Failed** - git-annex couldn't track the video URLs
**Metadata/Captions/Comments:** ✅ **Working** - Successfully downloaded with authentication

## Summary

Successfully implemented and tested cookie support for **metadata collection** with the Python API. The `--remote-components` support allows downloading metadata, captions, comments, and thumbnails with authentication.

**However:** Video URL tracking via git-annex failed - no actual video files were tracked or downloaded.

### Environment
- **Miniconda**: Installed at `/tmp/miniconda3`
- **Environment**: `deno` with Python 3.11
- **Deno Runtime**: 2.3.3
- **yt-dlp**: 2026.01.29
- **annextube**: 0.1.0 (installed in editable mode)

### Demo Location
- **Script**: `test-archives/demo-cookies.sh`
- **Fake HOME**: `test-archives/fake-home-demo/` (preserved for inspection)
- **Archive**: `test-archives/fake-home-demo/archive/`

## What Actually Works ✅

### Python API (Metadata Collection)

**Successfully downloads with authentication:**
- ✅ Video metadata (title, description, upload date, etc.)
- ✅ Captions/subtitles (.vtt files)
- ✅ Comments (with yt-dlp fallback when no API key)
- ✅ Thumbnails (.jpg files)
- ✅ Author information

**Configuration:**
```toml
# ~/.config/annextube/config.toml
cookies_file = "/home/yoh/proj/annextube/.git/yt-cookies.txt"
ytdlp_extra_opts = ["--remote-components", "ejs:github"]
```

## What Doesn't Work ❌

### Video URL Tracking Failed

**Error from demo:**
```
[WARNING] Failed to track video URL: Command '['git', 'annex', 'addurl',
'https://www.youtube.com/watch?v=hBROP344w-0', '--file',
'.../video.mkv', '--relaxed', '--fast', '--no-raw']'
returned non-zero exit status 1.
```

**Result:** No video files in archive (no .mkv, .mp4, or .webm files)

**Files NOT present:**
- ❌ video.mkv
- ❌ video.mp4
- ❌ video.webm

**Git-annex tracking:** Only thumbnails, captions, and comments are tracked. Video URLs were not registered.

## Demo Results

### ✅ What Was Downloaded

```
test-archives/fake-home-demo/archive/videos/
├── 2026-01-30_русский-молодняк/
│   ├── metadata.json       (3.1K)  ✅ Downloaded
│   ├── comments.json       (5.7K)  ✅ Downloaded with auth
│   ├── captions.tsv        (170B)  ✅ Downloaded
│   ├── video.ru.vtt        (271K)  ✅ Downloaded (caption file)
│   └── thumbnail.jpg       (107K)  ✅ Downloaded
├── 2026-01-30_про-россию-и-Украину/
│   ├── metadata.json       ✅
│   ├── comments.json       ✅
│   ├── captions.tsv        ✅
│   ├── video.ru.vtt        (408K) ✅
│   └── thumbnail.jpg       ✅
└── videos.tsv              (748 bytes)
```

### ❌ What Was NOT Downloaded

```
(No video files - addurl failed)
```

## Technical Details

### Python API Changes (Completed)

**Added to YouTubeService:**
```python
def __init__(self, ..., remote_components: Optional[str] = None):
    self.remote_components = remote_components

def _get_ydl_opts(self, download: bool = False):
    if self.remote_components:
        opts["remote_components"] = [self.remote_components]  # Must be list
```

**Added to Archiver:**
```python
def _parse_remote_components(self, ytdlp_extra_opts: list[str]):
    # Parses ["--remote-components", "ejs:github"] -> "ejs:github"
```

### Git-Annex Issue (Needs Investigation)

The `git annex addurl` command fails when trying to track YouTube video URLs. This needs investigation to determine:

1. Why does git-annex addurl fail for YouTube URLs?
2. Is this expected behavior (YouTube URLs aren't directly downloadable)?
3. Does git-annex need special yt-dlp integration for YouTube?
4. Should annextube use a different approach for video tracking?

## Actual Demo Output

```
✓ Successfully fetched metadata for 2 video(s)

Processing video 1/2: 🔴русский молодняк
⚠ Failed to track video URL          ← VIDEO FAILED
✓ Downloaded 1 caption(s): ['ru']    ← Captions worked
✓ Comments: 13 new                    ← Comments worked

Processing video 2/2: 🔴про россию и Украину
⚠ Failed to track video URL          ← VIDEO FAILED
✓ Downloaded 1 caption(s): ['ru']    ← Captions worked
✓ Comments: 11 new                    ← Comments worked

Summary:
  Videos processed: 2
  Videos tracked: 2         ← Misleading - metadata tracked, not videos
  Metadata files: 2
  Captions downloaded: 2
```

## Comparison: What Actually Works

### ✅ Working (Metadata Collection with Authentication)

**Before** (without remote_components):
```
ERROR: [youtube] n challenge solving failed
Result: 0 videos processed
```

**After** (with remote_components):
```
✓ Successfully fetched metadata for 2 videos
✓ Downloaded captions
✓ Downloaded comments with authentication
Result: 2 videos' metadata processed
```

### ❌ Not Working (Video Files)

**Both before and after:**
```
WARNING: Failed to track video URL
Result: No video files
```

## What This Means

### For Metadata Archival ✅

The implementation **is complete and working** for:
- Archiving video metadata (title, description, stats)
- Downloading captions/subtitles
- Downloading comments (with authentication)
- Downloading thumbnails
- Generating searchable web interface

### For Video File Archival ❌

The implementation **does not work** for:
- Tracking video URLs with git-annex
- Downloading actual video files
- Playing videos in the web interface

## Next Steps

### 1. Investigate Video URL Tracking Issue

Need to understand why `git annex addurl` fails for YouTube URLs:
- Check git-annex documentation for YouTube support
- Investigate if special configuration is needed
- Consider alternative approaches (e.g., yt-dlp download + git-annex add)

### 2. Possible Solutions

**Option A:** Use yt-dlp to download, then `git annex add`
**Option B:** Configure git-annex to use yt-dlp as external downloader
**Option C:** Track URLs differently (if YouTube URLs aren't directly downloadable)

## Conclusion

**Cookie + remote_components support:** ✅ **Complete** for metadata collection
**Video file downloads:** ❌ **Not working** - requires investigation

The Python API correctly handles cookies and the deno JS solver for authenticated metadata collection. However, actual video file downloads via git-annex need additional work to function properly.

Users can currently:
- ✅ Archive all metadata with authentication
- ✅ Browse metadata via web interface
- ❌ Download or play actual video files
