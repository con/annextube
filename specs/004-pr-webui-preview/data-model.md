# Phase 1 Data Model: PR Web UI Previews

This feature is CI/CD workflow infrastructure, not an application with a
persistent database — "entities" here are the artifacts and state the
workflow manages on the `gh-pages` branch and on the pull request, not
database rows. Documented for traceability back to `spec.md`'s Key Entities.

## PR Preview

Represents one pull request's currently-published preview.

| Field | Description | Source of truth |
|---|---|---|
| `pr_number` | The pull request number; used to derive the subpath and as the unique key (FR-012). | GitHub PR event payload |
| `head_sha` | The commit the current preview was built from. | GitHub PR event payload |
| `path` | `gh-pages:/pr-<pr_number>/` — where the build output lives. | Derived (`pr-<pr_number>`) |
| `url` | The public GitHub Pages URL for `path`. | Derived from the repository's Pages base URL + `path` |
| `state` | One of: `building`, `published`, `failed`, `retired`. | Workflow run outcome |
| `comment_id` | The PR comment (or check) carrying the current `url`, updated in place rather than re-posted on every push (FR-006, avoids comment spam). | Created on first publish; reused thereafter |

**Lifecycle** (state transitions):

```
(PR opened/pushed, matches trigger paths)
        │
        ▼
    building ──(build/generate-web fails)──► failed  (FR-008: surfaced as a failed check, no publish)
        │
        │ (build succeeds)
        ▼
    published ──(new commit pushed)──► building  (rebuild; FR-006/FR-007 — only a build for
        │                                          a commit newer than the one currently
        │                                          published may overwrite it)
        │
        │ (PR merged or closed)
        ▼
    retired   (FR-009: subpath removed / marked retired from gh-pages)
```

## Preview Source Dataset

The shared, read-only input every PR Preview is generated from.

| Field | Description |
|---|---|
| `branch` | `annextubetesting` (existing orphan branch, see `research.md`). |
| `channel` | `@AnnexTubeTesting` (existing project test channel, per `CLAUDE.md`). |
| `content_mode` | All video content committed to git (`--all-to-git`); no git-annex `get` required to render a preview. |
| `refresh_process` | Out of scope for this feature — refreshed independently via `tools/setup_demo_branch.sh`, same as today for the public demo. This feature only *reads* the branch, never writes to it. **Prerequisite**: as of this design, the branch is built locally only and is not present on `origin` (`git ls-remote --heads origin` does not list it) — it must be pushed once before a CI-based preview build can read it without a live YouTube fetch (see `research.md`). |

Never independently re-fetched per preview: every PR Preview's build step
reads this same branch's content from YouTube exactly once, no matter how
many previews exist (FR-011, SC-004). Its *served* copy is not
shared across previews under the recommended publish design — each
`pr-<number>/` subpath gets its own copy of the data files alongside the
generated frontend output — so served/checked-out storage scales with the
number of concurrently open previews (bounded, per FR-009/SC-003's
teardown), not with the size or count of historical previews. See
`research.md`'s "Net effect on the video-duplication question" for why the
stronger "zero duplication anywhere" claim an earlier draft made was not
achievable without new frontend capability this plan deliberately does not
propose adding.

## Preview Link/Announcement

The PR-visible pointer to a PR Preview.

| Field | Description |
|---|---|
| `location` | A PR comment (primary, per FR-004) — a check/status entry MAY be added as a secondary signal in the implementation phase, but is not required to satisfy FR-004. |
| `content` | The current `PR Preview.url`, plus enough context (which commit it reflects) that User Story 2's "is this current?" question is answerable without leaving the PR. |
| `update_policy` | Edited in place on rebuild (via `comment_id`), not reposted, to avoid notification spam on PRs with many pushes. |
