# Implementation Plan: YouTube Archive System

**Branch**: `001-youtube-backup` | **Date**: 2026-01-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-youtube-backup/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a comprehensive YouTube archival system that backs up channels, playlists, and videos using git-annex for efficient storage and incremental updates. The system provides CLI, Python library, and client-side web interface for browsing archives offline. Core capabilities include metadata extraction, comment tracking, caption backup, configurable filtering, and automated updates via CI/CD platforms.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: datasalad (git/git-annex operations), yt-dlp (YouTube downloads), NEEDS CLARIFICATION (frontend framework choice)
**Storage**: File-based (NO databases) - git-annex repository with git for metadata (JSON, TSV, VTT, markdown) and git-annex for binaries (videos, thumbnails); summary metadata in TSV files (videos.tsv, playlists.tsv) for efficient querying; git-annex special remotes (S3, WebDAV, directory, etc.) for content storage
**Testing**: pytest (backend/library), NEEDS CLARIFICATION (frontend testing framework - Vitest/Jest + Playwright/Cypress)
**Target Platform**: Linux/macOS/Windows (CLI), modern browsers ES6+ (web UI), GitHub Actions/Codeberg Actions/Forgejo (CI/CD)
**Project Type**: Web application (backend library + CLI + frontend)
**Performance Goals**: Incremental update of 1000-video channel with 5 new videos in <5 minutes; web UI loads 1000-video archive in <3 seconds; initial metadata-only archive of 100-video channel in <30 minutes
**Constraints**: Offline-capable web UI (file:// protocol support); efficient incremental updates (avoid re-checking all content); YouTube API rate limiting compliance; memory-bounded operations via streaming
**Scale/Scope**: Support channels with 10,000+ videos; handle multiple languages for captions; configurable hierarchies and filters; CI/CD automation modes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Library-First Architecture ✓
- Core archival logic implemented as standalone Python library
- Library exposes clear API for channel/playlist/video archival operations
- Independent from CLI and web UI implementations
- Testable in isolation

### II. Multi-Interface Exposure ✓
- **CLI**: Command-line interface for all operations (create-dataset, backup, update, export, generate-web)
- **API**: Python library API for programmatic access
- **Web UI**: Client-side static web interface for browsing archives
- CLI follows Unix philosophy: stdin/args → stdout, errors → stderr, JSON output mode, meaningful exit codes, idempotent operations

### III. Test-First Development ✓
- TDD mandatory: tests written before implementation
- Tests define requirements and must be reviewed/approved
- Red-green-refactor cycle enforced

### IV. Integration Testing ✓
- Contract tests for library API boundaries
- CLI ↔ library integration tests
- Web UI ↔ library output integration (schema validation)
- End-to-end user workflow tests (backup → update → web UI)
- Frontend component integration tests

### V. Code Efficiency & Conciseness ✓
- YAGNI principle: implement only specified requirements
- Avoid over-engineering (e.g., no complex plugin system unless required)
- Clear, readable code prioritized

### VI. Observability & Debuggability ✓
- Structured logging (JSON format for machine parsing, human-readable option)
- Configurable log levels (debug, info, warning, error per FR-054)
- Clear error messages with actionable guidance
- Trace identifiers for operation tracking

### VII. Versioning & Breaking Changes ✓
- Semantic versioning (MAJOR.MINOR.PATCH)
- Migration guides for breaking changes
- Deprecation warnings in prior versions where possible

### VIII. DRY Principle - No Code Duplication ✓
- Introspect existing code before writing new functionality
- datasalad used for git/git-annex operations (avoid reimplementing)
- yt-dlp used for YouTube operations (avoid reimplementing)
- Extract common patterns into reusable utilities
- Code review must check for duplication

### IX. Shared Data Schema ✓
- JSON schema or TypeScript interfaces for data models (Video, Channel, Playlist, Comment, Caption, SyncState)
- Library outputs validated JSON/TSV
- Frontend generates types from schema (no manual duplication)
- Schema versioning independent of implementation

### X. FOSS Principles ✓
- OSI-approved open source license (needs LICENSE file - FR-083 Follow-up TODO)
- No telemetry/tracking without consent
- User data stays local (git-annex repositories)
- Offline-capable core functionality (web UI works via file://)
- Transparent dependency chain
- License compatibility verification in CI

### XI. Resource Efficiency ✓
- **Network**: Incremental updates (FR-010 to FR-016), API rate limiting (FR-077), batch requests
- **Disk**: Streaming for large files (FR-024), git-annex for efficient storage, configurable cache limits
- **Memory**: Bounded memory via streaming/pagination, no full dataset loads
- **CPU**: Efficient algorithms for metadata processing, lazy evaluation where appropriate
- **Energy**: Event-driven patterns, avoid polling where possible
- **Storage Simplicity**: File-based storage (TSV, JSON, VTT, Markdown) - NO database engines required (PostgreSQL, MySQL, etc.); aligns with mykrok pattern; metadata in videos.tsv and playlists.tsv for efficient querying

### Quality Standards
- Backend testing: pytest for unit/integration/contract tests
- Frontend testing: Vitest/Jest (unit), Testing Library (integration), Playwright/Cypress (E2E) - NEEDS RESEARCH
- Documentation: Diataxis framework (tutorial, how-to, reference, explanation) with Hugo + Congo theme
- Code review: duplication detection, test coverage verification

### Gates Summary
✅ **All constitution principles align with feature requirements**
⚠️ **Action Items**:
- Add LICENSE file to repository (FOSS Principle X)
- Configure license compatibility checking in CI
- Research frontend testing framework stack (Phase 0)
- Research frontend framework choice (React/Vue/Svelte) (Phase 0)

**Gate Status**: PASS (with action items for Phase 0)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
annextube/                    # Python package (library + CLI)
├── models/
│   ├── channel.py           # Channel entity
│   ├── video.py             # Video entity
│   ├── playlist.py          # Playlist entity
│   ├── caption.py           # Caption entity
│   ├── comment.py           # Comment entity
│   └── filter_config.py     # FilterConfig entity
├── services/
│   ├── git_annex.py         # datasalad wrapper for git-annex ops
│   ├── youtube.py           # yt-dlp wrapper for YouTube ops
│   ├── archiver.py          # Core archival logic
│   ├── metadata_export.py   # TSV export generation
│   ├── tsv_reader.py        # TSV reading utilities (max dates, counts)
│   └── web_generator.py     # Static web UI generation
├── cli/
│   ├── __main__.py          # CLI entry point
│   ├── create_dataset.py    # create-dataset command
│   ├── backup.py            # backup command
│   ├── update.py            # update command
│   ├── export.py            # export command
│   └── generate_web.py      # generate-web command
├── lib/
│   ├── logging_config.py    # Structured logging setup
│   ├── config.py            # Configuration file handling
│   └── utils.py             # Common utilities
└── schema/
    └── models.json          # JSON Schema for data models

frontend/                     # Client-side web interface
├── src/
│   ├── components/
│   │   ├── VideoList.{js,ts,vue,svelte}    # Video listing component
│   │   ├── VideoPlayer.{js,ts,vue,svelte}  # Video player with captions
│   │   ├── FilterPanel.{js,ts,vue,svelte}  # Filtering UI
│   │   └── CommentView.{js,ts,vue,svelte}  # Comment display
│   ├── pages/
│   │   ├── Index.{js,ts,vue,svelte}        # Main page
│   │   └── VideoDetail.{js,ts,vue,svelte}  # Video detail page
│   ├── services/
│   │   ├── data_loader.{js,ts}             # Load TSV/JSON data
│   │   └── search.{js,ts}                  # Client-side search
│   └── types/
│       └── models.{ts,d.ts}                # Generated from schema/models.json
└── tests/
    ├── unit/                                # Component unit tests
    ├── integration/                         # Component integration tests
    └── e2e/                                 # End-to-end tests

tests/                        # Backend/library tests
├── contract/                 # Library API contract tests
├── integration/              # CLI ↔ library, service integration tests
└── unit/                     # Unit tests for models, services

docs/                         # Hugo documentation site
├── content/
│   ├── tutorial/             # Diataxis: Tutorial
│   ├── how-to/               # Diataxis: How-to guides
│   ├── reference/            # Diataxis: Reference
│   └── explanation/          # Diataxis: Explanation
└── config.toml               # Hugo config with Congo theme

.github/workflows/            # CI/CD
├── test.yml                  # Run tests
├── update-archive.yml        # Automated archive update workflow template
└── publish-pages.yml         # Publish docs and demo to GitHub Pages
```

**Structure Decision**: Web application structure (Option 2 variant) selected due to:
- Backend Python library + CLI (annextube/ package)
- Frontend client-side web UI (frontend/ directory)
- Separation allows independent development and testing
- Shared schema (schema/models.json) bridges backend and frontend
- Frontend framework choice deferred to Phase 0 research (React/Vue/Svelte)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations requiring justification. All design decisions align with constitutional principles.

## Pending Implementation

### TODO: Automatic Playlist Discovery (FR-002a, FR-002b, FR-002c)

**Status**: Not yet implemented  
**Priority**: P2 (Nice to have, improves user experience)  
**Estimated Effort**: 4-6 hours

**Requirements**:
- FR-002a: Auto-discover all playlists from channel when `include_playlists` configured  
- FR-002b: Filter discovered playlists by regex pattern (include/exclude)
- FR-002c: Discover and backup podcasts from channel's Podcasts tab

**Implementation Tasks**:

1. **Config Schema Update** (`annextube/lib/config.py`):
   ```python
   @dataclass
   class SourceConfig:
       url: str
       type: str  # 'channel' or 'playlist'
       enabled: bool = True
       # NEW FIELDS:
       include_playlists: str = "none"  # "all", "none", or regex pattern
       exclude_playlists: Optional[str] = None  # Regex pattern to exclude
       include_podcasts: bool = False  # Auto-discover podcasts
   ```

2. **YouTube Service Enhancement** (`annextube/services/youtube.py`):
   - Add `get_channel_playlists(channel_url: str) -> List[Dict]` method
   - Add `get_channel_podcasts(channel_url: str) -> List[Dict]` method
   - Use yt-dlp to fetch channel's /playlists and /podcasts tabs
   - Return list of playlist/podcast dicts with: id, title, url, video_count

3. **Playlist Filtering Logic** (`annextube/services/archiver.py`):
   ```python
   def _discover_playlists(self, channel_url: str, config: SourceConfig) -> List[str]:
       """Discover and filter playlists based on config."""
       if config.include_playlists == "none":
           return []
       
       # Fetch all playlists
       playlists = self.youtube.get_channel_playlists(channel_url)
       
       if config.include_podcasts:
           podcasts = self.youtube.get_channel_podcasts(channel_url)
           playlists.extend(podcasts)
       
       # Filter by include pattern
       if config.include_playlists != "all":
           import re
           pattern = re.compile(config.include_playlists)
           playlists = [p for p in playlists if pattern.search(p['title'])]
       
       # Filter by exclude pattern
       if config.exclude_playlists:
           import re
           pattern = re.compile(config.exclude_playlists)
           playlists = [p for p in playlists if not pattern.search(p['title'])]
       
       return [p['url'] for p in playlists]
   ```

4. **Backup Integration** (`annextube/services/archiver.py`):
   - Modify `backup_channel()` to call `_discover_playlists()` after backing up channel videos
   - For each discovered playlist URL, call `backup_playlist()`
   - Log discovered playlists for transparency

5. **Configuration Documentation**:
   - Update `generate_config_template()` with examples:
     ```toml
     [[sources]]
     url = "https://www.youtube.com/@channel"
     type = "channel"
     enabled = true
     include_playlists = "all"  # Auto-backup all playlists
     # include_playlists = "историк.*"  # Only playlists matching regex
     # exclude_playlists = ".*shorts.*|.*old.*"  # Exclude matching playlists
     # include_podcasts = true  # Also backup podcasts
     ```

6. **Testing**:
   - Unit tests for `_discover_playlists()` with mock playlist data
   - Integration test: channel with 3 playlists, filter to 2
   - Integration test: podcasts discovery
   - Contract test: verify playlist discovery doesn't break existing behavior

**Example Usage After Implementation**:
```toml
# Before (manual):
[[sources]]
url = "https://www.youtube.com/@apopyk"
type = "channel"

[[sources]]
url = "https://www.youtube.com/playlist?list=PLxxx1"
type = "playlist"

[[sources]]
url = "https://www.youtube.com/playlist?list=PLxxx2"
type = "playlist"

# After (automatic):
[[sources]]
url = "https://www.youtube.com/@apopyk"
type = "channel"
include_playlists = "all"  # Discovers all 8 playlists automatically
```

**Benefits**:
- Eliminates manual playlist enumeration
- Automatically discovers new playlists created on channel
- Powerful filtering for selective playlist backup
- Cleaner configuration files

**Dependencies**: None (uses existing yt-dlp capabilities)

**Risks**: None (purely additive feature, backward compatible)

### TODO: Eliminate sync_state.json - Use Actual Data Files (CURRENT)

**Status**: In progress  
**Priority**: P1 (Performance and simplicity improvement)  
**Estimated Effort**: 6-8 hours

**Problem**: sync_state.json duplicates data already present in videos.tsv, metadata.json, comments.json, and file modification times. This violates DRY principle and adds complexity.

**Solution**: Derive all sync state from actual data files.

**Implementation Tasks**:

1. **Update videos.tsv to use datetime** (currently date only):
   - Change published column from YYYY-MM-DD to ISO 8601 datetime with timezone
   - Update ExportService to write full datetime
   - Benefits: Enables precise `publishedAfter` queries to YouTube API

2. **Create TSV reader utilities** (`annextube/services/tsv_reader.py`):
   ```python
   class TSVReader:
       @staticmethod
       def get_latest_video_datetime(videos_tsv_path: Path) -> Optional[datetime]:
           """Read videos.tsv, return max(published) datetime."""
           
       @staticmethod
       def get_latest_playlist_update(playlists_tsv_path: Path, playlist_id: str) -> Optional[datetime]:
           """Read playlists.tsv, return last_updated for playlist_id."""
           
       @staticmethod
       def get_latest_comment_datetime(comments_json_path: Path) -> Optional[datetime]:
           """Read comments.json, return max(timestamp) from all comments."""
   ```

3. **Add date filtering to YouTube service** (`annextube/services/youtube.py`):
   ```python
   def get_channel_videos(self, channel_url: str, limit: int = None,
                         published_after: Optional[datetime] = None) -> List[Dict]:
       ydl_opts = self._get_ydl_opts(download=False)
       
       if published_after:
           # Format as YYYYMMDD for yt-dlp
           ydl_opts['dateafter'] = published_after.strftime('%Y%m%d')
       
       # ... rest of method
   ```

4. **Remove sync_state_service.py completely**:
   - Delete `annextube/services/sync_state_service.py`
   - Delete `annextube/models/sync_state.py`
   - Remove all imports and references

5. **Update archiver to use TSV-based state** (`annextube/services/archiver.py`):
   ```python
   def backup_channel(self, channel_url: str, source_config: Optional['SourceConfig'] = None,
                     update_mode: str = "videos-incremental") -> dict:
       """Backup channel with efficient incremental updates."""
       
       if update_mode == "videos-incremental":
           # Get latest video datetime from videos.tsv
           latest_datetime = TSVReader.get_latest_video_datetime(
               self.repo_path / "videos" / "videos.tsv"
           )
           videos = self.youtube.get_channel_videos(
               channel_url,
               limit=self.config.filters.limit,
               published_after=latest_datetime  # Only new videos!
           )
       elif update_mode == "all-incremental":
           # Fetch new videos + update social for recent ones
           latest_datetime = TSVReader.get_latest_video_datetime(...)
           new_videos = self.youtube.get_channel_videos(..., published_after=latest_datetime)
           
           # Also update social data for videos within time window
           recent_cutoff = datetime.now() - timedelta(days=7)
           recent_videos = [v for v in all_videos if v.published_at > recent_cutoff]
           for video in recent_videos:
               self._update_social_data(video)
       elif update_mode == "all-force":
           # Re-process everything (existing behavior)
           videos = self.youtube.get_channel_videos(...)
   ```

6. **Implement update modes in CLI** (`annextube/cli/backup.py`):
   ```python
   @click.option(
       "--update",
       type=click.Choice(["videos-incremental", "all-incremental", "social", "all-force"]),
       default="videos-incremental",
       help="Update mode (default: videos-incremental - fastest, only new videos)"
   )
   ```

7. **Update playlists.tsv to include last_updated datetime**:
   - Add last_updated column (ISO 8601 datetime)
   - Use for incremental playlist sync

8. **Comments incremental fetch** (if YouTube API supports it):
   - Check if YouTube API has `publishedAfter` for comments
   - If yes: fetch only comments newer than max timestamp in comments.json
   - If no: compare comment count, re-fetch if changed

**Benefits**:
- ✅ Single source of truth (actual data files)
- ✅ No duplicate timestamps
- ✅ Archive is self-describing
- ✅ Massive performance improvement (query YouTube API with date filters)
- ✅ Simpler codebase (remove sync_state_service.py)
- ✅ Can reconstruct state from archive at any time

**Example Performance Gain**:
Before:
```
# Channel with 10,000 videos, checking for new videos
1. Fetch metadata for all 10,000 videos (slow!)
2. Skip 9,995 in our code
3. Process 5 new ones
```

After:
```
# Query YouTube API directly
1. Fetch only videos published after 2026-01-24T16:48:00Z
2. Get back 5 videos (only the new ones!)
3. Process 5 new ones
```

**Testing**:
- Unit tests for TSVReader utilities
- Integration test: backup channel, verify only new videos fetched on second run
- Integration test: all-incremental mode updates social data for recent videos only
- Contract test: verify videos.tsv datetime format

**Migration**: Existing archives need videos.tsv regeneration to add datetime (backward compatible - can parse old date-only format and default to midnight UTC)
