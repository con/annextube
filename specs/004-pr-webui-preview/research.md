# Phase 0 Research: PR Web UI Previews

## Context gathered from the existing codebase

Before comparing hosting options, the following existing project
infrastructure directly informs the design (all found in-repo, not assumed):

- **`deploy-demo.yml`** (`.github/workflows/deploy-demo.yml`) already
  publishes a generated `web/` build to the `gh-pages` branch, but its
  `push`-triggered auto-run is **disabled** with the comment: *"YouTube
  blocks datacenter IPs (bot detection)."* It only runs on
  `workflow_dispatch` today, and even then it fetches live from YouTube
  inside the job — which is exactly the failure mode a PR-preview workflow
  (running automatically, far more often, including from forks) must not
  inherit.
- **`tools/setup_demo_branch.sh`** builds an orphan git branch named
  `annextubetesting` from the `@AnnexTubeTesting` test channel (the
  project's own dedicated, stable test channel — see `CLAUDE.md`), with
  `annextube init ... --all-to-git` so **all** video content (not just
  metadata) is committed directly to git, not left as unretrieved git-annex
  pointers. This branch is built *locally on demand* (via a `git worktree`
  in `.worktrees/annextubetesting`), is **not** pushed to `origin` of *this*
  repository, and is used by `tools/deploy-demo.sh` for the unrelated
  public-demo deployment — out of scope for this feature to change.
- **Second correction — `con/annextubetesting` is a separate GitHub
  repository, not something this feature needs to build.** An earlier
  draft of this research (see below) assumed the preview-build job would
  need `annextubetesting` pushed to `origin` as a branch of *this*
  (`con/annextube`) repository, as a one-time implementation prerequisite.
  That assumption was wrong: **`con/annextubetesting`** already exists as
  its own, standalone, public repository — a real, already-populated
  annextube archive of the `@AnnexTubeTesting` channel (`videos/`,
  `playlists/`, `.annextube/`, per-video `metadata.json`/`thumbnail.jpg`,
  etc.), unrelated to and independent from `con/annextube`'s own branches.
  It requires no CI-side setup at all: the preview-build job clones it
  directly and anonymously (`git clone --depth=1
  https://github.com/con/annextubetesting.git`, no token, since it's
  public) exactly the way it would clone any other public dependency. Its
  `.gitattributes` marks per-video `thumbnail.jpg`, all `*.tsv`/`*.md`, and
  JSON/TSV metadata as plain git content (`annex.largefiles=nothing`);
  only the actual video files and `comments.json` are git-annex/URL-backed
  and were never fetched into it either — so a plain clone, no `git annex
  get`, is already everything `generate-web` needs to render a preview.
  This removes the "push a branch once" prerequisite entirely: there is
  nothing left to set up before a preview-build CI job can run.
- **`tools/deploy-demo.sh`** generates the web UI from the local
  `annextubetesting` branch above (`git archive annextubetesting | tar -x
  ...` into a temp dir, then `annextube generate-web`) and publishes the
  result to `gh-pages` by switching branches, clearing the tree, copying in
  the new `web/` output, and committing — using raw git commands directly
  in the shell script. This feature's own build step follows the same
  export-then-`generate-web` shape, but against a clone of the separate
  `con/annextubetesting` repository instead (see the correction above) —
  `deploy-demo.sh` itself is unmodified.
- **`annextube prepare-ghpages` and `annextube unannex`** (already-registered
  CLI commands — `annextube/cli/prepare_ghpages.py`,
  `annextube/cli/unannex.py`, wired into `annextube/cli/__main__.py`) are
  existing library functionality that substantially overlaps with what a
  preview-publish step needs: `prepare-ghpages` already builds the frontend
  with a configurable GitHub Pages base path, creates-or-reuses a target
  branch (checking local, then `origin/<branch>`, then falling back to an
  orphan branch), copies the frontend build and data files (`videos/`,
  `playlists/`, `authors.tsv`) into it, sets up `.nojekyll` and a
  client-routing `404.html`, and commits — all as one `annextube` library
  call, not ad-hoc shell. **Neither command has automated test coverage or
  documentation today** (verified: no references under `tests/` or `docs/`)
  — "existing" is accurate, "tested"/"proven" is not; extending untested
  code and routing it into an automated, PR-triggered CI path raises the
  bar for what this feature's own implementation-phase testing needs to
  cover (new tests for the extended behavior are not optional). **These
  commands are not currently used by `deploy-demo.yml`/`deploy-demo.sh`**
  (which predates them and still hand-rolls similar steps in bash, and,
  on inspection, appears to only copy the built frontend to `gh-pages` —
  not the `videos/`/`playlists/` data files `prepare-ghpages` does copy;
  see the correction under "Decision: Preview source dataset" below) — a
  pre-existing gap in the codebase that is out of scope for this feature to
  fix, but this feature's implementation MUST NOT repeat it by hand-rolling
  a *third*, parallel, similarly-incomplete copy of the same branch-publish
  logic. See Decision below.
- The web UI itself (`frontend/`, per `CLAUDE.md`) is explicitly
  **client-side only**, with `file://` protocol and static-hosting support
  built in (hash-based routing, no backend dependency) — it is designed to
  be trivially deployable as static files to any host, which is why both
  candidate approaches below are viable at all.

This means the hard part most preview-per-PR systems have to solve — "where
do we get a working dataset to render, without live API calls in CI, and
without a backend" — is **already solved** by the separate, already-populated
`con/annextubetesting` repository. The remaining design question is purely about
*where to publish* the generated static output per PR, and *how to keep it
current and cleaned up*.

## Decision: Publish location — GitHub Pages per-PR subpath vs. Netlify

**Decision**: Reuse the project's existing GitHub Pages deployment,
publishing each PR's build to a dedicated subpath on the `gh-pages` branch
(e.g. `gh-pages:/pr-<number>/index.html`), rather than adopting Netlify or
an equivalent external static host.

**Rationale**: See comparison table below. The deciding factors are (a) zero
new external-vendor dependency for a project whose constitution favors
self-hosted/offline-capable infrastructure (Principle X), (b) directly
reusing existing `annextube` library functionality — specifically the
`prepare-ghpages`/`unannex` CLI commands (see Decision below) — instead of
building a second, parallel deployment mechanism (Principle V/VIII — DRY,
avoid over-engineering), and (c) GitHub Pages requires no new credentials
for fork PRs beyond what the workflow already needs to read the repository
and write to `gh-pages` via the built-in `GITHUB_TOKEN` — Netlify would
require provisioning and (for fork PRs) carefully scoping a third-party API
token as a repository secret.

| Dimension | Netlify (external host) | GitHub Pages, per-PR subpath (recommended) |
|---|---|---|
| **Cost** | Free tier covers small OSS projects, but is a third-party account the project doesn't otherwise need; scales with bandwidth/build minutes on their pricing, an external cost surface. | Already paid for (free for public repos) and already in use for the public demo — no incremental cost. |
| **Setup complexity** | New account, new site config, a Netlify API token stored as a GitHub secret, `netlify.toml`/CLI integration, and its own preview-URL/comment integration (though Netlify does have first-class "deploy preview" support that's less workflow code). | No new account. Reuses the existing `gh-pages` branch and the `GITHUB_TOKEN` GitHub Actions already has. The existing `annextube prepare-ghpages` CLI command already implements branch-create-or-reuse, frontend build, and data copy — it needs one new capability added (publish under a subpath instead of always the branch root) rather than new logic being written from scratch; see Decision below. |
| **Secrets needed for fork PRs** | Requires a Netlify deploy token available to the workflow run. Giving a fork PR's workflow run access to any secret needs care (`pull_request_target` or a two-workflow "build then deploy" split) — the same care is needed either way, but there's an extra credential to scope and rotate. | Only needs `GITHUB_TOKEN` with `contents: write` scoped to `gh-pages`, which GitHub Actions already provides; the same fork-PR trust-boundary care (build in the fork's context, publish in a trusted context) is still required, but there's one credential surface, not two. |
| **Video bandwidth/storage given git-annex** | Video content would need to be uploaded to Netlify per deploy (or fetched from GitHub at build time and re-uploaded) — Netlify has no awareness of git-annex; every preview build risks re-transferring the same video bytes to a third party, and Netlify's own storage would hold one copy per deploy preview. | The preview-source repository, `con/annextubetesting`, keeps video content itself git-annex/URL-backed (never materialized in it) — the build step clones it as-is and never fetches or transfers the actual video bytes at all, regardless of preview count (satisfies FR-011/SC-004 trivially; see "Decision: Reuse `prepare-ghpages`/`unannex`" below for the full mechanism). The only per-subpath duplication is the small, fixed-size thumbnail/metadata/playlist set — negligible next to actual video bandwidth, and strictly better than Netlify's per-deploy video storage. |
| **PR comment/link workflow** | Netlify's GitHub integration posts a "Deploy Preview" comment/check automatically — less custom code for FR-004. | Not automatic; the workflow must post/update its own PR comment (or check) with the `pr-<number>` subpath URL — one additional, but simple and well-precedented (many GitHub Actions do this), piece of workflow logic. |
| **Cleanup of stale previews (FR-009)** | Netlify auto-removes deploy previews when a PR closes as part of its GitHub integration — no custom code needed. | Must be implemented explicitly: a `pull_request: closed` (covers both merge and close-without-merge) trigger removes `gh-pages:/pr-<number>/` and commits. Straightforward (same branch-edit-commit pattern as publishing), but is custom logic rather than "comes for free." |

**Alternatives considered**:
- *Netlify* — rejected as the primary recommendation for the reasons above
  (new external dependency, doesn't reuse existing infra) despite offering
  more turnkey preview/comment/cleanup behavior. Recorded here rather than
  discarded because if the custom GitHub Pages cleanup/comment logic proves
  more fragile in practice than expected, Netlify remains a documented
  fallback — the static `web/` output this project produces is portable to
  either host without any application-level change.
- *A dedicated preview-only repository or orphan branch per PR* (instead of
  subpaths on the single `gh-pages` branch) — rejected: more moving parts
  (branch-per-PR churn, harder to reason about GitHub Pages' single-site
  serving model) for no benefit over subpaths, which GitHub Pages serves
  natively from one branch's directory structure.
- *`pull_request_target` running the full build in the base repo's trusted
  context for fork PRs* vs. *building in the fork's untrusted context, then
  publishing via a separate trusted workflow triggered by
  `workflow_run`* — not decided here (this is an implementation-phase
  detail, not a spec-level or hosting-choice decision), but flagged for
  `/speckit.tasks`/`/speckit.implement` to resolve: the two-workflow split
  is the safer, more common pattern for "build untrusted PR code, publish
  with trusted credentials" and is the direction this plan assumes
  (see `quickstart.md` and `contracts/preview-workflow.md`).

## Decision: Reuse `annextube prepare-ghpages`/`unannex`, extended for subpaths

**Decision**: The implementation phase should extend the existing
`annextube prepare-ghpages` CLI command with two new options — `--subpath
pr-<number>` (publish under a subdirectory of the target branch instead of
always overwriting the branch root) and `--source-dir <path>` (copy the
frontend build and data files from an explicit source directory instead of
always reading from `--output-dir`'s own `origin/master`/`origin/main`) —
rather than writing new, parallel branch-publish logic (as `deploy-demo.sh`
currently does) or using `deploy-demo.sh` as a copy-paste starting point.
`--output-dir` keeps its current meaning (the git checkout `prepare-ghpages`
runs branch/commit operations against); `--source-dir` is the new,
separate path to the content being published (see `contracts/preview-workflow.md`'s
Publish step for the concrete worked example).

**Rationale**: `prepare-ghpages` already implements, as `annextube` library
code (not a shell script), most of the steps a preview-publish needs — but
this is a genuinely heavier extension than "add one `--subpath` flag."
Verified against the actual implementation (`annextube/cli/prepare_ghpages.py`):

- Frontend build with a configurable public base path
  (`build_frontend_for_ghpages`, currently always `/{repo_name}/` — needs to
  become `/{repo_name}/{subpath}/` when a subpath is given). Reusable with
  a parameter change.
- Target-branch create-or-reuse, correctly handling "local branch exists",
  "only remote exists" (fetches it, avoiding the orphan-branch-blowing-away-
  history mistake `deploy-demo.yml`'s comment explicitly calls out fixing),
  and "branch doesn't exist yet" (`create_ghpages_branch`). Reusable as-is.
- Copying the built frontend and data files in
  (`copy_frontend_to_ghpages`, `copy_data_to_ghpages`) — currently always
  into the branch root; needs to target `<branch-root>/<subpath>/` instead
  when publishing a preview, and must NOT delete sibling subpaths
  (other PRs' previews, or the root demo) the way its current root-level
  `git rm -rf .`/overwrite behavior would.
- **`copy_data_to_ghpages` also hardcodes its data source** as
  `origin/master`/`origin/main` of whatever `--output-dir` points at
  (`git checkout origin/master -- videos/ playlists/ authors.tsv`) — it
  assumes the archive being published lives in a repo whose own default
  branch already has that data. For previews, the actual data source is
  the separate `con/annextubetesting` repository (accessed via the
  downloaded build artifact — see `contracts/preview-workflow.md`'s Build
  step — not this repository's `master`). This function needs the new `--source-dir`
  parameter above, not just a destination subpath, to be reusable here — a
  real (if small and well-contained) code change, not a pure extension.
- **`prepare-ghpages`'s git operations (`git remote get-url origin`,
  `git rev-parse --verify refs/heads/...`, etc.) all assume `--output-dir`
  is itself a git working tree with an `origin` remote** — i.e., a checkout
  of the `annextube` project repository itself, not an arbitrary directory.
  This does not compose, as-is, with a build step that extracts
  `con/annextubetesting`'s content via `git archive ... | tar -x` into a
  plain (non-git) temp directory (the same export-then-`generate-web`
  pattern `tools/deploy-demo.sh` and this plan's `quickstart.md` use,
  against a clone of the separate repository instead) — the implementation phase needs to either
  run `prepare-ghpages` from within an actual clone of `con/annextube` (not
  a bare export), or relax this assumption. `quickstart.md` and
  `contracts/preview-workflow.md` are written to reflect this: `generate-web`
  still runs against a plain export for the *build* step, while the
  *publish* step's `prepare-ghpages` call happens against the repository
  checkout the GitHub Actions job already has (which is a real git
  clone with an `origin` remote by construction).
- GitHub Pages routing config (`.nojekyll`, a client-side-routing
  `404.html`) — reusable as-is; only needs to exist once per branch, not
  once per subpath.
- Commit step (`commit_ghpages`) — reusable as-is.

`copy_data_to_ghpages` currently copies real files (whatever is checked out
at its source path), not git-annex symlinks specifically — its behavior
with annexed-but-unretrieved content depends on that source checkout's
state. **Correction from an earlier draft of this research**: that earlier
draft assumed the preview-source dataset would be `--all-to-git` (all
video content materialized, no git-annex pointers) — true of the *local*
`annextubetesting` branch `tools/setup_demo_branch.sh` builds, but **not**
true of the actual `con/annextubetesting` repository this feature uses
(see the correction above). Its own `.gitattributes` keeps only
thumbnails/metadata/TSV/JSON as plain git content; video files,
`comments.json`, and `.vtt` captions are git-annex/URL-backed and were
never fetched into it. The build step therefore strips any symlinks
`git archive` exports for those paths right after export (`find ... -type
l -delete` — see `contracts/preview-workflow.md`), both because nothing in
CI can materialize them (no annex remote, no live YouTube fetch) and
because `copy_frontend_to_ghpages`/`copy_data_to_ghpages`'s `--source-dir`
path already refuses to copy *any* symlink from an untrusted source for
unrelated security reasons (fork-PR trust boundary, above) — a symlink
reaching that far would simply fail the publish step. **Net effect on
scope**: previews render metadata, thumbnails, and playlists; they do not
offer video playback or caption content. `unannex` remains available as a
documented option if a future preview source dataset needs it.

**Net effect on the video-duplication question (FR-011/SC-004)**: **revised
by the correction above** — since video content is stripped from the
export entirely (never materialized in CI, per the previous section),
there is no video duplication to bound in the first place: FR-011/SC-004's
"fetched from the source once, never re-fetched per preview" is satisfied
trivially (never fetched at all). The only per-subpath duplication left is
the small, fixed-size thumbnail/metadata/playlist set (`copy_data_to_ghpages`
copies real files into each subpath, not symlinks resolved from one shared
location — the frontend resolves all data/media URLs relative to its own
deployed base path, with no separate "shared data path" concept) — cheap
enough at this project's single-digit concurrently-open-PR scale
(`plan.md` Scale/Scope) that a shared-data-path frontend capability to
eliminate it would be over-engineering relative to the problem
(YAGNI/Principle V). If preview volume or dataset size ever grows enough
to matter, decoupling the data path is the documented follow-up (see
Alternatives below).

**Alternatives considered**:
- *Hand-roll new bash following `deploy-demo.sh`'s pattern* (the direction
  an earlier draft of this research took, before `prepare-ghpages` was
  found) — rejected once `prepare-ghpages` was found to already cover most
  of the same steps as library code: writing new shell would create a
  *third* parallel implementation of "build frontend, manage gh-pages
  branch, copy data, commit" (after `deploy-demo.sh` and `prepare-ghpages`
  itself), directly against Constitution Principle VIII (DRY — "Before
  writing new code: introspect existing codebase for similar functionality
  ... prefer reusing existing functions over creating new ones").
- *Leave `prepare-ghpages` untouched and only use it for the non-preview
  (end-user, whole-branch) use case, writing separate subpath logic for
  previews* — rejected: would still duplicate most of `prepare-ghpages`'s
  steps (frontend build, branch handling, config files, commit) for a
  narrower need (a subpath instead of the root); extending the one existing
  command with the parameter changes described above is still smaller and
  more DRY than a parallel implementation.
- *An existing third-party GitHub Action for subpath-based PR previews on a
  single `gh-pages`-style branch* (a generic category of Action exists for
  this pattern, with built-in comment-posting and close-triggered cleanup)
  — considered as a way to avoid hand-extending `prepare_ghpages.py`'s
  branch-mutation logic (and its `git rm -rf .`/overwrite risk called out
  above) at all. Not recommended as the primary path: this project's
  publish step has project-specific requirements a generic Action doesn't
  know about (the `con/annextubetesting` data-source wiring, git-annex
  awareness, the base-path frontend build) that would still need custom
  workflow code around any such Action, and adding a third-party Action as
  a dependency for the *branch-write* step specifically cuts against
  Constitution Principle X's transparency/auditability emphasis for
  something that already has a first-party, project-owned equivalent
  (`prepare-ghpages`) needing only a contained, testable extension. Worth
  revisiting in the implementation phase if extending `prepare_ghpages.py`
  safely (see subpath-isolation requirement above) proves harder in
  practice than expected.
- *Also migrating `deploy-demo.yml`/`deploy-demo.sh` to call the extended
  `prepare-ghpages` instead of its own bash* — out of scope for this
  feature (would touch working, unrelated infrastructure) but noted as a
  natural, low-risk follow-up once `prepare-ghpages` gains subpath support,
  since it would let the public demo and PR previews share one publish code
  path (and, as a side effect, fix `deploy-demo.sh`'s apparent existing gap
  of not copying `videos/`/`playlists/` data to `gh-pages` at all — see the
  correction under "Decision: Preview source dataset" below).

**Known limitation carried forward, not solved, by this decision**: every
preview publish-then-retire cycle adds commits to `gh-pages` that add, then
remove, a subpath's worth of content. Over the project's lifetime this
grows that branch's git history/pack size (distinct from its *working-tree*
size, which stays bounded by currently-open previews per FR-009/SC-003).
Since `gh-pages` is checked out fresh by every future preview build and
demo deploy, unbounded history growth would eventually slow those checkouts
down. This plan does not propose a fix (premature for a project with
single-digit concurrent PRs today) but flags it as a documented,
foreseeable maintenance item: a periodic orphan-branch history reset/squash
of `gh-pages` (a pattern some projects use specifically for this reason) is
the natural mitigation if/when it becomes a real cost.

## Decision: Preview source dataset

**Decision**: Use the separate, standalone `con/annextubetesting`
repository — a real, already-populated annextube archive of the
`@AnnexTubeTesting` channel — as the single shared preview source for
every PR's build, cloned anonymously and read-only. Do not fetch from
YouTube during preview builds, and do not create a second/separate preview
dataset. **This is a correction from an earlier draft of this research**,
which recommended the *local* `annextubetesting` orphan branch built by
`tools/setup_demo_branch.sh` (requiring it be pushed to `origin` as a
one-time prerequisite) — that branch is a separate, unrelated local
artifact `tools/deploy-demo.sh` uses for the public-demo deployment, not
the actual dataset this feature should use (see "Context gathered" above).

**Rationale**: `con/annextubetesting` already exists specifically as this
project's designated, stable test fixture's real archive (`CLAUDE.md`:
*"Small, controlled channel for testing all features... Predictable
content (stable test fixtures)"*), already has playlists for exercising
those UI paths, and requires no setup, refresh, or prerequisite of any
kind — it is simply cloned as-is. Unlike the local orphan branch this
research previously recommended, it is **not** `--all-to-git`: only
thumbnails/metadata/TSV/JSON are plain git content in it (per its
`.gitattributes`); video files, `comments.json`, and `.vtt` captions
remain git-annex/URL-backed and were never fetched into it either. The
build step accounts for this by dropping any symlinks `git archive`
exports for those paths (see "Decision: Reuse `prepare-ghpages`/`unannex`"
above) — previews render metadata, thumbnails, and playlists, not video
playback or captions. **Also corrected here**: this research previously
claimed the `annextubetesting` + `generate-web`/`deploy-demo.sh`
combination was "already proven to work in production (the public
demo)." Checked directly and found false: `git log` shows
`tools/deploy-demo.sh` was added over a month *after* `gh-pages`'s
last actual update, and the content currently live on `gh-pages` (per its
committed `README.md`) was built from a different source, not
`@AnnexTubeTesting`. That claim was about the unrelated local-branch
pipeline in any case, not the `con/annextubetesting`-based one this
feature actually uses — the implementation phase's manual verification
(`quickstart.md`, updated to clone the real repository) is the load-bearing
check for *this* pipeline, not a nice-to-have sanity check. Every preview
build reading the *same* source repository still means it is never
re-fetched per preview, no matter how many previews are built — see the
video-duplication note in the previous Decision for what this does and
does not guarantee about *served* copies.

**Alternatives considered**:
- *A larger/different real dataset* (e.g., the ReproTube collection at
  `datasets.datalad.org`, mentioned in the originating issue as a
  possible-approaches reference, not as a specific dataset recommendation) —
  rejected for previews: it's external to this repository (would need its
  own fetch/access-provisioning story, reintroducing exactly the
  "fetch-at-build-time" risk this plan avoids) and isn't purpose-built as a
  stable, minimal test fixture the way `@AnnexTubeTesting` is. It remains
  useful as a *reference example* of what a larger real-world archive looks
  like, but not as the preview build's source of truth.
- *Synthetic/mocked data generated on the fly* — rejected outright: violates
  Constitution Principle XII (Data Integrity & Authenticity — "Application
  code MUST NEVER generate fake, synthetic, or mock data during normal
  operation"; previews are not test code, they are a production-adjacent
  developer-facing feature rendering what reviewers will believe is
  representative real output).
- *Multiple/rotating test datasets* (to exercise more edge cases per
  preview) — rejected as unnecessary complexity for this feature's goal
  (US1: reviewer confirms a UI change renders and works); a single stable
  fixture is sufficient and keeps preview builds fast and predictable. Can
  be revisited later if a specific UI feature needs a dataset property
  `@AnnexTubeTesting` doesn't have.

## Decision: Trigger scope (which PRs get a preview)

**Decision**: Trigger preview builds only for PRs whose changed files touch
`frontend/**` or the backend code paths that produce `web/` output
(`annextube/cli/generate_web.py` and whatever it imports for web
generation/templating) — using GitHub Actions' built-in path-filtering
(`paths:` on `pull_request`), not custom logic.

**Rationale**: Directly satisfies FR-001/SC-002 ("0% of PRs that don't touch
that code get an unnecessary preview build") using a built-in GitHub
Actions mechanism rather than new custom detection logic (Principle V —
avoid over-engineering).

**Alternatives considered**: Building a preview for every PR regardless of
files changed — rejected: wastes CI minutes and produces noise (a preview
link on a docs-only PR) with no reviewer value, directly contradicted by
FR-001's edge case.

## Decision: Fork-PR trust boundary and build-freshness check (FR-007, FR-010)

**Decision**: Split the workflow into two GitHub Actions jobs/workflows —
an untrusted **build** job triggered by `pull_request` (runs with a
fork PR's own code, no write credentials, no secrets) that uploads its
`web/` output as a build artifact (`actions/upload-artifact`); and a
trusted **publish** job triggered by `workflow_run` (runs in the base
repository's context, holds `contents: write`) that downloads that
artifact (`actions/download-artifact` with `run-id:
${{ github.event.workflow_run.id }}`) and, before publishing, derives the
PR number and freshness **entirely from GitHub-authoritative fields on the
`workflow_run` event itself — never from anything carried in the
artifact**:

1. Read `github.event.workflow_run.head_sha` (the commit GitHub actually
   ran the build job against — set by GitHub when the run was created, not
   self-reported by the fork's code, so it cannot be forged by anything the
   untrusted build job does).
2. Use that SHA to look up which PR it belongs to via a trustworthy API
   call keyed on the commit itself (e.g. GitHub's "list pull requests
   associated with a commit" endpoint,
   `gh api repos/{owner}/{repo}/commits/{head_sha}/pulls`) — this derives
   the PR **number** from the commit, rather than trusting a PR number the
   artifact claims. If the artifact separately carries a PR number, it
   MUST be cross-checked against this derived number and the publish
   skipped on any mismatch, rather than trusted on its own.
3. With that trustworthy PR number in hand, fetch the PR's *current* head
   SHA (e.g. `gh pr view <number> --json headRefOid`) and compare it to
   `workflow_run.head_sha` from step 1. If they don't match, skip
   publishing this build (a newer one is already published or on its way).

**Rationale**: This is the standard, documented GitHub Actions pattern for
"build untrusted fork code, then publish with trusted credentials," and
resolving it explicitly here (rather than leaving it for the implementation
phase to rediscover) matters because of a specific, easy-to-miss pitfall:
`github.event.workflow_run.pull_requests` is frequently **empty for
fork-originated runs**, which tempts implementations into trusting a PR
number/SHA value carried over from the untrusted build job's own artifact
metadata instead. **An earlier draft of this decision made exactly that
mistake**: it recommended re-checking freshness via `gh pr view <number>`
without specifying where `<number>` itself comes from, leaving the door
open for a malicious fork PR to tag its own artifact with a *different,
victim* PR's number and its real (publicly known) current head SHA — the
prescribed check would then pass, and the trusted job would overwrite the
victim PR's preview. Deriving the PR number from `workflow_run.head_sha`
(step 1–2 above) instead of from the artifact closes that specific hole:
the attacker's build job cannot control what commit GitHub recorded the
`workflow_run` against, so it cannot make step 2 resolve to a PR number
other than its own. The re-check in step 3 is what makes FR-007 (no stale
overwrite) and FR-010 (fork-PR safety) hold together, not just the two-job
split by itself.

A `concurrency:` group on the *build* workflow (e.g.
`group: preview-${{ github.event.pull_request.number }}`,
`cancel-in-progress: true`) is additionally recommended to cheaply
supersede an in-flight build when a newer push arrives, reducing (though
not by itself eliminating the need for the freshness re-check above) how
often the race in FR-007's edge case is even hit.

**Alternatives considered**:
- *`pull_request_target` running the full build directly in the base
  repository's trusted context* — rejected: this is the well-known
  anti-pattern of checking out and executing a fork's arbitrary code
  (`frontend/`, `annextube/cli/generate_web.py`, etc. — exactly what this
  feature builds and runs) while holding write credentials, which is the
  attack this two-job split exists to avoid. Only reasonable if the build
  step never executes fork-authored code, which is not the case here.
- *Trusting `github.event.workflow_run.pull_requests[0].number` directly*
  — rejected per the pitfall above (empty for many fork-PR runs, and even
  when populated, is still data about the *triggering run*, not a live
  re-check of current PR state at publish time — doesn't handle the
  quick-succession-pushes race in FR-007's edge case on its own).
- *Trusting a PR number carried in the build artifact's own metadata*
  (an earlier draft of this Decision's own mistake, corrected above) —
  rejected: the artifact is produced by the untrusted build job, so nothing
  in it is more trustworthy than the fork PR's own code; a malicious fork
  could tag its artifact with any PR number it likes. Deriving the number
  from `workflow_run.head_sha` (a GitHub-set field the build job cannot
  influence) instead is the only way the freshness re-check actually closes
  the cross-PR spoofing gap rather than just moving it.
