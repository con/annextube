# Phase 0 Research: Real Video Playback in PR Previews

## Environment check: what's actually feasible here

Before designing anything, this session checked what this sandbox itself can
do, since issue #32 explicitly asks for real (if downscaled) video content:

- **YouTube/general internet access**: not available. The session's egress
  proxy allows `github.com`/`raw.githubusercontent.com`/`pypi.org`/
  `registry.npmjs.org`/Ubuntu package mirrors, but denies most other hosts
  outright by organization policy at the proxy itself (`datasets.datalad.org`,
  `huggingface.co`, and `pixi.sh` all came back as `connect_rejected` /
  403 directly from the proxy, per its own status endpoint — not from the
  destination). A separate attempt at a well-known public Google Cloud
  Storage sample-video URL got a *tunnel* through the proxy (so that host
  isn't proxy-blocked) but a 403 from Google's own server on that specific
  object — a different, unrelated failure, not evidence either way about
  proxy policy for that host. No attempt was made to reach
  `youtube.com`/`googlevideo.com` directly —
  `docs/content/how-to/troubleshooting.md` documents YouTube's bot-detection
  behavior generally, and `.github/workflows/deploy-demo.yml`'s own comment
  (quoted in 004's `research.md`) is more specific: "YouTube blocks
  datacenter IPs" — which this sandbox's egress is, regardless of what the
  proxy itself allows.
- **`ffmpeg`**: not preinstalled, but installable from the Ubuntu archive
  mirror (`apt-get install ffmpeg`, itself reachable) — version 6.1.1.
- **A real, small, freely-licensed sample video**: reachable. `raw.githubusercontent.com`
  serves `mediaelement/mediaelement-files`' `big_buck_bunny.mp4` (a
  standard, freely-licensed 640x360, 60s, 5.5MB H.264/AAC sample used widely
  for browser video-tag testing) with `Content-Length: 5510872` and
  `Accept-Ranges: bytes`.

This means a real (if not YouTube-sourced) ffmpeg downscale/snippet pipeline
*could* be prototyped end-to-end, which the next section does. It also means
the actual `@AnnexTubeTesting` content could **not** be fetched in this
session — the curation step this design recommends is something only a
maintainer with real YouTube access can execute (see "Decision: curation is
a maintainer-run, out-of-band step" below).

## Real ffmpeg prototype (proof of concept, not YouTube content)

Run against the downloaded `big_buck_bunny.mp4` (640x360, 60.1s, h264/aac,
5,510,872 bytes = ~91.8 KB/s average bitrate):

| Variant | Command shape | Resolution | Duration | Audio | Output size |
|---|---|---|---|---|---|
| Source | — | 640x360 | 60.1s | AAC | 5,510,872 bytes |
| A | `scale=320:-2`, `-crf 32`, `-preset veryslow` | 320x180 | 8s | none | 55,488 bytes |
| B | same, `-crf 28` | 320x180 | 8s | none | 95,353 bytes |
| C | same as A, 4s | 320x180 | 4s | none | 24,333 bytes |
| D | `scale=240:-2`, `-crf 32` | 240x135 | 8s | none | 33,589 bytes |
| E | same as A, muxed into `.mkv` instead of `.mp4` | 320x180 | 3s | none | 15,799 bytes |

Takeaways this design leans on:

1. **A 320-pixel-wide, few-second, silent H.264 clip costs tens of
   kilobytes**, not megabytes — two to three orders of magnitude smaller
   than typical original YouTube video, and small enough that committing a
   handful of these as plain git blobs (not git-annex) is a non-issue for
   repository size (`con/annextubetesting`'s entire git history today is
   dominated by JSON/TSV/thumbnails, already plain git content of a similar
   order of magnitude per file).
2. **The container doesn't matter to the encode cost**: muxing into
   `.mkv` instead of `.mp4` (Variant E) works exactly as expected with
   plain `ffmpeg -i ... out.mkv` — relevant because the frontend hardcodes
   the filename `video.mkv` (see below), so curated content must be
   produced (or remuxed) into that container regardless of what format it
   started as.
3. Real `@AnnexTubeTesting` videos are already only 1-5 seconds (see next
   section) — shorter than every prototype variant above — so real curated
   output will be smaller still than these numbers, not larger.

These numbers are illustrative of *order of magnitude*, not a claim about
what the real curated files will measure — they were produced against a
generic 640x360 sample, not actual `@AnnexTubeTesting` source video, which
this session had no way to fetch (see above).

## What `con/annextubetesting` actually contains today (verified, not assumed)

Cloned anonymously (`git clone --depth=1 https://github.com/con/annextubetesting.git`)
and inspected directly, correcting/confirming what `specs/004-pr-webui-preview/research.md`
already found:

- **10 videos total** (verified by directory count and `videos/videos.tsv`'s
  row count — an earlier draft of this research miscounted this as 12 by
  including the `videos/2026` and `videos/2026/02` container directories
  themselves), all under `videos/2026/02/`. Every one of them has a
  `video.mkv` that is a **dangling symlink** into
  `.git/annex/objects/.../URL--yt&c...` — i.e. exactly what 004's `research.md`
  already documented: git-annex/URL-backed, never fetched into this
  repository.
- **Every video's real duration is 1-5 seconds**, and every description
  says so explicitly, e.g.: `"Test video with Creative Commons license. 1
  second, solid yellow."`, `"...2 seconds, solid magenta."`,
  `"...3 seconds, solid cyan."`. These are synthetic, minimal test fixtures
  — real YouTube uploads (real `video_id`s, real URLs, listed in a real
  `All-Creative-Commons-Videos` playlist), but not visually substantial
  footage.
- **Licensing is mixed and explicit per video**: `metadata.json`'s `license`
  field is `"Creative Commons Attribution license (reuse allowed)"` for
  5 of the 10 (the three numbered "Creative Commons" videos, "Multi-language
  Captions", and "Recorded in London"); the remaining 5 are `"standard"`
  (including, notably, "Test-Video-With-English-Captions" — the one other
  video with caption tracks).
  `con/annextubetesting`'s own `playlists/All-Creative-Commons-Videos/`
  already curates exactly the CC-licensed subset.
- **`.gitattributes` already has a precedent for a plain-git override on a
  specific video-directory path**: `videos/2026/02/*/thumbnail.jpg
  annex.largefiles=nothing` sits alongside the default rule that sends any
  binary file over 10KB to git-annex. This is the exact mechanism this
  feature's curated `video.mkv` files need, scoped per curated video path
  rather than changed globally.

## Decision: which videos to curate, and how many

**Decision**: Curate a small, explicitly named subset — **1 to 3 videos**
from the channel's own `All-Creative-Commons-Videos` playlist (e.g.
`Test-Video-Creative-Commons-1` for plain playback, plus
`Test-Video-Multi-language-Captions` to also exercise the caption-track code
path `VideoPlayer.svelte` renders `<track>` elements for — both are
CC-licensed; `Test-Video-With-English-Captions` would exercise the same
caption code path but is `"standard"`-licensed, so it's not the first choice
here) — not the whole 10-video catalog.

**Rationale**: SC-001 only needs *one* working example to prove the "Play
from Archive" tab is real and functional in a preview; a reviewer testing a
`VideoPlayer.svelte` change needs to exercise a couple of code paths (plain
playback, and — separately — caption tracks), not the full catalog.
Restricting to CC-licensed videos sidesteps the licensing judgment call
entirely (see next section) rather than resolving it. Going further (all 10)
would be pure YAGNI for what issue #32 and this repo's own preview feature
actually need, and multiplies the amount of manual `yt-dlp`/`ffmpeg` curation
work for no corresponding benefit.

**Alternatives considered**:
- *All 10 videos* — rejected: no preview scenario needs more than a couple
  of playable examples; more curated files is more one-time maintainer work
  and more things to keep in sync (`download_status`, `.gitattributes`) for
  no measurable benefit to SC-001/SC-002.
- *Zero curation, wait for a future real (non-synthetic) test channel* —
  rejected: `@AnnexTubeTesting` is this project's designated, stable preview
  source per `CLAUDE.md` and 004's own `data-model.md`; introducing a second
  dataset just to get "more visually interesting" content would directly
  contradict 004's "single stable fixture" decision and reopen an already-
  closed design question for a benefit (nicer-looking preview video) issue
  #32 doesn't actually ask for.

## Decision: default resolution/duration/format

**Decision**: Downscale to a **320-pixel-wide** video (height computed to
preserve the source's native aspect ratio, e.g. `ffmpeg -vf scale=320:-2`),
muxed into an **`.mkv`** container (matching the frontend's hardcoded
filename), keeping the video's **existing full duration** (already ≤5
seconds for every `@AnnexTubeTesting` video today — no separate trimming
needed), audio track preserved as-is if the source has one (these synthetic
clips likely don't carry meaningful audio; this is not a hard requirement
either way given the negligible size impact demonstrated above).

**Rationale**:
- **"320x200" (the issue's literal number) is a ~8:5 aspect ratio; real
  YouTube video is essentially always 16:9 (or occasionally another native
  ratio) — forcing 200px height on a 320px-wide 16:9 source would either
  crop or squash it.** Scaling to a 320px width and letting height follow
  the source's own aspect ratio (`scale=320:-2`) gets the spirit of the
  issue's suggestion (a small, thumbnail-adjacent resolution) without
  distortion. This is called out explicitly because the issue phrased it as
  "or alike" — read as "roughly this small", not as a literal fixed
  200px-height requirement.
- **Duration**: the issue's "cut out short snippets" assumes source videos
  long enough to need trimming. Verified against the real dataset (above):
  every current `@AnnexTubeTesting` video is already 1-5 seconds. There is
  nothing left to cut. The `yt-dlp --download-sections "*0-N"` mechanism
  (native to `yt-dlp`, no new annextube code needed) remains the documented
  path for a future, longer source video, but implementing or wiring it up
  now would be speculative generality for a dataset that doesn't need it
  yet (Constitution Principle V, per `CLAUDE.md`/the project's own
  YAGNI stance already invoked repeatedly in 004's `plan.md`).
- **Format**: see the "container doesn't matter to encode cost" prototype
  finding above — `.mkv` costs nothing extra and matches
  `data-loader.ts`'s hardcoded `${base}/videos/${filePath}/video.mkv` (see
  next section), so no frontend change is needed.

**Alternatives considered**:
- *Exactly 320x200 as literally stated* — rejected per the aspect-ratio
  distortion problem above.
- *A larger "sane minimum" like 480p* — rejected: the issue explicitly asks
  for something small/downscaled specifically to keep git-hosted size down;
  320px-wide already produces tens-of-kilobytes files per the prototype
  above, comfortably inside plain-git territory — there's no size pressure
  pushing toward a larger default, and a smaller preview-only video is more
  obviously "not the real archive copy" to anyone who stumbles on it.
- *WebM/VP9 instead of MKV/H264* — not rejected outright (either would work
  size-wise, and `.mkv` can contain either codec), but not recommended as
  the change to make here: the frontend's `getVideoPath()` always requests
  `video.mkv` regardless of the codec inside it, so the container choice is
  fixed by existing code, while the *codec* inside it is an implementation
  detail for whoever runs `quickstart.md` (H.264 has marginally broader
  native `<video>` support than VP9 across the browsers `VideoPlayer.svelte`
  already targets — see `specs/002-mkv-video-playback/`).

## Decision: reuse the existing pipeline unmodified — verified, not assumed

**Decision**: No change to `annextube/cli/generate_web.py`,
`annextube/cli/prepare_ghpages.py`, or any `.github/workflows/pr-webui-preview-*.yml`
file is needed to make curated video content flow through to a published
preview. This is the central DRY finding of this research phase.

**Verified against the actual code** (not assumed):

1. **Frontend playback path is a pure convention + live check, not a
   generated reference**: `frontend/src/services/data-loader.ts`'s
   `getVideoFileUrl()` always builds
   `${baseUrl}/videos/${filePath}/video.mkv` (or with a `channelDir` prefix)
   — a fixed, hardcoded filename, not something read from metadata.
   `VideoPlayer.svelte`'s `hasLocalVideo` is set by an actual `HEAD` request
   to that exact URL (`checkVideoAvailability`), explicitly *not* derived
   from `download_status` (its own comment: *"Actual availability determined
   by HEAD request, NOT by metadata"*). **Consequence**: dropping a real file
   at that conventional path is sufficient, by itself, for the "Play from
   Archive" tab to appear and work — no frontend code change, no new field,
   no build-time manifest to regenerate.
2. **`VideoCard.svelte` (the video-listing hover-preview and status badge)
   is the one place that *does* gate on `download_status`** — but checked
   directly against the actual dataset, this needs a narrower claim than an
   earlier draft of this research made. `videos/videos.tsv`'s
   `download_status` column for every one of these ten videos is already
   `"tracked"` (not, as their individual `metadata.json` files inconsistently
   say, `"not_downloaded"` — the TSV, not `metadata.json`, is what
   `frontend/src/services/data-loader.ts` actually surfaces to components:
   its `loadVideoMetadata()` explicitly overwrites whatever
   `metadata.json` says with `metadata.download_status = video.download_status`,
   `video` being the TSV-sourced object). The hover-preview gate
   (`if (download_status !== 'downloaded' && !== 'tracked') return;`)
   already passes for `"tracked"` — **so hover-preview probing already
   works today**, with zero metadata changes, the moment a real file exists
   at the conventional path. **What does *not* already work** is the status
   *badge*: its `{#if === 'downloaded'} ... {:else if === 'metadata_only'}`
   switch has no branch for `"tracked"` at all, so these videos currently
   show no badge; only bumping `download_status` to `"downloaded"` would
   make the green "available locally" checkmark badge appear, correctly
   reflecting that a real file is now there. FR-004 is about this cosmetic-
   but-real consistency gap (a video that plays but shows no "downloaded"
   badge would be a needless, confusing loose end), not about hover-preview
   functioning at all — that part needs no metadata change.
3. **The build workflow's symlink-drop step only deletes symlinks**:
   `pr-webui-preview-build.yml`'s `find /tmp/preview-build -type l -delete`
   step (added because git-annex-backed paths export from `git archive` as
   dangling symlinks) does not touch real, materialized files. Once a
   curated `video.mkv` is committed as plain git content (not annex), `git
   archive HEAD` exports it as an ordinary file, and this step leaves it
   untouched — verified by reading the step's own command, not merely by
   its comment.
4. **`copy_data_to_ghpages()`'s `--source-dir` path already copies
   `videos/` recursively via `_copy_tree_no_symlinks()`**, which copies any
   real file it finds and only *refuses* (raises) on an actual symlink
   (`annextube/cli/prepare_ghpages.py`). A curated `video.mkv` is a real
   file by the time it reaches this step (point 3), so it is copied through
   like any other data file, unmodified, into the published preview's
   subpath.
5. **`generate_web.py`** (the frontend build step run against the exported
   dataset) does not special-case which videos have `video.mkv` present —
   `VideoPlayer.svelte`'s own live `HEAD` check (point 1) is what makes a
   video's "Play from Archive" tab conditional, not anything `generate-web`
   decides ahead of time.

**Net effect**: this feature's entire "implementation" (once curated content
exists) is *data* added to a repository outside `con/annextube` — no
`annextube/`, `frontend/`, or `.github/workflows/` diff in *this* repository
is required to satisfy FR-001-FR-003/SC-001/SC-004. This mirrors exactly how
004 already treats `con/annextubetesting`'s own refresh as "out of scope for
this feature to change" (`specs/004-pr-webui-preview/data-model.md`,
"refresh_process").

**Alternatives considered**:
- *Add a manifest/flag the build step consults to decide which videos have
  curated content* — rejected: redundant with the live `HEAD` check
  `VideoPlayer.svelte` already performs; would be new code solving a
  problem the existing design already solves more simply (Principle VIII,
  DRY).
- *Teach `prepare_ghpages.py` to special-case "preview-quality" video files
  differently from "real" ones* — rejected: nothing downstream needs to
  distinguish them; a curated file is, from every consuming code path's
  perspective, indistinguishable from (and should behave exactly like) an
  ordinarily-downloaded video. Special-casing it would be complexity with
  no behavioral payoff.

## Decision: curation is a maintainer-run, out-of-band step (no new CLI option, yet)

**Decision**: Document the curation step (`quickstart.md`) as a manual,
locally-run `yt-dlp` + `ffmpeg` invocation a maintainer performs with real
YouTube network access, committed directly to `con/annextubetesting` by
hand. **Do not** add a new `annextube` CLI option (e.g. a resolution cap on
`annextube backup`) in this design increment.

**Rationale**: This mirrors the constraint 004 already established and this
spec's User Story 2 makes explicit: CI must never fetch from YouTube, and by
extension, this design should not smuggle a "curation mode" into a CI-
reachable code path either. A new CLI option would be genuine `annextube/`
application code that this sandbox has no way to exercise against real
YouTube content (no network access — see the Environment check above),
so it could not be verified here, and the task guidance for this session is
explicit that unverifiable pipeline code should not be implemented
speculatively. The scope is also small enough (1-3 videos, a one-time
action) that a documented shell one-liner is proportionate; a new
first-class CLI feature for it would be over-engineering relative to the
problem (Principle V, `CLAUDE.md`).

**Alternatives considered**:
- *Add `--max-height`/`--download-sections`-style options to `annextube`'s
  download path now* — rejected for this increment (see above), but
  recorded as the natural next step if curating more than a handful of
  videos, or refreshing curated content periodically, ever becomes routine
  enough to be worth first-class support. Flagged in `plan.md`'s Complexity
  Tracking as a deliberately deferred, not rejected, idea.
- *Have the untrusted PR-preview *build* job itself do the downscaling from
  whatever `con/annextubetesting` already has* — not viable: that job never
  has real, fetched video bytes to downscale in the first place (the whole
  problem this spec exists to solve), and even if it did, it would
  reintroduce a per-build cost/dependency (`ffmpeg`) for content that only
  needs to be produced once, ever, until the source videos change.

## Decision: `download_status` semantics for curated (lossy, downscaled) content

**Decision**: Set the curated video's `download_status` — in
`videos/videos.tsv`, the field the frontend actually reads (see the previous
Decision's correction), and in that video's own `metadata.json` for
consistency with the rest of that repository's per-video files — to the
existing `"downloaded"` value (the one `VideoCard.svelte`'s badge switch
renders as the green "available locally" checkmark; hover-preview probing
already works for the current `"tracked"` value too, see above) — there is
no new enum value introduced — and record, in `con/annextubetesting`'s own
documentation (e.g. its README or a comment near the `.gitattributes`
override), that this specific file is a downscaled preview copy, not a
full-quality archival backup.

**Rationale**: Reusing `"downloaded"` is what makes FR-003's "no code
change" claim hold — introducing a new status value would require frontend
changes (`VideoCard.svelte`'s switch, `filter.ts`'s type) this feature
explicitly should not need. The honesty gap this creates (a "downloaded"
video that is not actually the full-quality archived copy) is real but
judged acceptable specifically *because* `con/annextubetesting` is already,
by design, a synthetic/test dataset (`CLAUDE.md`: "Predictable content
(stable test fixtures)") rather than a production archive anyone relies on
for real preservation — the same repository already contains 1-5-second
solid-color placeholder clips labeled as real "videos", so a documented,
intentionally-downscaled preview copy is consistent with, not a new
departure from, what that repository already is.

**Alternatives considered**:
- *A new `download_status` value (e.g. `"preview_only"`)* — rejected for
  this increment: would require `frontend/` schema/type/UI changes,
  contradicting FR-003's "no code change" goal, for a distinction that only
  matters to someone reading `con/annextubetesting`'s own source, not to any
  preview reviewer's actual workflow.
- *Leave `download_status` as the current `"tracked"` and rely solely on
  `VideoPlayer.svelte`'s live check* — not viable: hover-preview would
  already work (see above), but the video-listing page's status badge would
  keep showing no badge at all for a video that now actually plays, a
  needless (if minor) inconsistency FR-004 exists to close for free — the
  fix is a one-line metadata value change, not new code.

## Alternatives considered at the whole-design level

- *A new, separate "official sample video" dataset/repository* — rejected:
  `con/annextubetesting` already **is** this project's single, stable,
  purpose-built preview source (004's `data-model.md`); adding a second
  dataset just for curated video content would fragment that single-source-
  of-truth design 004 deliberately established, for no benefit — everything
  this feature needs (a place for real files, an existing `.gitattributes`
  override precedent, an existing consuming pipeline) already exists there.
- *Store curated videos on `gh-pages` directly, or in a new branch of
  `con/annextube` itself* — rejected: breaks 004's "clone the single source
  fresh per build" model and would need new fetch/wiring logic in the build
  job that reading real files out of the already-cloned
  `con/annextubetesting` does not.
- *Git-annex-track the curated files, backed by a bundled/committed key or a
  second, non-URL special remote* — rejected as unnecessary complexity: the
  existing plain-git-override precedent (`thumbnail.jpg`) already solves
  this more simply, and file sizes are small enough (tens of KB, per the
  prototype above) that git-annex's usual "keep large files out of git"
  rationale doesn't apply here in the first place.
- *A shared, de-duplicated video path so all concurrently-open previews
  serve one copy of curated content instead of one copy per `pr-<number>/`
  subpath* — not proposed, for the same reason 004's own `plan.md`
  Complexity Tracking already declined this for the whole dataset (small,
  bounded, concurrently-open-PR-count duplication is cheaper than the new
  frontend capability needed to eliminate it). Curated video content adds,
  per the prototype numbers, tens of kilobytes per preview on top of what
  004 already duplicates per subpath — not a material change to that
  existing tradeoff.
