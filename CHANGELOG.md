# Changelog

All notable changes to annextube will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2026-02-18

### Added

- **`embed-config` command**: Propagate shared TOML settings (e.g. `[curation]` glossary) from a super-dataset config into subdataset configs with comment-preserving deep merge. Supports `--existing keep` (default) and `--existing update` modes. Skips `[[sources]]` (per-subdataset)
- **Caption curation design spec**: Planning document for the curation pipeline
- **`[curation]` section in config template**: Generated configs now include documented curation settings (glossary, fuzzy matching, LLM, audio alignment)
- **Glossary discovery with parent collation**: `glossary_path` + `glossary_collate_parents` in `[curation]` config for multi-channel setups — walk up parent dirs and merge all glossaries found
- **Caption curation pipeline**: 8-stage ASR correction (`curate-captions` command) — glossary regex, LLM corrections, fuzzy matching, filler removal, ASR artifact fixes, sentence segmentation, cue chunking, timestamp restoration
- **Clone command panel**: Web UI header button to clone the archive repository
- **`tomlkit` dependency**: Comment-preserving TOML editing for `embed-config`
- **`types-PyYAML` dev dependency**: Fix mypy type checking for yaml imports

### Fixed

- **`curate-captions` ignoring archive config for VIDEO_PATH**: Direct video directory mode was creating bare `CurationConfig()` defaults instead of loading `.annextube/config.toml`, silently ignoring `glossary_path` and other `[curation]` settings
- **Transcript language selector reverting**: Fixed CaptionBrowser resetting user language picks on reactive updates
- **Clone command UI**: Fixed reactive updates, tab switching, and inline layout
- **Curated captions not default in transcript browser**: CaptionBrowser now auto-selects the curated variant (e.g. `en-curated`) over the base language; `en-curated` displays as "EN (curated)"

### Changed

- **Skip already-archived videos during playlist backup**: Incremental playlist backup no longer re-processes existing videos

## [0.8.0] - 2026-02-16

### Added

- **yt-dlp rate-limit detection and concurrency limiting**: Detects YouTube 429/rate-limit responses and retries with exponential backoff. Cross-process concurrency limiting via file locks prevents parallel yt-dlp calls from triggering rate limits
- **`tox -e sdist-check`**: Automated pre-release verification — builds sdist, installs in clean venv, verifies built frontend is included and `generate-web` works
- **`tox -e full`**: Run all non-network tests with all optional deps (including playwright)
- **Pre-release sdist verification checklist**: Documented manual tarball inspection steps

### Fixed

- **Catastrophically slow sdist build**: `skip-excluded-dirs = true` prevents hatchling from walking into multi-GB cache directories (201s → 0.04s)
- **Built frontend missing from sdist**: `force-include` and `artifacts` config ensures `web/` is included; dropped frontend source from sdist
- **Skip known-unavailable videos during playlist backup**: Avoid re-attempting videos that are known to be unavailable
- **Rate-limit and concurrency implementation gaps**: Fixed three issues in the initial rate-limit implementation
- **e2e test fixture**: Added pytest-playwright dependency

## [0.7.0] - 2026-02-14

### Added

- **Extra metadata with DataCite vocabulary**: User-managed `extra_metadata.json` per video for supplemental metadata (related slides, papers, code repos). LinkML schema defines `RelatedResource` using DataCite v4.6 relationType and resourceTypeGeneral vocabularies. Merged additively into `metadata.json` during export (never overwrites archiver-managed fields)
- **Related resources display**: Frontend shows linked resources in video details with type badges (`[Presentation slides]`, `[Software]`, etc.)
- **Human-readable caption labels**: Caption language selector shows readable labels for yt-dlp variant suffixes (e.g. `en-cur1` → `EN (curated)`, `en-orig` → `EN (original)`)
- **Caption download button**: Download VTT caption files directly from the transcript panel header
- **Deno as core dependency**: Required for yt-dlp YouTube JS challenge solver
- **Skip network tests by default**: pytest addopts `-m "not network"` prevents flaky CI from YouTube bot detection. Use `tox -e network` for full network test sweep

### Fixed

- **Phased backup_channel() flow**: Refactored into discovery → fetch → store → link phases, fixing O(P^2) TSV regeneration and symlink overhead
- **Version injection after appVersion refactor**: Fixed placeholder matching in `deploy_frontend()` after Vite inlining changed from `v0.0.0-unknown` to bare `0.0.0-unknown`
- **TypeError on None playlist titles**: Handle yt-dlp returning None for playlist titles
- **Empty videos.tsv crash**: Handle missing `videos/` directory gracefully
- **Frontend build warnings**: A11y labels, version variable reference, video caption attributes
- **Encoding consistency**: Use `encoding="utf-8"` instead of `text=True` in all subprocess calls
- **yt-dlp options consistency**: Use `_get_ydl_opts()` for all yt-dlp calls, apply env vars in UserConfig

### Changed

- **Header renamed to AnnexTube**: Links to GitHub repo https://github.com/con/annextube
- **ejs:github enabled by default**: Remote JavaScript components for yt-dlp challenge solver
- **Test infrastructure**: pytest tmp_path fixture, datalad in test deps, playwright skip when missing, dedicated network test environment

## [0.6.0] - 2026-02-14

### Added

- **URL permalink for caption search state**: Shared links now also restore caption search context — query, case-sensitive/regex/filter toggles, and match position. URL params `q`, `cs`, `re`, `filter`, `match` are appended alongside existing player params (e.g. `#/channel/X/video/Y?tab=local&t=90&lang=en&q=neuroimaging&cs=1&re=1&filter=1&match=3`). Match position is restored on first load, then resets normally on new searches.

## [0.5.0] - 2026-02-13

### Added

- **URL permalink for video player state**: Shared links now restore the full viewing context — active player tab (archive/youtube), wide mode, transcript visibility, playback position, and caption language. URL params are appended to the hash route (e.g. `#/channel/X/video/Y?tab=youtube&wide=1&t=90&transcript=0&lang=es`). Only non-default values are written, keeping URLs clean. Uses `history.replaceState` to avoid history pollution.

## [0.4.0] - 2026-02-13

### Added

- **Interactive caption/transcript browser**: Side-by-side panel next to video player with full transcript display, click-to-seek, and active cue highlighting synced to playback position
- **Transcript search**: Search within captions with case-sensitive (C), regex (.*), and filter (F) modes. Filter mode hides non-matching cues; dim mode preserves timeline context. Enter/Shift+Enter keyboard navigation between matches with N/M position indicator
- **WebVTT parser with auto-caption dedup**: Zero-dependency parser handles YouTube auto-caption rolling 3-cue pattern (display→snapshot→carry-over), merging overlapping cues and stripping carry-over lines. Reduces a 1-hour video from ~4000 raw cues to ~1400 clean cues
- **Wide/theater mode**: Toggle (button or `t` key) to use full browser width for video+transcript layout, persisted in localStorage
- **Language selector**: Switch between available caption languages in the transcript panel
- **Auto-scroll with manual override**: Transcript auto-scrolls to active cue during playback, pauses on manual scroll, re-enables after 5s idle or cue click. "Resume auto-scroll" button when disabled
- **GitHub Pages sharing**: `annextube unannex` command and `prepare-ghpages` workflow for sharing archives via GitHub Pages
- **Frontend download button**: Download local video files directly from the player
- **YouTube external links**: "View on YouTube" button with source URL

### Fixed

- **Per-playlist videos.tsv**: Use `os.walk` to follow directory symlinks when indexing playlist videos
- **Playlist symlink indexing**: Fixed per-playlist videos.tsv generation
- **DataLoader archive root discovery**: Probe ascending paths at runtime instead of assuming fixed `../` relative path, enabling deployment at any URL depth
- **Click-to-seek scroll glitch**: Set activeCueIndex immediately on cue click to prevent afterUpdate scrolling to the old active cue while the async seek completes
- **Search regex statefulness**: Removed `g` flag from shared searchRegex — `RegExp.test()` with `g` advances `lastIndex`, breaking match detection in loops across different strings
- **Wide→normal height revert**: CSS Grid `align-items: start` breaks the circular dependency where `--player-height` was measured from the grid-row height inflated by the caption browser
- **Search nav button clipping**: Redesigned as two-row layout — search options on row 1, navigation (Filter + Prev/Next) on conditional row 2
- **Filter→unfilter scroll position**: Scroll to current match when exiting filter mode instead of jumping to top
- **Caption file path**: Fixed `getCaptionPath` in DataLoader to use `video.{lang}.vtt` naming (was `caption_{lang}.vtt`)
- **Missing captions in transcript browser**: Reconcile `captions_available` in metadata.json with actual VTT files on disk during export. Fixes videos where captions were downloaded but metadata wasn't re-saved
- **YouTube customUrl field**: Strip leading `@` from API response

### Changed

- **Simplified unannex**: Replaced 632-line implementation with thin git-annex wrapper
- **Version injection**: Use `0.0.0-unknown` placeholder in frontend build, replaced at deploy time by `deploy_frontend()`
- **Video+transcript layout**: CSS Grid with `align-items: start` and dynamic `--player-height` variable ensures transcript panel matches video height exactly

## [0.3.0] - 2026-02-11

### Added

- **Batch YouTube API calls**: Pre-fetch statistics and metadata in bulk instead of per-video API calls
- **`--comments-depth` CLI option**: Override comments depth at backup time (-1=unlimited, 0=disabled, N=limit)
- **DataLad dataset support**: `--datalad` flag for `init` command to create DataLad-managed archives
- **Version display in web UI**: Show annextube version in the header, injected during `generate-web`
- **Channel permalink routing**: Direct URLs to channels and per-channel playlist support in web UI
- **TSV regeneration for multi-channel collections**: `--update=tsv_metadata` works across collections
- **`serve --regenerate=web`**: Allow creating the web directory if it doesn't exist yet

### Fixed

- **Incremental backup discarding new videos**: Social date window filter was incorrectly applied to new video discovery in incremental mode, silently dropping videos published outside the 1-week window
- **Frontend URL state feedback loop**: Changing any filter caused a hashchange → restoreFromURL → re-render cycle, visibly resetting selections. Fixed with `history.replaceState()` instead of `window.location.hash`
- **URL defaults pollution**: Default sort params (`sort=date&dir=desc`) no longer appended to clean URLs
- **Video player paths at subpath deployments**: Absolute `/videos/...` paths replaced with relative `../videos/...` for correct resolution at any deployment subpath
- **Video player reactivity**: Fixed state not updating when video prop changes
- **Video availability checking**: Use HEAD requests instead of relying on TSV download_status; include 'tracked' status; centralized checking logic
- **VideoPlayer thumbnail fallback**: Use YouTube CDN thumbnail when video not downloaded locally
- **Video metadata/comments loading**: Use file_path from video object instead of reconstructing paths
- **Browser back/forward navigation**: Fixed multi-channel video metadata loading on history navigation
- **Page reloads and playlist selection**: Fixed routing to preserve context and support nested routes
- **TSV field escaping**: Properly escape newlines and special characters in TSV output
- **Unicode encoding errors**: Fixed encoding issues in channel avatar display
- **Metadata sync**: Sync metadata.json download_status with actual file system state during TSV generation

### Changed

- **Asset filenames**: Vite build now produces clean filenames (`index.js`, `index.css`) without content hashes
- **FilterPanel initialization**: Uses Svelte `tick()` for clean reactive cycle during mount

## [0.2.2] - 2026-02-09

### Added

- **Multi-channel collections**: Hierarchical structure with channels.tsv, aggregate/export/generate-web/serve commands
- **Auto-generate channel.json**: Automatically created during backup for seamless multi-channel integration
- **YouTube API channel metadata**: Three-tier extraction (API → yt-dlp → archive) for complete channel information
- **Channel avatar download**: Automatic download with MIME type detection and git-annex tracking
- **Timestamp filtering for channel.json**: Prevents unnecessary commits when only timestamps change
- **Quota exceeded auto-retry**: Automatic wait and retry when YouTube API quota is exceeded
- **Periodic checkpoint commits**: Configurable intermediate commits during long backup operations with interruption recovery
- **Configurable playlist symlink patterns**: Use {video_id}, {video_title}, {position} in playlist symlinks
- **Archive discovery helpers**: Central discovery system for single-channel vs multi-channel detection

### Fixed

- **Playlist video reprocessing**: Skip reprocessing existing videos in 'playlists' update mode
- **Caption download for existing videos**: Properly download captions when adding to existing archive
- **Incremental playlist optimization**: Skip unavailable videos in incremental mode for faster processing
- **Path pattern validation**: Fail early on unknown placeholders in video_path_pattern
- **E2E test environment**: Use 'uv run annextube' to ensure correct environment activation
- **Type checking**: Complete mypy compliance across all modules
- **Linting**: Full ruff compliance across all modules

### Changed

- **Default include-playlists**: Changed from 'none' to 'all' for better discoverability
- **Default include-podcasts**: Changed from 'none' to 'all' for consistency
- **Default playlist path pattern**: Changed from {playlist_id} to {playlist_title} for readability
- **Config template formatting**: Simplified double-brace escaping for better readability

### Documentation

- **Quota handling guide**: Complete documentation for YouTube API quota management
- **Checkpoint system guide**: Documentation for periodic commits and recovery
- **Multi-channel collections**: End-to-end guide for creating and managing collections
- **yt-dlp challenge solver**: Documented dependency issues and solutions

## [0.2.0] - 2026-02-05

### Added

- **Incremental social data updates**: Efficient API-optimized updates with statistics gate and early stopping (96% API request reduction)
- **Containerization support**: Complete Podman/Docker/Singularity recipes with documentation
- **Progress indicators**: Real-time feedback for long-running playlist/channel fetches
- **Video file validation**: Magic byte detection to identify HTML error pages disguised as videos
- **YouTube Data API integration**: Enhanced metadata and comment fetching with yt-dlp fallback
- **Per-source component configuration**: Override global settings per channel/playlist
- **User-wide configuration**: Cookies, proxy, network settings in ~/.config/annextube/config.toml
- **Hierarchical video structure**: Year/month subdirectories for better organization
- **Range server with annextube serve**: Local playback with seeking support
- **Comprehensive E2E test suite**: Playwright tests for web UI and complete workflows
- **Full web frontend**: Search, filter, sort, video player with local/YouTube tabs

### Fixed

- **Nested directory bug**: git-annex addurl with relative paths creating nested structures
- **EJS solver integration**: Support for authenticated access with cookies + deno
- **Playlist creation bug**: Ensure playlists are created with correct video associations
- **Download status detection**: Proper differentiation between tracked and downloaded videos
- **Video player issues**: Blank screen, iframe sizing, seeking with range requests
- **git-annex addurl**: Remove --no-raw flag to avoid conflicts with --fast
- **Cookie path handling**: Remove quotes from git-annex cookie configuration
- **Code quality**: Complete mypy and ruff linting fixes

### Changed

- **Test infrastructure**: Dedicated AnnexTube test channel with 10 videos and 5 playlists
- **E2E browser setup**: Avoid sudo prompts by checking existing installations
- **Default update mode**: Changed to all-incremental (videos + social data updates)

### Documentation

- Complete frontend MVP documentation with phase-by-phase progress
- Container deployment guide for Podman/Docker/Singularity
- User configuration documentation with cookie and network settings examples

## [0.1.0] - 2026-01-28

Initial release with core YouTube archival functionality:
- Channel and playlist backup
- git-annex integration for efficient storage
- Metadata extraction (JSON + TSV)
- Caption and thumbnail downloads
- Comment fetching
- Basic web UI for browsing archives

[0.7.0]: https://github.com/con/annextube/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/con/annextube/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/con/annextube/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/con/annextube/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/con/annextube/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/con/annextube/compare/v0.2.0...v0.2.2
[0.2.0]: https://github.com/con/annextube/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/con/annextube/releases/tag/v0.1.0
