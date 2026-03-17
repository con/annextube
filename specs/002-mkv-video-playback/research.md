# Research: MKV/WebM Video Playback Support

**Date**: 2026-03-16
**Feature**: 002-mkv-video-playback

## Key Findings

### 1. Video.js Does NOT Demux MKV

Video.js wraps the native HTML5 `<video>` element. It does **not** perform
Matroska container parsing or demuxing. The vhs-utils 3.0.0 changelog mentions
MKV parsing, but this is **container identification only** — detecting that a
file is MKV and extracting codec metadata. It is NOT a demuxer or remuxer.

If the browser's native `<video>` element cannot play MKV, Video.js cannot
either. Confirmed by [Video.js issue #5910](https://github.com/videojs/video.js/issues/5910).

**Decision**: Video.js is not a solution for MKV playback in browsers that
lack native support.

### 2. Firefox 145+ Natively Supports MKV

Firefox 145 (Nightly, late 2025) [enabled MKV by default](https://bugzilla.mozilla.org/show_bug.cgi?id=1991752)
with support for H.264, H.265, VP8, VP9, AV1 video and AAC, Opus, Vorbis audio
in Matroska containers. This was resolved as FIXED and is in stable Firefox as
of early 2026.

**Decision**: The Firefox MKV problem is self-resolving. Users on Firefox 145+
(current stable by March 2026) can play all MKV files natively.

### 3. Safari Remains Without Native MKV Support

Safari has no native MKV support and no announced plans to add it. Safari
supports H.264+AAC codecs, but only in MP4/MOV containers.

### 4. file:// Protocol Is a Hard Constraint

| Approach | Works on file://? | Reason |
|----------|-------------------|--------|
| Native `<video>` | Yes (if browser supports MKV) | No API restrictions |
| MediaSource Extensions (MSE) | **No** (unreliable) | Origin restrictions on file:// |
| WebCodecs | **No** | Requires Secure Context (HTTPS/localhost) |
| Web Workers + WASM | **No** (unreliable) | SharedArrayBuffer needs COOP/COEP headers |
| Pure JS decode + canvas | Yes, but impractical | Huge bundle, slow, no `<video>` controls |

**Decision**: For file:// protocol, only native `<video>` playback works
reliably. Any JS-based remuxing approach (MSE, WebCodecs) requires HTTP.

### 5. JS-Based Remuxing Pipeline (HTTP only)

For HTTP-served archives, a pure JS pipeline can remux MKV to fragmented MP4
for MSE playback:

1. **mkv-demuxer** (~30 KB) — parse Matroska, extract raw H.264/AAC packets
2. **jMuxer** (~40 KB) — repackage into fragmented MP4, feed to MSE
3. Browser decodes H.264+AAC natively (all modern browsers)

Total: ~70 KB, no WASM, works in all modern browsers over HTTP.

**Alternatives considered**:

| Option | Bundle Size | WASM? | Verdict |
|--------|------------|-------|---------|
| mkv-demuxer + jMuxer | ~70 KB | No | Best fit for HTTP mode |
| web-demuxer (Bilibili) | ~493 KB gz | Yes | WebCodecs only, no file:// |
| libav.js (custom build) | ~1-2 MB | Yes | Overkill, WASM complexity |
| ffmpeg.wasm | ~4.8+ MB | Yes | Too heavy |
| ogv.js | N/A | Yes | No MKV/H.264 support |

**Decision**: For HTTP-served archives, use mkv-demuxer + jMuxer as a
progressive enhancement fallback. For file://, rely on native browser support
with clear error messaging and YouTube fallback.

### 6. Current Browser MKV Support (March 2026)

| Browser | Native MKV (H.264+AAC) | Native MKV (VP9+Opus) | file:// MKV |
|---------|------------------------|----------------------|-------------|
| Chrome/Edge | Yes | Yes | Yes |
| Firefox 145+ | Yes (NEW) | Yes | Yes |
| Firefox <145 | No | Yes | Partial |
| Safari | No | No | No |
| iOS Safari | No | No | No |

With Firefox 145+ shipping MKV support, only Safari users are affected.
Safari's market share in the academic/FOSS community (annextube's primary
audience) is relatively small.

## Revised Approach

Given the research:

1. **Do not adopt Video.js** — it doesn't solve the problem and adds bundle
   weight for no benefit.
2. **Improve error messaging** — detect MKV playback failure and show
   actionable guidance (browser version, YouTube fallback).
3. **Optional progressive enhancement** — for HTTP-served archives, add
   MSE-based remuxing as a fallback for Safari users. This is a P2/P3
   enhancement, not the core fix.
4. **The Firefox problem is already solved** by browser update.

## Sources

- [Video.js Issue #5910](https://github.com/videojs/video.js/issues/5910)
- [vhs-utils CHANGELOG](https://github.com/videojs/vhs-utils/blob/main/CHANGELOG.md)
- [Firefox Bug 1991752 — Enable Matroska by default](https://bugzilla.mozilla.org/show_bug.cgi?id=1991752)
- [mkv-demuxer](https://github.com/SuperYanjun/mkv-demuxer)
- [jMuxer](https://github.com/samirkumardas/jmuxer)
- [web-demuxer (Bilibili)](https://github.com/ForeverSc/web-demuxer)
- [libav.js](https://github.com/Yahweasel/libav.js/)
- [ffmpeg.wasm](https://github.com/ffmpegwasm/ffmpeg.wasm)
