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
| `.github/workflows/deploy-demo.yml` | `workflow_dispatch` job: runs `annextube init --all-to-git`, `annextube backup`, `annextube generate-web` against `@AnnexTubeTesting`, then `mv demo-build/web /tmp/demo-web` and force-pushes **only that `web/` subdir** (`index.html` + `assets/`) to the `gh-pages` branch root. | Close to the shape a PR-preview build needs, but see the gap below — it does not currently copy the data files a preview also needs. |
| `tools/deploy-demo.sh` + `tools/setup_demo_branch.sh` | Local equivalent of the above; `setup_demo_branch.sh` maintains an `annextubetesting` orphan branch with pre-fetched channel content so a full rebuild doesn't need a live YouTube fetch every time. | Establishes the *intended* pattern (fetch once, rebuild the static UI many times from cached content) — but see the gap below, this branch is **local-only today**, never pushed to `origin`. |
| `gh-pages` branch (already live) | Currently serves one deployed copy of the demo at its root: `videos/`, `playlists/playlists.tsv`, `authors.tsv`, `assets/*.js|css`, `index.html`. ~1 MB total, 3 videos, no video binaries (playback uses the "YouTube" tab fallback in `VideoPlayer.svelte` when no local `video.mkv` is present). | This is the "dataset with videos" the issue asks to choose. It's small, and playback needs no binaries — good preview material. **But** its single commit ("Deploy demo from a49065e...", different README text than the current scripts produce) predates the current `deploy-demo.yml`/`deploy-demo.sh`, so it is not proof those scripts work today (see gap below). |
| `annextube generate-web` CLI | Writes the export data (`videos/`, `playlists/`, `authors.tsv`, `channel.json`, via `ExportService`) directly under `--output-dir`, and separately copies a **pre-built** frontend bundle into `--output-dir/web/` (`deploy_frontend()` in `annextube/cli/generate_web.py`). It does **not** itself run `npm run build`/Vite. | The step every preview needs — but a PR-preview workflow must build the frontend (`npm run build` under `frontend/`, or rely on the package's existing build hook) *before* calling `generate-web`, or it will just redeploy whatever bundle happens to already be on disk rather than the PR's actual frontend changes. |
| `enh-gh_pages` branch (stale, pre-DataLad-migration) | An earlier, abandoned attempt at gh-pages deployment; noted that GitHub Pages cannot serve git-annex symlinks/content, hence `--all-to-git` in `deploy-demo.yml`. | Confirms the same constraint applies here: PR previews must use `--all-to-git`-style archives, not annexed content — and rules out plain filesystem symlinks too, since GitHub Pages doesn't resolve those either (see §3). |

**Conclusion on "which dataset to use"**: there is only one real
candidate — the `@AnnexTubeTesting` demo archive already used by
`deploy-demo.yml`. It is small (~1 MB), fast to build from, has playlists
and captions (exercises most of the UI), and video playback works without
hosting any video binaries (falls back to the YouTube-embed tab). No other
archive/dataset exists in the repo. The open question is not *which*
dataset, but *how it's refreshed and shared* (§3) — and, per the gaps
below, the existing scripts need real fixes before either of those is free.

**Gap found while writing this plan (blocks reuse as-is)**: `ExportService`
writes `videos/`, `playlists/`, `authors.tsv`, `channel.json` as **siblings**
of `web/` under `--output-dir` (`annextube/services/export.py`), not inside
it. `deploy-demo.yml` and `deploy-demo.sh` both `mv`/`cp` only the `web/`
subdir onto `gh-pages` — the sibling data files are left behind and never
committed. Run today, these scripts would deploy a frontend with no data
behind it; the data currently visible on `gh-pages` is a leftover from an
earlier, different version of the pipeline, not evidence the current
scripts work end-to-end. Likewise, `tools/setup_demo_branch.sh` creates the
`annextubetesting` cache branch **locally only** — `git ls-remote` shows it
does not exist on `origin`, so nothing in CI can check it out today. Both
of these are pre-existing gaps in `deploy-demo.yml`/`deploy-demo.sh`
independent of this feature, but a PR-preview workflow inherits them:
**fixing the data-copy step (and, if the cached-branch approach is kept,
pushing `annextubetesting` to `origin` and refreshing it there) is a
prerequisite**, not something to extend as-is.

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
- **Pros**: builds on infrastructure and credentials that already exist —
  `GITHUB_TOKEN` (`contents: write` already granted in `deploy-demo.yml`,
  plus `pull-requests: write` for the preview comment, see §5 — both
  same-repo token scopes, no new external credential); no new external
  account; per-PR cost stays small (~1 MB or less, §3) whether or not
  true dataset sharing ships in v1; consistent with the "no external
  dependencies" project philosophy.
- **Cons**: requires writing and maintaining the subpath-management and
  cleanup logic ourselves (Netlify gives this for free); concurrent PR
  builds pushing to the same branch need conflict-safe retry logic;
  `gh-pages` branch history grows over time (mitigated by the existing
  `--force` push pattern, or a periodic history squash); the data-copy gap
  in `deploy-demo.yml`/`deploy-demo.sh` (§1) needs fixing first, since
  this option extends that same pipeline.

### Recommendation

**Option B (`gh-pages` subpath)**, for the initial version:

1. It is a small, additive extension of a pattern the repo already runs
   (once the §1 data-copy gap is fixed), rather than a new category of
   infrastructure.
2. It needs no new external account, secret, or vendor relationship —
   consistent with the project's existing "no external service
   dependency" posture.
3. The issue's own suggestion of reusing one underlying dataset across
   previews is achievable here (§3) — via a small `data-loader.ts` change
   or, as a cheaper v1 fallback, a per-PR copy of the ~1 MB dataset (note:
   a literal filesystem *symlink*, as originally suggested in the issue,
   will not work — GitHub Pages doesn't resolve symlinks, same constraint
   noted for git-annex in §1) — and is much harder to achieve at all on
   Netlify, where each deploy is normally a fully self-contained upload.

Netlify remains a reasonable fallback if `gh-pages`-based cleanup proves
too fiddly in practice (e.g. push-conflict rate under concurrent PRs turns
out to be a real problem) — worth revisiting after the first
implementation, not blocking it.

## 3. Shared-dataset strategy (sketch, not final)

To satisfy FR-003 (don't re-fetch from YouTube per PR) and minimize
duplication (FR-004):

- Fix the prerequisite gap above first: refresh a single copy of the
  `@AnnexTubeTesting` archive's data files (`videos/`, `playlists/`,
  `authors.tsv`, `channel.json`) on `gh-pages`, on a schedule/dispatch
  independent of individual PR builds — **not** rebuilt by the
  PR-preview workflow itself. Use a plain top-level path such as
  `data/annextubetesting/` (**not** `_data/...` — GitHub Pages runs
  Jekyll by default on `gh-pages`, and Jekyll silently excludes any
  top-level path starting with `_`; the branch also has no `.nojekyll`
  marker today, which is worth adding regardless, as the standard
  practice for a Vite-style static deploy).
- **Read of `frontend/src/services/data-loader.ts`** (`DataLoader
  ._discoverArchiveRoot()`): it only probes strict **ancestor**
  directories of the served page (`..`, `.`, `../..`, `../../..`,
  `../../../..`) via `HEAD` requests for `channels.tsv` /
  `videos/videos.tsv` / `channel.json`. It has **no** mechanism today to
  point sideways at a named shared sibling like `data/annextubetesting/`.
  So a `pr-<number>/` build that ships only a frontend bundle and expects
  it to find the shared dataset by climbing upward will not work
  unmodified — nor would a symlink from `pr-<number>/` to the shared
  path, since GitHub Pages does not resolve filesystem symlinks (same
  constraint as the git-annex case in §1).
  Genuine zero-duplication therefore requires one of, to be decided in
  `/speckit.plan`:
  (a) a small `data-loader.ts` change adding a configurable/sideways data
  root (e.g. read from a `<meta>` tag or build-time constant pointing at
  `data/annextubetesting/`), or
  (b) accept that each `pr-<number>/` build gets its own **copy** of the
  data files as a v1 fallback — the dataset is only ~1 MB (§1), so this
  is cheap in absolute terms even if not truly "shared"; see the revised
  FR-004/SC-005 in `spec.md`, which now allows this as an acceptable v1
  outcome rather than requiring true sharing on day one.

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
- **OQ-4 (prerequisite fixes)**: Confirm agreement that the `deploy-demo.yml`
  data-copy gap and the never-pushed `annextubetesting` branch (§1) should
  be fixed as part of this feature (they block it either way) rather than
  as a separate, prior piece of work.
- **OQ-5 (true dataset sharing vs. per-PR copy)**: Confirm the §3(b)
  fallback — a small per-PR copy of the ~1 MB dataset, rather than a
  `data-loader.ts` code change for true cross-PR sharing — is acceptable
  for v1, given the size is small enough that SC-005's budget tolerates it.

## 5. Other notes for `/speckit.plan`

- **Required-status-check interaction**: if the preview workflow is ever
  marked a required status check, PRs that don't touch in-scope paths
  (FR-007) will never trigger it and could show "Expected — waiting for
  status" indefinitely, blocking merge. Not a concern for v1 (no plan to
  make it required), but worth a no-op fallback job if that changes later.
- **Comment-posting permissions**: FR-005 (post/update a PR comment) needs
  `pull-requests: write` (or `issues: write`) on `GITHUB_TOKEN`, in
  addition to the `contents: write` `deploy-demo.yml` already has for
  pushing to `gh-pages`. Both are same-repo `GITHUB_TOKEN` scopes — no new
  external credential, just a broader token permission than today's demo
  workflow uses.

## 6. Next steps

This document and `spec.md` are the design-plan deliverable requested in
the issue. Once @yarikoptic has reviewed/chosen between the approaches
(§2) and answered the open questions (§4), the next step is to run the
full spec-kit pipeline on this same feature branch/directory:

```
/speckit.clarify   # resolve OQ-1..OQ-5 into the spec
/speckit.plan       # produce the real plan.md, data-model.md
/speckit.tasks      # produce tasks.md
/speckit.implement  # build it
```
