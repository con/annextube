# Where to See MVP Demo Results

## Quick Answer

**Demo is ready at**: `/tmp/annextube-mvp-demo/demo-archive`

To explore it:
```bash
cd /tmp/annextube-mvp-demo/demo-archive

# View TSVs
cat videos/videos.tsv | column -t -s $'\t'
cat playlists/playlists.tsv | column -t -s $'\t'

# See playlist symlinks (underscore separator)
ls -la playlists/select-lectures/

# Check video paths (no video_id)
ls videos/
```

Or run fresh demo:
```bash
# Test script (creates structure)
bash specs/001-youtube-backup/test_tsv_refactoring.sh
```

## What You'll See

### 1. Updated Documentation

**Main MVP Demo**: `specs/001-youtube-backup/MVP_DEMO.md`
- Shows all enhanced features
- Updated repository structure
- New TSV format examples
- Step-by-step demonstration

**TSV Refactoring Summary**: `specs/001-youtube-backup/TSV_REFACTORING_SUMMARY.md`
- Complete summary of all changes
- Before/after comparisons
- Configuration examples

### 2. Demo Repository Structure

After running the test script, explore:

```bash
cd /tmp/tsv-refactoring-demo/my-archive/

# TSV files (new location and format)
cat videos/videos.tsv          # Title-first column order
cat playlists/playlists.tsv    # Title-first column order

# Playlist organization (ordered symlinks)
ls -la playlists/*/            # See 0001_, 0002_ with underscore separator

# Video paths (no video_id by default)
ls -d videos/*/                # See YYYY-MM-DD_video-title format

# Video content
ls videos/*/                   # See comments.json, filtered captions
```

### 3. Key Files to Check

```
/tmp/tsv-refactoring-demo/my-archive/
├── videos/
│   ├── videos.tsv                    ← CHECK: Title first, path+id last
│   └── 2020-01-10_video-title/       ← CHECK: No video_id in path
│       ├── comments.json             ← NEW: Comments download
│       └── captions/*.vtt            ← CHECK: Only en.* files
└── playlists/
    ├── playlists.tsv                 ← CHECK: Title first, path+id last
    └── select-lectures/              ← CHECK: Readable name
        ├── 0001_2020-01-10_...       ← CHECK: Underscore separator
        └── 0002_2023-02-15_...
```

## API Key Security (IMPORTANT)

**API keys are now read from environment variables, never stored in config files!**

```bash
# Set API key (REQUIRED for real downloads)
export YOUTUBE_API_KEY="your-api-key-here"

# Verify it's set
echo $YOUTUBE_API_KEY
```

The config file (`.annextube/config.toml`) should NEVER contain your API key.

## Manual Demo (with Real API Key)

If you have a YouTube API key:

```bash
# 1. Set API key (environment variable, not in config!)
export YOUTUBE_API_KEY="your-api-key-here"

# 2. Create fresh repository
cd /tmp
annextube create-dataset my-demo
cd my-demo

# 3. Configure a playlist (no api_key in config!)
cat >> .annextube/config.toml << 'EOF'

[[sources]]
url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
type = "playlist"
enabled = true

[filters]
limit = 3

[components]
caption_languages = "en.*"  # English only
comments = true
EOF

# 4. Run backup
annextube backup

# 5. Explore results
cat videos/videos.tsv | column -t -s $'\t'
cat playlists/playlists.tsv | column -t -s $'\t'
ls -la playlists/*/
```

## Expected TSV Format

### videos.tsv
```
title                           channel      published   duration  views   likes  comments  captions  path                          video_id
Deep Learning State of the Art  Lex Fridman  2020-01-10  5261      100000  5000   200       3         2020-01-10_deep-learning...   0VH1Lim8gL8
```

**Note**:
- First column is `title` (human-readable)
- Last column is `video_id` (technical)
- `captions` is a count (3), not boolean (true)
- `path` is relative to videos/ directory

### playlists.tsv
```
title            channel      video_count  total_duration  last_updated         path             playlist_id
Select Lectures  Lex Fridman  3            15045           2023-02-17T00:00:00  select-lectures  PLrAXtmErZgOe...
```

**Note**:
- First column is `title` (human-readable)
- Last column is `playlist_id` (technical)
- `path` is relative folder name (not full path)

## Verification Checklist

After running the demo, verify:

- [ ] `videos/videos.tsv` exists (not at root)
- [ ] `playlists/playlists.tsv` exists (not at root)
- [ ] TSV first column is "title"
- [ ] TSV last column is "video_id" or "playlist_id"
- [ ] TSV has "captions" column (numeric count)
- [ ] TSV has "path" column (not "file_path" or "folder_name")
- [ ] Playlist symlinks use underscore: `0001_...` (not `0001-...`)
- [ ] Video paths exclude video_id: `2020-01-10_title` (not `2020-01-10_ID_title`)
- [ ] Only English captions downloaded (*.en*.vtt)
- [ ] comments.json files present

## Troubleshooting

**No API key?**
- Test script will fail during backup, but you can still check code structure
- Review generated config and verify defaults are correct

**Want to see old vs new structure?**
- Compare `specs/001-youtube-backup/MVP_DEMO.md` (shows both)
- Check "Repository Structure" section for before/after

**Need more details?**
- `specs/001-youtube-backup/TSV_REFACTORING_SUMMARY.md` - Complete change log
- `specs/001-youtube-backup/TODO_PLAYLIST_ENHANCEMENT.md` - Implementation status
- `tests/test_tsv_refactoring.py` - Unit tests showing expected behavior

## Summary

**To see results immediately**:
1. Read updated `specs/001-youtube-backup/MVP_DEMO.md`
2. Run `bash specs/001-youtube-backup/test_tsv_refactoring.sh`
3. Explore `/tmp/tsv-refactoring-demo/my-archive/`

**To see with real data**:
1. Get YouTube API key
2. Follow "Manual Demo" section above
3. Explore TSV files and playlist organization
