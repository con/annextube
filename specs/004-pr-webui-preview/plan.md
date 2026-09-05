# Implementation Plan: PR Web UI Previews

**Branch**: `004-pr-webui-preview` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-pr-webui-preview/spec.md`

**Note**: Per the originating issue (#21), this PR delivers the design-plan
artifacts only (`spec.md`, `research.md`, this `plan.md`, `data-model.md`,
`contracts/`, `quickstart.md`). No CI workflow code is implemented in this
PR — `/speckit.tasks` and `/speckit.implement` are follow-up work once this
design is reviewed and accepted.

## Summary

Reviewers of PRs that change the AnnexTube web UI (frontend source, or the
backend code that generates `web/`) currently have no way to see the result
without checking out the branch and running `annextube generate-web`
locally. This plan adds an automated, per-PR preview: build the web UI from
the PR's head commit against the project's existing pre-archived
`annextubetesting` demo dataset, publish it somewhere reviewers can click
into, post/update a link on the PR, and tear the preview down when the PR
closes.

**Recommended approach** (see `research.md` for the full comparison):
reuse the project's existing GitHub Pages deployment (the `gh-pages` branch
already used by `deploy-demo.yml`) by publishing each PR's build to a
per-PR subpath (`gh-pages:/pr-<number>/`), generated from the
`annextubetesting` orphan branch (pushed to `origin` as a one-time
prerequisite — see `research.md`'s correction) — not Netlify, and not a
live YouTube fetch. The publish step itself should extend the existing
`annextube prepare-ghpages` CLI command (source-directory and subpath
parameters) rather than hand-rolling new branch-publish logic (research.md,
"Decision: Reuse `prepare-ghpages`/`unannex`") — a contained, focused
extension, though a larger one than a single new flag; see that section for
what changes it needs.

## Technical Context

**Language/Version**: Python 3.10+ (extending the existing `annextube` CLI)
plus YAML (GitHub Actions workflow) — no new application language
introduced.
**Primary Dependencies**: GitHub Actions (`actions/checkout`,
`actions/github-script` or equivalent for PR comments), the project's own
`annextube` CLI — specifically `prepare-ghpages` (extended with subpath
support) and `generate-web`/`unannex` as needed — git/git-annex (already
required build dependencies). No new runtime dependency.
**Storage**: The `gh-pages` git branch (already used for the public demo)
gains per-PR subdirectories; source content is the existing `annextubetesting`
orphan branch (already git-annex-tracked, already has all demo video content
committed to git via `--all-to-git`; pushed to `origin` as a prerequisite,
per `research.md`). No database, no new storage system.
**Testing**: Workflow-level validation only (this is CI infrastructure, not
application code): a dry-run build step that fails the check on generation
error (FR-008); manual verification steps captured in `quickstart.md`.
Existing `tox`/`pytest`/`playwright` suites are unaffected — this feature
does not touch `annextube/` or `frontend/` source.
**Target Platform**: GitHub-hosted Actions runners (`ubuntu-latest`), output
served as static files via GitHub Pages.
**Project Type**: CI/CD workflow (infrastructure), not an application
feature — no `frontend/`/`backend/` source directories are added; the only
new "source" is `.github/workflows/` and `tools/` scripts (implementation
phase, not this PR).
**Performance Goals**: Preview build-and-publish completes within a typical
CI job duration (SC-001/FR-006 target: reviewer can interact with a preview
within ~2 minutes of checks completing) — bounded by the existing
`generate-web` runtime against the small, fixed `annextubetesting` dataset
(already used for the public demo, currently well under a minute to
generate).
**Constraints**: MUST NOT fetch from YouTube at preview-build time (already
fails in CI due to bot detection — see `docs/content/how-to/troubleshooting.md`);
MUST NOT require secrets on fork PRs beyond what a read-only checkout needs;
MUST NOT re-fetch video content from YouTube per preview (the shared
`annextubetesting` source is fetched once, independent of preview count —
see `research.md` for why served/checked-out copies are bounded by, not
zero across, concurrent preview count under the recommended design).
**Scale/Scope**: Bounded by the number of concurrently open PRs touching the
web UI (currently low, single-digit at any time for this project) — no
scale requirements beyond "doesn't grow `gh-pages` without bound," which
FR-009/SC-003 (cleanup) directly addresses.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **X. FOSS Principles** (offline capability / no mandatory cloud
  dependency beyond what the project already depends on): PASS for the
  recommended GitHub Pages approach — it adds no new third-party service;
  the project already depends on GitHub for hosting, CI, and its existing
  public demo. A Netlify-based alternative would introduce a new external
  vendor dependency and was weighed against this principle in
  `research.md` (see the comparison table) as a factor against it, not a
  hard violation (previews are optional, developer-facing infrastructure,
  not end-user functionality) — flagged in Complexity Tracking below since
  it's a judgment call, not a strict spec conflict.
- **XI. Resource Efficiency** (avoid re-fetching/duplicating data): PASS on
  the requirement this principle most directly governs — network
  efficiency/avoiding re-fetching — since the design's core requirement
  (FR-011) is to reuse the single `annextubetesting` branch as the shared
  preview *source* rather than each preview independently fetching from
  YouTube. **Not** a strict pass on disk efficiency in the fullest sense:
  the recommended publish mechanism gives each concurrently open preview
  its own on-disk/served copy of the (small, fixed) dataset rather than a
  single shared served copy — a bounded, explicitly-scoped tradeoff, not an
  oversight; see `research.md`'s "Net effect on the video-duplication
  question" and the Complexity Tracking entry below.
- **XIII. DataLad-Native Operations**: PASS with a note — the existing
  `annextubetesting` branch and `tools/setup_demo_branch.sh` currently use
  raw git/git-annex commands (predating this principle's adoption), not
  `datalad create`/`datalad save`. This plan does not introduce new raw
  git-annex usage beyond what those existing scripts already do, so it does
  not add a new violation; bringing those existing scripts into DataLad-native
  form is out of scope for this feature and tracked as a follow-up
  (see `research.md` Alternatives Considered).
- **V. Code Efficiency & Conciseness** / **VIII. DRY**: PASS — the
  recommended design extends the existing `annextube prepare-ghpages` CLI
  command (which already implements gh-pages branch handling, frontend
  build, and data copy) — via a source-directory parameter plus a subpath
  parameter, a real if contained code change (see `research.md`'s Decision
  for the specifics `copy_data_to_ghpages` needs) — and reuses
  `tools/setup_demo_branch.sh`'s `annextubetesting` dataset, rather than
  introducing a parallel new deployment mechanism or hand-rolling new shell
  logic (`research.md`, "Decision: Reuse `prepare-ghpages`/`unannex`").
- **II. Multi-Interface Exposure / Frontend Independence**: PASS — the
  preview publishes the same static `web/` output the frontend already
  produces client-side-only; no backend is stood up for previews.

No unresolved violations. One judgment-call tradeoff (GitHub Pages vs.
Netlify, weighed toward GitHub Pages) is recorded in Complexity Tracking for
visibility, not because it's a constitution violation.

## Project Structure

### Documentation (this feature)

```text
specs/004-pr-webui-preview/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md         # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── preview-workflow.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

This is a CI/CD-infrastructure feature, not a new application module — the
existing `annextube/models|services|cli|lib` and `frontend/src` structure
(documented in `CLAUDE.md`) is unaffected. Implementation (a follow-up PR,
after `/speckit.tasks`) is expected to touch only:

```text
annextube/cli/
└── prepare_ghpages.py        # EXISTING — gains a new `--subpath` option
                              #   (e.g. `pr-<number>`) so it can publish under
                              #   a subdirectory of the target branch instead
                              #   of always overwriting the branch root
                              #   (implementation phase; see research.md)

.github/workflows/
├── deploy-demo.yml          # existing — unaffected
└── pr-webui-preview.yml     # NEW — build+publish preview on PR events
                              #        (calls `annextube prepare-ghpages
                              #        --subpath pr-<number>`), teardown on
                              #        close (implementation phase)

tools/
├── deploy-demo.sh            # existing — unaffected
└── setup_demo_branch.sh      # existing — reused as the source of the
                              #   annextubetesting dataset this feature builds
                              #   from; pushing that branch to `origin` once
                              #   is a deployment prerequisite (research.md)
```

**Structure Decision**: No new top-level project/module. This is additive
CI configuration plus a contained extension of the *existing*
`annextube prepare-ghpages` CLI command (new source-directory and subpath
parameters — see Complexity Tracking below for why this is more than a
one-flag change), reusing `setup_demo_branch.sh`'s `annextubetesting`
dataset. `frontend/` is unmodified — the design deliberately does not add a
shared-data-path frontend capability (see Complexity Tracking); only
`annextube/cli/prepare_ghpages.py` changes, in the implementation phase.

## Complexity Tracking

> Recorded for visibility per the Constitution Check judgment calls above —
> none are strict violations requiring rejection, but each trades off
> against a principle enough to warrant an explicit record rather than a
> silent PASS.

| Judgment call | Why the alternative was considered | Why the simpler (recommended) option was chosen |
|---|---|---|
| External host (Netlify) vs. reusing GitHub Pages | Netlify's free tier offers automatic deploy-preview-per-PR and PR-comment integration out of the box, which is less custom workflow code to write than a hand-rolled per-PR-subpath scheme | Reusing GitHub Pages avoids a new external account/vendor dependency (Principle X), reuses existing project infrastructure (Principle VIII/DRY), and avoids re-solving "how do I get video content onto a third-party host" — the content is already fetched into this repository's own infrastructure. See `research.md` for the full comparison, including that this choice is *not* strictly better than Netlify on served-storage duplication (both scale per-preview) — the deciding factors are the vendor/credential-surface ones, not storage. |
| Bounded per-preview data duplication vs. a shared-data-path frontend capability | A separate `VITE_DATA_BASE_PATH`-style capability (decoupling where the frontend fetches data/media from where its own app assets are served) would let every preview's subpath share one served copy of `videos/`/`playlists/`, giving FR-011/SC-004 a stronger "zero duplication" guarantee | Not proposed: this project's concurrently-open-PR count is small (single-digit) and the preview dataset is small/fixed, so the resulting duplication is bounded and cheap — adding new, untested frontend architecture to eliminate a cost this small would be over-engineering relative to the problem (Principle V). Documented as the natural follow-up if preview volume or dataset size ever grows enough to matter (`research.md`). |
