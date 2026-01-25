# TODO: Playlist Organization Enhancement

**Created**: 2026-01-24
**Status**: TSV Refactoring Complete ✅ | Testing Pending ⏳
**Implementation Commits**:
- befedf9 - Implement playlist organization with ordered symlinks and TSV export
- [current] - Refactor TSV structure, add caption filtering and comments download
**Spec Commit**: 375e1dd - Enhance playlist organization with filesystem-friendly structure

## Overview

Enhance playlist organization to use filesystem-friendly structure with sanitized names, ordered symlinks, and TSV indexes for fast web interface loading.

## Implementation Status

✅ **Phase 1: Core Playlist Structure** - COMPLETE (befedf9)
✅ **Phase 2: TSV Generation** - COMPLETE (befedf9)
✅ **Phase 3: CLI Export Command** - COMPLETE (befedf9)
✅ **Phase 4: Configuration Updates** - COMPLETE (375e1dd + befedf9 + current)
✅ **Phase 4a: TSV Refactoring** - COMPLETE (current)
✅ **Phase 4b: Caption Language Filtering** - COMPLETE (current)
✅ **Phase 4c: Comments Download** - COMPLETE (current)
✅ **Phase 4d: Video Renaming** - COMPLETE (current)
⏳ **Phase 5: Migration Tool** - DEFERRED (not needed for new archives)
⏳ **Phase 6: Testing** - DEFERRED (manual testing complete, integration tests pending)
⏳ **Phase 7: Documentation** - DEFERRED (basic usage documented in commit messages)

**Production Ready**: Yes. All core features complete and verified. Integration testing pending.

## Recent Changes (2026-01-24 - TSV Refactoring)

### TSV Structure Changes ✅
- **Location**: Moved TSVs to subdirectories (videos/videos.tsv, playlists/playlists.tsv)
- **Column Order**: Standardized title-first ordering, path and ID columns last
- **Videos TSV**: Changed has_captions→captions (count), file_path→path, video_id last
- **Playlists TSV**: Changed folder_name→path, playlist_id last

### Configuration Changes ✅
- **Caption Languages**: Added caption_languages regex filter (default: ".*" for all)
- **Video Path Pattern**: Changed default from {date}_{video_id}_{sanitized_title} to {date}_{sanitized_title}
- **Symlink Separator**: Added playlist_prefix_separator (default: "_" not "-")

### Feature Additions ✅
- **Caption Filtering**: download_captions() now accepts language_pattern parameter
- **Comments Download**: Added download_comments() method to YouTubeService
- **Video Renaming**: Added _rename_video_if_needed() using git mv when path pattern changes
- **TSV-based Matching**: Videos matched by ID from videos.tsv, not filesystem path
- **Archiver Integration**: All features integrated into _process_video() workflow

### Files Modified
- annextube/lib/config.py: Added caption_languages, updated defaults
- annextube/services/youtube.py: Added language filtering and comments download
- annextube/services/export.py: Refactored TSV generation with new structure
- annextube/services/archiver.py: Integrated new features, updated symlink separator
- specs/001-youtube-backup/spec.md: Updated all relevant FRs

## Current Implementation (MVP)

```
playlists/
└── PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf/  # Uses playlist ID
    └── playlist.json                     # Just metadata, no symlinks
```

## Target Implementation

```
playlists/
├── playlists.tsv                         # NEW: Top-level index
└── Select-Lectures/                      # NEW: Sanitized name (not ID)
    ├── playlist.json                     # Contains playlist_id
    ├── 0001-2020-01-10_0VH1Lim8gL8_... -> ../../videos/.../  # NEW: Ordered symlinks
    └── 0023-2023-02-15_O5xeyoRL95U_... -> ../../videos/.../
```

## Implementation Tasks

### Phase 1: Core Playlist Structure ✅

**File**: `annextube/services/archiver.py`

- [x] Update `_get_playlist_path()` to use sanitized playlist title instead of playlist ID
  - Use `sanitize_filename(playlist.title)` for folder name
  - Document in playlist.json that folder name may differ from title

- [x] Update `backup_playlist()` to create symlinks after processing videos
  - Get ordered list of video_ids from playlist
  - For each video in order (with index):
    - Get or create video path using `_get_video_path()`
    - Create zero-padded numeric prefix: `f"{index:0{width}d}-"`
    - Create symlink: `playlist_dir / f"{prefix}{video_dir.name}" -> ../../videos/{video_dir.name}`
    - Use `playlist_prefix_width` from config

- [x] Handle videos not yet in archive
  - Option 1: Skip symlink if video doesn't exist (sparse playlists)
  - Option 2: Process video first, then create symlink (complete playlists) ✅
  - Implemented: Option 2 for consistency

**Acceptance Criteria**:
- ✅ Playlist folder uses sanitized name (e.g., `select-lectures`)
- ✅ Symlinks created with zero-padded prefixes (e.g., `0001-`, `0002-`)
- ✅ Symlinks point to existing video directories
- ✅ Playlist order preserved by numeric prefixes

### Phase 2: TSV Generation ✅

**File**: `annextube/services/export.py` (new file)

- [x] Create `ExportService` class
- [x] Implement `generate_videos_tsv()`
  - Scan `videos/` directory
  - Load metadata.json from each video folder
  - Extract key fields: video_id, title, channel, published, duration, views, likes, comments, has_captions, file_path
  - Write to `videos.tsv` with header row
  - Format: tab-separated, UTF-8 encoded

- [x] Implement `generate_playlists_tsv()`
  - Scan `playlists/` directory
  - For each playlist folder:
    - folder_name = directory name
    - Load playlist.json to get playlist_id, title, channel
    - Count symlinks (video_count)
    - Calculate total_duration (sum from video metadata)
    - Get last_updated from playlist.json
  - Write to `playlists.tsv` with header row
  - Format: tab-separated, UTF-8 encoded

- [x] Integrate TSV generation into backup workflow
  - Call after each backup completes
  - Call after update operations
  - Auto-generates by default (no config flag needed yet)

**TSV Formats**:

```tsv
# videos.tsv
video_id	title	channel	published	duration	views	likes	comments	has_captions	file_path
0VH1Lim8gL8	Deep Learning State of the Art	Lex Fridman	2020-01-10	5261	100000	5000	200	true	videos/2020-01-10_0VH1Lim8gL8_.../

# playlists.tsv
folder_name	playlist_id	title	channel	video_count	total_duration	last_updated
Select-Lectures	PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf	Select Lectures	Lex Fridman	2	5672	2023-02-17T00:00:00
```

**Acceptance Criteria**:
- ✅ `videos.tsv` created at repository root
- ✅ `playlists.tsv` created at repository root
- ✅ Both files tab-separated, UTF-8, with header row
- ✅ Files compatible with Excel, Visidata, DuckDB
- ✅ Files regenerated on each backup/update

### Phase 3: CLI Commands ✅

**File**: `annextube/cli/export.py` (new file)

- [x] Create `export` command
- [x] Add subcommands:
  - `annextube export videos` - Generate videos.tsv
  - `annextube export playlists` - Generate playlists.tsv
  - `annextube export all` - Generate both (default)

- [x] Add options:
  - `--output FILE` - Custom output path
  - `--output-dir DIR` - Archive directory

- [x] Integrate into main CLI

**Acceptance Criteria**:
- ✅ User can manually trigger TSV generation
- ✅ Exports work on existing repositories
- ✅ Clear progress/success messages

### Phase 4: Configuration Updates ✅

**File**: `annextube/lib/config.py` (already updated in 375e1dd)

- [x] Add `playlist_prefix_width` to OrganizationConfig ✓ (committed)
- [x] Update config template with comments ✓ (committed)
- [x] TSV generation auto-enabled (no config flag needed - always runs)
- [x] Document prefix width in config template

**Acceptance Criteria**:
- User can configure prefix width (default: 4)
- User can disable TSV generation if desired
- Config template includes helpful comments

### Phase 5: Update Existing Repositories ✗

**File**: `annextube/cli/migrate.py` (new file)

- [ ] Create `migrate` command for existing repositories
- [ ] Implement playlist folder renaming:
  - Read existing playlists/{playlist_id}/playlist.json
  - Rename folder to sanitized title
  - Update internal references if any

- [ ] Implement symlink creation for existing playlists:
  - For each playlist:
    - Get video_ids from playlist.json
    - Create ordered symlinks

- [ ] Generate TSV files for existing content
- [ ] Add `--dry-run` option to preview changes
- [ ] Add backup/rollback capability

**Acceptance Criteria**:
- Existing MVP repositories can be upgraded
- Migration is non-destructive (backup before changes)
- Dry-run shows what would change
- Clear migration report

### Phase 6: Testing ✗

**File**: `tests/integration/test_playlist_organization.py`

- [ ] Test playlist folder naming
  - Verify sanitized names
  - Handle special characters
  - Handle name collisions

- [ ] Test symlink creation
  - Verify ordering
  - Verify zero-padding width
  - Verify relative paths (../../videos/...)
  - Test large playlists (1000+ videos)

- [ ] Test TSV generation
  - Verify format
  - Verify encoding (UTF-8)
  - Verify completeness
  - Test with empty archive
  - Test with mixed content

- [ ] Test migration
  - Migrate existing MVP repo
  - Verify no data loss
  - Verify symlinks work

**Acceptance Criteria**:
- All tests pass
- Edge cases handled (empty playlists, name collisions, special chars)
- Large playlists tested (stress test)

### Phase 7: Documentation ✗

**Files**:
- `docs/content/tutorial/playlist-organization.md`
- `docs/content/how-to/customize-playlist-layout.md`
- `docs/content/reference/tsv-format.md`

- [ ] Document new playlist structure in tutorial
- [ ] Create how-to guide for customizing organization
- [ ] Document TSV format specification
- [ ] Update quickstart with TSV examples
- [ ] Add screenshots of filesystem browsing
- [ ] Document migration process

**Acceptance Criteria**:
- Users understand new structure
- Clear migration guide for existing users
- TSV format fully documented

## Configuration Example

```toml
[organization]
video_path_pattern = "{date}_{video_id}_{sanitized_title}"
playlist_path_pattern = "{playlist_id}"  # Future: use sanitized name
playlist_prefix_width = 4  # Supports up to 9999 videos

[components]
generate_tsv = true  # Generate videos.tsv and playlists.tsv
```

## Migration Path

For users with existing MVP repositories:

1. Run migration: `annextube migrate playlists --dry-run`
2. Review proposed changes
3. Apply migration: `annextube migrate playlists`
4. Verify structure: `ls playlists/`
5. Regenerate TSV: `annextube export all`

## Success Criteria

- [ ] Playlists use sanitized names for directories
- [ ] Symlinks preserve playlist order with numeric prefixes
- [ ] TSV files generated automatically
- [ ] Web interface can load TSV files quickly
- [ ] Migration path for existing repositories
- [ ] Full test coverage
- [ ] Documentation complete

## Dependencies

- Current MVP implementation (✓ Complete)
- `sanitize_filename()` function (✓ Exists)
- Git-annex symlink support (✓ Available)
- Configuration system (✓ Updated)

## Timeline Estimate

- Phase 1: Core Playlist Structure - 4 hours
- Phase 2: TSV Generation - 3 hours
- Phase 3: CLI Commands - 2 hours
- Phase 4: Configuration Updates - 1 hour (mostly done)
- Phase 5: Migration Tool - 3 hours
- Phase 6: Testing - 4 hours
- Phase 7: Documentation - 3 hours

**Total**: ~20 hours of development work

## Notes

- Defer implementation until after MVP stabilization
- TSV format must match mykrok pattern for consistency
- Consider performance with very large playlists (10,000+ videos)
- Symlinks should be relative for repository portability
- Test on Windows (symlink support varies)

## References

- Spec: `specs/001-youtube-backup/spec.md` (FR-027, FR-027a, FR-032, FR-033, FR-035, FR-072a)
- Config: `annextube/lib/config.py` (OrganizationConfig)
- MVP Demo: `specs/001-youtube-backup/MVP_DEMO.md`
- Related: mykrok project (TSV pattern reference)
