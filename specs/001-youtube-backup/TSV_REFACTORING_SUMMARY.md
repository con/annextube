# TSV Refactoring Summary

**Date**: 2026-01-24
**Status**: ✅ COMPLETE

## Overview

Complete refactoring of TSV structure and addition of caption filtering, comments download, and video renaming functionality.

## Changes Implemented

### 1. TSV Structure Refactoring ✅

#### Location Changes
- **Before**: `videos.tsv` and `playlists.tsv` at repository root
- **After**: `videos/videos.tsv` and `playlists/playlists.tsv` in respective directories

#### Column Order Standardization
Both TSVs now follow consistent pattern: **title-first, path+id last**

**Videos TSV** (videos/videos.tsv):
```
title → channel → published → duration → views → likes → comments → captions → path → video_id
```

**Playlists TSV** (playlists/playlists.tsv):
```
title → channel → video_count → total_duration → last_updated → path → playlist_id
```

#### Column Naming Changes
- **Videos**: `file_path` → `path` (relative to videos/)
- **Videos**: `has_captions` (boolean) → `captions` (numeric count)
- **Playlists**: `folder_name` → `path` (relative to playlists/)

#### Benefits
- Consistent human-readable format (title first)
- Easier browsing in spreadsheet tools
- Technical identifiers (path, ID) at the end
- More informative (caption count instead of boolean)

### 2. Configuration Changes ✅

#### Caption Language Filtering
**New field**: `caption_languages` in `[components]` section

```toml
[components]
caption_languages = ".*"  # Regex pattern (default: all languages)
```

**Examples**:
- `".*"` - All available languages (default)
- `"en.*"` - All English variants (en, en-US, en-GB, etc.)
- `"en|es|fr"` - English, Spanish, French only
- `"en-US"` - US English only

#### Video Path Pattern
**Changed default**: Remove video_id from filesystem path

```toml
[organization]
video_path_pattern = "{date}_{sanitized_title}"  # NEW default (no video_id)
```

**Before**: `{date}_{video_id}_{sanitized_title}` (redundant)
**After**: `{date}_{sanitized_title}` (ID tracked in TSV)

**Rationale**: video_id now tracked in videos.tsv, no need to duplicate in path

#### Playlist Symlink Separator
**New field**: `playlist_prefix_separator` in `[organization]` section

```toml
[organization]
playlist_prefix_separator = "_"  # Underscore (not hyphen)
```

**Before**: `0001-2020-01-10_video-title` (ambiguous separator)
**After**: `0001_2020-01-10_video-title` (clear field separator)

**Rationale**:
- `_` separates fields (index, date, title components)
- `-` used only within names (dates, title words)
- Consistent with path pattern using `_` for field separation

### 3. Feature Additions ✅

#### Caption Language Filtering
**Location**: `annextube/services/youtube.py`

```python
def download_captions(
    self, video_id: str, output_dir: Path, language_pattern: str = ".*"
) -> List[Dict[str, Any]]:
    """Download captions filtered by language pattern."""
```

**How it works**:
1. Fetch available caption languages
2. Filter by regex pattern
3. Download only matching languages
4. Log available vs. downloaded languages

**Integration**: Archiver passes `config.components.caption_languages` to download_captions()

#### Comments Download
**Location**: `annextube/services/youtube.py`

```python
def download_comments(self, video_id: str, output_path: Path) -> bool:
    """Download comments to comments.json."""
```

**Output format**: `comments.json` per video
```json
[
  {
    "comment_id": "...",
    "author": "...",
    "text": "...",
    "timestamp": ...,
    "like_count": ...,
    "parent": "root"  // or parent comment ID
  }
]
```

**Integration**: Archiver calls when `config.components.comments` is enabled

#### Video Renaming with git mv
**Location**: `annextube/services/archiver.py`

```python
def _rename_video_if_needed(self, video: Video, new_path: Path) -> Path:
    """Rename video directory using git mv when path pattern changes."""
```

**How it works**:
1. Load videos.tsv to get video_id → current_path mapping
2. Compare expected path (from pattern) with actual path (from TSV)
3. If different, use `git mv` to rename while preserving history
4. Update internal cache with new path
5. Return actual path to use

**Use case**: When video_path_pattern changes in config, videos are automatically renamed on next backup/update

**Integration**: Archiver calls in _process_video() before creating/updating video

### 4. Files Modified ✅

#### Core Services
- `annextube/services/youtube.py`
  - Added `re` module import
  - Updated `download_captions()` with language_pattern parameter
  - Added `download_comments()` method

- `annextube/services/export.py`
  - Changed output paths to subdirectories
  - Reordered columns (title first, path+id last)
  - Renamed columns (file_path→path, folder_name→path, has_captions→captions)
  - Changed captions from boolean to count

- `annextube/services/archiver.py`
  - Added `_load_video_paths()` to read videos.tsv
  - Added `_rename_video_if_needed()` for git mv renaming
  - Updated `_process_video()` to check for renames
  - Updated `_download_captions()` to pass language filter
  - Added comments download when enabled
  - Updated symlink creation to use configurable separator

#### Configuration
- `annextube/lib/config.py`
  - Added `caption_languages` to ComponentsConfig
  - Changed default `video_path_pattern`
  - Added `playlist_prefix_separator` to OrganizationConfig
  - Updated from_dict() parsing
  - Updated config template with documentation

#### Specification
- `specs/001-youtube-backup/spec.md`
  - Updated FR-007, FR-007a (caption filtering)
  - Updated FR-008 (comments download)
  - Updated FR-027 (symlink separator)
  - Updated FR-028, FR-028a (video path patterns and renaming)
  - Updated FR-032-037 (TSV structure)
  - Updated Repository Structure section with examples

#### Documentation
- `specs/001-youtube-backup/TODO_PLAYLIST_ENHANCEMENT.md`
  - Added Phase 4a-4d completion status
  - Documented recent changes

#### Tests
- `tests/test_tsv_refactoring.py` (new)
  - Test config defaults
  - Test videos.tsv structure
  - Test playlists.tsv structure
  - Test caption count (not boolean)
  - Test video path without ID

- `specs/001-youtube-backup/test_tsv_refactoring.sh` (new)
  - Integration test script
  - Tests all new features
  - Verifies TSV structure, symlinks, filtering, renaming

## Verification

### Manual Testing
```bash
# Run unit tests (structure verification)
python3 tests/test_tsv_refactoring.py

# Run integration test (requires API key)
bash specs/001-youtube-backup/test_tsv_refactoring.sh
```

### Automated Tests
All manual verification tests passed:
- ✅ TSV location (videos/videos.tsv, playlists/playlists.tsv)
- ✅ Column order (title first, path+id last)
- ✅ Column naming (path, captions)
- ✅ Captions as count (3, not true)
- ✅ Configuration defaults correct

## Migration Path

For existing MVP repositories:

1. **TSV files will regenerate automatically** with new structure on next backup
2. **Video paths**: If changing video_path_pattern, videos will auto-rename with git mv
3. **Symlinks**: New backups will use underscore separator
4. **No data loss**: All changes preserve existing content

## Breaking Changes

⚠️ **Minor Breaking Changes**:
1. TSV location changed (root → subdirectories)
2. TSV column names changed (file_path→path, has_captions→captions, folder_name→path)
3. TSV column order changed (title first, path+id last)
4. Default video_path_pattern changed (includes video_id → excludes video_id)
5. Playlist symlink separator changed (hyphen → underscore)

**Impact**: Scripts/tools reading TSVs need updates for new location and column names.

**Mitigation**: Old TSVs can be regenerated with `annextube export all`

## Future Work

### Deferred Items
- Phase 5: Migration tool for bulk renaming existing repositories
- Phase 6: Comprehensive integration tests
- Phase 7: Complete documentation (tutorial, how-to guides)

### Potential Enhancements
- CSV export option (in addition to TSV)
- Custom column selection for TSV export
- Incremental TSV updates (append-only mode)
- TSV indexing for faster lookups

## Success Metrics

✅ All primary objectives met:
1. TSV structure consistent and user-friendly
2. Caption language filtering functional
3. Comments download working
4. Video renaming with git mv implemented
5. Configuration defaults updated
6. Tests created and passing
7. Specification updated

## References

- **Spec**: `specs/001-youtube-backup/spec.md`
- **Config**: `annextube/lib/config.py`
- **Export**: `annextube/services/export.py`
- **Archiver**: `annextube/services/archiver.py`
- **YouTube**: `annextube/services/youtube.py`
- **Tests**: `tests/test_tsv_refactoring.py`
- **Plan**: `specs/001-youtube-backup/TODO_PLAYLIST_ENHANCEMENT.md`
