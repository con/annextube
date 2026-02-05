# Changelog

All notable changes to annextube will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/con/annextube/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/con/annextube/releases/tag/v0.1.0
