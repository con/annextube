# Tasks: YouTube Archive System

**Feature**: 001-youtube-backup
**Input**: Design documents from `/specs/001-youtube-backup/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are written alongside implementation per Constitution III (TDD). Test tasks are implicit in each implementation task rather than tracked separately. Backend tests live in `tests/`, frontend tests in `frontend/tests/`.

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
- [X] T014 [P] Setup frontend project structure (frontend/src/ with Svelte components, services, types)
- [X] T015 [P] Configure frontend build tooling (Vite for Svelte, TypeScript, hash-based routing for file:// support)

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
- [X] T021 [US1] Add comment fetching to YouTubeService in annextube/services/youtube.py (implemented in youtube_api.py via YouTube Data API v3)
- [X] T022 [US1] Add caption downloading to YouTubeService in annextube/services/youtube.py (yt-dlp --write-subs --write-auto-subs, all languages to VTT per FR-007)
- [X] T022a [US1] Add playlist video listing to YouTubeService in annextube/services/youtube.py (API playlistItems.list, support "Liked Videos" special case)
- [X] T023 [US1] Add thumbnail downloading to Archiver service in annextube/services/archiver.py (highest resolution per FR-006)
- [X] T024 [US1] Implement repository structure creation in Archiver (videos/, playlists/ directories created by archiver.py)
- [X] T025 [US1] Implement metadata persistence (write metadata.json, comments.json, captions.tsv per video)
- [X] T026 [US1] Configure .gitattributes rules in GitAnnexService (configure_gitattributes() with size/type-based rules per FR-024)
- [X] T027 [US1] Add URL tracking to GitAnnexService in annextube/services/git_annex.py (git annex addurl --relaxed --fast per FR-029)
- [X] T028 [US1] Add progress indicators to backup command in annextube/cli/backup.py (per-source progress in backup output)
- [X] T029 [US1] Implement exit codes in CLI commands (0=success, non-zero for errors via click context)
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

- [X] T031 [P] [US2] Implement update modes in backup command (FR-051; `backup --update` with videos-incremental, all-incremental, social, all-force modes — no separate update command)
- [X] T032 [US2] ~~Implement Updater service~~ OBSOLETE — update logic merged into Archiver (archiver.py handles all update modes)
- [X] T033 [US2] ~~Implement SyncState persistence~~ OBSOLETE — sync state derived from actual data files (videos.tsv timestamps) per plan.md TODO 2
- [X] T034 [US2] Add new video detection to Archiver (compare published_at from videos.tsv, fetch only newer videos)
- [X] T035 [US2] Add comment update detection in Archiver (compare comment counts, re-fetch if changed)
- [X] T036 [US2] Add caption update detection in Archiver (detect new/changed captions)
- [X] T037 [US2] Add metadata change detection in Archiver (timestamp filtering via _filter_timestamp_only_changes in git_annex.py)
- [X] T038 [US2] Implement yt-dlp archive file integration in YouTubeService (skip already-processed videos)
- [ ] T039 [US2] Add batch API request optimization to YouTubeService in annextube/services/youtube.py (minimize API calls per FR-016)
- [X] T040 [US2] Implement retry logic with exponential backoff (ytdlp_ratelimit.py + quota_manager.py)
- [X] T041 [US2] ~~Update SyncState~~ OBSOLETE — state derived from data files; timestamp-only commit filtering in git_annex.py
- [X] T042 [US2] Add --force and date range options to backup command (--date-start, --date-end, --limit, --update modes)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - can create archive AND keep it updated

---

## Phase 5: User Story 3 - Selective Filtering and Scope Control (Priority: P2)

**Goal**: Filter videos by date range, license type, playlist membership, metadata attributes (FR-017 to FR-022)

**Independent Test**: Configure filter in `.annextube/config.toml` (`license = "creativeCommon"`, `date_start = "2024-01-01"`), run `annextube backup`, and verify only matching videos are included

### Implementation for User Story 3

- [X] T043 [P] [US3] Implement filter configuration in config.py (filters section in config.toml: limit, date_start, date_end, components)
- [X] T044 [US3] Add filter support to backup command (--limit, --date-start, --date-end, --no-comments, --no-captions, --no-thumbnails, --no-videos)
- [X] T045 [US3] Implement date range filtering in Archiver (filter by published_at via date_start/date_end config)
- [ ] T046 [US3] Implement license type filtering in Archiver in annextube/services/archiver.py (filter by license field per FR-018)
- [X] T047 [US3] Implement playlist filtering in Archiver (include_playlists config, playlist-specific backup)
- [ ] T048 [US3] Implement metadata attribute filtering in Archiver in annextube/services/archiver.py (duration, view_count, tags per FR-020)
- [X] T049 [US3] Implement component selection in Archiver (videos, metadata, comments, captions, thumbnails toggleable via config)
- [ ] T050 [US3] Add named filter support in backup command in annextube/cli/backup.py (--filter NAME loads from .config/filters.json per cli-contract.md)
- [ ] T051 [US3] Implement FilterConfig persistence in Archiver (save/load .config/filters.json per data-model.md)

**Checkpoint**: User Stories 1, 2, AND 3 should all work independently - can create, update, and filter archives

---

## Phase 6: User Story 4 - Browse and Search Archive via Web Interface (Priority: P2)

**Goal**: Generate client-side web interface for browsing offline archive with search, filtering, video playback, comments (FR-037 to FR-047)

**Independent Test**: Run `annextube generate-web` (in archive directory), open `web/index.html` in browser via file://, verify search/filtering/playback work without server

### Implementation for User Story 4

- [X] T052 [P] [US4] Implement export command in annextube/cli/export.py (generate videos.tsv, playlists.tsv)
- [X] T053 [P] [US4] Implement ExportService in annextube/services/export.py (TSV generation + channel.json)
- [X] T054 [US4] Generate videos.tsv in ExportService (video_id, title, channel, published_at, duration, views, etc.)
- [X] T055 [US4] Generate playlists.tsv in ExportService (playlist_id, title, video_count, total_duration, etc.)
- [X] T056 [P] [US4] Implement generate-web command in annextube/cli/generate_web.py (static web UI generation + search index)
- [X] T057 [P] [US4] Web generation logic in generate_web.py (frontend build + data copying + search index build)
- [X] T058 [P] [US4] Generate TypeScript types from JSON Schema (frontend/src/types/models.ts auto-generated)
- [X] T059 [P] [US4] Create VideoList + VideoCard components (frontend/src/components/)
- [X] T060 [P] [US4] Create VideoPlayer component (frontend/src/components/VideoPlayer.svelte)
- [X] T061 [P] [US4] Create FilterPanel component (frontend/src/components/FilterPanel.svelte)
- [X] T062 [P] [US4] Create CommentView component (frontend/src/components/CommentView.svelte)
- [X] T063 [US4] Implement data loader service (frontend/src/services/data-loader.ts)
- [X] T064 [US4] Implement client-side search (frontend/src/services/search.ts + pagefind.ts for full-text caption search)
- [X] T065 [US4] Create Index/App page (frontend/src/App.svelte as main browsing interface)
- [X] T066 [US4] Create VideoDetail page (frontend/src/components/VideoDetail.svelte)
- [X] T067 [US4] Configure hash-based routing (frontend/src/services/router.ts, file:// protocol works)
- [X] T068 [US4] Implement shareable URL state (frontend/src/services/url-state.ts)
- [X] T069 [US4] Build frontend to static assets (Vite build outputs to web/ directory, included in sdist)
- [X] T070 [US4] Copy TSV files and metadata to web/ directory (generate-web handles this)

**Checkpoint**: User Stories 1-4 should all work - can create, update, filter archives AND browse them offline via web UI

---

## Phase 7: User Story 5 - Configurable Organization Structure (Priority: P3)

**Goal**: Customize disk organization (by year, by playlist, flat vs nested), symlink support for playlists (FR-023 to FR-030)

**Independent Test**: Configure hierarchy template (e.g., videos/{year}/{video_id}/), run backup, verify files organized according to template with playlists using symlinks

### Implementation for User Story 5

- [ ] T071 [P] [US5] Add hierarchy template support to init command (--subdataset-pattern per cli-contract.md)
- [X] T072 [US5] Implement date-based path hierarchy in Archiver (videos/{year}/{month}/{title}_{video_id}/ structure)
- [ ] T073 [US5] Add subdataset creation support to GitAnnexService (detect '//' separator, create subdatasets per FR-025)
- [X] T074 [US5] Implement symlink organization in Archiver (playlists/ with zero-padded symlinks: NNNN_video_path → ../../videos/)
- [ ] T075 [US5] Store hierarchy templates in configuration in annextube/lib/config.py (persist file naming/path templates per FR-028)
- [ ] T076 [US5] Add custom file naming template support in Archiver (configurable video/metadata filenames per FR-028)

**Checkpoint**: User Stories 1-5 should all work - full archive functionality including custom organization

---

## Phase 8: User Story 6 - Export Summary Metadata (Priority: P3)

**Goal**: Export high-level metadata in TSV format for analysis with Excel, DuckDB, Visidata (FR-031 to FR-036)

**Independent Test**: Run `annextube export` (in archive directory), open videos.tsv in Visidata/Excel, verify data is properly formatted and queryable

### Implementation for User Story 6

- [X] T077 [US6] TSV format is compatible with Visidata, DuckDB, Excel (tsv_utils.py handles escaping)
- [ ] T078 [US6] Add --videos-file and --playlists-file options to export command in annextube/cli/export.py (custom output paths)
- [X] T079 [US6] TSV regeneration happens automatically during backup (export.py called by Archiver after backup)
- [ ] T080 [US6] Add JSON export format support to export command in annextube/cli/export.py (--json output mode)

**Checkpoint**: User Stories 1-6 complete - full metadata export capabilities

---

## Phase 9: User Story 7 - Caption Curation Workflow (Priority: P4)

**Goal**: Export captions for editing, validate format, prepare for upload (FR-058 to FR-062)

**Independent Test**: Export captions, modify them externally, validate format - system should prepare them for upload

### Implementation for User Story 7

- [X] T081 [P] [US7] Implement caption curation pipeline in annextube/services/caption_curator.py (glossary-based correction, VTT parsing/generation)
- [X] T082 [US7] Implement VTT parsing and validation (parse_vtt in search_index.py, VTT generation in caption_curator.py)
- [ ] T083 [US7] Add caption upload preparation interface (generate upload-ready format per FR-060)
- [X] T084 [US7] Add LLM integration for caption correction (llm_corrector.py using Claude API)
- [X] T085 [US7] Implement batch caption curation via CLI (curate-captions command processes multiple videos)

**Checkpoint**: User Stories 1-7 complete - caption curation workflow enabled

---

## Phase 10: User Story 8 - Public Archive Hosting (Priority: P4)

**Goal**: Publish archive as public website via GitHub Pages (FR-063 to FR-067)

**Independent Test**: Run publish command, push to GitHub Pages, verify archive is accessible via public URL

### Implementation for User Story 8

- [X] T086 [US8] Implement prepare-ghpages command in annextube/cli/prepare_ghpages.py (restructure files for GitHub Pages hosting)
- [ ] T087 [US8] Implement isolated publishing branch creation (gh-pages branch without history per FR-064)
- [ ] T088 [US8] Add incremental publish support (only update changed files per FR-067)
- [X] T089 [US8] Metadata-only publish mode works by default (videos are git-annex symlinks, web UI links to YouTube)
- [ ] T090 [US8] Create GitHub Actions workflow template in .github/workflows/publish-pages.yml (auto-deployment example)

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

- [X] T105 [P] Update CLAUDE.md with complete technology stack (Svelte, Vitest, Playwright, datasalad, yt-dlp, DataLad)
- [X] T106 [P] Add error handling and recovery suggestions (format_subprocess_error in error_utils.py, error summary in backup output)
- [X] T107 [P] Implement rate limiting (ytdlp_ratelimit.py for yt-dlp, quota_manager.py for YouTube API v3)
- [X] T108 [P] Add operation resumability (backup resumes from last processed video, checkpoint commits per batch)
- [ ] T109 [P] Implement content integrity validation in GitAnnexService in annextube/services/git_annex.py (verify downloads per FR-080)
- [ ] T110 [P] Add trace identifiers to logging in annextube/lib/logging_config.py (operation tracking per Constitution Principle VI)
- [ ] T111 Run quickstart.md validation (verify 15-minute completion per SC-015)
- [ ] T112 Performance optimization (verify SC-001, SC-002, SC-003 success criteria)
- [ ] T113 Security review (validate no secrets in plain version control per FR-075)
- [X] T123 [P] Add duplication detection to CI in tox.ini (Constitution VIII: enforce <3% threshold; jscpd via npx; `tox -e duplication` calling tools/check-duplication.sh; current: 0.66%)
- [X] T124 [P] Add accessibility testing to Playwright E2E suite in frontend/tests/e2e/ (Constitution IV: WCAG 2.1 AA compliance; integrate axe-core via @axe-core/playwright; test archive-workflow pages for a11y violations)
- [X] T125 [P] DRY: Extract shared `_track_api_call`/`get_quota_summary` into a `QuotaTracker` mixin or base class in annextube/services/youtube_api.py (duplicated between `YouTubeCommentService` and `YouTubeAPIMetadataClient`, 12 lines)
- [X] T126 [P] DRY: Extract shared video metadata field construction (`video_id`, `title`, `channel`, `published`) into a helper in annextube/services/git_annex.py (duplicated at lines 732-737 and 802-807, 5 lines)
- [X] T127 [P] DRY: Extract shared curate-and-write loop (load corrections → parse VTT → curate → report → write → LLM corrections) into a helper function in annextube/cli/curate_captions.py (duplicated between `curate_captions` and `curate_video` commands, two clones: 12+21 lines)
- [X] T128 [P] DRY: Extract shared pagefind-import-check + `build_caption_index` invocation + stats reporting into a helper in annextube/cli/build_search_index.py or a shared module (duplicated between `build_search_index.py` and `generate_web.py`, 25 lines)
- [X] T129 [P] DRY: Extract shared TSV-to-playlist loading (fetch TSV → parse → map → load metadata) into a helper in frontend/src/services/data-loader.ts (duplicated between `loadPlaylists` and `loadChannelPlaylists`, 14 lines)
- [X] T130 Enforce zero-tolerance duplication policy: set threshold to 0 in .jscpd.json so any detected clone fails CI unless suppressed with `jscpd:ignore` pragma; update tools/check-duplication.sh exit code handling if needed (depends on T125-T129)

---

## Phase 14: YouTube API Enhanced Metadata (Optional Enhancement)

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

## Phase 15: Test Infrastructure Improvement

**Goal**: Create controlled test environment to eliminate dependency on external YouTube channels

**Motivation**: Current integration tests use external channels (Khan Academy, etc.) which can have videos deleted or privacy settings changed, causing flaky test failures.

### Implementation for Test Channel Setup

- [X] T116 [P] Create test channel on YouTube (COMPLETED - created channel UCHpuDwi3IorJ_Uez2e7pqHA "AnnexTube Test Channel")
- [X] T117 [P] Setup Google Cloud OAuth credentials (COMPLETED - used credentials from .git/oauth-secret.json)
- [X] T118 [P] Create video generation script in tools/setup_test_channel.py (generate 12 short test videos with ffmpeg, upload to YouTube, set licenses, create playlists, add captions/comments)
- [X] T119 [P] Document test channel setup process in tools/README.md (prerequisites, usage, quota costs, integration with tests)
- [X] T120 [P] Execute test channel setup (COMPLETED - uploaded 10 videos with different licenses, captions, GPS metadata; created 5 playlists with strategic overlaps)
- [X] T121 [P] Update integration tests to use test channel (COMPLETED - updated test_api_enhanced_metadata.py, test_comprehensive_backup.py, test_incremental_backup.py to use test channel instead of external channels)
- [X] T122 [P] Verify all integration tests pass with test channel (COMPLETED - all 5 previously failing tests now pass, no flaky failures)

**Benefits:**
- Reliable test channel under our control
- Fast test execution (videos are 1-5 seconds each)
- Comprehensive metadata coverage (licenses, captions, locations, comments)
- One-time quota cost (~21,000 units = $21 or 2 days free tier)

**Delivered:**
- Test channel: https://www.youtube.com/channel/UCHpuDwi3IorJ_Uez2e7pqHA
- 10 videos (4 standard license, 6 Creative Commons)
- 5 playlists with strategic overlaps for testing duplicate detection
- 2 videos with captions (EN and EN/ES/DE multilingual)
- 2 videos with GPS location metadata
- All test files in tools/test_videos/ (70 KB total)
- TEST_CHANNEL_CONSTANTS.py with all video IDs and playlist IDs
- All integration tests updated to use test channel
- Fixed unicode encoding errors (replaced ✓✗⚠→ with ASCII equivalents)

**Status:** ✅ COMPLETE - All tasks finished, all tests passing

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

**Total Tasks**: 140 | **Completed**: 104 | **Remaining**: 36 | **Obsolete**: 3

**Task Count by Phase** (completed / total):
- Phase 1 (Setup): 6/6
- Phase 2 (Foundational): 9/9
- Phase 3 (US1 - Initial Archive): 18/19
- Phase 4 (US2 - Incremental Updates): 11/12
- Phase 5 (US3 - Filtering): 5/9
- Phase 6 (US4 - Web Interface): 19/19
- Phase 7 (US5 - Organization): 2/6
- Phase 8 (US6 - Export Metadata): 2/4
- Phase 9 (US7 - Caption Curation): 4/5
- Phase 10 (US8 - Public Hosting): 2/5
- Phase 11 (CI/CD): 0/7
- Phase 12 (Documentation): 0/7
- Phase 13 (Polish): 12/17
- Phase 14 (API Enhancement): 7/8
- Phase 15 (Test Infrastructure): 7/7

**Task Count by User Story**:
- US1 (Initial Channel Archive - P1): 19 tasks
- US2 (Incremental Updates - P1): 12 tasks
- US3 (Filtering - P2): 9 tasks
- US4 (Web Interface - P2): 19 tasks
- US5 (Organization - P3): 6 tasks
- US6 (Export Metadata - P3): 4 tasks
- US7 (Caption Curation - P4): 5 tasks
- US8 (Public Hosting - P4): 5 tasks

**Parallel Opportunities**: 47 tasks marked [P] can run in parallel with others in their phase

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
- Task ID: Sequential (T001-T130)
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
