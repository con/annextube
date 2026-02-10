# Changelog

All notable changes to annextube will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.2]: https://github.com/con/annextube/compare/v0.2.0...v0.2.2
[0.2.0]: https://github.com/con/annextube/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/con/annextube/releases/tag/v0.1.0
