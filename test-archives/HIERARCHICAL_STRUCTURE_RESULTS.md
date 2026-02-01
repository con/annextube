# Hierarchical Directory Structure - Test Results ✅

Successfully implemented and tested year/month hierarchical video directory structure.

## Summary

Implemented hierarchical video organization with `{year}/{month}/{date}_{sanitized_title}` pattern. Videos are now organized in year and month subdirectories for better scalability with large archives.

## Implementation

### Default Pattern

New default: `{year}/{month}/{date}_{sanitized_title}`
Previous: `{date}_{sanitized_title}` (flat)

Example hierarchical structure:
```
videos/
├── 2026/
│   └── 01/
│       ├── 2026-01-30_русский-молодняк/
│       ├── 2026-01-31_Нокаут-русского-историка-Кто-из-нас-Русь/
│       └── 2026-01-31_побочка-спутника/
└── videos.tsv
```

### Features

- ✅ Hierarchical year/month subdirectories
- ✅ CLI option `--video-path-pattern` for custom patterns
- ✅ Config template supports new placeholders: `{year}`, `{month}`
- ✅ Playlist symlinks work correctly with subdirectories
- ✅ Backward compatible with flat patterns
- ✅ Comprehensive unit tests

### Available Placeholders

- `{year}` - Publication year (YYYY)
- `{month}` - Publication month (MM)
- `{date}` - Publication date (YYYY-MM-DD)
- `{video_id}` - YouTube video ID
- `{sanitized_title}` - Video title (sanitized for filesystem)
- `{channel_id}` - Channel ID
- `{channel_name}` - Channel name (sanitized)

### Custom Patterns

```bash
# Hierarchical by year only
annextube init --video-path-pattern "{year}/{date}_{sanitized_title}"

# Flat layout (old behavior)
annextube init --video-path-pattern "{date}_{sanitized_title}"

# Year/month with video ID
annextube init --video-path-pattern "{year}/{month}/{video_id}"
```

## Test Results

### Test 1: @apopyk Channel (Hierarchical Pattern)

**Command:** `./test-hierarchical-apopyk.sh`

**Configuration:**
- Pattern: `{year}/{month}/{date}_{sanitized_title}` (default)
- Videos: enabled
- Limit: 3 most recent videos
- Cookies: enabled
- Remote components: ejs:github

**Results:** ✅ SUCCESS

Videos organized hierarchically:
```
videos/
└── 2026/
    └── 01/
        ├── 2026-01-30_русский-молодняк/
        │   ├── video.mkv (309 MB, 1080p av01)
        │   ├── metadata.json
        │   ├── captions.tsv
        │   ├── comments.json
        │   ├── video.ru.vtt
        │   └── thumbnail.jpg
        ├── 2026-01-31_Нокаут-русского-историка-Кто-из-нас-Русь/
        │   ├── video.mkv
        │   ├── metadata.json
        │   ├── captions.tsv
        │   ├── comments.json
        │   ├── video.ru.vtt
        │   └── thumbnail.jpg
        └── 2026-01-31_побочка-спутника/
            ├── video.mkv
            ├── metadata.json
            ├── captions.tsv
            ├── comments.json
            ├── video.ru.vtt
            └── thumbnail.jpg
```

**Summary:**
- Videos processed: 3
- All components downloaded: ✅
  - Video files: ✅ (actual .mkv files)
  - Metadata: ✅
  - Captions: ✅
  - Comments: ✅
  - Thumbnails: ✅
- Directory structure: ✅ Year/month subdirectories created
- Git-annex tracking: ✅ Working correctly

## Technical Details

### Playlist Symlinks

Fixed playlist symlinks to support hierarchical paths using `relative_to()`:

```python
# Before (broken with hierarchy):
relative_target = Path("..") / ".." / "videos" / video_dir.name

# After (works with any structure):
relative_target = Path("..") / ".." / video_dir.relative_to(self.repo_path)
```

Example symlink with hierarchical paths:
```
playlists/my-playlist/0001_2026-01-30_видео
  -> ../../videos/2026/01/2026-01-30_видео
```

### Config Template

Updated config template generation to properly handle pattern interpolation in f-strings:

```python
# Build organization section separately to avoid f-string brace escaping
organization_section = f'''
[organization]
video_path_pattern = "{video_path_pattern}"  # Interpolates correctly
# Examples with escaped braces for documentation:
#   "{{{{year}}}}/{{{{month}}}}/..."
'''
```

## Unit Tests

Created comprehensive test suite: `tests/unit/test_hierarchical_video_paths.py`

Tests cover:
- ✅ Default pattern is hierarchical
- ✅ Video path generation with year/month subdirectories
- ✅ Backward compatibility with flat patterns
- ✅ Custom pattern support
- ✅ Playlist symlinks with hierarchical paths
- ✅ Multiple videos in different months
- ✅ Config template generation
- ✅ Custom pattern in config template

All tests passing (8/8).

## Code Changes

**Files modified:**
1. `annextube/cli/init.py` - Added `--video-path-pattern` option
2. `annextube/lib/config.py` - Updated default pattern and template generation
3. `annextube/services/archiver.py` - Added year/month placeholders, fixed symlink paths
4. `tests/unit/test_hierarchical_video_paths.py` - Comprehensive test suite

**Commit:**
```
48ba810 Add hierarchical video directory structure with year/month subdirectories
```

## Next Steps

Remaining tests to run:
1. Test with @datalad channel
2. Create mytube archive with user's playlists (no limit)
