# Tasks: Multi-Channel Collections

**Feature**: 003-multi-channel-collections
**Input**: Design documents from `/specs/003-multi-channel-collections/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are written alongside implementation per Constitution III (TDD). Test tasks are implicit in each implementation task rather than tracked separately.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Discovery & Aggregation (DONE)

**Purpose**: Channel discovery and metadata aggregation — already implemented

- [X] T001 Implement `aggregate` command in annextube/cli/aggregate.py (glob-based channel.json discovery, channels.tsv generation)
- [X] T002 Implement `export --channel-json` flag in annextube/cli/export.py (per-channel channel.json generation)
- [X] T003 [P] Add `discover_channels()` function in annextube/cli/aggregate.py (depth 1-3 scanning)
- [X] T004 [P] Add `compute_archive_stats()` in annextube/cli/aggregate.py (video count, date range from videos.tsv)
- [X] T005 [P] Define `Channel` and `ChannelTSVRow` types in frontend/src/types/models.ts
- [X] T006 [P] Add multi-channel detection to DataLoader in frontend/src/services/data-loader.ts (probe channels.tsv)
- [X] T007 [P] Create `ChannelList.svelte` component in frontend/src/components/ChannelList.svelte

**Checkpoint**: Phase 1 is complete — `aggregate` and `export --channel-json` work, frontend types and detection exist

---

## Phase 2: Web UI Multi-Channel Mode (US1 Aggregate + US2 Browse) — Priority: P1

**Goal**: Wire multi-channel mode into the web UI so users can browse a collection with channel overview and drill-down to per-channel video listings (FR-023 to FR-027)

**Independent Test**: Generate web UI for a collection with `channels.tsv`, open in browser, verify channel overview loads and clicking a channel shows its videos

### Implementation

- [X] T008 [US2] Wire ChannelList into App.svelte routing for multi-channel mode in frontend/src/App.svelte (show channel overview when channels.tsv detected)
- [X] T009 [US2] Implement per-channel video loading in frontend/src/services/data-loader.ts (load `{channel_dir}/videos/videos.tsv` on channel selection)
- [ ] T010 [US2] Add breadcrumb navigation in frontend/src/App.svelte (currently "← Back to channels" button; upgrade to Home > Channel > Video breadcrumb)
- [X] T011 [US2] Verify backward compatibility: single-channel mode unchanged when channels.tsv absent in frontend/src/App.svelte
- [ ] T012 [P] [US2] Add unit tests for multi-channel data loading in frontend/tests/unit/channel-list.test.ts
- [ ] T013 [P] [US2] Add E2E test for multi-channel navigation in frontend/tests/e2e/multi-channel.spec.ts

**Checkpoint**: Web UI displays channel overview for collections and falls back to single-channel mode

---

## Phase 3: Collection Management — Add Channel (US3 + US5) — Priority: P2

**Goal**: Single-command channel addition with collection-level config defaults (FR-006 to FR-011, FR-019 to FR-022)

**Independent Test**: Run `annextube collection add <url>` on a collection directory, verify subdataset created, initialized with collection defaults, and first backup runs

### Implementation

- [ ] T014 [US5] Add `CollectionConfig` dataclass to annextube/lib/config.py (`[collection]` section: comments_depth, curation, search, include_playlists, include_podcasts, common_config, push_remote)
- [ ] T015 [US5] Implement `[collection]` section parsing in annextube/lib/config.py (load from `.annextube/config.toml` at collection root)
- [ ] T016 [US3] Create collection service in annextube/services/collection.py (`add_channel()`: extract handle, create subdataset, init, apply defaults, embed common config, backup)
- [ ] T017 [US3] Implement handle extraction from YouTube URL in annextube/services/collection.py (parse @handle from various URL formats)
- [ ] T018 [US3] Implement common config embedding in annextube/services/collection.py (copy/merge common config file into channel config)
- [ ] T019 [US3] Create `collection` command group in annextube/cli/collection.py (Click group with `add` subcommand)
- [ ] T020 [US3] Implement `collection add` CLI command in annextube/cli/collection.py (options: --name, --no-backup, --output-dir per cli-contract.md)
- [ ] T021 [US3] Register `collection` command group in annextube/cli/__main__.py
- [ ] T022 [P] [US3] Add unit tests for collection service in tests/unit/test_collection_service.py (handle extraction, config merging)
- [ ] T023 [P] [US3] Add contract tests for `collection add` in tests/contract/test_collection_cli.py

**Checkpoint**: Can add channels to a collection with a single command; collection defaults are inherited

---

## Phase 4: Collection Management — Batch Backup (US4) — Priority: P2

**Goal**: Batch update all channels with continue-on-failure semantics and aggregate reporting (FR-012 to FR-018)

**Independent Test**: Run `annextube collection backup` on a collection with 2+ channels, verify each gets updated and summary report shows per-channel status

### Implementation

- [ ] T024 [US4] Implement `backup_all()` in annextube/services/collection.py (discover subdatasets, iterate channels, run backup per channel, accumulate results)
- [ ] T025 [US4] Implement `discover_subdatasets()` in annextube/services/collection.py (find directories with `.annextube/config.toml`)
- [ ] T026 [US4] Implement continue-on-failure logic in annextube/services/collection.py (catch per-channel errors, log, continue)
- [ ] T027 [US4] Implement batch result reporting in annextube/services/collection.py (per-channel success/failure summary with reasons)
- [ ] T028 [US4] Add `--parallel N` support in annextube/services/collection.py (concurrent channel processing with configurable limit)
- [ ] T029 [US4] Implement `collection backup` CLI command in annextube/cli/collection.py (options: --parallel, --save, --push per cli-contract.md)
- [ ] T030 [US4] Implement `--save` flag: run aggregate + datalad save at collection level in annextube/cli/collection.py
- [ ] T031 [US4] Implement `--push` flag: datalad push -r to configured remote in annextube/cli/collection.py
- [ ] T032 [P] [US4] Add unit tests for batch backup in tests/unit/test_collection_service.py (error accumulation, continue-on-failure)
- [ ] T033 [P] [US4] Add contract tests for `collection backup` in tests/contract/test_collection_cli.py
- [ ] T034 [P] [US4] Add integration test for full pipeline in tests/integration/test_collection.py (add -> backup -> aggregate -> generate-web)

**Checkpoint**: Can batch-update all channels; partial failures don't stop the run; summary report shows status

---

## Phase 5: External Archive Import (US6) — Priority: P3

**Goal**: Add existing external archives to a collection via clone (FR-028 to FR-032)

**Independent Test**: Clone a published channel archive into a collection, run aggregate, verify it appears in channels.tsv

### Implementation

- [ ] T035 [US6] Document external archive import workflow in specs/003-multi-channel-collections/quickstart.md (datalad clone -d . <url>, then aggregate)
- [ ] T036 [US6] Add `collection clone` or document `datalad clone -d .` usage in annextube/cli/collection.py (optional: thin wrapper around datalad clone with aggregate auto-run)
- [ ] T037 [US6] Verify aggregate handles cloned archives in tests/integration/test_collection.py (channels without local backup history)

**Checkpoint**: External archives can be composed into a collection

---

## Phase 6: Polish & Automation

**Purpose**: Cross-cutting improvements

- [ ] T038 [P] Auto-run `aggregate --force` in `generate-web` when channels.tsv is missing in annextube/cli/generate_web.py
- [ ] T039 [P] Auto-run `aggregate --force` after `collection backup --save` in annextube/cli/collection.py
- [ ] T040 [P] Improve error handling for malformed channel.json in annextube/cli/aggregate.py (structured warnings, skip gracefully)
- [ ] T041 [P] Add JSON Schema definitions for channels.tsv and collection config in annextube/schema/models.json
- [ ] T042 Run quickstart.md validation (verify workflow completes as documented)

---

## Phase 7: Cross-Channel Search (US7) — Priority: P4

**Goal**: Search across all channels simultaneously in the web UI

**Independent Test**: Open multi-channel web UI, search for a term, verify results include videos from multiple channels

### Implementation

- [ ] T043 [US7] Implement cross-channel video loading in frontend/src/services/data-loader.ts (load all channels' videos.tsv in parallel)
- [ ] T044 [US7] Add cross-channel search in frontend/src/services/search.ts (search across loaded channel data with channel attribution)
- [ ] T045 [US7] Add channel filter on overview page in frontend/src/App.svelte (date range filter highlighting matching channels)
- [ ] T046 [P] [US7] Add tests for cross-channel search in frontend/tests/unit/search.test.ts

**Checkpoint**: All user stories complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Discovery/Aggregation)**: DONE
- **Phase 2 (Web UI)**: No dependencies on other phases — can start immediately
- **Phase 3 (Collection Add)**: No dependencies on Phase 2 — can start in parallel
- **Phase 4 (Batch Backup)**: Depends on Phase 3 (needs collection service)
- **Phase 5 (External Import)**: Can start after Phase 1 — mostly documentation
- **Phase 6 (Polish)**: Can start after Phases 2-4
- **Phase 7 (Cross-Channel Search)**: Depends on Phase 2 (web UI multi-channel mode)

### User Story Dependencies

- **US1 (Aggregate - P1)**: DONE — no work needed
- **US2 (Browse - P1)**: Mostly done — routing, loading, backward compat implemented; breadcrumb + tests remain
- **US3 (Add Channel - P2)**: Can start immediately — backend-only work
- **US4 (Batch Backup - P2)**: Depends on US3 (needs collection service from T016)
- **US5 (Config - P2)**: Part of US3 phase (T014-T015 feed into T016)
- **US6 (Import - P3)**: Can start immediately — mostly documentation + testing
- **US7 (Cross-Search - P4)**: Depends on US2 (needs multi-channel web UI)

### Parallel Opportunities

- **Phase 2 + Phase 3**: Frontend (T008-T013) and backend (T014-T023) can run in parallel
- **Within Phase 3**: T022 and T023 (tests) can run in parallel with each other
- **Within Phase 4**: T032, T033, T034 (tests) can run in parallel
- **Phase 5**: Independent from Phase 3/4 work
- **Phase 6**: T038, T039, T040, T041 all touch different files

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Phase 1 already DONE
2. Complete Phase 2: Web UI Multi-Channel Mode (6 tasks)
3. **STOP and VALIDATE**: Open web UI for a collection, verify channel overview and drill-down work
4. This delivers browsable multi-channel collections!

### Incremental Delivery

1. Phase 2 (Web UI) → Test with existing aggregate output → **Demo: browsable collection**
2. Phase 3 (Collection Add) → Test adding channels → **Demo: single-command channel setup**
3. Phase 4 (Batch Backup) → Test batch updates → **Demo: replaces cron scripts**
4. Phase 5 (Import) → Test cloning archives → **Demo: composable archives**
5. Phase 6 (Polish) → Auto-aggregate, better errors
6. Phase 7 (Cross-Search) → Test cross-channel search → **Demo: unified search**

---

## Task Summary

**Total Tasks**: 46 | **Completed**: 10 | **Remaining**: 36

**Task Count by Phase** (completed / total):
- Phase 1 (Discovery/Aggregation): 7/7 (DONE)
- Phase 2 (Web UI Multi-Channel): 3/6 (routing, loading, compat done; breadcrumb + tests remain)
- Phase 3 (Collection Add): 0/10
- Phase 4 (Batch Backup): 0/11
- Phase 5 (External Import): 0/3
- Phase 6 (Polish): 0/5
- Phase 7 (Cross-Channel Search): 0/4

**Task Count by User Story**:
- US1 (Aggregate - P1): 4 tasks (all done)
- US2 (Browse - P1): 6 tasks
- US3 (Add Channel - P2): 8 tasks
- US4 (Batch Backup - P2): 8 tasks
- US5 (Config - P2): 2 tasks (within Phase 3)
- US6 (Import - P3): 3 tasks
- US7 (Cross-Search - P4): 4 tasks
- Cross-cutting: 5 tasks (Phase 6 polish)

**Parallel Opportunities**: 14 tasks marked [P]

**Suggested MVP Scope**: Phase 2 (6 tasks) — delivers browsable multi-channel collections via web UI using existing aggregate output

---

## Notes

- [P] tasks = different files, no blocking dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tasks reference functional requirements (FR-XXX) from spec.md
- All file paths follow plan.md project structure
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
