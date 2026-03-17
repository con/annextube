# Tasks: MKV/WebM Video Playback Support

**Input**: Design documents from `/specs/002-mkv-video-playback/`
**Prerequisites**: plan.md (required), spec.md (required), research.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new project setup needed — this feature modifies the existing
frontend. This phase covers prerequisite research validation only.

- [x] T001 Verify Firefox 145+ MKV support by testing a local H.264+AAC MKV file in current Firefox stable (manual browser test)
- [x] T002 [P] Verify current VideoPlayer.svelte error handling behavior in Chrome, Firefox, and Safari with an H.264+AAC MKV file (manual baseline test)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the browser detection utility used by both US1 and US2.

- [x] T003 Create browser/protocol detection utility in `frontend/src/services/browser-detect.ts` — export functions: `isSafari()`, `isFirefox()`, `getFirefoxVersion()`, `isFileProtocol()`, `supportsMediaSource()`
- [x] T004 [P] Add unit tests for browser detection utility in `frontend/tests/unit/browser-detect.test.ts`

**Checkpoint**: Browser detection utility ready — user story implementation can begin

---

## Phase 3: User Story 1 — MKV Error Messaging in Firefox (Priority: P1)

**Goal**: When MKV playback fails, show clear, browser-specific error messages
with actionable guidance instead of a generic error. This is the MVP —
zero new dependencies, pure TypeScript/Svelte changes.

**Independent Test**: Open an annextube archive in Firefox <145 or Safari with
an H.264+AAC MKV file. Verify the error message names the specific browser,
explains the issue, and provides a prominent "Watch on YouTube" button.

### Implementation for User Story 1

- [x] T005 [US1] Refactor `handleVideoError()` in `frontend/src/components/VideoPlayer.svelte` to detect MKV-specific failures: when error code is `MEDIA_ERR_SRC_NOT_SUPPORTED` and source URL ends in `.mkv`, call browser detection utility to generate context-aware error message
- [x] T006 [US1] Add browser-specific error messages to `handleVideoError()` in `frontend/src/components/VideoPlayer.svelte`: Firefox <145 → "Update Firefox to 145+"; Safari → "Safari doesn't support MKV, use Chrome/Firefox"; generic → "Try Chrome or Firefox 145+"
- [x] T007 [US1] Add prominent "Watch on YouTube" button to the MKV error message UI in `frontend/src/components/VideoPlayer.svelte` — the button should call `switchTab('youtube')` and be visually distinct (primary action style)
- [x] T008 [US1] Update the HTML5 fallback `<p>` text in `frontend/src/components/VideoPlayer.svelte` from generic "Your browser doesn't support HTML5 video or the MKV format" to context-aware message using browser detection
- [ ] T009 [US1] Verify no regressions: VP9+Opus MKV files still play in Chrome and Firefox, caption tracks load correctly, `?t=` timestamp seeking works, file:// protocol works (manual E2E verification)

**Checkpoint**: MKV playback failures show actionable, browser-specific guidance. MVP complete.

---

## Phase 4: User Story 2 — MSE Remuxing Fallback (Priority: P2 — DEFERRED / BLOCKED)

**Status**: Implemented, tested, and **removed** due to codec mismatch showstopper.

**Showstopper**: jMuxer only supports H.264+AAC audio, but annextube's default
yt-dlp format selection downloads VP9+Opus (or AV1+Opus). Real-world testing
confirmed all archive videos have H.264+Opus — jMuxer rejects Opus audio.
MSE remuxing solves a container problem (MKV→fMP4), but the real barrier for
Safari is codec support (VP9/AV1), not the container. For Firefox <145,
VP9+Opus MKV plays natively — only H.264 in MKV fails, and when it does, the
audio is typically Opus (not AAC).

**Prerequisites to unblock** (any one):
- A JS MSE library that supports Opus audio in fMP4
- annextube option to force H.264+AAC downloads
- Safari VP9/AV1 decode support

*All T010-T019 tasks were completed and reverted. No tasks remain for this phase.*

---

## Phase 5: User Story 3 — Consistent Player UI (Priority: P3 — DEFERRED)

**Goal**: Consistent player controls across browsers.

**Decision**: Deferred per plan.md. Native `<video>` controls work well enough.
Revisit if user feedback demands it.

*No tasks generated for this phase.*

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, documentation, bundle size verification

- [x] T020 Measure bundle size impact: run `cd frontend && npm run build` and compare `web/assets/` size before and after changes. Document in plan.md. Verify remuxer is code-split (not in initial bundle).
- [x] T021 [P] Update `frontend/src/components/VideoPlayer.svelte` inline comments to document the MKV playback strategy (native first → MSE fallback → YouTube fallback)
- [ ] T022 [P] Run `annextube generate-web` on a test archive and verify the updated player works end-to-end (manual E2E verification)
- [x] T023 Regenerate web UI for existing archives by running `annextube generate-web` (this is done by archive maintainers, not automated — document in quickstart.md)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — manual verification
- **Foundational (Phase 2)**: No dependencies — can start immediately
- **User Story 1 (Phase 3)**: Depends on Phase 2 (browser detection utility)
- **User Story 2 (Phase 4)**: Depends on Phase 3 (error handling refactor)
- **User Story 3 (Phase 5)**: DEFERRED
- **Polish (Phase 6)**: Depends on all completed user stories

### User Story Dependencies

- **User Story 1 (P1)**: Depends on T003 (browser detection utility). Independently testable after completion.
- **User Story 2 (P2)**: Depends on US1 completion (T005-T009) because it extends the error handler. Independently testable after completion.
- **User Story 3 (P3)**: DEFERRED. No dependencies generated.

### Within Each User Story

- T005 before T006 (error detection before messages)
- T006 before T007 (messages before UI button)
- T010 before T011 (deps before service)
- T011 before T012-T013 (core before seeking/cleanup)
- T014 before T015-T018 (integration before edge cases)

### Parallel Opportunities

```bash
# Phase 2 — both can run in parallel:
T003: Browser detection utility
T004: Unit tests for browser detection

# Phase 4 — test in parallel with documentation:
T019: Unit tests for mkv-remuxer
T020: Bundle size measurement (Phase 6, but can start early)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Manual verification (T001-T002)
2. Complete Phase 2: Browser detection utility (T003-T004)
3. Complete Phase 3: Error messaging (T005-T009)
4. **STOP and VALIDATE**: Test in Firefox, Safari, Chrome — verify actionable
   error messages appear for unsupported MKV and no regressions for working MKV
5. Ship MVP — this alone solves the most visible user pain

### Incremental Delivery

1. MVP (Phase 1-3) → Actionable error messages for all browsers
2. Add User Story 2 (Phase 4) → Safari can play H.264+AAC MKV over HTTP
3. Polish (Phase 6) → Bundle size documented, comments updated

### Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- US3 (consistent player UI) is deferred — can be added later
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
