# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v0.1.0 (2026-01-28)

Initial release of annextube - YouTube archival system using git-annex.

#### 🚀 Enhancement

- Implement core YouTube channel and playlist backup functionality [7b04e96](https://github.com/con/annextube/commit/7b04e96), [8e15114](https://github.com/con/annextube/commit/8e15114)
- Add git-annex integration with URL backend for video tracking [7b04e96](https://github.com/con/annextube/commit/7b04e96)
- Implement video metadata extraction and JSON storage per video [8e15114](https://github.com/con/annextube/commit/8e15114)
- Add comments download with configurable depth [c61e9f9](https://github.com/con/annextube/commit/c61e9f9)
- Add captions download with language filtering and VTT format [f2e05db](https://github.com/con/annextube/commit/f2e05db), [b7993d8](https://github.com/con/annextube/commit/b7993d8)
- Add thumbnail download support [8e15114](https://github.com/con/annextube/commit/8e15114)
- Implement TSV exports for videos, playlists, and authors [4839217](https://github.com/con/annextube/commit/4839217), [5b03481](https://github.com/con/annextube/commit/5b03481)
- Add automatic playlist discovery with pattern matching [2317dbc](https://github.com/con/annextube/commit/2317dbc)
- Implement playlist organization with ordered symlinks [befedf9](https://github.com/con/annextube/commit/befedf9)
- Add incremental update support with multiple update modes (all-incremental, social, users, comments) [1df5964](https://github.com/con/annextube/commit/1df5964), [9809f96](https://github.com/con/annextube/commit/9809f96)
- Implement true incremental updates using video ID filtering [09e0d0f](https://github.com/con/annextube/commit/09e0d0f), [cf7b854](https://github.com/con/annextube/commit/cf7b854)
- Add smart date parsing support ("1 week", "2 days", ISO dates) [3268116](https://github.com/con/annextube/commit/3268116)
- Add privacy tracking for removed/private videos [3268116](https://github.com/con/annextube/commit/3268116)
- Implement atomic file updates for git-annex compatibility [bfadcb1](https://github.com/con/annextube/commit/bfadcb1), [788e726](https://github.com/con/annextube/commit/788e726)
- Add comprehensive git-annex metadata for all annexed files [8b9e6fe](https://github.com/con/annextube/commit/8b9e6fe), [75bdc2f](https://github.com/con/annextube/commit/75bdc2f)
- Implement sensitive file protection (authors.tsv, comments.json to annex) [b8eb99e](https://github.com/con/annextube/commit/b8eb99e)
- Add configurable path patterns for video organization [24a6ad0](https://github.com/con/annextube/commit/24a6ad0)
- Add `info` command for archive statistics [b666777](https://github.com/con/annextube/commit/b666777)
- Add `check` command for archive integrity validation [566e0e3](https://github.com/con/annextube/commit/566e0e3)
- Extend `init` command with --limit, --thumbnails, --include-playlists options [566e0e3](https://github.com/con/annextube/commit/566e0e3)

#### 🐛 Bug Fix

- Fix video URL tracking to use YouTube watch URLs [586b1d5](https://github.com/con/annextube/commit/586b1d5), [ce75d14](https://github.com/con/annextube/commit/ce75d14)
- Fix date extraction for path patterns [c785f43](https://github.com/con/annextube/commit/c785f43)
- Fix datetime handling in git-annex metadata [605ba3b](https://github.com/con/annextube/commit/605ba3b)
- Fix channel URL handling to append /videos for proper extraction [716c0ab](https://github.com/con/annextube/commit/716c0ab)
- Fix config loading with absolute paths [be32c0b](https://github.com/con/annextube/commit/be32c0b)
- Fix playlist discovery to handle yt-dlp entry types [ff84e9e](https://github.com/con/annextube/commit/ff84e9e)
- Fix git commits to tolerate 'nothing to commit' scenario [b667341](https://github.com/con/annextube/commit/b667341)
- Fix incremental updates: datetime filtering and skip timestamp-only commits [660fc00](https://github.com/con/annextube/commit/660fc00), [022006d](https://github.com/con/annextube/commit/022006d)
- Fix NameError in incremental update logging [9a89793](https://github.com/con/annextube/commit/9a89793)
- Fix playlist duplicate processing [cf4758f](https://github.com/con/annextube/commit/cf4758f)
- Fix comment timestamp stability - preserve API timestamps [96b1598](https://github.com/con/annextube/commit/96b1598)
- Fix KeyError on 'id' in component-specific update modes [d73d100](https://github.com/con/annextube/commit/d73d100)
- Fix --from-date and --to-date filtering for all update modes [de382f8](https://github.com/con/annextube/commit/de382f8)
- Fix captions: exclude auto-translated, only download configured languages [654e588](https://github.com/con/annextube/commit/654e588)
- Fix config parsing for auto_translated_captions [2e7b887](https://github.com/con/annextube/commit/2e7b887)
- Fix caption filenames to match video base for player auto-discovery [e8e796b](https://github.com/con/annextube/commit/e8e796b)
- Fix playlist processing in component-specific update modes [530a50f](https://github.com/con/annextube/commit/530a50f)
- Fix race condition in git-annex add during batch file updates [1b000d6](https://github.com/con/annextube/commit/1b000d6)
- Fix: Skip playlist symlinks when setting sensitive metadata [a4ef2e8](https://github.com/con/annextube/commit/a4ef2e8)
- Fix staticmethod call in from_dict (cls not self) [d2f4eec](https://github.com/con/annextube/commit/d2f4eec)
- Fix caption downloads and implement timestamp-only commit prevention [022006d](https://github.com/con/annextube/commit/022006d)

#### 📝 Documentation

- Add comprehensive MVP demonstration summary [0ed8b6d](https://github.com/con/annextube/commit/0ed8b6d), [0dae6ff](https://github.com/con/annextube/commit/0dae6ff)
- Add comprehensive demo verification documentation [e0ba864](https://github.com/con/annextube/commit/e0ba864)
- Add comprehensive final MVP status documentation [777c3b0](https://github.com/con/annextube/commit/777c3b0)
- Document system requirements for yt-dlp and ffmpeg [3651566](https://github.com/con/annextube/commit/3651566)
- Add quickstart guide and comprehensive specification [specs/001-youtube-backup/]

#### 🏠 Internal

- Eliminate sync_state.json - use TSV files as single source of truth [cecc599](https://github.com/con/annextube/commit/cecc599)
- Complete TSV refactoring and add data integrity guarantees [4839217](https://github.com/con/annextube/commit/4839217)
- Implement fail-fast error handling in archiver [c781f84](https://github.com/con/annextube/commit/c781f84)
- Add retry logic for YouTube extraction [ce75d14](https://github.com/con/annextube/commit/ce75d14)
- Improve YouTube channel video extraction robustness [592f0a0](https://github.com/con/annextube/commit/592f0a0), [e46619f](https://github.com/con/annextube/commit/e46619f)
- Change include_podcasts from bool to pattern matching [6195637](https://github.com/con/annextube/commit/6195637)
- Clean up root directory: move demo files to specs/demos/ [3a23b33](https://github.com/con/annextube/commit/3a23b33)
- Add end-to-end integration tests [566e0e3](https://github.com/con/annextube/commit/566e0e3)
- Preserve original casing in video directory names [be32c0b](https://github.com/con/annextube/commit/be32c0b)
- Add deterministic sorting to prevent false diffs [c61e9f9](https://github.com/con/annextube/commit/c61e9f9)

#### Authors

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))
- Claude Sonnet 4.5

---

## Initial Development

For detailed development history and specifications, see:
- [specs/001-youtube-backup/spec.md](specs/001-youtube-backup/spec.md) - Complete feature specification
- [specs/001-youtube-backup/plan.md](specs/001-youtube-backup/plan.md) - Implementation plan
- [specs/001-youtube-backup/quickstart.md](specs/001-youtube-backup/quickstart.md) - Quickstart guide
