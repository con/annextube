# Implementation Plan: MKV/WebM Video Playback Support

**Branch**: `002-mkv-video-playback` | **Date**: 2026-03-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-mkv-video-playback/spec.md`

## Summary

Improve MKV video playback across browsers. Research revealed that Video.js
does NOT demux MKV (it only wraps the native `<video>` element), and Firefox
145+ (stable since early 2026) now natively supports MKV with H.264+AAC.

The revised approach focuses on:
1. Better error detection and messaging when MKV playback fails
2. No adoption of Video.js (it doesn't solve the core problem)
3. MSE-based remuxing was implemented and removed (codec mismatch — see Phase 2)

## Technical Context

**Language/Version**: TypeScript (ES2020 target), Svelte 4.x
**Primary Dependencies**: Svelte, Vite; new: mkv-demuxer + jMuxer (optional)
**Storage**: N/A (frontend-only change)
**Testing**: Vitest + @testing-library/svelte (unit), Playwright (E2E)
**Target Platform**: Modern browsers (Chrome, Firefox 145+, Safari, Edge)
**Project Type**: Web application (frontend only — no backend changes)
**Performance Goals**: Video playback starts within 2 seconds on HTTP for @AnnexTubeTesting videos
**Constraints**: Must work on file:// protocol (core constraint); MSE fallback HTTP-only
**Scale/Scope**: Single component change (VideoPlayer.svelte) + new service module

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First | PASS | Frontend component, no library boundary change |
| II. Multi-Interface | PASS | Web UI improvement, CLI/API unchanged |
| III. Test-First | PASS | E2E tests with Playwright for cross-browser playback |
| IV. Integration Testing | PASS | Component integration tests for player behavior |
| V. Code Efficiency | PASS | Minimal change; ~32 KB gzipped optional dependency (code-split) |
| VI. Observability | PASS | Improved error messages with actionable guidance |
| VII. Versioning | PASS | No breaking changes |
| VIII. DRY | PASS | Reuses existing VideoPlayer component |
| IX. Shared Schema | PASS | No schema changes |
| X. FOSS | PASS | mkv-demuxer (MIT), jMuxer (MIT) |
| XI. Resource Efficiency | PASS | Progressive enhancement (loaded only when needed) |
| XII. Data Integrity | PASS | No data changes |
| XIII. DataLad-Native | N/A | Frontend-only, no dataset operations |

## Project Structure

### Documentation (this feature)

```text
specs/002-mkv-video-playback/
├── plan.md              # This file
├── research.md          # Phase 0: Video.js evaluation, alternatives
├── spec.md              # Feature specification
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/
│   │   └── VideoPlayer.svelte         # MODIFY: error handling, browser-specific messages
│   └── services/
│       └── browser-detect.ts          # NEW: browser/protocol detection utility
└── tests/
    └── unit/
        └── browser-detect.test.ts     # NEW: unit tests for browser detection
```

**Structure Decision**: Frontend-only change. The core modification is to
`VideoPlayer.svelte` with one new service module (browser detection).
No backend or Python changes needed. MSE remuxer was implemented and removed
(see Phase 2 showstopper).

## Implementation Phases

### Phase 1: Improved Error Detection & Messaging (P1 — MVP)

**Goal**: When MKV playback fails, show clear, actionable guidance instead of
generic errors. This is the highest-value change with minimal code.

**Changes to `VideoPlayer.svelte`**:

1. **Detect MKV-specific failure**: When `MEDIA_ERR_SRC_NOT_SUPPORTED` fires
   and the source is a `.mkv` file, show MKV-specific guidance:
   - Detect if serving over file:// vs HTTP
   - Detect browser (Firefox version, Safari, Chrome)
   - Show appropriate message:
     - Firefox <145: "Your Firefox version doesn't support MKV. Update to
       Firefox 145+ or watch on YouTube."
     - Safari: "Safari doesn't support MKV format. Use Chrome/Firefox, or
       watch on YouTube."
     - Generic: "Your browser doesn't support MKV format. Try Chrome or
       Firefox 145+, or watch on YouTube."
   - Always include a prominent "Watch on YouTube" button in the error

2. **Auto-switch to YouTube tab**: When MKV playback fails and a YouTube embed
   is available, offer a one-click switch (or optionally auto-switch after a
   short delay with user notification).

3. **Update fallback `<p>` text**: Replace the generic "Your browser doesn't
   support HTML5 video or the MKV format" with context-aware messaging.

**No new dependencies**. Pure Svelte/TypeScript changes.

### Phase 2: MSE-Based Remuxing Fallback (P2 — DEFERRED / BLOCKED)

**Status**: Deferred. Implemented and tested but **removed** due to codec mismatch.

**Showstopper**: jMuxer only supports H.264/H.265 + AAC audio. However,
annextube's default yt-dlp configuration downloads VP9+Opus (or AV1+Opus),
which are modern codecs that jMuxer cannot remux. Testing on a real archive
confirmed all videos are H.264+Opus — jMuxer rejects Opus audio.

**Impact analysis** (why MSE remuxing rarely helps):

| Typical download | Firefox <145 | Safari | MSE remuxing? |
|---|---|---|---|
| VP9+Opus (default) | Plays natively | Can't decode VP9 | No — codec issue, not container |
| AV1+Opus | Plays natively | Can't decode AV1 | No — codec issue, not container |
| H.264+Opus | Container issue | Container issue | No — jMuxer rejects Opus |
| H.264+AAC (rare) | Container issue | Container issue | **Yes** — but very rare |

MSE remuxing solves a container problem (MKV → fMP4), but the real barrier
for Safari is codec support (VP9/AV1), not the container. For Firefox <145,
VP9+Opus MKV plays natively — only H.264 in MKV fails, and when it does,
the audio is typically Opus (not AAC).

**Prerequisites to unblock**:
- A JS MSE library that supports Opus audio in fMP4 (none exist as of 2026-03)
- Or: annextube adds an option to download H.264+AAC format specifically
- Or: Safari adds VP9/AV1 decode support

**Previous implementation** (removed in this branch): mkv-demuxer + jMuxer,
code-split via dynamic import (~138 KB / ~32 KB gz on demand). Code was
functional for the H.264+AAC case but not useful for real-world archives.

### Phase 3: Consistent Player UI (P3 — optional polish)

**Goal**: If Video.js is not adopted (and it shouldn't be per research),
this phase adds minor CSS normalization to make native `<video>` controls
more consistent across browsers. This is low-priority polish.

**Approach**: Custom CSS overlay for play/pause, progress bar, volume,
and caption toggle. Use the existing `<video>` element underneath but
hide native controls and provide custom Svelte-based controls.

**Decision**: Defer this phase. The native controls work well enough and
the effort is significant for marginal UX improvement. Can be revisited
if user feedback demands it.

## Key Design Decisions

### 1. No Video.js Adoption

**Decision**: Do not adopt Video.js.
**Rationale**: Research confirmed Video.js does not demux MKV — it just wraps
`<video>`. Adding it would increase bundle size (~200 KB+) without solving the
core problem.
**Alternatives rejected**: Video.js, Plyr, MediaElement.js — all wrap native
`<video>` without adding MKV demuxing capability.

### 2. Progressive Enhancement for MSE

**Decision**: MSE remuxing is an optional fallback, not the primary playback
path.
**Rationale**: Native `<video>` is simpler, works on file://, and is the only
approach that works offline. MSE requires HTTP and adds complexity. Most users
(Chrome + Firefox 145+) don't need it.

### 3. file:// Remains Native-Only

**Decision**: No JS-based playback workaround for file:// protocol.
**Rationale**: MSE, WebCodecs, and WASM-based approaches all fail on file://
due to browser security restrictions. This is a fundamental platform
limitation. The YouTube fallback tab covers this case.

### 4. Dynamic Loading of Remuxer

**Decision**: mkv-demuxer and jMuxer loaded via dynamic import only when
needed.
**Rationale**: Keeps initial bundle size unchanged. The ~138 KB (~32 KB gz)
remuxer code is only loaded when native playback fails on HTTP.

## Bundle Size Impact

Minimal impact — only the browser detection utility (~1.5 KB) is added to the
main bundle. No new npm dependencies (MSE remuxer was removed).

## Complexity Tracking

No constitution violations requiring justification.
