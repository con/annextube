# Tasks: YouTube Archive System

**Feature**: 001-youtube-backup
**Input**: Design documents from `/specs/001-youtube-backup/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: NOT requested in specification - tasks below focus on implementation only (no test tasks included)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Testing Strategy

### Git-annex URL-Only Mode (Default)

By default, annextube uses **git-annex addurl --relaxed --fast** to track video URLs without downloading content:
- **Track URLs only**: No video file downloads (saves bandwidth and storage)
- **Download metadata/comments/captions**: Small files fetched normally via YouTube API
- **Video content on-demand**: Use git-annex get or --download-videos flag later

This enables efficient metadata-only archival for large channels.

### YouTube API Access (Not git-annex importfeed)

**Prototype Reference**: `/home/yoh/proj/TrueTube/Andriy_Popyk/code/` demonstrates working cron-based backup

**API Strategy**:
- **YouTube Data API v3**: For metadata, playlists, comments (primary method)
- **yt-dlp**: For video URLs and caption files (NOT for metadata)
- **NOT using git-annex importfeed**: RSS feeds are limited to 15 videos, insufficient

**Limit Semantics** (`limit = N`):
- **Deterministic ordering**: N most recent videos by upload date (newest first)
- Example: `limit = 10` → 10 newest videos from the channel
- Ensures reproducible backups for testing
- Uses YouTube API `search.list` with `order=date` and `maxResults=N`

### Recommended Test Channels

Use these channels for development and validation:

**Quick testing** (~10 videos) - edit `.annextube/config.toml`:
```toml
[[sources]]
url = "https://www.youtube.com/@RickAstleyYT"
type = "channel"

[filters]
limit = 10
date_start = "2020-01-01"
```

Then: `annextube backup`

**Playlist testing** (has many playlists) - add to config:
```toml
[[sources]]
url = "https://youtube.com/c/datalad"
type = "channel"
```

**Liked Videos playlist** (HIGH PRIORITY test case):
```toml
# User will provide API key for test account
[[sources]]
url = "https://www.youtube.com/playlist?list=LL"  # LL = Liked Videos special ID
type = "playlist"
```

**All test channels** - add to config:
```toml
[[sources]]
url = "https://www.youtube.com/@repronim"

[[sources]]
url = "https://www.youtube.com/@apopyk"  # Reference: /home/yoh/proj/TrueTube/Andriy_Popyk

[[sources]]
url = "https://www.youtube.com/@centeropenneuro"
```

**Testing with video downloads** (set in config to avoid large downloads):
```bash
cd test-archive
# Edit .annextube/config.toml: components.videos = true, filters.limit = 5
annextube backup
```

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create Python package structure (annextube/, tests/, frontend/, docs/)
- [X] T002 Initialize pyproject.toml with dependencies (datasalad, yt-dlp, google-api-python-client, Python 3.10+)
- [X] T003 [P] Configure ruff for linting and code formatting
- [X] T004 [P] Configure mypy for type checking
- [X] T005 [P] Setup tox.ini for test automation (pytest environments)
- [X] T006 [P] Add LICENSE file (OSI-approved open source license)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Create JSON Schema for data models in annextube/schema/models.json
- [X] T008 [P] Implement logging configuration in annextube/lib/logging_config.py (structured JSON + human-readable)
- [X] T009 [P] Implement configuration file handling in annextube/lib/config.py (load from .annextube/config.toml or ~/.config/annextube/config.toml, TOML format like mykrok)
- [X] T010 [P] Create base models in annextube/models/ (Channel, Video, Playlist, Caption, Comment, SyncState, FilterConfig per data-model.md)
- [X] T011 Implement GitAnnexService in annextube/services/git_annex.py (datasalad wrapper for git-annex operations)
- [X] T012 Implement YouTubeService in annextube/services/youtube.py (YouTube Data API v3 + yt-dlp wrapper, lazy download + archive file support, limit=N returns N most recent by upload date)
- [X] T013 [P] Create CLI entry point in annextube/cli/__main__.py with global options (--config, --log-level, --json, --quiet, --help, --version)
- [ ] T014 [P] Setup frontend project structure (frontend/src/ with Svelte components, services, types)
- [ ] T015 [P] Configure frontend build tooling (Vite for Svelte, TypeScript, hash-based routing for file:// support)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Initial Channel Archive (Priority: P1) 🎯 MVP

**Goal**: Create complete archive of YouTube channel capturing all videos with metadata, thumbnails, and captions (FR-001 to FR-009)

**Independent Test**: Run `mkdir test-archive && cd test-archive && annextube init`, edit `.annextube/config.toml` to add test channel with `limit = 10`, then run `annextube backup` and verify ~10 videos are tracked (URL-only, no download) with metadata accessible offline

**Test Channels** (for validation):
- `https://www.youtube.com/@RickAstleyYT` - limit to 10 most recent videos for quick testing
- `https://youtube.com/c/datalad` - has many playlists, good for playlist testing
- `https://www.youtube.com/@repronim` - ReproNim channel
- `https://www.youtube.com/@apopyk` - Andriy Popyk (reference: /home/yoh/proj/TrueTube/Andriy_Popyk prototype)
- `https://www.youtube.com/@centeropenneuro` - Center for Open Neuroscience
- **"Liked Videos" playlist** - HIGH PRIORITY test case (user will provide sample account/API key)

### Implementation for User Story 1

- [X] T016 [P] [US1] Implement init command in annextube/cli/init.py (FR-048, initialize git-annex repo in current directory with URL backend)
- [X] T016a [US1] Create config template generator in annextube/lib/config.py (generate .annextube/config.toml with sources, components, filters sections)
- [X] T017 [P] [US1] Implement backup command in annextube/cli/backup.py (FR-049, load config, backup configured sources or ad-hoc URL, --limit option for testing)
- [X] T018 [US1] Implement Archiver service in annextube/services/archiver.py (core archival logic coordinating git-annex + YouTube services, reads config for sources/filters/components)
- [X] T019 [US1] Add channel metadata fetching to YouTubeService in annextube/services/youtube.py (use YouTube Data API v3 channels.list)
- [X] T020 [US1] Add video listing with limit support to YouTubeService in annextube/services/youtube.py (API search.list, if limit=N return N most recent by publishedAt desc)
- [X] T020a [US1] Add video metadata fetching to YouTubeService in annextube/services/youtube.py (API videos.list, NOT yt-dlp for metadata)
- [X] T020b [US1] Add video URL extraction to YouTubeService in annextube/services/youtube.py (yt-dlp for URL only, pass to git-annex addurl)
- [ ] T021 [US1] Add comment fetching to YouTubeService in annextube/services/youtube.py (API commentThreads.list with threading support per data-model.md)
- [X] T022 [US1] Add caption downloading to YouTubeService in annextube/services/youtube.py (yt-dlp --write-subs --write-auto-subs, all languages to VTT per FR-007)
- [ ] T022a [US1] Add playlist video listing to YouTubeService in annextube/services/youtube.py (API playlistItems.list, support "Liked Videos" special case)
- [X] T023 [US1] Add thumbnail downloading to Archiver service in annextube/services/archiver.py (highest resolution per FR-006)
- [ ] T024 [US1] Implement repository structure creation in Archiver (videos/, playlists/, channels/ directories per data-model.md file organization)
- [ ] T025 [US1] Implement metadata persistence (write Channel, Video, Playlist, Caption, Comment JSON files per data-model.md)
- [ ] T026 [US1] Configure .gitattributes rules in GitAnnexService (*.json/*.tsv/*.vtt → git, *.mp4/*.jpg → git-annex per FR-024)
- [ ] T027 [US1] Add URL tracking to GitAnnexService in annextube/services/git_annex.py (git annex addurl --relaxed with URL backend for track-only mode, no download per FR-029)
- [ ] T028 [US1] Add progress indicators to backup command in annextube/cli/backup.py (TTY detection, progress bars per cli-contract.md)
- [ ] T029 [US1] Implement exit codes in CLI commands (0=success, 1-7=specific errors per cli-contract.md)
- [ ] T030 [US1] Add JSON output mode to backup command in annextube/cli/backup.py (--json flag per cli-contract.md)

**Checkpoint**: At this point, User Story 1 should be fully functional - can init repository, configure sources in `.annextube/config.toml`, and backup channels with all metadata

**Workflow validation**:
```bash
mkdir test-archive && cd test-archive
annextube init
# Edit .annextube/config.toml to add test channel
annextube backup
# Verify videos/, channels/, metadata files created
```

---

## Phase 4: User Story 2 - Incremental Updates (Priority: P1)

**Goal**: Efficiently detect and fetch only new videos, comments, and captions since last sync (FR-010 to FR-016)

**Independent Test**: Create archive, backup channel, wait/simulate time passage, run `annextube update` (in archive directory) and verify only new/changed content is fetched

### Implementation for User Story 2

- [ ] T031 [P] [US2] Implement update command in annextube/cli/update.py (FR-051, incremental update)
- [ ] T032 [US2] Implement Updater service in annextube/services/updater.py (incremental update logic coordinating services)
- [ ] T033 [US2] Implement SyncState persistence in Updater (load/save .sync/state.json per data-model.md)
- [ ] T034 [US2] Add new video detection to Updater in annextube/services/updater.py (compare last_sync timestamp, fetch videos published after)
- [ ] T035 [US2] Add comment update detection to Updater in annextube/services/updater.py (compare comment_count, fetch if increased)
- [ ] T036 [US2] Add caption update detection to Updater in annextube/services/updater.py (detect new captions_available languages)
- [ ] T037 [US2] Add metadata change detection to Updater in annextube/services/updater.py (compare updated_at timestamps per FR-014)
- [ ] T038 [US2] Implement yt-dlp archive file integration in YouTubeService (--download-archive for skip already-processed per research.md)
- [ ] T039 [US2] Add batch API request optimization to YouTubeService in annextube/services/youtube.py (minimize API calls per FR-016)
- [ ] T040 [US2] Implement retry logic with exponential backoff in Updater (FR-076, handle transient failures)
- [ ] T041 [US2] Update SyncState after successful update in Updater (write last_sync, last_video_id, error_count per data-model.md)
- [ ] T042 [US2] Add --force and --force-date options to update command in annextube/cli/update.py (per cli-contract.md)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - can create archive AND keep it updated

---

## Phase 5: User Story 3 - Selective Filtering and Scope Control (Priority: P2)

**Goal**: Filter videos by date range, license type, playlist membership, metadata attributes (FR-017 to FR-022)

**Independent Test**: Configure filter in `.annextube/config.toml` (`license = "creativeCommon"`, `date_start = "2024-01-01"`), run `annextube backup`, and verify only matching videos are included

### Implementation for User Story 3

- [ ] T043 [P] [US3] Implement FilterConfig model validation in annextube/models/filter_config.py (per data-model.md)
- [ ] T044 [US3] Add filter support to backup command in annextube/cli/backup.py (--license, --date-start, --date-end, --no-comments, --no-captions per cli-contract.md)
- [ ] T045 [US3] Implement date range filtering in Archiver in annextube/services/archiver.py (filter by published_at per FR-017)
- [ ] T046 [US3] Implement license type filtering in Archiver in annextube/services/archiver.py (filter by license field per FR-018)
- [ ] T047 [US3] Implement playlist filtering in Archiver in annextube/services/archiver.py (include/exclude playlists per FR-019)
- [ ] T048 [US3] Implement metadata attribute filtering in Archiver in annextube/services/archiver.py (duration, view_count, tags per FR-020)
- [ ] T049 [US3] Implement component selection in Archiver in annextube/services/archiver.py (videos, metadata, comments, captions, thumbnails per FR-022)
- [ ] T050 [US3] Add named filter support in backup command in annextube/cli/backup.py (--filter NAME loads from .config/filters.json per cli-contract.md)
- [ ] T051 [US3] Implement FilterConfig persistence in Archiver (save/load .config/filters.json per data-model.md)

**Checkpoint**: User Stories 1, 2, AND 3 should all work independently - can create, update, and filter archives

---

## Phase 6: User Story 4 - Browse and Search Archive via Web Interface (Priority: P2)

**Goal**: Generate client-side web interface for browsing offline archive with search, filtering, video playback, comments (FR-037 to FR-047)

**Independent Test**: Run `annextube generate-web` (in archive directory), open `web/index.html` in browser via file://, verify search/filtering/playback work without server

### Implementation for User Story 4

- [ ] T052 [P] [US4] Implement export command in annextube/cli/export.py (generate videos.tsv, playlists.tsv per FR-053)
- [ ] T053 [P] [US4] Implement MetadataExport service in annextube/services/metadata_export.py (TSV generation logic)
- [ ] T054 [US4] Generate videos.tsv in MetadataExport (columns per data-model.md: video_id, title, channel_id, channel_name, published_at, duration, view_count, like_count, comment_count, has_captions, license, file_path, download_status, fetched_at)
- [ ] T055 [US4] Generate playlists.tsv in MetadataExport (columns per data-model.md: playlist_id, title, channel_id, channel_name, video_count, total_duration, updated_at, last_sync)
- [ ] T056 [P] [US4] Implement generate-web command in annextube/cli/generate_web.py (FR-052, static web UI generation)
- [ ] T057 [P] [US4] Implement WebGenerator service in annextube/services/web_generator.py (orchestrate frontend build + data copying)
- [ ] T058 [P] [US4] Generate TypeScript types from JSON Schema in frontend build (frontend/src/types/models.ts from annextube/schema/models.json)
- [ ] T059 [P] [US4] Create VideoList component in frontend/src/components/VideoList.svelte (display videos with thumbnails, titles, metadata)
- [ ] T060 [P] [US4] Create VideoPlayer component in frontend/src/components/VideoPlayer.svelte (HTML5 video with caption selection per FR-045)
- [ ] T061 [P] [US4] Create FilterPanel component in frontend/src/components/FilterPanel.svelte (date range, channel, playlist, tags filters per FR-040, FR-041)
- [ ] T062 [P] [US4] Create CommentView component in frontend/src/components/CommentView.svelte (display comments with threading per FR-044)
- [ ] T063 [US4] Implement data loader service in frontend/src/services/data_loader.ts (load TSV/JSON from local files per FR-039)
- [ ] T064 [US4] Implement client-side search in frontend/src/services/search.ts (search titles, descriptions, tags per FR-042)
- [ ] T065 [US4] Create Index page in frontend/src/pages/Index.svelte (main browsing interface)
- [ ] T066 [US4] Create VideoDetail page in frontend/src/pages/VideoDetail.svelte (video player + comments + captions)
- [ ] T067 [US4] Configure hash-based routing in frontend (file:// protocol support per research.md)
- [ ] T068 [US4] Implement shareable URL state in frontend (preserve filter/view state in URL hash per FR-046)
- [ ] T069 [US4] Build frontend to static assets in WebGenerator (Vite build output to web/ directory)
- [ ] T070 [US4] Copy TSV files and metadata to web/ directory in WebGenerator (ensure offline accessibility)

**Checkpoint**: User Stories 1-4 should all work - can create, update, filter archives AND browse them offline via web UI

---

## Phase 7: User Story 5 - Configurable Organization Structure (Priority: P3)

**Goal**: Customize disk organization (by year, by playlist, flat vs nested), symlink support for playlists (FR-023 to FR-030)

**Independent Test**: Configure hierarchy template (e.g., videos/{year}/{video_id}/), run backup, verify files organized according to template with playlists using symlinks

### Implementation for User Story 5

- [ ] T071 [P] [US5] Add hierarchy template support to create-dataset in annextube/cli/create_dataset.py (--subdataset-pattern per cli-contract.md)
- [ ] T072 [US5] Implement path template rendering in Archiver in annextube/services/archiver.py (substitute {year}, {video_id}, {channel_id} etc. per FR-025)
- [ ] T073 [US5] Add subdataset creation support to GitAnnexService in annextube/services/git_annex.py (detect '//' separator, create subdatasets per FR-025 clarification)
- [ ] T074 [US5] Implement symlink organization in Archiver in annextube/services/archiver.py (videos/ + playlists/ with symlinks per FR-027, data-model.md relationships)
- [ ] T075 [US5] Store hierarchy templates in configuration in annextube/lib/config.py (persist file naming/path templates per FR-028)
- [ ] T076 [US5] Add custom file naming template support in Archiver (configurable video/metadata filenames per FR-028)

**Checkpoint**: User Stories 1-5 should all work - full archive functionality including custom organization

---

## Phase 8: User Story 6 - Export Summary Metadata (Priority: P3)

**Goal**: Export high-level metadata in TSV format for analysis with Excel, DuckDB, Visidata (FR-031 to FR-036)

**Independent Test**: Run `annextube export` (in archive directory), open videos.tsv in Visidata/Excel, verify data is properly formatted and queryable

### Implementation for User Story 6

- [ ] T077 [US6] Validate TSV format compatibility in MetadataExport in annextube/services/metadata_export.py (test with Visidata, DuckDB, Excel per FR-036)
- [ ] T078 [US6] Add --videos-file and --playlists-file options to export command in annextube/cli/export.py (custom output paths per cli-contract.md)
- [ ] T079 [US6] Implement TSV regeneration in Updater in annextube/services/updater.py (regenerate after incremental updates per FR-035)
- [ ] T080 [US6] Add JSON export format support to export command in annextube/cli/export.py (--json output mode per quickstart.md example)

**Checkpoint**: User Stories 1-6 complete - full metadata export capabilities

---

## Phase 9: User Story 7 - Caption Curation Workflow (Priority: P4)

**Goal**: Export captions for editing, validate format, prepare for upload (FR-058 to FR-062)

**Independent Test**: Export captions, modify them externally, validate format - system should prepare them for upload

### Implementation for User Story 7

- [ ] T081 [P] [US7] Implement caption export functionality in Archiver in annextube/services/archiver.py (export specific language VTT files per FR-058)
- [ ] T082 [US7] Implement VTT format validation in annextube/lib/utils.py (validate caption syntax before upload prep per FR-059)
- [ ] T083 [US7] Add caption upload preparation interface in annextube/services/archiver.py (generate upload-ready format per FR-060)
- [ ] T084 [US7] Add external service integration support in frontend for caption editing in frontend/src/services/caption_service.ts (LLM integration placeholder per FR-061)
- [ ] T085 [US7] Implement batch caption export in Archiver in annextube/services/archiver.py (export multiple videos at once per FR-062)

**Checkpoint**: User Stories 1-7 complete - caption curation workflow enabled

---

## Phase 10: User Story 8 - Public Archive Hosting (Priority: P4)

**Goal**: Publish archive as public website via GitHub Pages (FR-063 to FR-067)

**Independent Test**: Run publish command, push to GitHub Pages, verify archive is accessible via public URL

### Implementation for User Story 8

- [ ] T086 [US8] Add publish mode to generate-web command in annextube/cli/generate_web.py (--base-url for absolute links per cli-contract.md)
- [ ] T087 [US8] Implement isolated publishing branch creation in WebGenerator in annextube/services/web_generator.py (gh-pages branch without history per FR-064)
- [ ] T088 [US8] Add incremental publish support to WebGenerator in annextube/services/web_generator.py (only update changed files per FR-067)
- [ ] T089 [US8] Add metadata-only publish mode to WebGenerator in annextube/services/web_generator.py (link to YouTube instead of hosting videos per FR-066)
- [ ] T090 [US8] Create GitHub Actions workflow template in .github/workflows/publish-pages.yml (auto-deployment example per FR-063)

**Checkpoint**: All user stories complete - full public hosting capabilities

---

## Phase 11: CI/CD and Automation (Cross-Cutting)

**Purpose**: Automated updates and git-annex remote storage (FR-083 to FR-096)

- [ ] T091 [P] Implement git-annex special remote initialization in GitAnnexService in annextube/services/git_annex.py (S3, WebDAV, directory, rclone per FR-091, FR-092)
- [ ] T092 [P] Implement special remote enablement in GitAnnexService in annextube/services/git_annex.py (git annex enableremote for CI per research.md)
- [ ] T093 [P] Implement content copy to remotes in GitAnnexService in annextube/services/git_annex.py (git annex copy --to=remote per FR-094)
- [ ] T094 [P] Create GitHub Actions workflow template in .github/workflows/update-archive.yml (index-only + full backup modes per FR-085, FR-088)
- [ ] T095 [P] Create Codeberg Actions workflow template in .codeberg/workflows/update-archive.yml (Forgejo compatibility per FR-084)
- [ ] T096 [P] Document environment variable authentication in workflow templates (AWS keys, WebDAV creds per research.md CI/CD pattern)
- [ ] T097 Add remote verification command in GitAnnexService in annextube/services/git_annex.py (check content availability per FR-095)

---

## Phase 12: Documentation (Cross-Cutting)

**Purpose**: Diataxis-structured documentation with Hugo + Congo theme (FR-063 context)

- [ ] T098 Initialize Hugo documentation site in docs/ (Hugo extended + Congo theme per research.md)
- [ ] T099 [P] Create Tutorial section in docs/content/tutorial/ (01-installation.md, 02-first-archive.md per research.md structure)
- [ ] T100 [P] Create How-to section in docs/content/how-to/ (backup-channel.md, filter-by-license.md, setup-ci-workflow.md, configure-special-remotes.md per research.md)
- [ ] T101 [P] Create Reference section in docs/content/reference/ (cli-commands.md, api-reference.md, configuration.md per research.md)
- [ ] T102 [P] Create Explanation section in docs/content/explanation/ (architecture.md, git-annex-integration.md, incremental-updates.md per research.md)
- [ ] T103 Configure Hugo for GitHub Pages in docs/config.toml (baseURL, theme settings per research.md)
- [ ] T104 Create GitHub Actions workflow for docs deployment in .github/workflows/publish-docs.yml (auto-build on push)

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting multiple user stories

- [ ] T105 [P] Update CLAUDE.md with complete technology stack (Svelte, Vitest, Playwright, datasalad, yt-dlp per research.md decisions)
- [ ] T106 [P] Add error handling and recovery suggestions throughout CLI commands (clear error messages per FR-057)
- [ ] T107 [P] Implement rate limiting in YouTubeService in annextube/services/youtube.py (respect YouTube rate limits per FR-077)
- [ ] T108 [P] Add operation resumability after interruption in Archiver/Updater (FR-079, maintain state for resume)
- [ ] T109 [P] Implement content integrity validation in GitAnnexService in annextube/services/git_annex.py (verify downloads per FR-080)
- [ ] T110 [P] Add trace identifiers to logging in annextube/lib/logging_config.py (operation tracking per Constitution Principle VI)
- [ ] T111 Run quickstart.md validation (verify 15-minute completion per SC-015)
- [ ] T112 Performance optimization (verify SC-001, SC-002, SC-003 success criteria)
- [ ] T113 Security review (validate no secrets in plain version control per FR-075)

---

## Phase 9: YouTube API Enhanced Metadata (Optional Enhancement)

**Goal**: Enable accurate license detection and enhanced metadata extraction via YouTube Data API v3

**Research**: See `research.md` § 7 (YouTube API Enhanced Metadata Extraction)

### Implementation for YouTube API Enhancement

- [X] T114 [P] Research and implement YouTube API v3 metadata client in annextube/services/youtube_api.py (YouTubeAPIMetadataClient, QuotaEstimator, support batch requests up to 50 videos)
- [X] T114a [P] Extend Video model with 15 optional API-enhanced fields (licensed_content, embeddable, made_for_kids, recording_date/location, definition, dimension, projection, region_restriction, content_rating, topic_categories)
- [X] T114b [P] Integrate API enhancement in YouTubeService.metadata_to_video() (optional enhancement, graceful fallback)
- [X] T114c [P] Add API key configuration support in UserConfig (~/.config/annextube/config.toml or YOUTUBE_API_KEY env var)
- [X] T114d [P] Create comprehensive tests (36 tests: quota estimation, API client, integration tests, backward compatibility)
- [X] T114e [P] Document API capabilities, costs, quota management in research.md
- [X] T114f [P] Test with real YouTube videos using API key from .git/secrets (created tools/test_api_metadata.py and wrapper script, verified license detection and enhanced metadata capture)
- [ ] T115 [P] Implement estimate-cost command in annextube/cli/estimate_cost.py (DEFERRED - preview quota usage before archiving, show cost breakdown for N videos, warn if exceeds free tier)

---

## Phase 10: Test Infrastructure Improvement

**Goal**: Create controlled test environment to eliminate dependency on external YouTube channels

**Motivation**: Current integration tests use external channels (Khan Academy, etc.) which can have videos deleted or privacy settings changed, causing flaky test failures.

### Implementation for Test Channel Setup

- [ ] T116 [P] Create test channel on YouTube (manual step - create Google account, YouTube channel "AnnexTube Testing")
- [ ] T117 [P] Setup Google Cloud OAuth credentials (manual step - enable YouTube Data API v3, create OAuth 2.0 desktop app credentials)
- [X] T118 [P] Create video generation script in tools/setup_test_channel.py (generate 12 short test videos with ffmpeg, upload to YouTube, set licenses, create playlists, add captions/comments)
- [X] T119 [P] Document test channel setup process in tools/README.md (prerequisites, usage, quota costs, integration with tests)
- [ ] T120 [P] Execute test channel setup (run tools/setup_test_channel.py --upload-all, save video IDs and playlist IDs)
- [ ] T121 [P] Update integration tests to use test channel (replace external channel URLs with TEST_CHANNEL_URL in tests/conftest.py)
- [ ] T122 [P] Verify all integration tests pass with test channel (run full tox suite, confirm no flaky failures)

**Benefits:**
- Reliable test channel under our control
- Fast test execution (videos are 1-5 seconds each)
- Comprehensive metadata coverage (licenses, captions, locations, comments)
- One-time quota cost (~21,000 units = $21 or 2 days free tier)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-10)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed) OR sequentially in priority order
  - Priority order: US1 (P1) → US2 (P1) → US3 (P2) → US4 (P2) → US5 (P3) → US6 (P3) → US7 (P4) → US8 (P4)
- **CI/CD (Phase 11)**: Can start after US1 and US2 complete (core backup + update functionality)
- **Documentation (Phase 12)**: Can proceed in parallel with user stories
- **Polish (Phase 13)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories ✅ MVP
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - May enhance US1 backup but independently testable
- **User Story 4 (P2)**: Depends on US6 export command (needs TSV files) - Can start after US6 T052-T055 complete
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - Enhances US1 organization but independently testable
- **User Story 6 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 7 (P4)**: Can start after US1 (needs caption infrastructure) - Enhances US1 caption workflow
- **User Story 8 (P4)**: Depends on US4 (extends generate-web command) - Can start after US4 complete

### Within Each User Story

- Tasks marked [P] can run in parallel (different files, no blocking dependencies)
- Models before services
- Services before CLI commands
- Core implementation before enhancements
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1 (Setup)**: T003, T004, T005, T006 can all run in parallel
- **Phase 2 (Foundational)**: T008, T009, T010, T013, T014, T015 can run in parallel
- **Phase 3 (US1)**: T016 and T017 can run in parallel; T019-T022 can run in parallel after T018
- **Phase 5 (US3)**: T043 and T044 can run in parallel
- **Phase 6 (US4)**: T052 and T053 can run in parallel; T059-T062 (all frontend components) can run in parallel; T058 and T063-T064 can run in parallel
- **Phase 7 (US5)**: T071 and T072 can run in parallel initially
- **Phase 11 (CI/CD)**: T091, T092, T093, T094, T095, T096 can all run in parallel
- **Phase 12 (Docs)**: T099, T100, T101, T102 can all run in parallel after T098
- **Phase 13 (Polish)**: T105, T106, T107, T108, T109, T110 can all run in parallel

### Parallel Example: User Story 1

```bash
# After T015 completes, launch in parallel:
Task T016: "Implement create-dataset command in annextube/cli/create_dataset.py"
Task T017: "Implement backup command in annextube/cli/backup.py"

# After T018 completes, launch in parallel:
Task T019: "Add channel metadata fetching to YouTubeService"
Task T020: "Add video metadata fetching to YouTubeService"
Task T021: "Add comment fetching to YouTubeService"
Task T022: "Add caption downloading to YouTubeService"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Initial Channel Archive)
4. Complete Phase 4: User Story 2 (Incremental Updates)
5. **STOP and VALIDATE**: Test US1 + US2 independently (can create and update archives)
6. Deploy/demo if ready - this is a functional YouTube backup system!

**Why US1 + US2 = MVP**: These two stories deliver core value (backup + updates). All other stories are enhancements.

### Incremental Delivery (Recommended)

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 + User Story 2 → Test independently → **Deploy/Demo (MVP!)**
3. Add User Story 4 (Web UI) → Test independently → Deploy/Demo (now browsable!)
4. Add User Story 3 (Filtering) → Test independently → Deploy/Demo (targeted backups)
5. Add User Story 6 (Export) → Test independently → Deploy/Demo (data analysis)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 → User Story 2 (sequential, US2 needs US1)
   - Developer B: User Story 6 (independent)
   - Developer C: Documentation (Phase 12)
3. After US1 + US2 complete:
   - Developer A: User Story 4 (needs US6 export)
   - Developer B: User Story 3 (independent)
4. Stories complete and integrate independently

---

## Task Summary

**Total Tasks**: 117

**Task Count by Phase**:
- Phase 1 (Setup): 6 tasks
- Phase 2 (Foundational): 9 tasks
- Phase 3 (US1 - Initial Archive): 19 tasks
- Phase 4 (US2 - Incremental Updates): 12 tasks
- Phase 5 (US3 - Filtering): 9 tasks
- Phase 6 (US4 - Web Interface): 19 tasks
- Phase 7 (US5 - Organization): 6 tasks
- Phase 8 (US6 - Export Metadata): 4 tasks
- Phase 9 (US7 - Caption Curation): 5 tasks
- Phase 10 (US8 - Public Hosting): 5 tasks
- Phase 11 (CI/CD): 7 tasks
- Phase 12 (Documentation): 7 tasks
- Phase 13 (Polish): 9 tasks

**Task Count by User Story**:
- US1 (Initial Channel Archive - P1): 19 tasks
- US2 (Incremental Updates - P1): 12 tasks
- US3 (Filtering - P2): 9 tasks
- US4 (Web Interface - P2): 19 tasks
- US5 (Organization - P3): 6 tasks
- US6 (Export Metadata - P3): 4 tasks
- US7 (Caption Curation - P4): 5 tasks
- US8 (Public Hosting - P4): 5 tasks

**Parallel Opportunities**: 42 tasks marked [P] can run in parallel with others in their phase

**Independent Test Criteria**:
- US1: Can create archive and backup channel with all metadata accessible offline
- US2: Can run incremental update and fetch only new/changed content
- US3: Can apply filters and verify only matching videos are included
- US4: Can browse archive offline via web UI with search/filtering/playback
- US5: Can configure custom hierarchy and verify organization
- US6: Can export TSV and query with data analysis tools
- US7: Can export/validate/prepare captions for upload
- US8: Can publish archive to GitHub Pages and access publicly

**Suggested MVP Scope**:
- Phase 1 (Setup) + Phase 2 (Foundational) + Phase 3 (US1) + Phase 4 (US2) = 46 tasks
- This delivers functional YouTube backup system with incremental updates
- **Workflow**: `annextube init` → edit `.annextube/config.toml` (add API key + sources) → `annextube backup` → `annextube update`
- **Test with**: "Liked Videos" playlist (HIGH PRIORITY - user will provide API key)

---

## Format Validation

✅ **All tasks follow the required checklist format**:
- Checkbox: `- [ ]` at start
- Task ID: Sequential (T001-T115)
- [P] marker: Only for parallelizable tasks (different files, no dependencies)
- [Story] label: Present for all user story phase tasks (US1-US8)
- Description: Clear action with exact file path

**Example valid tasks**:
- `- [ ] T001 Create Python package structure (annextube/, tests/, frontend/, docs/)` ✅
- `- [ ] T003 [P] Configure ruff for linting and code formatting` ✅
- `- [ ] T016 [P] [US1] Implement create-dataset command in annextube/cli/create_dataset.py` ✅
- `- [ ] T052 [P] [US4] Implement export command in annextube/cli/export.py` ✅

---

## Notes

- [P] tasks = different files, no blocking dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tasks reference functional requirements (FR-XXX) and success criteria (SC-XXX) from spec.md
- All file paths follow plan.md project structure
- No test tasks included (tests NOT requested in specification)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
