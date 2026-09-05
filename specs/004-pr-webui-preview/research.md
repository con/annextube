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
  pointers. **Correction from an earlier draft of this research**: this
  branch is built *locally on demand* (via a `git worktree` in
  `.worktrees/annextubetesting`) and, as of this writing, is **not** pushed
  to `origin` (`git ls-remote --heads origin` does not list it) — only
  `gh-pages` and an unrelated `enh-gh_pages` branch exist remotely. A
  preview-build CI job cannot assume this branch is fetchable; making it
  usable in CI requires either (a) pushing it to `origin` once (and
  refreshing it periodically, decoupled from per-PR runs, exactly like the
  existing `deploy-demo.yml`'s disabled auto-trigger already avoids
  live-fetching per run), or (b) caching its content another way (e.g. a
  release asset, an Actions cache keyed on channel content). This plan
  assumes (a) — pushing it once as an implementation prerequisite — as the
  simplest option consistent with "no live YouTube fetch per preview build."
- **`tools/deploy-demo.sh`** generates the web UI from that branch
  (`git archive annextubetesting | tar -x ...` into a temp dir, then
  `annextube generate-web`) and publishes the result to `gh-pages` by
  switching branches, clearing the tree, copying in the new `web/` output,
  and committing — using raw git commands directly in the shell script.
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
without a backend" — is **already solved** by this project's own
`annextubetesting` branch. The remaining design question is purely about
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
| **Video bandwidth/storage given git-annex** | Video content would need to be uploaded to Netlify per deploy (or fetched from GitHub at build time and re-uploaded) — Netlify has no awareness of git-annex; every preview build risks re-transferring the same video bytes to a third party, and Netlify's own storage would hold one copy per deploy preview. | The video/media *source* is fetched from YouTube exactly once (the shared `annextubetesting` branch, never re-fetched per preview — satisfies FR-011/SC-004 as written). Whether the *served* bytes are also deduplicated across concurrently open previews depends on the publish mechanism (see "Decision: Reuse `prepare-ghpages`/`unannex`" below): as currently designed, each preview subpath gets its own on-disk/in-tree copy of the video files, so served/checkout storage scales with concurrent preview count — acceptable here because that count is small (single-digit open PRs at a time, per `plan.md`'s Scale/Scope), but this is a real, bounded cost, not zero, and is *no worse* than Netlify's per-deploy storage while adding no third-party transfer. |
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
  the separate `annextubetesting` branch (accessed via the downloaded build
  artifact — see `contracts/preview-workflow.md`'s Build step — not this
  repository's `master`). This function needs the new `--source-dir`
  parameter above, not just a destination subpath, to be reusable here — a
  real (if small and well-contained) code change, not a pure extension.
- **`prepare-ghpages`'s git operations (`git remote get-url origin`,
  `git rev-parse --verify refs/heads/...`, etc.) all assume `--output-dir`
  is itself a git working tree with an `origin` remote** — i.e., a checkout
  of the `annextube` project repository itself, not an arbitrary directory.
  This does not compose, as-is, with a build step that extracts
  `annextubetesting`'s content via `git archive ... | tar -x` into a plain
  (non-git) temp directory (the pattern `tools/deploy-demo.sh` and this
  plan's `quickstart.md` use) — the implementation phase needs to either
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
state. For the *preview* use case specifically, this plan continues to rely
on the `annextubetesting` branch's `--all-to-git` property (see the
correction above) so preview builds have real, already-materialized video
bytes without invoking `unannex` or `git annex get` — `unannex` remains
available as a documented option if a future preview source dataset is
annexed rather than `--all-to-git`.

**Net effect on the video-duplication question (FR-011/SC-004)**: because
`copy_data_to_ghpages` copies real files into each subpath (not symlinks
that could be resolved from one shared location — the frontend today
resolves all data/media URLs relative to its own deployed base path, with
no separate "shared data path" concept), publishing N concurrent previews
this way means N on-disk copies of the video files under `gh-pages`, not
one shared copy. This is why FR-011/SC-004 above were written to require
only "fetched from the source once, never re-fetched per preview" rather
than "zero duplication of served bytes" — the stronger claim an earlier
draft of this research made was not achievable without a new frontend
capability (a data base path decoupled from the app's own base path),
which this plan deliberately does NOT propose adding, per YAGNI/Principle V:
this project's concurrently-open-PR count is small (single-digit,
`plan.md` Scale/Scope), so bounded per-preview duplication of a *small,
fixed-size* test dataset is an acceptable, explicitly-scoped tradeoff
rather than a problem worth new frontend architecture to solve. If preview
volume ever grows enough to matter, decoupling the data path is the
documented follow-up (see Alternatives below).

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
  know about (the `annextubetesting` data-source wiring, git-annex
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

**Decision**: Use the existing `annextubetesting` orphan branch (built by
`tools/setup_demo_branch.sh` from the `@AnnexTubeTesting` channel) as the
single shared preview source for every PR's build. Do not fetch from
YouTube during preview builds, and do not create a second/separate preview
dataset.

**Rationale**: This branch already exists specifically as this project's
designated, stable test fixture (`CLAUDE.md`: *"Small, controlled channel
for testing all features... Predictable content (stable test fixtures)"*),
already has playlists and captions for exercising those UI paths, and
already has all video content committed to git (no on-demand git-annex
`get` needed, no re-fetch). **Correction from an earlier draft of this
research**: this research previously claimed the `annextubetesting` +
`generate-web`/`deploy-demo.sh` combination was "already proven to work in
production (the public demo)." Checked directly and found false: `git log`
shows `tools/deploy-demo.sh` was added over a month *after* `gh-pages`'s
last actual update, and the content currently live on `gh-pages` (per its
committed `README.md`) was built from a different source, not
`@AnnexTubeTesting`. `deploy-demo.sh`/`deploy-demo.yml` are designed to
work this way but have not been exercised end-to-end in their current
form — this plan should be read as relying on a *designed-but-unverified*
pipeline, not a proven one; the implementation phase's manual verification
(`quickstart.md`) is therefore load-bearing, not just a nice-to-have sanity
check. This does not change the *recommendation* (nothing else in the
codebase is a better preview source), but it does mean the implementation
phase should budget time to actually run the full pipeline once, end to
end, before trusting it in automated per-PR CI. Every preview build reading
the *same* source branch still means the video content is fetched from
YouTube only once, no matter how many previews are built — see the
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
