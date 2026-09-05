# Design Plan: PR Web UI Preview Hosting

**Feature**: `004-pr-webui-preview` | **Date**: 2026-09-05
**Spec**: [`spec.md`](./spec.md)
**Issue**: [con/annextube#21](https://github.com/con/annextube/issues/21)

This is the Phase 0 research/design-plan artifact requested by the issue
("First prepare PR with design plan"). It compares hosting approaches,
identifies the dataset to reuse, and surveys existing in-repo helpers, so
that a follow-up `/speckit.plan` + `/speckit.tasks` pass can turn this into
an implementable task list.

## 1. What already exists in this repo

Before designing anything new, here is what the repo already has that
this feature should build on rather than duplicate:

| Existing piece | What it does | Relevance |
|---|---|---|
| `.github/workflows/deploy-demo.yml` | `workflow_dispatch` job: runs `annextube init --all-to-git`, `annextube backup`, `annextube generate-web` against `@AnnexTubeTesting`, force-pushes the `web/` output to the `gh-pages` branch root. | This is almost exactly what a PR-preview build needs, minus the per-PR subpath and cleanup logic. |
| `tools/deploy-demo.sh` + `tools/setup_demo_branch.sh` | Local equivalent of the above; maintains an `annextubetesting` orphan branch holding pre-fetched channel content so `generate-web` doesn't need a live YouTube fetch every time. | Confirms the intended pattern: fetch once, rebuild the static UI many times from cached content. |
| `gh-pages` branch (already live) | Currently holds one deployed copy of the demo at its root: `videos/`, `playlists/playlists.tsv`, `authors.tsv`, `assets/*.js|css`, `index.html`. ~1 MB total, 3 videos, no video binaries (playback uses the "YouTube" tab fallback in `VideoPlayer.svelte` when no local `video.mkv` is present). | This is the "dataset with videos" the issue asks to choose — it already exists and is already small enough to be trivially cheap to copy per PR if needed, and cheap enough to share once. |
| `annextube generate-web` CLI | Renders a fully static, client-side web UI (Svelte build + generated `.tsv`/`.json` data files) from an archive directory — no backend required. | The one build step every preview needs; must not be reimplemented. |
| `enh-gh_pages` branch (stale, pre-DataLad-migration) | An earlier, abandoned attempt at gh-pages deployment; noted that GitHub Pages cannot serve git-annex symlinks/content, hence `--all-to-git` in `deploy-demo.yml`. | Confirms the same constraint applies here: PR previews must use `--all-to-git`-style archives, not annexed content. |

**Conclusion on "which dataset to use"**: there is only one real
candidate — the `@AnnexTubeTesting` demo archive already used by
`deploy-demo.yml`. It is small (~1 MB), fast to build from, has playlists
and captions (exercises most of the UI), and video playback works without
hosting any video binaries (falls back to the YouTube-embed tab). No other
archive/dataset exists in the repo. The open question is not *which*
dataset, but *how it's refreshed and shared* (§3).

## 2. Approaches compared

### Option A — Netlify (as suggested by analogy to `stamped-paper`'s PDF previews)

- A GitHub Action builds the site and calls the Netlify CLI/API (or the
  official Netlify GitHub App) to create a deploy preview; Netlify posts
  its own PR comment with the preview URL and tears it down automatically
  on PR close.
- **Pros**: purpose-built for this exact use case — automatic per-PR
  isolated URLs, automatic comment, automatic cleanup, no custom
  branch-management code to write or maintain, no risk of interfering
  with the existing `gh-pages` deployment.
- **Cons**: introduces a new external service and credentials
  (`NETLIFY_AUTH_TOKEN`, site ID) that the project doesn't otherwise
  depend on — annextube's stated storage/infra philosophy is file-based
  with no external service dependencies (`CLAUDE.md`: "Storage: File-based
  (NO database dependencies)"); someone has to own the Netlify
  account/team; adds an account outside `con`'s existing GitHub-only
  footprint.

### Option B — `gh-pages` subpath per PR (`pr-<number>/`)

- Extend the existing `deploy-demo.yml` pattern: on a qualifying PR
  event, build the web UI via `annextube generate-web` against the shared
  demo archive, then commit the output under `pr-<number>/` on the
  `gh-pages` branch (instead of the root), post/update a PR comment with
  the link, and delete the subpath on PR close.
- **Pros**: reuses infrastructure and credentials that already exist
  (`GITHUB_TOKEN` with `contents: write`, already granted in
  `deploy-demo.yml`); no new external account; the shared dataset can
  live once on `gh-pages` (e.g. at a fixed top-level path) and every
  `pr-<number>/` build just needs the generated frontend bundle plus
  data files pointed at it, keeping per-PR cost small; consistent with
  the "no external dependencies" project philosophy.
- **Cons**: requires writing and maintaining the subpath-management and
  cleanup logic ourselves (Netlify gives this for free); concurrent PR
  builds pushing to the same branch need conflict-safe retry logic;
  `gh-pages` branch history grows over time (mitigated by the existing
  `--force` push pattern, or a periodic history squash).

### Recommendation

**Option B (`gh-pages` subpath)**, for the initial version:

1. It is a small, additive extension of a pattern the repo already runs
   in production (`deploy-demo.yml`), rather than a new category of
   infrastructure.
2. It needs no new external account, secret, or vendor relationship —
   consistent with the project's existing "no external service
   dependency" posture.
3. The issue's own suggestion ("symlinking the same underlying dataset
   with the videos") is a natural fit for this option and much harder to
   do cleanly on Netlify, where each deploy is normally a self-contained
   upload.

Netlify remains a reasonable fallback if `gh-pages`-based cleanup proves
too fiddly in practice (e.g. push-conflict rate under concurrent PRs turns
out to be a real problem) — worth revisiting after the first
implementation, not blocking it.

## 3. Shared-dataset strategy (sketch, not final)

To satisfy FR-003/FR-004 (don't re-fetch from YouTube per PR, don't
duplicate the dataset per PR):

- Keep exactly one refreshed copy of the `@AnnexTubeTesting` archive
  output on `gh-pages` (e.g. `_data/annextubetesting/`), updated by the
  *existing* `deploy-demo.yml` job (or a small variant of it) — **not**
  rebuilt by the PR-preview workflow itself.
- Each `pr-<number>/` build runs `annextube generate-web` against a
  **locally checked-out** copy of that same archive content (fetched from
  the `annextubetesting` branch mentioned in `tools/deploy-demo.sh`, or
  from the shared `gh-pages` copy), so the *data* step never touches
  YouTube in a PR-preview run — only the *frontend build* varies per PR.
- Exact packaging (do all `pr-<number>/` dirs reference `_data/` via a
  relative path baked into `generate-web`'s output, or does each dir get
  its own copy of just the small `.tsv`/`.json` files while sharing
  thumbnails?) is left to `/speckit.plan`, since it depends on how
  `generate-web` currently resolves data paths (`dataLoader.baseUrl` in
  `frontend/src/services/data-loader.ts` and friends) — needs a closer
  read of that code during planning, not assumed here.

## 4. Open questions for @yarikoptic

- **OQ-1 (fork PRs)**: Should PR previews work for fork-originated PRs?
  The default `pull_request` trigger can't get `contents: write` for
  forks; supporting them would need `pull_request_target` (checking out
  untrusted code with write-capable credentials — a known footgun) or a
  two-workflow `workflow_run` pattern. Recommend: **out of scope for v1**,
  same-repo PRs only, revisit if needed.
- **OQ-2 (trigger paths)**: Confirm the exact path filters for "affects
  the generated web UI" — proposed: `frontend/**` plus whatever backend
  module(s) implement `generate-web` (needs identifying the exact
  module(s) during planning).
- **OQ-3 (Netlify vs gh-pages)**: Confirm agreement with the Option B
  recommendation above, or indicate a preference for Netlify despite the
  added external dependency.

## 5. Next steps

This document and `spec.md` are the design-plan deliverable requested in
the issue. Once @yarikoptic has reviewed/chosen between the approaches
(§2) and answered the open questions (§4), the next step is to run the
full spec-kit pipeline on this same feature branch/directory:

```
/speckit.clarify   # resolve OQ-1..OQ-3 into the spec
/speckit.plan       # produce the real plan.md, data-model.md
/speckit.tasks      # produce tasks.md
/speckit.implement  # build it
```
