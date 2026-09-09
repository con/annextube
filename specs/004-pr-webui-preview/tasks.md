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
      **Post-review hardening**: `source_dir` is an untrusted, fork-PR-
      produced build artifact (see T007's note); a symlink inside it (or
      `<source_dir>/web` itself being a symlink) could otherwise cause
      arbitrary host content to be dereferenced and copied into the
      publicly-served `gh-pages` branch. Added `_copy_tree_no_symlinks()`
      and made this function refuse (raise) on any symlink found under
      `source_dir` rather than following it.
- [x] T005 [P] Update `copy_data_to_ghpages()` in
      `annextube/cli/prepare_ghpages.py` to copy `videos/`, `playlists/`,
      `authors.tsv` directly from `source_dir` (not `git checkout
      origin/master --`) when `source_dir` is given, writing into
      `<repo_path>/<subpath>/` when `subpath` is given.
      **Post-review hardening**: (1) the `source_dir` branch now also uses
      `_copy_tree_no_symlinks()` for the same reason as T004. (2) the
      non-`source_dir` branch was rewritten from `git checkout <branch> --
      <item>` + `shutil.move()` (which destroyed other root-level content
      already checked out in the working tree) to `git archive <branch> --
      <item> | tar -x` into a scratch `tempfile.TemporaryDirectory()`,
      copying only the requested items into `dest_root` afterward —
      preserving any pre-existing root content untouched.
- [x] T006 [P] Add `tests/unit/test_prepare_ghpages.py`: subpath isolation
      (publishing `pr-2` doesn't touch existing `pr-1` or root content),
      `--source-dir` copy behavior for both frontend and data files, and
      base-path construction with/without a subpath.
      **Post-review hardening**: added
      `test_copy_frontend_to_ghpages_rejects_symlink_in_source_dir`,
      `test_copy_frontend_to_ghpages_rejects_symlinked_web_dir`,
      `test_copy_data_to_ghpages_rejects_symlink_in_source_dir`,
      `test_copy_data_to_ghpages_no_source_dir_preserves_root_content`, and
      `test_prepare_ghpages_rejects_unsafe_subpath` (parametrized over `/`,
      `\`, `.`, `..`, empty, and absolute-path subpaths) — 17 tests total,
      up from 7.

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
      **Post-review hardening**: (1) added the missing `actions: read`
      permission (required by `actions/download-artifact@v4`'s
      cross-run `run-id:` fetch — the job silently 404'd without it).
      (2) added a git identity config step (`prepare-ghpages`'s commit
      fails without one on a fresh runner). (3) replaced the direct
      `git checkout gh-pages` + `git push` with
      `tools/gh_pages_push_retry.sh` driving a dedicated git *worktree*
      (not the main checkout) — see T011's hardening note for why a
      worktree specifically. (4) the freshness check is now re-run
      immediately before each publish attempt inside
      `tools/gh_pages_publish_preview.sh`, not just once at job start, to
      close the TOCTOU window between the initial check and
      artifact-download/Python-setup/retry time.
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
      **Post-review hardening**: (1) hardened to reject a commit associated
      with more than one open PR (was previously silently taking the first
      match via `.[0]`, which could resolve to the wrong PR). (2) added
      `tools/gh_pages_push_retry.sh` (`Usage: gh_pages_push_retry.sh
      <worktree_dir> -- <command> [args...]`): creates/resets a git
      *worktree* from `origin/gh-pages` on each of up to 5 attempts, runs
      the given mutate command against it, and pushes, retrying on
      rejection. A worktree (rather than `git checkout -B gh-pages` inside
      the same directory the running `tools/*.sh` scripts live in) is
      required because `gh-pages` has no `tools/` directory at all —
      checking it out in-place would make the executing script's own file
      vanish mid-run. (3) added `tools/gh_pages_publish_preview.sh`
      (`Usage: gh_pages_publish_preview.sh <head_sha> <source_dir>
      <worktree_dir>`), the mutate step T008's publish job now drives
      through the retry wrapper — re-checks freshness on every invocation
      and skips (via a `$PREVIEW_SKIP_MARKER` file, default
      `/tmp/preview-stale-skip`, exit 0) rather than failing when stale, so
      the PR-comment step can tell "skipped" from "published" and the
      wrapper's subsequent push is a harmless no-op. Manually verified
      end-to-end (concurrent-push-race retry, staleness-skip, and the
      symlink/root-preservation cases from T004-T006) against scratch git
      repos with a mocked `gh` CLI.
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
      **Post-review hardening**: (1) changed the trigger from
      `pull_request` to `pull_request_target` — GitHub silently downgrades
      `GITHUB_TOKEN` to read-only for `pull_request`-triggered runs from
      fork PRs regardless of the `permissions:` block, which would make
      every teardown `git push` fail for exactly the fork-PR case FR-010
      requires; safe here since this job never checks out or executes
      anything from the PR's own ref (no `actions/checkout` with a PR ref
      at all — it only operates on `gh-pages`). (2) dropped the `paths:`
      filter entirely: a closed PR's *final* diff might no longer touch the
      build-triggering paths even though it has a previously-published,
      now-orphaned preview, and FR-009 is unconditional. (3) added
      `tools/gh_pages_teardown_subpath.sh` (`Usage:
      gh_pages_teardown_subpath.sh <worktree_dir> <pr_number>`, idempotent,
      safe no-op when nothing to remove) and drives it through the same
      `tools/gh_pages_push_retry.sh` worktree wrapper as T008/T011, for the
      same self-modifying-script reason. (4) added the git identity config
      step.

**Checkpoint**: All three user stories independently functional.

## Phase 6.5: Independent-review round 2 (post-hardening)

A second pair of independent sub-agent reviews was run against the Phase
2-5 hardening commit itself (symlink safety, root-content-preservation,
worktree redesign). Neither found an exploitable defect in the actual
wired-up pipeline; both converged on real, non-blocking gaps, all fixed
here:

- [x] T016 [P] `annextube/cli/prepare_ghpages.py`: factored `--subpath`
      validation into a shared `_validate_subpath()` and call it from
      `copy_frontend_to_ghpages()`/`copy_data_to_ghpages()` directly, not
      only from the `prepare_ghpages` click callback — those two functions
      are called directly by this module's own tests (and could be by
      future code), so the isolation guarantee must not depend on every
      caller re-deriving the check itself. Also rejects `.git` as a
      subpath value (writing into a checkout's own `.git/` was previously
      not covered by the reject-list).
- [x] T017 [P] `tools/pr_preview_resolve_target.sh`: filter the
      `commits/{sha}/pulls` lookup and the multi-PR guard to `state ==
      "open"` (a stray closed/merged PR sharing a commit no longer causes
      a false "refuse to guess"), and explicitly check the resolved PR's
      *current* `state == "OPEN"` (not just its head SHA) before allowing
      a publish — closes a gap where a build that finishes just after its
      PR is closed could publish (or republish) an orphaned preview that
      the once-only close-transition teardown workflow would never remove.
- [x] T018 [P] `tests/unit/test_prepare_ghpages.py`: added deeply-nested
      symlink-rejection tests for both the frontend and data copy paths
      (the previous tests only placed the malicious symlink at the shallow
      entry point each guard is first invoked from, not inside a
      recursively-copied subdirectory), and direct-call subpath-validation
      tests for `copy_frontend_to_ghpages()`/`copy_data_to_ghpages()`
      (T016) bypassing the CLI. 34 tests total, up from 17.
- [x] T019 `.github/workflows/pr-webui-preview-publish.yml`: corrected the
      comment claiming npm's absence from `PATH` is why `hatch_build.py`'s
      frontend-build hook skips in this job — GitHub-hosted runners ship a
      system Node/npm, so it may well still run. Harmless either way (this
      checkout is always the trusted base branch, and `--source-dir`
      unconditionally skips consulting any locally-built frontend), but
      the comment now says why it's harmless instead of relying on an
      assumption that doesn't actually hold.
- [x] T020 `specs/004-pr-webui-preview/contracts/preview-workflow.md`:
      synced the trigger-events table, which still documented the teardown
      workflow as `pull_request: [closed]`, to the implementation's actual
      `pull_request_target: [closed]` (with the same rationale as T013's
      hardening note).
- [x] T021 Re-ran `tox -e py3`, `ruff check`, `mypy`, `shellcheck
      tools/*.sh`, and `actionlint` on the three workflow YAML files —
      all pass. Manually re-verified `pr_preview_resolve_target.sh`'s five
      decision branches (fresh/open, closed-but-fresh-SHA, multi-open-PR,
      stale SHA, no-PR-found) against a mocked `gh` CLI.

Not acted on (documented, not silently dropped): a reviewer noted the new
`tools/gh_pages_*.sh` orchestration scripts have no automated (pytest or
otherwise) regression tests, only `shellcheck` plus manual verification
against scratch git repos in both review rounds — a real gap for a future
change to that logic, left as a follow-up rather than blocking this PR on
building a bash-test harness from scratch.

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
