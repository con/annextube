# Feature Specification: PR Web UI Previews

**Feature Branch**: `004-pr-webui-preview`
**Created**: 2026-09-05
**Status**: Draft
**Input**: User description: Workflow to host/render web UI previews for PRs — when a PR changes the generated AnnexTube web archive UI, automatically build and publish a clickable preview of it so reviewers can see the change before merging, similar to PDF-preview-on-PR workflows. Compare an external static host (e.g. Netlify) against reusing the project's existing GitHub Pages deployment via a per-PR subpath, taking advantage of git-annex to avoid duplicating video content per preview. Survey available datasets with videos to use as the preview source. This is a design-plan issue: produce spec + plan artifacts first, not the full implementation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reviewer clicks through a live preview of a UI-changing PR (Priority: P1)

A maintainer reviewing a pull request that touches the web UI (frontend code, or
the archive-generation logic that produces it) wants to see and interact with
the resulting page — browsing videos, opening a video detail page, using
search — rather than only reading a diff or trusting a screenshot pasted into
the PR description.

**Why this priority**: This is the entire point of the feature. Without a
working, clickable preview, there is no improvement over the status quo
(manually pulling the branch and running the project's own web-UI-generation
tooling locally).

**Independent Test**: Open a PR that changes the web UI's source or the
code paths that generate it, wait for the preview to be built, follow the preview
link, and confirm the live page reflects the PR's changes (e.g., a UI label
change is visible, a new component renders).

**Acceptance Scenarios**:

1. **Given** a PR that modifies the frontend or web-UI-generation code,
   **When** its checks finish running, **Then** the PR shows a link (as a PR
   comment and/or a check/status) to a preview of the generated web UI built
   from that PR's code.
2. **Given** a published preview, **When** a reviewer opens the preview link,
   **Then** they see a fully working instance of the archive web UI —
   channel/video listing, video detail pages, and search — populated with
   real sample data, not an empty or placeholder page.
3. **Given** a PR that does **not** touch the frontend or web-UI-generation
   code (e.g., a documentation-only or CLI-only change), **When** its checks
   run, **Then** no preview build is triggered and reviewers are not shown a
   stale or irrelevant preview link.

---

### User Story 2 - Preview stays current as the PR is updated (Priority: P2)

A contributor pushes additional commits to an open PR (addressing review
feedback). A reviewer who already has the preview link open wants it to
reflect the latest commit, not the one they first reviewed.

**Why this priority**: PRs are rarely reviewed and merged from a single push;
without automatic refresh, a stale preview actively misleads reviewers into
approving code that no longer matches what they saw.

**Independent Test**: Push a second commit to an open PR that changes
something visible in the UI, wait for the preview to rebuild, reload the
existing preview URL, and confirm it now shows the new commit's change (same
URL, updated content — or a clearly superseded old link).

**Acceptance Scenarios**:

1. **Given** an open PR with an existing preview, **When** a new commit is
   pushed to the PR's branch, **Then** the preview is rebuilt from the new
   commit and the previously shared preview link (or an updated link posted
   to the same PR) shows the new content.
2. **Given** a preview rebuild in progress, **When** a reviewer opens the
   preview link mid-rebuild, **Then** they either see the previous build
   (not a broken/half-written page) or a clear "rebuilding" indicator — never
   a 404 or corrupted output.

---

### User Story 3 - Stale previews are cleaned up automatically (Priority: P3)

A maintainer merges or closes a PR that had a preview. They don't want that
preview to keep consuming hosting storage/bandwidth indefinitely, and they
don't want an old, merged PR's preview link to keep working and confuse
someone who finds it later (e.g., linked from a closed issue).

**Why this priority**: Without cleanup, the number of live previews grows
without bound as the project accumulates PRs, silently increasing hosting
cost/storage and leaving dead links around. This matters for sustainability
but doesn't block the core value of User Story 1, so it's lower priority.

**Independent Test**: Merge or close a PR that had a published preview, wait
for the cleanup step to run, and confirm the preview is either removed or
clearly marked as retired (e.g., replaced with a "this PR is closed" page),
and no longer counted against active hosting usage.

**Acceptance Scenarios**:

1. **Given** a PR with a published preview, **When** the PR is merged or
   closed (without merging), **Then** its preview is torn down (or marked
   retired) within a reasonable, bounded time.
2. **Given** many historical PRs, **When** an administrator checks hosting
   usage, **Then** only previews for currently-open PRs (plus a bounded
   grace period) count as active/live.

### Edge Cases

- What happens when the PR's code fails to build (compile error, generation
  error)? The preview build MUST fail visibly (a failed check on the PR)
  rather than silently publishing a stale or partial preview.
- What happens when two pushes to the same PR happen in quick succession?
  The system MUST end up serving the latest pushed commit's content once
  builds settle — an in-flight build for an older commit must not overwrite
  a newer one that finished first (no out-of-order publish).
- What happens for a PR opened from a fork by an external contributor (not a
  maintainer)? The preview MUST be built and published without requiring
  the fork's CI run to hold any secret/credential that would let it push
  content outside the preview's own isolated location, or write to
  unrelated parts of the project's public site.
- What happens if the sample dataset used for previews itself needs to be
  refreshed or is temporarily unavailable? Preview builds MUST NOT depend on
  fetching new data from YouTube live at build time (this already fails in
  CI today due to bot detection); they must use a pre-fetched, already
  archived dataset checked into the project's own infrastructure.
- What happens to a preview's underlying video/media content across many
  concurrent or historical previews? Reviewers must be able to open and play
  videos in a preview, but the design MUST avoid re-uploading or duplicating
  the same (potentially large) video files once per preview.
- What happens if a PR only changes something in the preview workflow itself
  (e.g., a change to `.github/workflows/`)? It's acceptable for this to also
  trigger a preview build if it's simpler to not special-case it, as long as
  doing so doesn't itself require secrets that fork PRs shouldn't have.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect, per pull request, whether the PR's
  changes could affect the rendered web UI (frontend source, or the backend
  code paths that generate the `web/` output) and only trigger a preview
  build for such PRs.
- **FR-002**: The system MUST build a fully functional instance of the
  generated web UI from the PR's exact code (the PR's head commit), using an
  existing, already-archived sample dataset that contains real videos,
  playlists, and captions — not a live YouTube fetch at build time.
- **FR-003**: The system MUST publish the built preview to a URL reachable by
  any reviewer with access to the repository, without requiring reviewers to
  check out the PR locally.
- **FR-004**: The system MUST make the preview URL discoverable directly from
  the pull request — as a posted comment, a check/status entry, or both —
  so a reviewer never has to look outside the PR to find it.
- **FR-005**: The published preview MUST behave like a real deployment of the
  archive web UI: channel/video browsing, video detail pages (including
  played-back video), and search MUST all work against the sample dataset.
- **FR-006**: When a PR receives new commits while open, the system MUST
  rebuild and republish its preview so the same PR always has a current
  preview available within a reasonable, bounded time of the push.
- **FR-007**: The system MUST NOT let an in-progress or delayed build for an
  older commit overwrite a preview that already reflects a newer commit on
  the same PR.
- **FR-008**: If the PR's code fails to build into a working web UI, the
  system MUST surface that failure on the PR (e.g., a failed check) rather
  than publishing a broken, empty, or stale preview silently.
- **FR-009**: The system MUST tear down or clearly mark as retired the
  preview for a PR once that PR is merged or closed, within a bounded time,
  so hosting usage does not grow without bound as PRs accumulate.
- **FR-010**: The system MUST work for pull requests opened from forks by
  outside contributors, without requiring the fork's own CI run to hold
  credentials capable of writing outside that PR's own isolated preview
  location.
- **FR-011**: The system MUST reuse the project's already-archived sample
  video dataset (or an equivalent pre-fetched dataset) as the single shared
  *source* of video/media content for every preview, rather than any
  preview independently fetching its own copy from the video platform.
  Per-preview served/checked-out copies of that shared source's content are
  acceptable as long as their number stays bounded by the number of
  concurrently open previews (see SC-004) — this requirement rules out
  re-fetching from the video platform per preview, not necessarily every
  form of at-rest copying.
- **FR-012**: Each preview's URL or identifier MUST be unique per pull
  request, so that concurrently open PRs each get their own independent,
  non-colliding preview.

### Key Entities

- **PR Preview**: A published, browsable instance of the generated AnnexTube
  web UI corresponding to one pull request's current head commit. Has a
  lifecycle (built → published → rebuilt on new commits → retired on
  close/merge) and a stable, discoverable location reviewers can reach from
  the PR.
- **Preview Source Dataset**: The pre-archived collection of real channel(s),
  videos, playlists, and captions used as the sample content every preview
  is generated from. One shared source read by every preview build (never
  independently re-fetched per preview), so build time doesn't scale with
  video count. Whether *served* copies also stay deduplicated across
  concurrently open previews, or scale (boundedly) with preview count, is a
  plan-level design choice — see FR-011, SC-004.
- **Preview Link/Announcement**: The PR comment and/or check/status entry
  that carries the current preview's URL and is kept up to date as the PR
  changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a push that opens or updates a UI-changing PR, a reviewer
  can be interacting with a live preview of it (browsing at least one video
  and using search) within one typical CI job's worth of wall-clock time
  (single-digit minutes), without running any command locally. (Excludes
  time spent waiting on unrelated, slower checks the PR may also run —
  this criterion is about the preview specifically, not the whole PR's CI
  suite.)
- **SC-002**: 100% of PRs that change the frontend or web-UI-generation code
  get a preview link posted or updated on the PR within one build cycle of
  being opened or pushed to; 0% of PRs that don't touch that code get an
  unnecessary preview build.
- **SC-003**: After a PR is merged or closed, its preview is no longer
  reachable (or is clearly marked retired) within one cleanup cycle (e.g.,
  by the next scheduled cleanup run, or immediately on close/merge if
  cleanup is event-driven) — verified by comparing the set of live preview
  locations against the set of currently-open PRs.
- **SC-004**: The video/media content every preview is generated from is
  fetched from the video platform exactly once, independent of how many
  previews exist or are built — no preview build re-fetches it live.
  Storage/bandwidth consumed by *serving* previews is allowed to scale with
  the number of concurrently open previews, but MUST stay bounded by that
  count (never by historical/closed-PR count, per SC-003) — verified by
  confirming served-copy count never exceeds concurrently-open-PR count.
- **SC-005**: A PR whose preview build fails shows that failure directly on
  the PR (visible without opening any external dashboard), and no reviewer
  is ever sent a preview link that 404s or shows broken/partial content as
  the *current* state of an open PR.

## Assumptions

- "Web UI" for the purposes of triggering a preview means both the
  client-side interface source and the backend code paths that assemble its
  static output, since either can change what a reviewer sees. (Which
  specific source paths that maps to today is a plan-level detail — see
  `plan.md`/`research.md`.)
- The project's existing pre-archived sample content (the dataset already
  used to demo the project's web UI) is an acceptable, sufficient preview
  source and does not need to be a live/fresh fetch from the video
  platform — matching how the project's existing public demo deployment
  already avoids live fetches in CI due to bot detection on datacenter IPs.
  (Which specific dataset that is today is a plan-level detail.)
- Preview builds share their underlying video/media dataset at the level of
  the project's own storage (the same archived content is read by every
  build, never independently re-fetched) — see `plan.md`/`research.md` for
  whether that also avoids duplicating served/checked-out bytes per
  concurrently open preview, which depends on implementation choices this
  spec does not mandate.
- "Reviewer" means anyone with read access to the repository (maintainers
  and, per FR-010, reviewers on fork PRs) — the preview does not need to be
  publicly world-readable beyond that, but also does not need per-reviewer
  authentication of its own; repository access is a sufficient gate.
- A "bounded time" for rebuild and teardown (FR-006, FR-009) is on the order
  of a typical CI job (minutes), not requiring near-real-time (seconds)
  publishing.
