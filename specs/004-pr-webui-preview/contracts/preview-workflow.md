# Contract: PR Preview Workflow Interface

This feature has no REST/GraphQL API — its "contract" is the GitHub Actions
workflow interface: what triggers it, what it reads, and what it produces.
Documented here so the implementation phase (`/speckit.tasks`) has an
unambiguous target, and so this contract itself can be reviewed before any
workflow YAML is written.

## Trigger events (inputs)

| Event | Effect |
|---|---|
| `pull_request: [opened, synchronize, reopened]`, filtered by `paths: ['frontend/**', 'annextube/cli/generate_web.py', ...]` (research.md) | Build-and-publish (or rebuild) the preview for that PR at its current head commit. |
| `pull_request: [closed]` (covers merge and close-without-merge) | Retire (remove) the PR's preview subpath. |

Fork PRs MUST be supported (FR-010) via a two-workflow split — an untrusted
`pull_request`-triggered **build** job (no secrets) and a trusted
`workflow_run`-triggered **publish** job (holds `contents: write`) — per
`research.md`, "Decision: Fork-PR trust boundary and build-freshness check."
That decision is the normative source for *why*; the steps below are its
concrete shape.

## Build step (untrusted context; produces the artifact to publish)

1. Check out the PR's head commit (untrusted context — may be a fork).
2. Check out/export the `annextubetesting` branch's content (trusted,
   read-only — pushed to `origin`, not the fork; see `data-model.md`
   prerequisite).
3. Run `annextube generate-web` (the PR's version of the code) against that
   content, exactly as `tools/deploy-demo.sh`/`tools/setup_demo_branch.sh`
   already do for the public demo.
4. On failure: stop here. The check MUST fail (FR-008) and no publish step
   runs — the previous published preview (if any) is left untouched, not
   overwritten with a broken one.
5. On success: upload the **whole build directory** (the `annextubetesting`
   export's data directories — `videos/`, `playlists/`, its TSV/JSON
   metadata — *plus* the `web/` subdirectory `generate-web` just added to
   it) as a build artifact (`actions/upload-artifact`), not just `web/`
   alone. Publishing needs both pieces: `web/` is only the frontend build;
   the data files it fetches at runtime (per `frontend/src/utils/config.ts`'s
   base-path-relative resolution) live alongside it, not inside it (see
   `annextube/cli/generate_web.py`'s own post-run instructions, which say
   to serve from the *parent* of `web/`, not from `web/` itself —
   `quickstart.md` demonstrates this). No `gh-pages` write happens in this
   job — it has no credentials to do so, and nothing it self-reports
   (including a PR number, if included in the artifact) is trusted by the
   publish step below.

## Publish step (trusted context only, triggered by `workflow_run`)

1. Download the build artifact (`actions/download-artifact`, `run-id:
   ${{ github.event.workflow_run.id }}`).
2. **Derive the PR number and freshness entirely from GitHub-authoritative
   fields on the `workflow_run` event — never from the artifact**:
   a. Read `github.event.workflow_run.head_sha` (the commit GitHub actually
      built — not self-reported by the untrusted build job).
   b. Resolve that SHA to a PR number via a commit-keyed API lookup (e.g.
      `gh api repos/{owner}/{repo}/commits/{head_sha}/pulls`), not via
      anything carried in the artifact.
   c. Fetch that PR's *current* head SHA (e.g. `gh pr view <number> --json
      headRefOid`) and compare it to `head_sha` from step (a). If they
      don't match, skip publishing (a newer build is already published or
      in flight).
   This closes both FR-007 (no stale overwrite) and the cross-PR spoofing
   gap FR-010 raises — see `research.md`'s "Decision: Fork-PR trust
   boundary and build-freshness check" for why deriving the PR number from
   the artifact instead of from `head_sha` would NOT be safe.
3. Run `annextube prepare-ghpages --output-dir <annextube-checkout>
   --source-dir <downloaded-artifact> --gh-branch gh-pages --subpath
   pr-<pr_number>` — the *extended* form of the existing CLI command (see
   `research.md`, "Decision: Reuse `prepare-ghpages`/`unannex`") — instead
   of hand-rolled branch-switch/copy/commit shell. Two distinct paths, not
   one, per `research.md`'s analysis of what the extension actually needs:
   - `--output-dir` is the Actions job's own checkout of `con/annextube`
     itself (a real git clone with an `origin` remote) — the repo
     `prepare-ghpages` runs its `git`/branch/commit operations against, as
     it already does today. It is NOT the downloaded artifact.
   - `--source-dir` (new parameter) is the downloaded, extracted build
     artifact from step 1 — this is what the extended `copy_frontend_to_ghpages`/
     `copy_data_to_ghpages` copy *from*, replacing today's
     `git checkout origin/master -- ...` (which reads from `--output-dir`'s
     own default branch and would find no `videos/`/`playlists/` there,
     since this repository's `master` doesn't carry that content — only
     `annextubetesting` does).

   The new `--subpath` option must confine all of `prepare-ghpages`'s
   existing writes (frontend copy, data copy, commit) to
   `<branch-root>/pr-<pr_number>/`, leaving the branch root and any other
   subpath (other PRs' previews) untouched.
4. Create or update (not duplicate) a PR comment with the preview URL
   (`https://<pages-domain>/pr-<pr_number>/`) and the commit it reflects
   (FR-004, FR-006).

## Teardown step (on PR close/merge)

1. Remove `gh-pages:/pr-<pr_number>/` (or mark it retired, e.g. replace its
   `index.html` with a short "this PR is closed" notice) and commit
   (FR-009).
2. Leave the PR comment in place but it now points at a removed/retired
   path — acceptable per spec (Assumptions: reviewers checking a
   long-closed PR's stale link is a lesser concern than active previews
   growing storage unbounded).

## Failure/edge-case contract (traceability to spec Edge Cases)

| Spec edge case | Contract behavior |
|---|---|
| Build fails | Failed check on the PR; no publish; existing preview (if any) untouched. |
| Two pushes in quick succession | Publish step's independent head-SHA re-check (above) ensures a build for an older commit is skipped, not published, once a newer one exists — regardless of which build finishes first. |
| Fork PR | Build has no secrets; only the separate, trusted publish step has `contents: write`, scoped to `gh-pages`; that step never trusts PR identity carried from the untrusted build without re-verifying it live (see above). |
| Sample dataset unavailable/needs refresh | Out of scope for build failure handling — the `annextubetesting` branch is committed content in this repo, not a live fetch, so it does not have a "temporarily unavailable" failure mode the way a live API call would. |
| Many concurrent/historical previews | The video *source* is fetched from YouTube once regardless of preview count (FR-011). *Served* copies scale with concurrently open previews (bounded, small — see `research.md`'s video-duplication note), not with historical/closed-PR count, since teardown (FR-009) removes each preview's subpath on close. |
