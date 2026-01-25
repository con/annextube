# TODO: Playlist Organization Enhancement

**Created**: 2026-01-24
**Status**: Specification Complete, Implementation Pending
**Related Commit**: 375e1dd - Enhance playlist organization with filesystem-friendly structure

## Overview

Enhance playlist organization to use filesystem-friendly structure with sanitized names, ordered symlinks, and TSV indexes for fast web interface loading.

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

### Phase 1: Core Playlist Structure ✗

**File**: `annextube/services/archiver.py`

- [ ] Update `_get_playlist_path()` to use sanitized playlist title instead of playlist ID
  - Use `sanitize_filename(playlist.title)` for folder name
  - Document in playlist.json that folder name may differ from title

- [ ] Update `backup_playlist()` to create symlinks instead of processing videos directly
  - Get ordered list of video_ids from playlist
  - For each video in order (with index):
    - Get or create video path using `_get_video_path()`
    - Create zero-padded numeric prefix: `f"{index:0{width}d}-"`
    - Create symlink: `playlist_dir / f"{prefix}{video_dir.name}" -> ../../videos/{video_dir.name}`
    - Use `playlist_prefix_width` from config

- [ ] Handle videos not yet in archive
  - Option 1: Skip symlink if video doesn't exist (sparse playlists)
  - Option 2: Process video first, then create symlink (complete playlists)
  - Recommend: Option 2 for consistency

**Acceptance Criteria**:
- Playlist folder uses sanitized name (e.g., `Select-Lectures`)
- Symlinks created with zero-padded prefixes (e.g., `0001-`, `0023-`)
- Symlinks point to existing video directories
- Playlist order preserved by numeric prefixes

### Phase 2: TSV Generation ✗

**File**: `annextube/services/export.py` (new file)

- [ ] Create `ExportService` class
- [ ] Implement `generate_videos_tsv()`
  - Scan `videos/` directory
  - Load metadata.json from each video folder
  - Extract key fields: video_id, title, channel, published, duration, views, likes, comments, has_captions, file_path
  - Write to `videos.tsv` with header row
  - Format: tab-separated, UTF-8 encoded

- [ ] Implement `generate_playlists_tsv()`
  - Scan `playlists/` directory
  - For each playlist folder:
    - folder_name = directory name
    - Load playlist.json to get playlist_id, title, channel
    - Count symlinks (video_count)
    - Calculate total_duration (sum from video metadata)
    - Get last_updated from playlist.json
  - Write to `playlists.tsv` with header row
  - Format: tab-separated, UTF-8 encoded

- [ ] Integrate TSV generation into backup workflow
  - Call after each backup completes
  - Call after update operations
  - Make optional via config flag (default: true)

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
- `videos.tsv` created at repository root
- `playlists.tsv` created at repository root
- Both files tab-separated, UTF-8, with header row
- Files compatible with Excel, Visidata, DuckDB
- Files regenerated on each backup/update

### Phase 3: CLI Commands ✗

**File**: `annextube/cli/export.py` (new file)

- [ ] Create `export` command
- [ ] Add subcommands:
  - `annextube export videos` - Generate videos.tsv
  - `annextube export playlists` - Generate playlists.tsv
  - `annextube export all` - Generate both

- [ ] Add options:
  - `--output FILE` - Custom output path
  - `--format {tsv,csv,json}` - Output format

- [ ] Integrate into main CLI

**Acceptance Criteria**:
- User can manually trigger TSV generation
- Exports work on existing repositories
- Clear progress/success messages

### Phase 4: Configuration Updates ✗

**File**: `annextube/lib/config.py` (already updated in 375e1dd)

- [x] Add `playlist_prefix_width` to OrganizationConfig ✓ (committed)
- [x] Update config template with comments ✓ (committed)
- [ ] Add `generate_tsv` flag to ComponentsConfig (default: true)
- [ ] Document TSV generation in config template

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
