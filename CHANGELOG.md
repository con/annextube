# Changelog

All notable changes to annextube will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.4.0]: https://github.com/con/annextube/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/con/annextube/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/con/annextube/compare/v0.2.0...v0.2.2
[0.2.0]: https://github.com/con/annextube/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/con/annextube/releases/tag/v0.1.0
