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
│   ├── sync_state.py        # SyncState entity
│   └── filter_config.py     # FilterConfig entity
├── services/
│   ├── git_annex.py         # datasalad wrapper for git-annex ops
│   ├── youtube.py           # yt-dlp wrapper for YouTube ops
│   ├── archiver.py          # Core archival logic
│   ├── updater.py           # Incremental update logic
│   ├── metadata_export.py   # TSV export generation
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
