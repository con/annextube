# Implementation Plan: Real Video Playback in PR Previews

**Branch**: `005-preview-real-videos` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-preview-real-videos/spec.md`

**Note**: Per issue #32 and this repo's own precedent for non-trivial
features (issue #21 → PR #25's design-first `specs/004-pr-webui-preview/`),
this PR delivers design-plan artifacts only (`spec.md`, `research.md`, this
`plan.md`, `quickstart.md`). It deliberately does **not** implement the
actual curation (no real curated video files are added here — this sandbox
has no YouTube network access to produce them, and fabricating video content
would violate this project's data-integrity stance, see `research.md`'s
Environment check and Constitution Principle XII, as already invoked by
004's own `research.md` when it rejected synthetic/mocked preview data).
`data-model.md`/`contracts/` are intentionally omitted
— this feature adds no new workflow trigger, API, or CLI contract (see
Constitution Check below); `research.md`'s "Decision: reuse the existing
pipeline unmodified" section *is* the data-model-equivalent finding for this
feature, so a separate `data-model.md` would only restate it.

## Summary

Issue #32 asks for real (downscaled) video content in PR previews, following
up on 004/PR #25's own documented gap: `con/annextubetesting` keeps only
thumbnails/metadata/TSV/JSON as plain git content, so previews render no
actual video. This plan adds a small, explicitly bounded set of curated,
downscaled `video.mkv` files (1-3 videos, sourced from the channel's own
Creative-Commons-licensed test videos) directly to `con/annextubetesting`,
produced once by a maintainer with real YouTube access
(`quickstart.md`) — **not** by any CI job. Verified against the actual
`prepare_ghpages.py`/`generate_web.py`/workflow code
(`research.md`), no change to any of them is needed: `VideoPlayer.svelte`
already resolves `video.mkv` by a fixed convention and a live `HEAD` check,
so a real file at that path is immediately picked up by the existing
pipeline. The only things that change are (a) data inside the separate
`con/annextubetesting` repository, and (b) that repository's own
`.gitattributes`, neither of which is part of this (`con/annextube`)
repository's own source tree.

## Technical Context

**Language/Version**: N/A for this PR's own diff (documentation only); the
curation step itself uses `yt-dlp` (already an `annextube` dependency) and
`ffmpeg` (a new, one-time, maintainer-machine-only tool requirement — not
added as a project dependency, since no application code invokes it).
**Primary Dependencies**: None added to `annextube`/`frontend`. The curation
step depends on `yt-dlp` (already used by the project) and `ffmpeg`
(maintainer's own machine only).
**Storage**: No change to this repository's storage model. The separate
`con/annextubetesting` repository gains a handful of real `video.mkv` files
(tens of KB each, per `research.md`'s prototype) as plain git content, plus
a `.gitattributes` override scoped to those specific paths — the same
plain-git-override mechanism already used for `thumbnail.jpg` there.
**Testing**: No new automated test is added by *this* PR (it adds no
`annextube`/`frontend` code — see FR-003/FR-007). Once curated content
actually exists in `con/annextubetesting` (a follow-up, out-of-band step —
see `quickstart.md`), the existing manual verification pattern 004's own
`tasks.md` T010 already established (build a preview end-to-end, look at it)
is how SC-001 gets checked; `pytest`/`playwright`/`shellcheck` in *this*
repository are unaffected and continue to run unmodified (SC-004).
**Target Platform**: Same as 004 — GitHub-hosted Actions runners for the
existing preview build/publish/teardown workflows (unmodified), a
maintainer's own machine for the one-time curation step.
**Project Type**: Design/data-curation, not a code feature — analogous to
how 004 itself treats `con/annextubetesting`'s existence/refresh as external
to `con/annextube`'s own source tree.
**Performance Goals**: Unaffected — curated files are tens of KB; 004's own
SC-001 (~2 minutes from push to interactive preview) has no new bottleneck
introduced by a few extra, tiny files being copied alongside the data this
pipeline already copies.
**Constraints**: Same non-negotiable constraint 004 already established and
this spec's User Story 2 reaffirms — **no live YouTube fetch in any CI job,
ever** — carried forward unchanged, not weakened, by this feature.
**Scale/Scope**: 1-3 curated videos for this first increment (FR-001,
`research.md`'s "Decision: which videos to curate, and how many") — not the
full 10-video `@AnnexTubeTesting` catalog, and explicitly not a general
video-processing pipeline (FR-007).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **XII. Data Integrity & Authenticity** (no fabricated/synthetic data in
  normal operation): PASS — this design's curated content is real,
  downscaled YouTube-sourced video (produced by a maintainer with real
  network access, per `quickstart.md`), not synthesized/mocked. This PR
  itself adds no video bytes at all (see Note above) — it would be a
  violation of this same principle to fabricate placeholder video content
  in a sandbox with no way to verify it against a real source, which is
  exactly why this PR stays a design plan.
- **XI. Resource Efficiency**: PASS — curated files are tens of KB each
  (`research.md`), and the design explicitly avoids scaling this beyond 1-3
  videos (FR-001/FR-007) or adding a new always-on pipeline.
- **V. Code Efficiency & Conciseness** / **VIII. DRY**: PASS, more strongly
  than a typical judgment call — `research.md`'s "Decision: reuse the
  existing pipeline unmodified" verifies directly against the code that
  *zero* lines change in `annextube/`, `frontend/`, or
  `.github/workflows/` to satisfy this feature's requirements. The only
  "new code" this design contemplates at all (a possible future
  resolution-cap CLI option) is explicitly deferred, not written now
  (FR-007).
- **X. FOSS Principles** (offline capability / no new mandatory cloud
  dependency): PASS — no new external service; `ffmpeg` is a maintainer-
  local, one-time tool, not a new runtime or CI dependency.
- **XIII. DataLad-Native Operations**: PASS — the curated files are added
  to `con/annextubetesting` as plain git content via an ordinary
  `.gitattributes` override (the same mechanism already used for
  `thumbnail.jpg` there), not via new raw git-annex plumbing of this
  feature's own invention.

No unresolved violations. No judgment-call tradeoff rises to the level of
004's GitHub-Pages-vs-Netlify one — see Complexity Tracking below for the
two real, smaller judgment calls this design does record.

## Project Structure

### Documentation (this feature)

```text
specs/005-preview-real-videos/
├── plan.md              # This file
├── research.md          # Phase 0 output
└── quickstart.md         # Phase 1 output — the maintainer curation steps
```

`data-model.md` and `contracts/` are intentionally omitted (see Note above)
— this feature introduces no new workflow trigger, CLI contract, or data
schema; `research.md`'s verification that the *existing* pipeline needs no
change *is* this feature's data-model-equivalent finding.

### Source Code (repository root)

**No `annextube/`, `frontend/`, `.github/workflows/`, or `tools/` file in
*this* repository (`con/annextube`) is added or modified by this feature's
implementation phase.** This is the central, verified (not assumed) finding
of `research.md`. The only content that changes as a result of implementing
this plan lives in the separate `con/annextubetesting` repository:

```text
(in the separate con/annextubetesting repository — NOT this repo)
videos/2026/02/2026-02-05_Test-Video-Creative-Commons-1/
└── video.mkv                 # NEW — real file replacing the dangling
                               #   git-annex symlink; downscaled to 320px
                               #   wide, plain git content
.gitattributes                 # gains a scoped override, e.g.:
                               #   videos/2026/02/2026-02-05_Test-Video-Creative-Commons-1/video.mkv annex.largefiles=nothing
                               #   (mirrors the existing thumbnail.jpg override)
```

(Repeated for up to 2 more curated videos per FR-001's 1-3 scope — see
`quickstart.md` for the exact commands and which videos are recommended.)

**Structure Decision**: No new top-level module or workflow in
`con/annextube`. This is, deliberately, a data-only change scoped to the
already-separate preview-source repository, following the same "not part of
this repo's own source tree" precedent 004 already set for
`con/annextubetesting`'s existence and refresh process
(`specs/004-pr-webui-preview/data-model.md`, "refresh_process": out of
scope for that feature to change).

## Complexity Tracking

> Recorded for visibility — neither is a constitution violation, but each is
> a real judgment call worth an explicit record rather than a silent PASS.

| Judgment call | Why an alternative was considered | Why the recommended option was chosen |
|---|---|---|
| Reusing the existing `"downloaded"` `download_status` value for a curated-but-lossy preview file, vs. introducing a new status value | A new value (e.g. `"preview_only"`) would let the frontend distinguish "this is a real archival copy" from "this is a downscaled preview copy" explicitly, which is arguably more honest | A new value requires `frontend/` type/UI changes this feature's FR-003 explicitly avoids, for a distinction that only matters to someone reading `con/annextubetesting`'s own source — not to a PR reviewer's actual workflow. Documenting the distinction in that repository's own README is judged sufficient. See `research.md`'s "Decision: `download_status` semantics". |
| Deferring a resolution-cap CLI option (e.g. `--max-height` on a download command) instead of adding it now | Would make future curation-step re-runs (or curating more videos later) more convenient and less manual | Cannot be verified in this sandbox (no YouTube network access — see `research.md`'s Environment check), and the current 1-3-video, one-time scope doesn't need it yet. Adding unverifiable application code speculatively would itself be a bigger risk than the manual `yt-dlp`/`ffmpeg` one-liner this plan documents instead. Recorded as a deferred (not rejected) future step. |

## Follow-up (out of scope for this PR, tracked for whoever picks this up next)

- Actually run `quickstart.md`'s curation steps against real
  `@AnnexTubeTesting` content and push the result to `con/annextubetesting`
  — requires a maintainer with real YouTube network access; not achievable
  in this sandboxed session (`research.md`'s Environment check).
  **This is the honest, expected state of this design plan**: it specifies
  exactly what to produce and how it plugs into the existing pipeline
  without needing that pipeline's own code to change, but the actual
  curated video bytes are not part of this PR.
- Once curated content exists, do the equivalent of 004's own `tasks.md`
  T010 (a real, manual end-to-end preview build/verification) before
  considering issue #32 fully closed — not just "the plan was written."
