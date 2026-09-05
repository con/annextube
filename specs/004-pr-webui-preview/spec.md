# Feature Specification: PR Web UI Preview Hosting

**Feature Branch**: `004-pr-webui-preview`
**Created**: 2026-09-05
**Status**: Draft (design plan — see `research.md`; not yet through `/speckit.clarify` or `/speckit.plan`)
**Input**: GitHub issue [con/annextube#21](https://github.com/con/annextube/issues/21) — "Workflow to host/render webUI preview for PRs"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reviewer sees a live preview of a frontend PR (Priority: P1)

A reviewer opens a pull request that changes the Svelte web UI. Without
checking out the branch locally, they want to click a link and interact
with the generated archive-browsing UI (search, playlists, video pages)
exactly as an end user would see it.

**Why this priority**: This is the entire point of the feature — reviewing
generated/rendered UI output is far more effective than reading a diff of
`.svelte` files. It directly addresses the workflow gap described in the
issue.

**Independent Test**: Open a PR that edits a component under `frontend/src/`,
confirm a preview URL is posted on the PR, and confirm the URL serves a
working, browsable copy of the web UI built from that PR's branch.

**Acceptance Scenarios**:

1. **Given** an open PR that modifies `frontend/**`, **When** CI finishes
   building the preview, **Then** a comment appears on the PR with a link
   to `https://con.github.io/annextube/pr-<number>/`.
2. **Given** a preview already posted on a PR, **When** the contributor
   pushes a new commit, **Then** the same preview path is rebuilt and the
   existing PR comment is updated in place (no duplicate comments).

---

### User Story 2 - Preview is cleaned up when the PR closes (Priority: P2)

A maintainer closes or merges a PR that had a preview. They don't want
`gh-pages` (or whatever hosting is chosen) to accumulate an ever-growing
pile of stale `pr-<number>/` directories.

**Why this priority**: Without cleanup, the hosting branch/site grows
without bound and eventually becomes unwieldy (large branch history,
messy directory listing, potential Pages size limits).

**Independent Test**: Close a PR that has an active preview; confirm its
`pr-<number>/` path is removed from the hosting branch within one workflow
run, without affecting other PRs' previews.

**Acceptance Scenarios**:

1. **Given** a merged PR with an active preview, **When** the close event
   fires, **Then** the corresponding preview path is deleted and committed
   to the hosting branch.
2. **Given** a closed-without-merge PR with an active preview, **When** the
   close event fires, **Then** the same cleanup happens (merge state is
   irrelevant to cleanup).

---

### User Story 3 - Non-frontend PRs are unaffected (Priority: P3)

A contributor opens a PR that only touches backend Python code (e.g.
`annextube/services/`) or documentation. They should not pay the cost
(CI minutes, a misleading "preview" comment) of a web UI preview build
that has nothing to do with their change.

**Why this priority**: Keeps the feature cheap and non-intrusive; avoids
CI noise on the majority of PRs, which do not touch the frontend.

**Independent Test**: Open a PR that only edits `docs/**` or backend code
outside anything `generate-web` reads from; confirm no preview workflow
run is triggered and no preview comment appears.

**Acceptance Scenarios**:

1. **Given** a PR that only changes `docs/content/**`, **When** the PR is
   opened, **Then** the preview workflow does not run.
2. **Given** a PR that changes `annextube/cli/generate_web.py` (or
   `annextube/services/export.py`, which feeds the generated web UI's
   data files), **When** the PR is opened, **Then** the preview workflow
   does run, since the output depends on that code even though
   `frontend/` itself is untouched.

---

### Edge Cases

- **Fork PRs**: PRs from forks cannot be granted `contents: write` under
  the default `pull_request` trigger, so they cannot push to the hosting
  branch directly. Out of scope for the initial version — see
  `research.md` open question OQ-1.
- **Concurrent PRs**: Two PRs' preview workflows finishing around the same
  time must not clobber each other's push to the shared hosting branch
  (each PR writes to its own `pr-<number>/` subpath, but the underlying
  git push is a single branch — needs a retry-on-conflict or per-PR
  concurrency-safe update strategy).
- **Dataset refresh failures**: The underlying demo archive is fetched
  from YouTube via `yt-dlp`, which is prone to bot-detection failures in
  hosted CI runners (already documented in `deploy-demo.yml` and
  `docs/content/how-to/troubleshooting.md`). Preview builds MUST NOT
  depend on a live YouTube fetch succeeding on every PR — see FR-003.
- **Stale/abandoned PRs**: A PR left open indefinitely keeps its preview
  live indefinitely. Acceptable for now; a periodic sweep could be added
  later if this becomes a problem (not required for the initial version).
- **Repeated pushes in quick succession**: Multiple commits pushed within
  seconds of each other should not queue redundant builds indefinitely;
  the workflow should behave like normal CI (latest push wins, via
  `concurrency` groups keyed on PR number).
- **Required-status-check interaction**: if this workflow is later made a
  required status check, PRs that don't touch in-scope paths (FR-007)
  would never trigger it and could block merge indefinitely. Not planned
  for v1, but a no-op fallback job would be needed if that changes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST build a static preview of the web UI for a
  PR using the existing `annextube generate-web` CLI command — the same
  code path already used for the production demo (`deploy-demo.yml`,
  `tools/deploy-demo.sh`) — rather than a new, parallel build mechanism.
- **FR-002**: The system MUST publish each PR's preview at a distinct,
  predictable path (`pr-<number>/`) so multiple PR previews can be live
  simultaneously without colliding.
- **FR-003**: The system MUST NOT require a live YouTube fetch (`yt-dlp`)
  to succeed on every PR build. It MUST reuse a single, previously
  generated demo archive (the `@AnnexTubeTesting` channel dataset) shared
  across all PR previews, refreshed independently of individual PR builds.
- **FR-004**: The system SHOULD minimize duplicating the shared demo
  dataset's metadata/thumbnails/captions once per PR preview. True sharing
  (per-PR artifact containing only the built frontend bundle, referencing
  one on-disk copy of the dataset) requires a small `data-loader.ts`
  change (it currently only discovers data by climbing ancestor
  directories, not by pointing at a named sibling — see `research.md`
  §3); a per-PR copy of the ~1 MB dataset is an acceptable v1 fallback if
  that change is deferred (bounded by SC-005). A literal filesystem
  symlink is not viable — GitHub Pages does not resolve symlinks.
- **FR-005**: The system MUST post a single PR comment containing the
  preview link, and MUST update (not duplicate) that comment on subsequent
  pushes to the same PR.
- **FR-006**: The system MUST remove a PR's preview path when the PR is
  closed (merged or not).
- **FR-007**: The system MUST trigger only on PRs whose changes can affect
  the generated web UI (paths under `frontend/**` and the backend
  `generate-web` code/templates), not on unrelated PRs (docs-only,
  unrelated backend changes).
- **FR-008**: The system MUST reuse existing project helpers
  (`annextube generate-web`, the `gh-pages` deployment pattern already
  established by `deploy-demo.yml`/`tools/deploy-demo.sh`) instead of
  introducing a new, unrelated hosting mechanism, unless the design plan
  concludes an external service is materially better (see `research.md`).
- **FR-009**: System MUST authenticate/authorize the build/publish/cleanup
  steps such that only the repository's own CI can modify the hosting
  branch and post/update PR comments, using only same-repo `GITHUB_TOKEN`
  scopes — `contents: write` (already granted to `deploy-demo.yml`) plus
  `pull-requests: write` for posting/updating the preview comment. No new,
  broader, or externally-issued credential is required.

### Key Entities

- **PR Preview**: A generated, static copy of the web UI for one open PR.
  Attributes: PR number, source commit SHA, hosting path (`pr-<number>/`),
  created/updated timestamp. Lifecycle: created on PR open/push affecting
  in-scope paths, rebuilt on subsequent qualifying pushes, deleted on PR
  close.
- **Shared Demo Dataset**: The generated `@AnnexTubeTesting` archive
  (videos.tsv, playlists.tsv, per-video metadata/captions/thumbnails; no
  video binaries — playback falls back to the YouTube tab in the player
  UI). Refreshed independently of PR previews; ideally a single copy
  referenced by every PR preview build, or (v1 fallback, see FR-004) one
  small copy per PR preview.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can reach a working preview of a frontend-changing
  PR from a link posted on the PR, within one CI run of that PR being
  opened or updated.
- **SC-002**: Closing a PR removes its preview path within one workflow
  run; no orphaned `pr-<number>/` paths remain after a PR is closed.
- **SC-003**: Opening/updating an in-scope PR does not trigger a live
  YouTube/`yt-dlp` fetch; preview builds succeed even when YouTube bot
  detection would otherwise block a fresh fetch. (Requires fixing the
  dataset-refresh gap identified in `research.md` §1 as a prerequisite —
  today's `deploy-demo.yml` still fetches live on every run.)
- **SC-004**: A PR that does not touch frontend-affecting paths does not
  trigger the preview workflow at all (zero added CI cost for the common
  case).
- **SC-005**: Hosting-branch growth per additional concurrently-open PR
  preview stays well under 1 MB, whether that's achieved via a true
  shared dataset (bundle-only per PR) or a small per-PR copy of the
  current ~1 MB dataset (acceptable v1 fallback, see FR-004).

## Out of Scope (initial version)

- Fork PR previews (see OQ-1 in `research.md`).
- Choosing/switching to an external hosting provider (Netlify) — captured
  as an alternative in `research.md`, not required for v1.
- Previewing arbitrary user-supplied archives (only the shared demo
  dataset is used).

## Prerequisites

- Fixing the `deploy-demo.yml`/`tools/deploy-demo.sh` data-copy gap
  (`web/` is deployed today, but the sibling `videos/`/`playlists/`/
  `authors.tsv`/`channel.json` export files are not — see `research.md`
  §1) is in scope for this feature, not a separate prior piece of work,
  since PR previews need the same data-plus-frontend deploy to work
  correctly.
