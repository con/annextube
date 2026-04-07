# Implementation Plan: Multi-Channel Collections

**Branch**: `003-multi-channel-collections` | **Date**: 2026-03-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-multi-channel-collections/spec.md`

## Summary

Add composable multi-channel collection support to annextube, enabling users to organize multiple independent channel archives under a single DataLad superdataset. The system discovers channels via `channel.json` scanning, aggregates metadata into a root-level `channels.tsv`, and extends the web UI to display a channel overview with drill-down navigation. Collection management commands (`collection add`, `collection backup`) streamline adding channels and performing batch updates with continue-on-failure semantics. This builds heavily on existing infrastructure: the `aggregate` command and `export --channel-json` are already implemented (Phase 1 backend complete), and the frontend already detects multi-channel mode via `channels.tsv` probing in the `DataLoader`.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: datasalad (git/git-annex operations), yt-dlp (YouTube downloads), datalad (dataset/subdataset management), Svelte (frontend framework)
**Storage**: File-based (NO databases) -- git-annex repository with git for metadata (JSON, TSV); DataLad superdataset for collection, DataLad subdatasets for individual channel archives; summary metadata in TSV files (channels.tsv at collection root, videos.tsv/playlists.tsv per channel)
**Testing**: pytest (backend/library), Vitest + @testing-library/svelte (frontend unit), Playwright (frontend E2E)
**Target Platform**: Linux/macOS/Windows (CLI), modern browsers ES6+ (web UI)
**Project Type**: Web application (backend library + CLI + frontend)
**Performance Goals**: `aggregate` command completes in <5s for 50-channel collection; channel overview page loads in <2s; batch backup processes channels sequentially with per-channel status reporting
**Constraints**: Offline-capable web UI (file:// protocol); DataLad subdataset composability (each channel independently versionable); no database dependencies; continue-on-failure for batch operations
**Scale/Scope**: Collections with up to 50 channels; per-channel archives with 10,000+ videos; nested directory structures up to 3 levels deep

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Library-First Architecture

- Aggregate logic (`discover_channels`, `compute_archive_stats`) is in `annextube/cli/aggregate.py` as reusable functions
- Collection management logic will be in `annextube/services/collection.py` (library layer)
- CLI commands are thin wrappers calling library functions

### II. Multi-Interface Exposure

- **CLI**: `aggregate` (done), `collection add`, `collection backup` commands
- **API**: Python functions for channel discovery, aggregation, collection management
- **Web UI**: Multi-channel overview page with drill-down to per-channel video listings
- Exit codes: 0 for full success, 1 for partial failure (some channels failed in batch)

### III. Test-First Development

- TDD mandatory: tests before implementation for all new code
- Contract tests for `collection add` and `collection backup` CLI interfaces
- Integration tests for multi-channel web UI detection and navigation

### IV. Integration Testing

- Contract tests for collection management API boundaries
- CLI integration tests (collection add -> backup -> aggregate -> generate-web pipeline)
- Frontend E2E tests for multi-channel mode detection and channel navigation
- Schema validation: frontend correctly parses `channels.tsv` rows

### V. Code Efficiency & Conciseness

- Reuse existing `discover_channels()`, `compute_archive_stats()` from aggregate.py
- Reuse existing `DataLoader` multi-channel detection (already implemented)
- No aggregated videos.tsv -- parallel per-channel TSV loading is fast enough

### VI. Observability & Debuggability

- Structured logging for channel discovery, batch operations
- Per-channel status reporting in batch backup summary
- Clear error messages for: directory conflicts, missing channel.json, backup failures

### VII. Versioning & Breaking Changes

- Additive feature: no breaking changes to existing single-channel archives
- `channels.tsv` is a new file format; schema versioned via column headers

### VIII. DRY Principle - No Code Duplication

- Reuse existing `ExportService.generate_channel_json()` for channel.json creation
- Reuse existing `discover_channels()` across aggregate and collection backup
- Reuse existing archiver service for per-channel backup in batch mode
- Reuse existing `ChannelList.svelte` component for multi-channel overview

### IX. Shared Data Schema

- `ChannelTSVRow` type already defined in `frontend/src/types/models.ts`
- `Channel` interface already includes `channel_dir` field for multi-channel
- channels.tsv column schema shared between Python writer and TypeScript parser

### X. FOSS Principles

- No new dependencies; all existing deps are OSI-licensed
- All data stays local; no telemetry
- Works offline (web UI via file://)

### XI. Resource Efficiency

- **Network**: Batch backup reuses existing incremental update logic
- **Disk**: No aggregated videos.tsv (avoids data duplication)
- **Memory**: channels.tsv is small (~1KB per channel); per-channel TSV loaded on demand
- **Storage Simplicity**: TSV + JSON files only, no database

### XII. Data Integrity & Authenticity

- All channel data derived from actual YouTube metadata via yt-dlp
- Archive stats computed from local videos.tsv (real archived data)
- No synthetic data in production paths

### XIII. DataLad-Native Operations

- Collections use `datalad create` for superdataset initialization
- Channels added as subdatasets via `datalad create -d .` or `datalad clone -d .`
- Changes recorded via `datalad save`
- Batch backup uses `datalad run` for reproducible command execution
- Publishing via `datalad push` (recursive for collections)

### Gates Summary

All constitution principles align with feature requirements.

**Gate Status**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/003-multi-channel-collections/
├── plan.md              # This file
├── research.md          # Phase 0 research (lightweight -- builds on existing infra)
├── data-model.md        # Phase 1 data model (channels.tsv, channel.json, collection config)
├── quickstart.md        # Phase 1 quickstart guide
├── contracts/           # Phase 1 API contracts
│   └── cli-contract.md  # CLI interface for aggregate, collection add, collection backup
└── tasks.md             # Phase 2 output (NOT created by plan)
```

### Source Code (repository root)

Files marked with **(done)** are already implemented. Files marked with **(new)** need to be created.

```text
annextube/                        # Python package
├── services/
│   ├── export.py                 # (done) generate_channel_json() for channel.json
│   ├── collection.py             # (new) Collection management service
│   │                             #   - add_channel(): create subdataset, init, backup
│   │                             #   - backup_all(): batch backup with error handling
│   │                             #   - discover_subdatasets(): find channel archives
│   └── archiver.py               # (done) Per-channel backup logic (reused by collection)
├── cli/
│   ├── aggregate.py              # (done) aggregate command + discover_channels()
│   ├── collection.py             # (new) collection add/backup commands
│   └── __main__.py               # (modify) Register collection command group
├── lib/
│   ├── config.py                 # (modify) Add CollectionConfig dataclass, [collection] parsing
│   ├── archive_discovery.py      # (done) discover_annextube() for archive type detection
│   └── tsv_utils.py              # (done) TSV escaping/parsing
└── schema/
    └── models.json               # (modify) Add channels.tsv schema, collection config schema

frontend/                         # Svelte web interface
├── src/
│   ├── App.svelte                # (modify) Add multi-channel routing and breadcrumbs
│   ├── components/
│   │   └── ChannelList.svelte    # (done) Channel overview component
│   ├── services/
│   │   └── data-loader.ts        # (done) Multi-channel detection + channel TSV loading
│   └── types/
│       └── models.ts             # (done) Channel, ChannelTSVRow types
└── tests/
    ├── unit/
    │   └── channel-list.test.ts  # (new) ChannelList component tests
    └── e2e/
        └── multi-channel.spec.ts # (new) Multi-channel E2E tests

tests/                            # Backend tests
├── contract/
│   └── test_collection_cli.py    # (new) CLI contract tests for collection commands
├── integration/
│   └── test_collection.py        # (new) Integration tests for collection workflows
└── unit/
    └── test_collection_service.py # (new) Unit tests for collection service
```

## Phasing

### Phase 1: Discovery & Aggregation (DONE)

Already implemented:
- `annextube aggregate` command with glob-based `channel.json` discovery (depth 1-3)
- `annextube export --channel-json` for generating per-channel metadata
- `DataLoader.init()` with multi-channel mode detection via `channels.tsv` probing
- `ChannelList.svelte` component for channel overview display
- `Channel` and `ChannelTSVRow` TypeScript types with `channel_dir` field

### Phase 2: Web UI Multi-Channel Mode (P1)

Already implemented:
- `ChannelList` wired into `App.svelte` routing (multi-channel detection, channel overview, drill-down)
- Per-channel `videos.tsv` loading on channel selection (`loadChannelVideos()`, `loadChannelPlaylists()`)
- Back-to-channels navigation ("← Back to channels" button)
- Backward compatibility: single-channel mode unchanged when `channels.tsv` absent

Remaining work:
- Upgrade "← Back to channels" button to proper breadcrumb navigation (Home > Channel > Video)
- Unit tests for multi-channel data loading
- E2E test for multi-channel navigation

### Phase 3: Collection Management — Add Channel (P2)

New commands:
- `annextube collection add <url>` -- create DataLad subdataset, init, backup
- Collection-level config: `[collection]` section in `.annextube/config.toml`
- Config inheritance: collection defaults applied to new channels via `collection add`

### Phase 4: Collection Management — Batch Backup (P2)

- `annextube collection backup` -- batch update all channels with error reporting
- Sequential by default, opt-in `--parallel N`
- `--save` and `--push` flags for collection-level operations

### Phase 5: External Archive Import (P3)

- Add existing external archives via `datalad clone -d .`
- Document import workflow

### Phase 6: Polish & Automation (P2)

- Auto-run `aggregate` in `generate-web` if `channels.tsv` missing
- Auto-run `aggregate` after `collection backup --save`
- Better error handling for malformed `channel.json`

### Phase 7: Cross-Channel Search (P4)

- Cross-channel search and filtering in web UI
- Nested grouping visualization
