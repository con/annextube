# Video Quality Verification

## Downloaded Video Quality

**Video 1: 26S5SKx4NmI**

**Downloaded:**
- Resolution: **1920x1080 (1080p)**
- Codec: **av01** (AV1)
- File size: **309 MB**
- Matches format **399**: av01.0.08M.08, 425k bitrate

**Available formats on YouTube:**

### 1080p Options (Best to Default):
```
356  webm  1080p  2669k  vp9    1.15 GiB  [Premium]
721  mp4   1080p   596k  av01    262 MB   [Premium]
137  mp4   1080p   886k  h264    390 MB
248  webm  1080p   762k  vp9     335 MB
399  mp4   1080p   425k  av01    187 MB   ← Downloaded
```

## Analysis

### What Was Downloaded
yt-dlp selected **format 399** (av01 codec, 425k bitrate) by default.

### Why Not Higher Bitrate?

**Default yt-dlp behavior:**
- Prefers modern codecs (av01 > vp9 > h264)
- AV1 provides better compression efficiency
- Downloads "best quality" which considers codec efficiency, not just bitrate

**Formats 356, 721 (Premium):**
- Require YouTube Premium subscription
- Higher bitrates (2669k, 596k)
- Not accessible without authentication as Premium user

**Formats 137, 248 (Standard):**
- Higher bitrate but older codecs (H.264, VP9)
- Larger file sizes for similar visual quality
- yt-dlp prefers efficient modern codecs

### Is This Optimal?

**For file size:** ✅ Yes - AV1 is most efficient
**For compatibility:** ✅ Yes - Modern codec, good support
**For archival:** ⚠️ Could use higher bitrate for preservation

## Recommendation for Best Quality

To force highest bitrate 1080p (format 137):
```toml
# In user config:
ytdlp_extra_opts = [
    "--remote-components", "ejs:github",
    "--format", "137+bestaudio/bestvideo+bestaudio/best"
]
```

Or for highest quality VP9 (format 248):
```toml
ytdlp_extra_opts = [
    "--remote-components", "ejs:github",
    "--format", "248+bestaudio/bestvideo+bestaudio/best"
]
```

Or to prefer file size efficiency (current default):
```toml
# No format specification needed - yt-dlp defaults to:
# bestvideo+bestaudio/best (prefers modern codecs)
```

## Git-Annex Configuration

**Current:**
```
annex.youtube-dl-options = --cookies /path/to/cookies.txt --remote-components ejs:github
```

**With format selection:**
```
annex.youtube-dl-options = --cookies /path/to/cookies.txt --remote-components ejs:github --format "137+bestaudio/best"
```

## Codec Comparison

| Codec | Bitrate | File Size | Quality/Efficiency | Support |
|-------|---------|-----------|-------------------|---------|
| AV1   | 425k    | 187 MB    | Best efficiency   | Modern  |
| VP9   | 762k    | 335 MB    | Good efficiency   | Wide    |
| H.264 | 886k    | 390 MB    | Standard          | Universal |

**Verdict:** The downloaded av01 format provides excellent quality at efficient file size. For archival purposes where storage isn't a concern, format 137 or 248 would provide higher bitrate.

## Test Command

To check available formats for any video:
```bash
yt-dlp --cookies /path/to/cookies.txt \
       --remote-components ejs:github \
       --list-formats \
       'https://www.youtube.com/watch?v=VIDEO_ID'
```

## Conclusion

✅ **1080p resolution achieved** (highest available for non-Premium)
✅ **Modern efficient codec** (av01)
✅ **Good quality** for the file size (425k bitrate)

⚠️ **For maximum quality archival:** Consider specifying `--format 137+bestaudio` or `248+bestaudio` to get higher bitrate versions at cost of larger files.

The current default behavior is reasonable for most use cases, preferring efficient modern codecs over raw bitrate.
