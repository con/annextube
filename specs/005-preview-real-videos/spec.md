# Feature Specification: Real Video Playback in PR Previews

**Feature Branch**: `005-preview-real-videos`
**Created**: 2026-09-17
**Status**: Draft
**Input**: GitHub issue con/annextube#32 ("Improve Preview with some real videos
(downscaled)"), opened by yarikoptic as a direct follow-up to issue #21 / PR
#25 (`specs/004-pr-webui-preview/`): *"not sure if we could host those large
videos fully as committed to git but likely we could downscale them
considerably (e.g. to 320x200 or alike) and may be cut out short snippets of
them do contain/rehost in that dataset in that form to be reused in the per
PR previews etc"*.

## Context: the gap this closes

PR #25 (`specs/004-pr-webui-preview/`) built the per-PR web UI preview
pipeline: an untrusted build job clones the separate `con/annextubetesting`
repository, exports it, drops any git-annex symlinks it cannot materialize
(`find ... -type l -delete`), runs `annextube generate-web`, and a trusted
publish job copies the result under `gh-pages:/pr-<number>/`. That plan's own
`research.md` and `data-model.md` document the resulting gap explicitly:
`con/annextubetesting`'s `.gitattributes` keeps only thumbnails, metadata, and
TSV/JSON as plain git content; every `video.mkv` is git-annex/URL-backed and
was never fetched into that repository, so the build job's symlink-drop step
deletes all ten of them before `generate-web` even runs. **Previews
currently render metadata, thumbnails, and playlists only — the "Play from
Archive" tab never has anything to play.** This spec is about closing exactly
that gap, not re-litigating any part of 004's publish/build/teardown design
(which is unaffected — see `research.md` and `plan.md`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reviewer sees a real, playable video in a preview (Priority: P1)

A maintainer reviewing a PR that touches `VideoPlayer.svelte` (or any other
video-playback-affecting code) opens its preview and wants to actually press
play on at least one video, not just read its title/thumbnail/description —
today the "Play from Archive" tab is not even offered because no
`con/annextubetesting` video has a real file on disk.

**Why this priority**: This is the entire point of issue #32 — without it,
"Play from Archive" is dead code as far as the preview environment is
concerned, and any PR that changes video-playback behavior (error handling,
caption tracks, seek behavior, the MKV-unsupported-browser fallback) cannot
be exercised end-to-end in its own preview.

**Independent Test**: Open (or refresh) a PR preview built after this
feature's curated content lands in `con/annextubetesting`, open a video that
has curated content, confirm the "Play from Archive" tab appears and the
video plays natively in the browser.

**Acceptance Scenarios**:

1. **Given** a PR preview built from `con/annextubetesting` after curated
   video content has been added, **When** a reviewer opens a video that has
   curated content, **Then** the "Play from Archive" tab is offered (not just
   "Play from YouTube") and clicking it plays a real, short video.
2. **Given** the same preview, **When** the reviewer looks at the video
   listing page, **Then** that video's hover-preview and "downloaded"
   status badge behave the same way they would for any other archived video
   (i.e. the curated content is indistinguishable, from the frontend's own
   logic's point of view, from an ordinarily-downloaded video — see
   `research.md`'s findings on `VideoCard.svelte`/`VideoPlayer.svelte`).
3. **Given** a video that does *not* have curated content, **When** a
   reviewer opens it, **Then** the preview behaves exactly as it does today
   (metadata/thumbnail only, "Play from YouTube" only) — this feature adds
   curated content for a small, named subset of videos, not all of them.

---

### User Story 2 - The curation step stays a one-time, out-of-band maintainer action (Priority: P1)

A maintainer needs to be able to (re-)produce or extend the curated video set
without that work ever becoming a hidden dependency of CI, and without a PR
author's build job silently trying (and failing, per the bot-detection
constraint `docs/content/how-to/troubleshooting.md` and `research.md` of 004
already document) to reach YouTube.

**Why this priority**: Violating this would reintroduce exactly the failure
mode 004 was designed around (`FR-011`/`SC-004` of `specs/004-pr-webui-preview/spec.md`:
never fetch from the video platform per preview, or at build time at all).
It is equally load-bearing as User Story 1 — a design that makes previews
show real video but does so by fetching from YouTube in CI is not an
acceptable solution to issue #32.

**Independent Test**: Confirm that no file under `.github/workflows/` or
`annextube/cli/` is modified to add a live YouTube-fetch code path, and that
`quickstart.md`'s curation steps are documented as something a maintainer
runs locally/out-of-band, not as a CI step.

**Acceptance Scenarios**:

1. **Given** the existing PR-preview build workflow
   (`pr-webui-preview-build.yml`), **When** it runs (including for a fork
   PR, with no secrets), **Then** it still never contacts YouTube and still
   never needs to — it only benefits from curated content because that
   content already sits as ordinary, real files in the
   `con/annextubetesting` clone it makes.
2. **Given** a maintainer wants to add or refresh a curated video,
   **When** they follow `quickstart.md`, **Then** the only network access
   required (to YouTube, via `yt-dlp`) happens on their own machine, not in
   any GitHub Actions job.

### Edge Cases

- What happens if the curated file's resolution/duration guess turns out to
  be wrong for some future, less-trivial test video (the current
  `@AnnexTubeTesting` catalog is all 1-5 second synthetic solid-color clips —
  see `research.md`)? The curation process (a plain `yt-dlp`/`ffmpeg`
  invocation, documented, not baked into `annextube` library code) is cheap
  to re-run with different parameters; this is explicitly a maintainer
  action, not a one-shot irreversible pipeline.
- What happens to a reviewer's experience for the many videos that don't get
  curated content in this first increment? Unchanged from today — metadata/
  thumbnail-only preview, exactly as 004 already ships. This spec does not
  claim to make every preview video playable.
- What happens if a curated video's `download_status` isn't bumped to
  `"downloaded"` alongside the real file that now exists at its `video.mkv`
  path? `VideoPlayer.svelte`'s "Play from Archive" tab (a live `HEAD` check,
  independent of `download_status`) and `VideoCard.svelte`'s hover-preview
  (already gated to allow both `"tracked"`, these videos' current value, and
  `"downloaded"`) would both keep working either way — verified directly
  against the actual dataset and code, not assumed (`research.md`). The one
  real gap is cosmetic but worth closing: `VideoCard.svelte`'s status *badge*
  has no rendering branch for `"tracked"`, so it would keep showing no badge
  for a video that now actually plays. `quickstart.md` updates
  `download_status` for exactly this reason.
- What happens if a maintainer runs the curation steps against a video whose
  YouTube-reported license is not Creative Commons? `quickstart.md` scopes
  the recommended first videos to the channel's own
  `All-Creative-Commons-Videos` playlist specifically to sidestep that
  question rather than resolve it — see `research.md`'s licensing note for
  why "standard license" test uploads on the project's own test channel are
  a judgment call this spec deliberately does not need to make yet.
- What happens to `gh-pages` storage/history growth from adding real (if
  tiny) video files to previews? Bounded by the same mechanism 004 already
  established for thumbnails/metadata: each concurrently open PR's subpath
  gets its own copy, removed on close (FR-009 of `specs/004-pr-webui-preview/spec.md`).
  A curated video adds tens of kilobytes per preview, not megabytes — see
  `research.md`'s prototype numbers — so this doesn't change 004's existing
  Complexity Tracking tradeoff in any material way.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The preview source dataset (`con/annextubetesting`) MUST gain
  real, playable, downscaled video content for a small, explicitly bounded
  subset of its videos (1-3 for this first increment — see `research.md` and
  `plan.md`'s Scale/Scope), so that at least one PR preview video offers
  genuine in-browser playback via the existing "Play from Archive" tab.
- **FR-002**: That curated content MUST be produced entirely outside of any
  GitHub Actions job (build, publish, or otherwise) — by a maintainer running
  documented commands locally, with their own real YouTube/network access —
  and MUST NOT introduce any new live-YouTube-fetch code path into
  `annextube/`, `.github/workflows/`, or `tools/`.
- **FR-003**: Curated content MUST be consumable by the *existing*
  build/publish pipeline (`annextube generate-web`,
  `annextube/cli/prepare_ghpages.py`'s `copy_data_to_ghpages`/
  `_copy_tree_no_symlinks`, the `pr-webui-preview-*.yml` workflows) with
  **no code change** to any of them — i.e. it MUST take the exact on-disk
  shape (`videos/<file_path>/video.mkv`, plain git content, not a
  git-annex symlink) those already expect and already copy verbatim. See
  `research.md`'s "Decision: reuse the existing pipeline unmodified" for the
  verification this rests on.
- **FR-004**: Adding curated content for a video MUST update its
  `download_status` to `"downloaded"` in both `videos/videos.tsv` (the field
  the frontend actually reads — see `research.md`) and that video's own
  `metadata.json`, consistent with the real file now present. Hover-preview
  and "Play from Archive" already work without this (both are gated to
  accept `"tracked"`, these videos' current value, not just `"downloaded"`
  — verified against the actual code, not assumed), but `VideoCard.svelte`'s
  status *badge* has no rendering branch for `"tracked"`, so leaving it
  unchanged would show no "available locally" badge for a video that
  actually plays — a real, if cosmetic, inconsistency this FR closes.
- **FR-005**: Curated video files MUST be added to `con/annextubetesting` as
  plain git content, not git-annex-backed, via an explicit
  `.gitattributes` override scoped to those specific file paths — following
  the precedent that repository's `.gitattributes` already sets for
  `videos/2026/02/*/thumbnail.jpg` — rather than changing that repository's
  default largefiles policy.
- **FR-006**: The default resolution/duration/format for curated content
  MUST be chosen and justified against concrete size evidence (not merely
  quoted from the issue), and MUST preserve the source video's native aspect
  ratio rather than force-fitting the issue's literal "320x200" suggestion
  where that would distort or letterbox 16:9 source video. See
  `research.md`'s decision and prototype numbers.
- **FR-007**: This feature MUST NOT propose or require a general-purpose
  video-transcoding pipeline, a new `annextube` CLI command, or a new CLI
  option on an existing download command in this design increment — the
  first increment's curation step is a documented, manual `yt-dlp`/`ffmpeg`
  invocation (`quickstart.md`), not new application code. A CLI option for
  resolution-capped downloads is recorded as a candidate future enhancement
  (`research.md`) only if this pattern needs to scale to many more videos
  later.

### Key Entities

- **Curated Preview Video**: A single video within `con/annextubetesting`
  for which the normally-dangling `video.mkv` git-annex symlink has been
  replaced with a real, downscaled, plain-git file, plus a consistent
  `download_status`/`videos.tsv` update. Bounded in count (1-3 for this
  increment); produced and refreshed only by a maintainer, out-of-band.
- **Preview Source Dataset** (`con/annextubetesting`): Unchanged in identity
  from `specs/004-pr-webui-preview/data-model.md` — this feature only adds
  content to it (a handful of real video files plus a `.gitattributes`
  override), it does not change which repository previews read from or how
  previews clone/export/publish it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one video rendered in a `con/annextube` PR preview
  offers a working "Play from Archive" tab that plays real video content
  natively in the browser (not a 404, not silently falling back to
  "Play from YouTube" only).
- **SC-002**: Zero new live-YouTube-fetch code paths exist in
  `.github/workflows/` or `annextube/` after this feature — verified by diff
  review of exactly which files this feature's implementation phase touches.
- **SC-003**: The curated video content's total size stays in the tens-of-
  kilobytes-per-video range (not megabytes), verified against the
  prototype numbers in `research.md` and re-confirmed with `ffprobe`/`ls -la`
  once real curated files exist.
- **SC-004**: No existing `pytest`/`playwright`/`shellcheck` check regresses,
  and no change is needed to `annextube/cli/prepare_ghpages.py`,
  `annextube/cli/generate_web.py`, or any `pr-webui-preview-*.yml` workflow
  to make SC-001 true (confirms FR-003's "no code change" claim rather than
  merely asserting it).

## Assumptions

- The `@AnnexTubeTesting` channel's existing videos (all real, already-
  archived YouTube uploads per `con/annextubetesting`'s own `videos.tsv`) are
  an acceptable source for curated content, even though — verified directly,
  not assumed — every one of its ten current videos is a synthetic,
  1-5 second, solid-color test clip (e.g. "Test video with Creative Commons
  license. 1 second, solid yellow."), not "real" footage in the everyday
  sense. This is judged sufficient for this issue's actual goal (exercising
  the real playback code path in a preview), not a claim that curated
  content will look visually interesting to a reviewer. If a more visually
  substantial sample is ever wanted, that is a content decision for whoever
  maintains `@AnnexTubeTesting`, out of scope for this spec.
- Because the current test videos are already 1-5 seconds, "cut out short
  snippets" (the issue's own suggestion) is not a separate step this
  increment needs to implement — downscaling the existing, already-short
  video is sufficient. The snippet-cutting capability the issue anticipates
  remains available (`yt-dlp --download-sections`, documented in
  `research.md`) as a future step if a longer video is ever curated.
- No YouTube network access was available in the environment that produced
  this design (see `research.md`); the concrete size/quality numbers backing
  FR-006/SC-003 come from a real `ffmpeg` prototype run against a freely-
  licensed (CC BY 3.0) reference video (Big Buck Bunny, fetched from a small
  public GitHub-hosted sample), not against actual `@AnnexTubeTesting`
  content — clearly labeled as such throughout `research.md` and never
  presented as if it were real YouTube-sourced output.
