# Tasks: PR Web UI Previews

**Input**: Design documents from `/specs/004-pr-webui-preview/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/preview-workflow.md, quickstart.md

**Tests**: Included for the Python CLI extension (Phase 2) per `research.md`'s
"new tests for the extended behavior are not optional" and `CLAUDE.md`'s
TDD convention. Workflow YAML (Phases 3-5) is validated per `quickstart.md`
and `shellcheck`, not pytest — there is no CI-testable unit for a GitHub
Actions trigger/permissions block itself.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [ ] T001 Ensure the `annextubetesting` orphan branch exists locally (via
      `tools/setup_demo_branch.sh` if not already built) and push it to
      `origin` — one-time prerequisite so CI can read it without a live
      YouTube fetch (`research.md`, "Decision: Preview source dataset").

## Phase 2: Foundational — extend `annextube prepare-ghpages` for subpaths

**⚠️ CRITICAL**: Blocks Phase 3 (the publish job calls this extended command).

- [x] T002 Add `--subpath` and `--source-dir` options to the `prepare_ghpages`
      command in `annextube/cli/prepare_ghpages.py`.
- [x] T003 [P] Update `build_frontend_for_ghpages()` in
      `annextube/cli/prepare_ghpages.py` to build `/{repo_name}/{subpath}/`
      as the Vite base path when `subpath` is given, and to be skipped
      entirely when `source_dir` is given (the artifact already contains a
      built `web/`).
- [x] T004 [P] Update `copy_frontend_to_ghpages()` in
      `annextube/cli/prepare_ghpages.py` to copy from `<source_dir>/web`
      instead of searching dist candidates when `source_dir` is given, and
      to write into `<repo_path>/<subpath>/` instead of `<repo_path>/` when
      `subpath` is given (never touching sibling subpaths or the root).
- [x] T005 [P] Update `copy_data_to_ghpages()` in
      `annextube/cli/prepare_ghpages.py` to copy `videos/`, `playlists/`,
      `authors.tsv` directly from `source_dir` (not `git checkout
      origin/master --`) when `source_dir` is given, writing into
      `<repo_path>/<subpath>/` when `subpath` is given.
- [x] T006 [P] Add `tests/unit/test_prepare_ghpages.py`: subpath isolation
      (publishing `pr-2` doesn't touch existing `pr-1` or root content),
      `--source-dir` copy behavior for both frontend and data files, and
      base-path construction with/without a subpath.

**Checkpoint**: `annextube prepare-ghpages --source-dir X --subpath pr-N`
publishes only under `pr-N/`, reading only from `X` — ready for Phase 3.

## Phase 3: User Story 1 (P1) — Reviewer gets a clickable preview 🎯 MVP

**Goal**: Every PR touching the web UI gets a working, linked preview built
from its own code against the `annextubetesting` dataset.

**Independent Test**: Open a PR that changes `frontend/**`, wait for checks,
follow the posted preview link, confirm it's a working, browsable instance
of the archive UI (per `quickstart.md`).

- [x] T007 [US1] Create `.github/workflows/pr-webui-preview-build.yml`:
      `pull_request: [opened, synchronize, reopened]` filtered by
      `paths: ['frontend/**', 'annextube/cli/generate_web.py']`; untrusted
      job (no secrets) that checks out the PR head, exports
      `annextubetesting` (`git archive annextubetesting | tar -x`), runs
      `annextube generate-web` against it, and uploads the whole export
      directory (data files + the new `web/`) as a build artifact on
      success. On failure the job fails (no artifact upload) — satisfies
      FR-008 without extra code (`contracts/preview-workflow.md`, Build
      step).
- [x] T008 [US1] Create `.github/workflows/pr-webui-preview-publish.yml`:
      `workflow_run` triggered on completion of the build workflow; trusted
      job (`permissions: contents: write`) that downloads the build
      artifact, derives the PR number from `workflow_run.head_sha` via
      `gh api repos/{owner}/{repo}/commits/{sha}/pulls` (never from the
      artifact), and runs `annextube prepare-ghpages --output-dir <checkout>
      --source-dir <artifact> --gh-branch gh-pages --subpath pr-<number>`
      (`contracts/preview-workflow.md`, Publish step 1-3).
- [x] T009 [US1] In the same publish job, create-or-update (by a marker
      string, not re-posting) a PR comment with the preview URL
      (`https://<pages-domain>/pr-<number>/`) and which commit it reflects
      (FR-004).
- [ ] T010 [US1] Run the manual verification in `quickstart.md`'s "Validating
      the design's core assumption" section once, end to end, before
      trusting the automated path (`research.md`'s "designed-but-unverified
      pipeline" note) — requires a real push to `origin` and is not
      something this session can execute standalone; leave as an explicit
      follow-up for whoever merges/enables the workflow. **NOT completed
      here** — see PR description.

**Checkpoint**: A PR touching `frontend/**` gets a working, linked preview.

## Phase 4: User Story 2 (P2) — Preview stays current

**Goal**: New pushes rebuild the preview; a stale/delayed build for an older
commit never overwrites a newer one.

**Independent Test**: Push a second commit with a visible UI change to an
open PR with an existing preview; confirm the preview updates to the new
commit and an artificially-delayed old build would not clobber it.

- [x] T011 [P] [US2] Extract the "resolve the PR number and compare head SHAs"
      logic from T008 into `tools/pr_preview_resolve_target.sh` (shellcheck-
      clean, independently invocable) so the freshness check
      (`contracts/preview-workflow.md`, Publish step 2) is a reviewable,
      testable unit rather than inline workflow YAML; the publish workflow
      calls it and skips publishing on any mismatch (FR-007).
- [x] T012 [US2] `shellcheck tools/pr_preview_resolve_target.sh` passes
      (`CLAUDE.md` shell-script convention).

**Checkpoint**: Two rapid pushes to the same PR settle on the newer commit's
content regardless of build-finish order.

## Phase 5: User Story 3 (P3) — Stale previews clean up

**Goal**: A closed/merged PR's preview is removed within a bounded time so
`gh-pages` doesn't grow without bound.

**Independent Test**: Close (or merge) a PR that had a published preview;
confirm `gh-pages:/pr-<number>/` is gone afterward and other PRs' previews
are untouched.

- [x] T013 [US3] Create `.github/workflows/pr-webui-preview-teardown.yml`:
      `pull_request: [closed]` (covers merge and close-without-merge);
      trusted job (`contents: write`) that checks out `gh-pages`, removes
      `pr-<number>/` if present, and commits (FR-009) — touching only that
      one subpath.

**Checkpoint**: All three user stories independently functional.

## Phase 6: Polish & Cross-Cutting

- [x] T014 [P] Update `CLAUDE.md`'s "Recent Changes"/Active Technologies
      004 entry from "design phase" to reflect the implemented workflows.
- [x] T015 Run `tox -e py3` (new `test_prepare_ghpages.py`), `ruff check`,
      and `shellcheck tools/*.sh` — all must pass before this PR is pushed.

## Dependencies & Execution Order

- Phase 1 (Setup) has no code dependencies but T007/T008 assume the branch
  it produces is already on `origin`.
- Phase 2 (Foundational) blocks Phase 3 — the publish workflow calls the
  extended CLI.
- Phase 3 (US1) is the MVP; Phase 4 (US2) and Phase 5 (US3) each add an
  independent, separately-testable increment on top of it without changing
  its behavior for the base case.
- Phase 6 (Polish) runs after all implemented stories.

## Implementation Strategy

MVP = Phase 1 + Phase 2 + Phase 3 (a working, linked preview per PR).
Phases 4 and 5 (freshness-race safety, cleanup) are correctness/hygiene
hardening on top of the same mechanism, not alternative designs — implement
all three in this PR rather than splitting further, since none is useful
shipped alone (an un-torn-down preview or an unguarded race is a real gap,
not a deferrable nice-to-have, per FR-007/FR-009 being MUST requirements).
