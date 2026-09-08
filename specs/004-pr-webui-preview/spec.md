# Feature Specification: PR Web UI Previews

**Feature Branch**: `004-pr-webui-preview`
**Created**: 2026-09-08
**Status**: Draft
**Input**: GitHub issue [con/annextube#21](https://github.com/con/annextube/issues/21) — "Workflow to host/render webUI preview for PRs": provide a reviewable, clickable preview of the generated AnnexTube web UI for each pull request, similar to PDF-preview-per-PR patterns used elsewhere (e.g. via Netlify), or alternatively by publishing each PR's build to a dedicated subpath of the project's existing GitHub Pages site while reusing (not duplicating) the underlying video dataset.

> **Scope note**: This document is the `spec.md` stage of the spec-kit pipeline only (the WHAT/WHY). Per the issue's own request ("First prepare PR with design plan... formalize it all following spec-kit"), `research.md`, `plan.md`, `data-model.md`, and `tasks.md` are deliberately left for a follow-up `/speckit.plan` + `/speckit.tasks` pass once the approach below is reviewed and accepted — this PR does not implement any CI workflow or CLI changes.

## Clarifications

### Session 2026-09-08

This is an unattended design pass; the questions below are the ones the issue explicitly asked to have resolved before formalizing the spec. Each is answered here as a recommendation for maintainer review, not as a locked-in irreversible decision — `/speckit.plan` can revisit any of them.

- Q: Which dataset should preview builds render? → A: The existing `@AnnexTubeTesting` YouTube channel, via the repository's existing `annextubetesting` git branch (see Assumptions). This is the project's own designated test channel (CLAUDE.md "Test Channel" section) and is already the source of the current gh-pages demo, so no new dataset needs to be created or maintained.
- Q: Netlify or GitHub Pages for hosting? → A: Extend the project's existing GitHub Pages deployment with a per-PR subpath (`pr-<number>/`), not Netlify. Rationale in Assumptions & Recommended Approach below.
- Q: How is the large per-video dataset kept from being duplicated across every open PR's preview? → A: Each PR preview publishes only the built frontend (static HTML/JS/CSS, a few hundred KB); it does not get its own copy of `videos/`, `playlists/`, or media files. All previews read the *same* single, shared copy of the demo dataset already present on the `gh-pages` branch. Precisely how the frontend build is pointed at that shared path (a relative fetch, a build-time base-path parameter, or a symlink committed on the `gh-pages` branch) is an open implementation question for `/speckit.plan` — see Edge Cases and Out of Scope.
- Q: What happens to a PR's preview when the PR is closed or merged? → A: The preview's `pr-<number>/` folder MUST be removed (or clearly marked stale) so `gh-pages` does not grow unbounded. Exact trigger mechanism (a `pull_request: closed` workflow job vs. a periodic sweep) is left to `/speckit.plan`.
- Q: How are previews built safely for PRs from forks (untrusted code, no secret access)? → A: Preview builds MUST NOT require repository secrets and MUST NOT run with write access to `gh-pages` while executing untrusted PR code (see Edge Cases). Since the demo dataset build reuses committed, already-fetched content (no live YouTube API/yt-dlp calls), this is achievable without secrets, but the trust-boundary split between "run untrusted frontend build" and "publish to gh-pages" is an open design question for `/speckit.plan`.

## Assumptions & Recommended Approach

This section records the survey and comparison the issue asked for. It is background/rationale for the Clarifications above and for the FRs below — not itself a set of requirements.

### Dataset survey

Candidates considered for the preview's content source:

| Candidate | Notes |
|---|---|
| **`@AnnexTubeTesting` channel / existing `annextubetesting` git branch** (recommended) | This is the project's own designated test channel (CLAUDE.md "Test Channel" section): small, fast, has playlists and captions, predictable/stable content. It is *already* archived, unannexed to plain git (`--all-to-git`), and checked into an orphan `annextubetesting` branch in this repository specifically to avoid live YouTube fetches in CI (`tools/setup_demo_branch.sh`, `tools/deploy-demo.sh`) — this is exactly the existing `deploy-demo.yml` demo's data source. Reusing it means zero new dataset creation/maintenance and sidesteps the bot-detection failures noted in `docs/content/how-to/troubleshooting.md` for live fetches from CI runners. |
| Live fetch of `@AnnexTubeTesting` (or any channel) during the PR build | Rejected as the per-PR data source: `deploy-demo.yml`'s own auto-trigger is disabled specifically because "YouTube blocks datacenter IPs (bot detection)" — this would make every PR preview build flaky/unreliable. |
| A newly created, separate "preview-only" fixture dataset | Rejected: would duplicate the `@AnnexTubeTesting` channel's purpose and require independent upkeep; no advantage identified over reusing `annextubetesting`. |
| Frontend E2E fixtures (`frontend/scripts/create-e2e-fixture.sh`, `frontend/tests/fixtures/`) | These exist for Playwright assertions (specific known video/caption counts) rather than as a demo-quality showcase; the `annextubetesting` branch is the more representative "real archive" experience for a human reviewer. Not recommended as the primary source, though the two could be reconciled in `/speckit.plan` if fixture parity becomes useful. |

**Recommendation**: reuse the existing `annextubetesting` branch content (and its `tools/setup_demo_branch.sh` refresh process) as the shared dataset for all PR previews.

### Hosting approach comparison

| Approach | Summary | Assessment |
|---|---|---|
| **(a) Netlify per-PR deploy previews** | The pattern referenced in the issue (via `stamped-principles/stamped-paper`, which this survey could not inspect — it is a separate, inaccessible repository, so this assessment reasons from Netlify's generally-documented PR-deploy-preview behavior, not from that repo's specifics). Netlify natively builds a distinct preview URL per PR/branch and tears it down on merge/close. | Would work, but introduces a new external service, a new account/site to provision and maintain, and (typically) a webhook/API token secret to manage — none of which this project currently has. It also does nothing to solve the "don't duplicate the video dataset per preview" requirement; that problem is orthogonal to which host is used, since Netlify would still need the same shared-content strategy as approach (b). No existing helper in this repo integrates with Netlify. |
| **(b) Same `gh-pages`, per-PR subpath (`pr-<number>/`), shared dataset** (recommended) | Extends the site the project *already* publishes and already builds via `annextube prepare-ghpages` / `deploy-demo.yml`, adding a subpath-aware publish mode and reusing the single already-committed `annextubetesting` content instead of re-fetching or re-copying it per PR. | Directly reuses existing, working infrastructure (`gh-pages` branch, `prepare-ghpages` CLI, `generate-web` CLI, the frontend's existing `VITE_BASE_PATH` build-time base-path support in `frontend/vite.config.ts`) rather than standing up something new. No new secrets or external accounts. The open question this approach must still resolve in `/speckit.plan` is the concrete mechanism for "many `pr-<number>/` frontend builds, one shared dataset" on a plain (non-git-annex) branch — see below. |
| **(c) Other static hosts (Vercel, Cloudflare Pages, a self-hosted preview server)** | Considered briefly; share Netlify's tradeoffs (new external dependency, no existing integration) without a clear advantage over (b) for this project's scale (a small OSS project without existing paid hosting relationships). | Not recommended; not explored further. |

**Recommendation**: **(b)**, per-PR subpath on the existing `gh-pages` branch.

### Reasoning on git-annex/dataset-sharing mechanics (a known open point, not resolved here)

The issue specifically suggested "symlinking the same underlying dataset with the videos". Two things are worth being precise about, since they affect what `/speckit.plan` needs to design:

1. **The demo dataset itself is not stored in git-annex on the publishing side.** The `annextubetesting` branch and `gh-pages` are deliberately `--all-to-git` (unannexed) specifically so GitHub Pages — which serves a plain static branch, not a git-annex working tree — can serve the files directly (see `tools/setup_demo_branch.sh`). So there is no git-annex object store to hardlink/share between previews on the *published* side; "symlinking" here would mean either (a) a real filesystem symlink checked into the `gh-pages` git tree pointing at one shared copy of `videos/`/`playlists/` from each `pr-<number>/` folder, or (b) simply not copying data into `pr-<number>/` at all and instead configuring/patching the built frontend to fetch data from one shared, well-known path on the same site. Which of these (or another mechanism) is used is a **`/speckit.plan` decision**, not resolved by this spec — this spec's requirement (FR-006) is only the outcome ("no duplicate copy per preview"), not the mechanism.
2. **On the source-archival side** (a user's own `~/my-archive`, not this preview feature), git-annex genuinely is used with a URL backend for video content, and DataLad subdatasets can share an annex object store via `git annex get --from`/DataLad's usual cross-clone mechanisms. That mechanism is not what serves `gh-pages`, though, so it is not directly reusable for the preview-publishing problem — flagged here so `/speckit.plan` does not conflate the two.

### Existing infrastructure this feature should build on (not replace)

- `.github/workflows/deploy-demo.yml` — the existing (currently `workflow_dispatch`-only) gh-pages demo deployment; the natural place to add PR-preview triggers alongside, or a sibling workflow that shares its `generate-web`/git-annex setup steps.
- `annextube/cli/prepare_ghpages.py` (`annextube prepare-ghpages`) — already builds the frontend with a configurable base path and publishes to a configurable branch (`--gh-branch`); does not yet support publishing to a *subpath within* a branch, which is the extension this feature needs. Currently has zero automated test coverage (`tests/` has no `test_prepare_ghpages*` or `test_unannex*` files) — `/speckit.tasks` should account for adding tests alongside any extension, per this project's TDD-mandatory policy.
- `annextube/cli/unannex.py` (`annextube unannex`) — used to convert git-annex-tracked media into plain git files suitable for static hosting; already used by `tools/setup_demo_branch.sh` to prepare `annextubetesting`.
- `tools/setup_demo_branch.sh` / `tools/deploy-demo.sh` — existing scripts that already solve "get `@AnnexTubeTesting` content into a git-hostable, non-annexed branch" and "generate + deploy the web UI from it".
- `frontend/vite.config.ts`'s `VITE_BASE_PATH` handling — already supports building the frontend for an arbitrary base path (used today for `/annextube/`); the per-PR subpath (`/annextube/pr-<number>/`) is the same mechanism at a different value, not a new one.

None of the above are proposed for replacement; this feature's job is to extend the subpath/multi-target gap in `prepare-ghpages` and wire it into PR events, per FR-004/FR-007.

### Out of scope for this spec (deferred to `/speckit.plan` / `/speckit.tasks`)

- The concrete CI trigger design (workflow_run vs. pull_request_target split for fork safety), and how a preview link is surfaced on the PR (comment vs. check vs. status).
- The concrete mechanism for one-shared-dataset-many-previews (symlink vs. shared fetch path vs. something else — see above).
- The exact cleanup trigger and its failure-recovery/audit mechanism (FR-009/FR-010).
- Whether/how fork PRs are supported in v1 (FR-012 only requires that the answer be explicit and documented, not what the answer is).
- Any actual workflow YAML, CLI flag additions, or frontend changes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reviewer Opens a Live Preview From the PR (Priority: P1)

A maintainer or contributor reviewing a pull request that touches the web UI (or the data/export pipeline that feeds it) wants to see the rendered result without checking out the branch, installing dependencies, and running a local build.

**Why this priority**: This is the entire value of the feature — everything else (dataset reuse, cleanup, fork safety) exists in service of making this link trustworthy and cheap to provide. Without it there is no feature.

**Independent Test**: Open a PR that changes `frontend/**` or web-generation code, wait for the preview build to complete, and confirm a working link to the rendered UI appears associated with the PR (e.g. as a PR comment, check, or status), and that clicking it shows the actual UI reflecting the PR's changes (not a stale build).

**Acceptance Scenarios**:

1. **Given** an open PR that modifies `frontend/**`, **When** the preview build completes, **Then** a link to that PR's preview is posted/updated on the PR and resolves to a working page showing the archive browsing UI (video listing, playlists, search) rendered against the shared demo dataset.
2. **Given** a PR preview link already posted, **When** the contributor pushes a new commit to the same PR, **Then** the same preview location is rebuilt and updated in place rather than accumulating a new link per push.
3. **Given** a PR that does not touch the web UI or web-generation code, **When** the PR is opened, **Then** no preview build is triggered (avoiding unnecessary CI cost).

---

### User Story 2 - Multiple Concurrent PR Previews Coexist (Priority: P1)

Several contributors have open PRs at the same time, each touching the web UI differently. Each PR's preview must be independently reachable and must not be overwritten by another PR's build.

**Why this priority**: A shared single preview slot (as in the existing `deploy-demo.yml`, which always deploys to the root of `gh-pages`) is unusable for concurrent review — the second PR's build would silently replace the first's. This is the mechanism that makes the feature usable at real PR volumes, so it ranks alongside Story 1.

**Independent Test**: Open two PRs, each touching the web UI differently; confirm both previews are simultaneously reachable at distinct URLs and each reflects only its own PR's changes.

**Acceptance Scenarios**:

1. **Given** two open PRs (#A and #B) both touching the web UI, **When** both preview builds complete, **Then** PR #A's preview and PR #B's preview are reachable at distinct URLs and each shows only that PR's changes.
2. **Given** PR #A's preview is live, **When** PR #B's preview build runs, **Then** PR #A's preview remains unchanged and reachable.

---

### User Story 3 - Stale Previews Are Cleaned Up (Priority: P2)

A maintainer merges or closes a PR and expects its preview to eventually disappear rather than remain as a permanent, unmaintained, publicly reachable artifact.

**Why this priority**: Without cleanup, every PR ever opened leaves a permanent subpath on the public site, which grows hosting size indefinitely and can leave stale/misleading previews reachable long after a PR is gone. Important, but the feature is still useful to reviewers even before cleanup exists (Stories 1–2 deliver value first).

**Independent Test**: Merge or close a PR that has an existing preview; confirm that within a bounded time the preview's subpath is removed or clearly marked as retired, and that the overall preview-hosting size does not grow without bound as PRs churn.

**Acceptance Scenarios**:

1. **Given** a merged PR with an existing preview, **When** the merge event is processed, **Then** that PR's preview subpath is removed from the published site.
2. **Given** a closed-without-merge PR with an existing preview, **When** the close event is processed, **Then** that PR's preview subpath is removed from the published site.
3. **Given** a preview cleanup step fails to run (e.g. workflow error), **When** a maintainer later reviews the hosting size or an index of active previews, **Then** stale previews are discoverable and can be pruned rather than accumulating invisibly forever.

---

### User Story 4 - Preview Builds From Fork PRs Are Safe (Priority: P2)

An external contributor (not a repository collaborator) opens a PR from a fork that modifies the web UI. A maintainer wants a preview without granting that untrusted code any ability to access repository secrets, push to protected branches, or otherwise affect anything beyond its own preview subpath.

**Why this priority**: Skipping this deliberately (i.e., only building previews for same-repo branches) is an acceptable interim scope reduction, so this ranks below core preview delivery (P1) — but the design must not paint the project into an insecure default, since GitHub Pages publishing requires elevated `contents: write` permissions that must never be exposed to a workflow run that executes untrusted fork code.

**Independent Test**: Open a PR from a fork that modifies the web UI; confirm that either (a) a preview is produced without the build step ever running with repository write credentials or secrets, or (b) the design explicitly and visibly scopes fork PRs out (e.g., requiring a maintainer action to opt a fork PR in) rather than silently granting elevated access to untrusted code.

**Acceptance Scenarios**:

1. **Given** a PR opened from a fork, **When** its preview build runs, **Then** the job executing the fork's code has no access to repository secrets and no direct write permission to `gh-pages`.
2. **Given** a PR opened from a fork whose preview was built safely, **When** the built (already-static) output is published, **Then** publishing happens in a separate, trusted context that only consumes the fork build's static output artifact — never its live code execution.
3. **Given** the project cannot yet guarantee safe fork-PR handling, **When** this feature ships its first iteration, **Then** the design explicitly states whether fork PRs are in scope for v1 and, if deferred, what the interim behavior is (e.g., "no preview for fork PRs" is an acceptable, clearly documented v1 limitation).

---

### Edge Cases

- **What happens when a PR is opened by a fork with no push access?** See User Story 4 — the design must not require exposing `contents: write` (or any secret) to a job that executes the fork's untrusted code. If full safety cannot be designed now, fork PRs are explicitly out of scope for the first iteration and reviewers are told so (e.g., via a status message) rather than the system silently doing nothing.
- **What happens if two pushes to the same PR trigger overlapping preview builds?** The later build for a given PR number MUST be the one that ends up published (last-write-wins per PR subpath); an in-flight earlier build finishing after a later one MUST NOT clobber the newer result. (Exact concurrency mechanism is a `/speckit.plan` concern; the requirement here is the observable outcome.)
- **What happens to gh-pages repository/hosting size as PRs accumulate over months?** Because each preview publishes only the frontend build (not a dataset copy), the marginal size per additional open PR is small and bounded; combined with Story 3's cleanup, total preview hosting size MUST stay bounded rather than growing linearly with all-time PR count.
- **What happens if the shared demo dataset itself needs to be refreshed (e.g. `@AnnexTubeTesting` channel gets new content)?** Refreshing it is out of scope for this feature (it's already a solved, existing process — see `tools/setup_demo_branch.sh`); this feature only needs read access to whatever the current shared copy is at build time.
- **What happens if a PR changes something that affects how data is exported/generated (not just the frontend), e.g. `annextube generate-web` itself?** The preview MUST reflect the PR's version of the generation logic where practical (i.e., the PR's own code should be used to (re)generate the site, not just its frontend assets against a pre-baked site) — otherwise a bug in `generate-web` itself would never show up in a preview. This may be infeasible without a live YouTube fetch (which already fails in this project's CI due to bot detection per `docs/content/how-to/troubleshooting.md`); if so, the limitation MUST be documented rather than silently producing a preview that doesn't actually exercise the PR's generation-side changes.
- **What happens when the preview link is requested for a PR that hasn't changed anything preview-relevant?** No build/publish should occur (see Story 1, Scenario 3) — avoids wasted CI minutes and avoids implying a preview exists when it doesn't.
- **What happens when two different PRs' preview-publish jobs race to update the same shared `gh-pages` branch at the same time?** Since every PR publishes to the same branch (different subpaths), concurrent publish jobs are a real possibility once more than one PR is active. One PR's publish MUST NOT silently drop or revert another PR's already-published subpath (e.g., due to a non-fast-forward push landing without a retry). This is an outcome requirement (FR-008); the concrete mechanism (serializing publishes, retry-with-rebase, a merge queue, or per-PR non-branch storage) is a `/speckit.plan` concern.
- **What happens to GitHub Pages' own soft size/bandwidth limits as more previews accumulate?** GitHub Pages sites are recommended to stay under roughly 1 GB and have soft bandwidth limits; because previews add only small frontend bundles (not dataset copies, per FR-006), this feature's own contribution to size should stay minor relative to those limits, but `/speckit.plan` should confirm the shared dataset's own existing size (already committed once on `gh-pages` for the current demo) doesn't already consume a meaningful fraction of that headroom before assuming unlimited room for growth.

## Requirements *(mandatory)*

### Functional Requirements

#### Preview Publishing

- **FR-001**: System MUST produce, for each open pull request that modifies web-UI-relevant paths, a reachable preview URL that renders the generated AnnexTube web interface reflecting that PR's changes.
- **FR-002**: System MUST publish each PR's preview to its own distinct location (e.g. a `pr-<number>` subpath) so that concurrently open PRs' previews do not overwrite one another (User Story 2).
- **FR-003**: System MUST rebuild and update a PR's existing preview location in place when new commits are pushed to that PR, rather than creating additional, accumulating preview locations for the same PR.
- **FR-004**: System MUST reuse the project's existing GitHub Pages publishing target (the `gh-pages` branch already used by `deploy-demo.yml` / `annextube prepare-ghpages`) for preview hosting rather than introducing a new, separate hosting provider, unless the follow-up planning phase documents a specific reason the existing target cannot satisfy this feature's requirements.
- **FR-005**: System MUST render preview builds against a single, shared underlying video/metadata dataset rather than fetching from YouTube live during the build (live fetches are known to fail in this project's CI due to YouTube bot detection, per existing troubleshooting documentation).
- **FR-006**: System MUST NOT store or transfer a separate copy of the shared dataset's video/media content for each individual PR preview; all PR previews MUST reference the same underlying stored content.
- **FR-007**: System MUST reuse the project's existing web-generation tooling (`annextube generate-web`, and the existing `annextube prepare-ghpages` command's branch/subpath-publishing logic) as the basis for preview publishing rather than introducing a parallel, disconnected publishing mechanism, extending that tooling where it does not yet support a per-PR subpath.
- **FR-008**: System MUST ensure that one PR's preview publish operation cannot silently drop, corrupt, or revert another PR's already-published, still-open preview, even when two or more publish operations run concurrently against the same shared hosting branch.

#### Lifecycle & Cleanup

- **FR-009**: System MUST remove (or unambiguously mark retired) a PR's preview location when that PR is closed or merged, so hosting size does not grow unbounded with cumulative PR history (User Story 3).
- **FR-010**: System MUST provide a way to discover which preview locations are currently active/stale (e.g., an index page or a periodic audit) so that a failed automatic cleanup can be caught and corrected rather than silently accumulating forever.

#### Safety & Trust Boundary

- **FR-011**: System MUST NOT grant repository secrets or `gh-pages` write access to a job that executes code from a pull request under review, whether or not that PR originates from a fork.
- **FR-012**: System MUST explicitly document, for its first iteration, whether pull requests from forks are supported and, if not, what the resulting (non-silent) behavior is for a reviewer opening such a PR.

#### Test/Demo Dataset

- **FR-013**: System MUST use the project's designated test channel (`@AnnexTubeTesting`, per CLAUDE.md) as the content source for preview builds, reusing the repository's existing pre-populated `annextubetesting` branch content rather than creating or maintaining a second copy of test/demo data.

### Key Entities

- **PR Preview**: A published, reachable rendering of the AnnexTube web UI corresponding to one open pull request's current commit. Has a lifecycle tied to that PR (created on open/push, updated on push, removed on close/merge) and a stable, distinct location while the PR is open.
- **Shared Demo Dataset**: The single underlying collection of video/playlist/caption metadata (and, where present, unannexed media) that all PR previews render against. Sourced from the `@AnnexTubeTesting` channel via the repository's existing `annextubetesting` branch; not duplicated per preview.
- **Preview Index**: A discoverable listing of currently active (and, optionally, recently retired) PR previews, used to audit for cleanup failures (FR-010).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can go from "PR is opened" to "viewing a working rendered preview of that PR's web UI" without running any command locally.
- **SC-002**: At least 5 pull requests with independently distinct preview changes can be open at the same time, each with its own correctly-isolated, non-overwritten preview.
- **SC-003**: The total hosting footprint added by PR previews does not scale with the cumulative number of PRs ever opened — only with the number of PRs *currently* open (i.e., closed/merged PRs' previews are reliably reclaimed).
- **SC-004**: Adding a new open PR's preview does not require re-storing the shared video dataset's content — the marginal storage/transfer cost of one additional concurrent preview is limited to the size of one built frontend bundle (not the size of the dataset).
- **SC-005**: A PR opened from a fork never results in fork-authored code running with access to repository secrets or publish credentials, even when a preview is produced for it.
- **SC-006**: A PR that does not touch web-UI-relevant paths triggers zero additional CI build time for this feature.
