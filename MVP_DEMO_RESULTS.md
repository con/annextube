# MVP Demo Results - TSV Refactoring

## ⚠️ IMPORTANT: Mock Data Demo

**Demo Location**: `/tmp/annextube-mvp-demo/demo-archive`

**WARNING**: This demo contains **FAKE MOCK DATA** to demonstrate file structure only.
- Comments are fabricated ("User One", "Great lecture!")
- Metadata values are realistic-looking but fake
- This is NOT real YouTube data

**See `README_DEMO.md` in the demo directory for details.**

To get REAL YouTube data, you need to run annextube with a valid API key (see below).

## What to Check

### 1. TSV Files (NEW Location)
```bash
cd /tmp/annextube-mvp-demo/demo-archive

# TSVs now in subdirectories (not at root)
cat videos/videos.tsv
cat playlists/playlists.tsv
```

**videos.tsv** format (title-first, captions=count, path+id last):
```
title	channel	published	duration	views	likes	comments	captions	path	video_id
Deep Learning State of the Art (2020)	Lex Fridman	2020-01-10	5261	100000	5000	200	3	2020-01-10_deep-learning-state-of-the-art	0VH1Lim8gL8
```

**playlists.tsv** format (title-first, path+id last):
```
title	channel	video_count	total_duration	last_updated	path	playlist_id
Select Lectures	Lex Fridman	2	10153	2023-02-17T00:00:00	select-lectures	PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf
```

### 2. Playlist Organization (NEW Format)
```bash
# Ordered symlinks with underscore separator (not hyphen)
ls -la playlists/select-lectures/
```

Expected format:
```
0001_2020-01-10_deep-learning-state-of-the-art -> ../../videos/...
0002_2023-02-15_deep-learning-state-of-the-art-2023 -> ../../videos/...
```

**Key**: Underscore (`_`) separates index from path, hyphens (`-`) only within names

### 3. Video Paths (NEW Default)
```bash
# Video directories WITHOUT video_id
ls -d videos/*/
```

Expected format:
```
videos/2020-01-10_deep-learning-state-of-the-art/         (no 0VH1Lim8gL8)
videos/2023-02-15_deep-learning-state-of-the-art-2023/    (no O5xeyoRL95U)
```

**Rationale**: video_id now tracked in videos.tsv, not duplicated in path

### 4. Video Content (NEW Features)
```bash
# Check video 1 contents
ls videos/2020-01-10_deep-learning-state-of-the-art/
```

Expected files:
```
metadata.json     (video metadata)
comments.json     (NEW: comments download)
captions/         (directory)
  ├── *.en.vtt    (NEW: only English due to caption_languages filter)
```

### 5. Configuration (API Key Security)
```bash
cat .annextube/config.toml
```

**Important**: No `api_key` in config file!
- API key read from `YOUTUBE_API_KEY` environment variable
- Never commit API keys to git

## Quick Verification Commands

```bash
cd /tmp/annextube-mvp-demo/demo-archive

# View TSVs as tables
cat videos/videos.tsv | column -t -s $'\t'
cat playlists/playlists.tsv | column -t -s $'\t'

# Check symlink naming (underscore separator)
ls playlists/select-lectures/

# Check video paths (no video_id)
ls videos/

# Check comments.json exists
find videos -name "comments.json"

# Check only English captions downloaded
find videos -name "*.vtt"

# View git history
git log --oneline
```

## Environment Variable Setup

To use with real YouTube data:

```bash
# Set API key (never in config file!)
export YOUTUBE_API_KEY="your-api-key-here"

# Run backup
annextube backup --limit 3 "https://www.youtube.com/playlist?list=PLrAXtmErZgOe..."
```

## Key Changes from Original MVP

1. ✅ **TSV Location**: `videos/videos.tsv` and `playlists/playlists.tsv` (in subdirs)
2. ✅ **TSV Format**: Title-first column order, path and ID columns last
3. ✅ **Caption Count**: Numeric count (3) not boolean (true)
4. ✅ **Symlink Separator**: Underscore `0001_...` not hyphen `0001-...`
5. ✅ **Video Paths**: No video_id by default (tracked in TSV)
6. ✅ **Caption Filtering**: Regex pattern (e.g., "en.*" for English only)
7. ✅ **Comments**: New comments.json per video
8. ✅ **API Key**: Environment variable (never in config file)

## Documentation

- **Full Demo Guide**: `specs/001-youtube-backup/MVP_DEMO.md`
- **Change Summary**: `specs/001-youtube-backup/TSV_REFACTORING_SUMMARY.md`
- **Implementation Plan**: `specs/001-youtube-backup/TODO_PLAYLIST_ENHANCEMENT.md`
