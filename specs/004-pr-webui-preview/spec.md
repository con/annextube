# Feature Specification: Per-PR Web UI Preview Hosting

**Feature Branch**: `004-pr-webui-preview`
**Created**: 2026-09-06
**Status**: Draft
**Input**: User description: "Workflow to host/render webUI preview for PRs" (#21)

## Summary

Frontend/web-UI pull requests currently have no way to be visually reviewed
except by checking out the branch and building locally. This feature adds an
automated workflow that renders the generated web UI for each open pull
request and publishes it at a stable, per-PR URL, so reviewers (including
non-technical ones) can click a link in the PR and see the change live.

See `research.md` for the comparison of hosting approaches and the choice of
test data source that this spec is built on.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reviewer opens a live preview from the PR (Priority: P1)

A reviewer looking at a pull request that touches `frontend/` or
`annextube/services/web*` wants to see the resulting UI without checking out
the branch and running `annextube generate-web` locally.

**Why this priority**: This is the entire point of the feature — without it,
nothing else here has value. It directly replaces the current "review the
diff and imagine the UI" workflow.

**Independent Test**: Open any PR that changes the frontend, find the
preview link (workflow summary and/or a PR comment), open it, and confirm it
renders the PR's version of the web UI against real (if canned) video
metadata — independently of any other story below.

**Acceptance Scenarios**:

1. **Given** a PR that modifies `frontend/` code, **When** the preview
   workflow completes, **Then** a comment (or updated comment) on the PR
   contains a working URL to that PR's rendered web UI.
2. **Given** a PR preview URL, **When** a reviewer opens it, **Then** the
   page shows videos, playlists, thumbnails and search working the same way
   they would in a real archive, using the shared demo dataset described in
   `research.md`.
3. **Given** a new commit is pushed to the PR, **When** the workflow re-runs,
   **Then** the same preview URL is updated in place (no new URL, no
   stale content left over from the previous commit).

---

### User Story 2 - Preview does not require re-fetching from YouTube (Priority: P1)

A contributor pushes a PR from a fork. The workflow must produce a preview
without needing YouTube credentials/cookies or making live YouTube requests,
because CI runners are blocked by YouTube's bot detection (see
`docs/content/how-to/troubleshooting.md` and the existing, currently-disabled
`deploy-demo.yml` auto-trigger) and because fork PRs must not require
repository secrets.

**Why this priority**: Without this, the workflow would be exactly as
unreliable as the existing demo-deploy automation, which is disabled for
this very reason. This is a hard constraint, not an enhancement.

**Independent Test**: Run the preview workflow with network access to
YouTube blocked; it still succeeds by building against the shared
`annextubetesting` data branch (published and refreshed per FR-002; see
`research.md` §1 for why this is *not* already the case today and must be
set up as part of this feature).

**Acceptance Scenarios**:

1. **Given** no `ANNEXTUBE_COOKIES_FILE` or YouTube network access is
   available in the workflow, **When** a PR preview is built, **Then** the
   build still succeeds using the shared `annextubetesting` demo dataset.
2. **Given** a PR opened from a fork, **When** the preview workflow runs,
   **Then** it requires no secrets beyond the default `GITHUB_TOKEN`.

---

### User Story 3 - Previews clean up after themselves (Priority: P2)

A maintainer does not want `gh-pages` to accumulate an unbounded number of
stale per-PR folders from closed/merged PRs.

**Why this priority**: Important for long-term hygiene of the `gh-pages`
branch, but the feature is useful even before this exists (it can be done
manually at first).

**Independent Test**: Close a PR that has a preview; confirm its preview
folder is removed from `gh-pages` and the link 404s, without affecting any
other PR's preview.

**Acceptance Scenarios**:

1. **Given** a PR with an existing preview is closed or merged, **When** the
   cleanup step runs, **Then** its `pr-<number>/` folder is removed from
   `gh-pages` and no other PR's folder is touched.

---

### Edge Cases

- What happens when two PRs are being previewed at the same time? Each must
  get its own subpath (`pr-<number>/`) so they don't overwrite each other.
- What happens when the PR does not touch anything that affects the web UI
  (e.g. a docs-only change)? The workflow SHOULD still be safe to run (it is
  a preview of the *repository state*, not just a diff), but MAY be skipped
  via path filters to save CI time — this is a performance choice, not a
  correctness requirement.
- What happens when `annextube generate-web` itself fails on the PR's
  branch (i.e. the PR introduces a bug)? The workflow MUST report that
  failure clearly (failed check / PR comment), not silently publish a stale
  or empty preview.
- What happens when the shared `annextubetesting` demo data branch is
  updated (new content) while a PR has been open for a while? The next
  preview rebuild for that PR MUST pick up the refreshed data (no pinning to
  a stale copy).
- What happens if `gh-pages` is pushed to concurrently by two workflow runs
  (two PRs updating previews at once)? The publish step MUST NOT lose either
  PR's folder. Unlike the existing `deploy-demo.sh`/`deploy-demo.yml`
  (which wipe the entire `gh-pages` tree before committing — fine when
  there is only one thing ever published, not fine here), the publish step
  for this feature MUST touch only its own `pr-<number>/` path and retry
  (rebase/re-fetch) around the push rather than `--force`-pushing from a
  stale checkout. See `research.md` §1 and §4.
- What happens when many PRs are open at once? Every open PR's preview
  duplicates the shared dataset's (unannexed, git-committed) video files
  into `gh-pages` history. Cleanup-on-close (User Story 3) bounds the
  number of *live* preview folders, not `gh-pages`' history size — accepted
  as a known tradeoff (see `research.md` §4) rather than something this
  feature must solve.
- A PR preview is served from the same origin as the production demo
  (`con.github.io/annextube/`), not an isolated subdomain per preview (as a
  hosted service like Netlify would give for free). This means a fork PR's
  own JS runs on a trusted project domain. This is an accepted risk of the
  chosen approach (see `research.md` §4), not a defect to fix within this
  feature, but MUST be a conscious, documented choice rather than an
  oversight.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST render, for every open pull request that
  changes web-UI-relevant paths (`frontend/**`, `annextube/**` insofar as it
  affects `generate-web` output, `.github/workflows/pr-preview*.yml`), a
  full static build of the web UI using that PR's code.
- **FR-002**: The system MUST build previews against a shared
  `annextubetesting` data branch, published on `origin` and refreshed by a
  scheduled job, rather than fetching fresh data from YouTube per PR.
  **Prerequisite**: as of this spec, `annextubetesting` exists only as
  something `tools/setup_demo_branch.sh` can create *locally* — it has
  never been pushed to `origin` (see `research.md` §1). Publishing it, and
  adding the scheduled refresh, is in scope for this feature, not a
  pre-existing asset it can assume.
- **FR-003**: The system MUST publish each PR's preview under a unique,
  predictable subpath of the project's existing `gh-pages` site (e.g.
  `https://con.github.io/annextube/pr-<number>/`). The publish step MUST
  create/update/delete only that one subpath and MUST NOT remove or modify
  any other path already present on `gh-pages` (this rules out reusing
  `deploy-demo.sh`/`deploy-demo.yml`'s existing wipe-the-whole-branch
  publish logic verbatim — see FR-008).
- **FR-004**: The system MUST surface the preview URL on the pull request
  itself (a PR comment that is updated in place on subsequent pushes, not
  duplicated).
- **FR-005**: The system MUST work for pull requests opened from forks
  without requiring any repository secret beyond the default `GITHUB_TOKEN`,
  and MUST NOT run any code originating from the PR (dependency install,
  `annextube generate-web`, or anything under `frontend/`/`annextube/`) in
  a job/context that holds a `GITHUB_TOKEN` with write access. This MUST be
  achieved via the build/publish split in FR-009, not via a bare assertion
  of "no extra secrets" — `GITHUB_TOKEN`'s `contents` permission is
  repository-wide, not scoped to `gh-pages`, so there is no permissions
  setting alone that satisfies this requirement (see `research.md` §4).
- **FR-006**: The system MUST remove a PR's preview folder from `gh-pages`
  when that PR is closed (merged or not), without touching any other PR's
  folder or the root demo (same scoped-update constraint as FR-003).
- **FR-007**: The system MUST report a clearly failed status on the PR when
  the preview build itself fails, rather than publishing a stale or partial
  preview.
- **FR-008**: The design MUST build on the *approach* already demonstrated
  by existing project automation (`tools/setup_demo_branch.sh`,
  `tools/deploy-demo.sh`, `.github/workflows/deploy-demo.yml`: archive a
  known dataset, run `annextube generate-web`, publish to `gh-pages`)
  rather than introducing an unrelated, parallel build or hosting
  mechanism. It MUST NOT assume those scripts/workflow can be invoked
  unmodified: their publish step wipes the entire `gh-pages` tree (violates
  FR-003/FR-006) and `deploy-demo.yml` does not use `annextubetesting` at
  all today (see `research.md` §1). Adapting their logic is expected;
  running them as-is is not sufficient.
- **FR-009**: The build step that executes any code from the PR (dependency
  install, `annextube generate-web`, anything under `frontend/` or
  `annextube/`) MUST run in an unprivileged job triggered by plain
  `pull_request` (default read-only `GITHUB_TOKEN`, no `contents: write`),
  producing only a static build artifact. The privileged step (checking out
  `gh-pages`, writing/removing a `pr-<number>/` subpath, pushing, and
  posting/updating the PR comment) MUST run in a separate job/workflow
  (triggered by `workflow_run` on completion of the build) that consumes
  only that uploaded artifact and MUST NOT check out, build, install
  dependencies for, or execute anything from the PR's ref. Path
  construction and any shell interpolation in either job MUST use only
  `github.event.pull_request.number` (a GitHub-assigned integer) — never a
  branch or ref name — to avoid path-traversal or command-injection via
  attacker-controlled strings. See `research.md` §4 for why this split is
  required rather than optional hardening.

### Key Entities

- **Preview deployment**: one directory (`pr-<number>/`) under the
  `gh-pages` branch, containing the static output of `annextube
  generate-web` for one specific PR's code, built against the shared
  `annextubetesting` data snapshot.
- **`annextubetesting` data branch**: an orphan branch holding a pre-fetched
  `@AnnexTubeTesting` archive (metadata, TSVs, committed video files); the
  single shared data source for all previews. Created today only by
  `tools/setup_demo_branch.sh` run locally — publishing it to `origin` and
  keeping it refreshed is part of this feature (FR-002), it is not yet the
  data source for the current root demo (see `research.md` §1).
- **Preview comment**: a single, updated-in-place PR comment carrying the
  current preview URL and build status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can go from "PR opened/updated" to "viewing the
  rendered web UI" in under 5 minutes without running any command locally.
- **SC-002**: Preview builds succeed with zero YouTube network calls and no
  repository secrets beyond `GITHUB_TOKEN`, including for fork-originated
  PRs.
- **SC-003**: `gh-pages` never carries a preview folder for a PR that has
  been closed for more than one workflow run's length of time.
- **SC-004**: Two PRs previewed concurrently never overwrite or corrupt each
  other's preview content.
- **SC-005**: No job that checks out, builds, or installs dependencies for a
  PR's own code ever runs with a `GITHUB_TOKEN` scoped to `contents:
  write` (verifiable by inspecting the `permissions:` block of the job that
  triggers on `pull_request`, and confirming the write-scoped job only
  triggers via `workflow_run` and never checks out the PR ref).
