# Feature Specification: MKV/WebM Video Playback Support

**Feature Branch**: `002-mkv-video-playback`
**Created**: 2026-03-16
**Status**: Draft
**Input**: User description: "We need support for .mkv in the frontend for some browsers without native support (e.g. Firefox). Video.js with vhs-utils 3.0.0 adds MKV parsing, so adopting Video.js as the overall player may solve this."

## Background

Annextube archives store videos as `video.mkv` files. Both Matroska (.mkv) and
WebM containers are used — WebM is a restricted profile of Matroska (VP8/VP9/AV1
+ Vorbis/Opus only). In a sample ReproTube collection: 309 files are Matroska,
32 are WebM, all with `.mkv` extension.

The current frontend uses a native HTML5 `<video>` element with no `type`
attribute (deliberate — specifying `type="video/x-matroska"` causes some
browsers to reject the video before attempting to load it). Browser MKV support
varies:

| Browser          | VP9+Opus in MKV | H.264+AAC in MKV | WebM container | Notes                           |
|------------------|-----------------|-------------------|----------------|---------------------------------|
| Chrome/Edge      | Yes             | Yes               | Yes            | Broad codec support             |
| Firefox 145+     | Yes             | Yes               | Yes            | MKV support added in Firefox 145 (stable early 2026) |
| Firefox <145     | Yes             | No                | Yes            | No H.264 in MKV container       |
| Safari           | No              | No                | Limited        | No native MKV support           |
| Mobile (mixed)   | Varies          | Varies            | Varies         | Platform-dependent              |

When playback fails, the user currently sees a generic error and must manually
switch to the "Play from YouTube" tab. This is a poor experience for archives
that are meant to be used offline or without YouTube access.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - MKV Playback and Error Messaging in Firefox (Priority: P1)

A researcher opens the annextube web UI in Firefox to watch archived lecture
videos. Firefox 145+ (stable since early 2026) natively supports MKV with
H.264+AAC, resolving playback for current Firefox users. For users on older
Firefox versions served over HTTP, the player automatically remuxes MKV to
MP4 via MSE so H.264+AAC content plays without manual intervention. On
file://, or if remuxing fails, the player shows a clear, browser-specific
error message with actionable guidance (update Firefox, try Chrome, or watch
on YouTube).

**Why this priority**: Firefox is a major browser used heavily in academic and
FOSS communities — the primary annextube audience.

**Independent Test**: Open an annextube archive over HTTP in Firefox <145 with
an H.264+AAC MKV file. Verify the video plays via automatic MSE remuxing.
On file://, verify the error message names the browser version and provides
a prominent "Watch on YouTube" button.

**Acceptance Scenarios**:

1. **Given** an archive with H.264+AAC encoded MKV videos served over HTTP,
   **When** a user opens the video detail page in Firefox <145, **Then** the
   video plays in the local player via MSE remuxing without manual intervention.
2. **Given** an archive with H.264+AAC encoded MKV videos on file://,
   **When** a user opens the video detail page in Firefox <145, **Then** the
   player shows an actionable error message and YouTube fallback.
3. **Given** an archive with VP9+Opus encoded MKV videos, **When** a user opens
   the video detail page in Firefox, **Then** the video plays (no regression from
   current behavior).
4. **Given** an archive with WebM-format files saved as `.mkv`, **When** a user
   opens the video in any supported browser, **Then** the video plays normally.

---

### User Story 2 - MSE Remuxing Fallback for Browsers Without Native MKV (Priority: P2)

A user opens the annextube web UI in a browser that lacks native MKV support
(Safari, Firefox <145, or other). When served over HTTP, the player
automatically demuxes MKV and remuxes to fragmented MP4 via MediaSource
Extensions, enabling transparent playback of H.264+AAC content without
manual intervention. This applies to any browser with MSE support and
H.264+AAC decoding capability — the container limitation is solved in
software.

**Why this priority**: This covers Safari (no native MKV at all) and Firefox
<145 (no H.264 in MKV). Together these represent the most common MKV
playback failures. MSE remuxing requires HTTP — on file://, users fall back
to error messaging and YouTube.

**Independent Test**: Open an annextube archive over HTTP in Safari and
Firefox <145 containing H.264+AAC MKV files and verify they play in the
local player.

**Acceptance Scenarios**:

1. **Given** an archive with H.264+AAC encoded MKV videos served over HTTP,
   **When** a user opens the video detail page in Safari, **Then** the video
   plays locally via MSE remuxing.
2. **Given** an archive with H.264+AAC encoded MKV videos served over HTTP,
   **When** a user opens the video detail page in Firefox <145, **Then** the
   video plays locally via MSE remuxing.
3. **Given** an archive with VP9+Opus encoded MKV videos, **When** a user opens
   the video in Safari (which lacks VP9 support), **Then** the player shows a
   clear message explaining the codec is unsupported and suggests the YouTube tab.
4. **Given** file:// protocol, **When** native MKV playback fails, **Then** the
   player does NOT attempt MSE remuxing and shows error message + YouTube fallback.

---

### User Story 3 - Consistent Player Controls Across Browsers (Priority: P3 — DEFERRED)

Different browsers render the native `<video>` controls differently (size,
layout, keyboard shortcuts, caption styling). A unified player UI would
provide a consistent playback experience across all browsers.

**Status**: Deferred. Native `<video>` controls work well enough. Revisit
if user feedback demands it. See plan.md Phase 3 decision.

**Acceptance Scenarios** (for future implementation):

1. **Given** any supported browser, **When** a user opens a video, **Then** the
   player UI (controls, progress bar, volume, caption toggle) is visually
   consistent.
2. **Given** a video with caption tracks, **When** a user enables captions,
   **Then** the caption display style is consistent across browsers.

---

### Edge Cases

- What happens when a video uses a codec supported by neither the browser nor
  the player library (e.g., AV1 in older Safari)? The player MUST show a
  clear, actionable error message and suggest switching to YouTube playback.
- What happens when the video file is not yet downloaded (git-annex symlink
  pointing to missing content)? Existing availability checking via HEAD request
  MUST continue to work — the player should show "file not available" before
  attempting playback.
- What happens when opened via `file://` protocol? The player MUST work without
  a web server, maintaining the current offline capability.
- What happens with the existing YouTube iframe fallback tab? It MUST remain
  fully functional — the player library only replaces the local playback tab.
- What about bundle size impact? The player library adds weight to the static
  web UI. The increase should be documented and kept reasonable for offline
  archive use.

## Clarifications

### Session 2026-03-17

- Q: Should MSE remuxing apply only to Safari or also to Firefox <145? → A: MSE remuxing applies to any browser lacking native MKV support over HTTP, including Firefox <145 and Safari. Firefox <145 supports MSE and can decode H.264+AAC in MP4 containers — it just can't handle the MKV container.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The web UI MUST play Matroska (.mkv) video files containing
  H.264+AAC streams in Firefox.
- **FR-002**: The web UI MUST play Matroska (.mkv) video files containing
  H.264+AAC streams in Safari.
- **FR-003**: The web UI MUST continue to play VP9+Opus MKV and WebM files
  in Chrome, Firefox, and Edge (no regressions).
- **FR-004**: The web UI MUST display a clear, user-friendly error message
  when a video uses a codec the browser cannot decode, and suggest switching
  to the YouTube playback tab.
- **FR-005**: The web UI MUST continue to work over the `file://` protocol
  for offline archive access.
- **FR-006**: The web UI MUST preserve the existing "Play from YouTube" tab
  as a fallback.
- **FR-007**: The web UI MUST continue to support VTT caption tracks with
  language selection.
- **FR-008**: The web UI MUST support seeking to a specific timestamp via URL
  parameter (`?t=120`) as it does today.
- **FR-009**: The web UI MUST support the existing video availability check
  (HEAD request to detect git-annex content presence) before attempting
  playback.

### Key Entities

- **Video Player**: The component responsible for local video playback,
  using the native `<video>` element with an optional MSE-based remuxing
  fallback that can demux Matroska containers in software when native
  playback fails (progressive enhancement over HTTP).
- **Codec Support Matrix**: The mapping of which codecs are playable in which
  browsers, used to provide actionable error messages.

## Assumptions

- ~~Video.js with vhs-utils is the leading candidate library.~~ **Evaluated and
  rejected** — Video.js does NOT demux MKV; it only wraps the native `<video>`
  element (see research.md). The approach uses mkv-demuxer + jMuxer instead.
- The player must work client-side only (no server-side transcoding).
- Bundle size increase is acceptable if it stays under ~500 KB gzipped
  (current frontend bundle is lightweight). Actual MSE fallback adds ~32 KB
  gzipped, code-split and loaded only when needed.
- The `video.mkv` filename convention remains unchanged — this feature solves
  playback, not file naming.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of H.264+AAC MKV videos play in the local player in
  Firefox — natively in 145+, via MSE remuxing in <145 over HTTP. On
  file://, users on Firefox <145 see actionable error messages.
- **SC-002**: 100% of H.264+AAC MKV videos play in the local player in
  Safari when served over HTTP (via MSE remuxing). On file://, users see
  an error message with YouTube fallback.
- **SC-003**: No playback regressions in Chrome/Edge for any codec/container
  combination currently working.
- **SC-004**: Caption track display works identically to the current
  implementation in all supported browsers.
- **SC-005**: Web UI continues to function over `file://` protocol without
  requiring a web server.
- **SC-006**: Users see a clear, actionable error message (not a generic
  browser error) when a codec is unsupported.
