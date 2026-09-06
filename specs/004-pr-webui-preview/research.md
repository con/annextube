# Phase 0 Research: PR Web UI Previews

Input: issue #21 asked to (1) review available datasets with videos to pick
one for previews, (2) decide between a Netlify-based approach (as used for
PDF previews in `stamped-principles/stamped-paper`) and a GitHub Pages
subpath approach, and (3) look for existing helpers already in the project
that manage such previews.

> **Note on scope**: this document was written alongside `spec.md`, ahead of
> a formal `/speckit.plan` pass, to answer the two research questions the
> issue asked for explicitly. `/speckit.plan`'s own Phase 0 should treat this
> as a starting point to verify/extend, not a substitute — in particular the
> security architecture in §4 below needs to be validated against whatever
> GitHub Actions triggers are actually chosen.
>
> **This revision corrects factual errors found by review** in the first
> draft, which overstated how much of this already works today. Every claim
> below about the current state of `annextubetesting`/`gh-pages` was
> re-verified directly against the repository (branches, workflow YAML,
> script contents, and the live `gh-pages` branch) rather than assumed.

## 1. Existing helpers already in the repo — what they actually do today

| File | What it does today |
|---|---|
| `tools/setup_demo_branch.sh` | **Local-only.** Creates an orphan `annextubetesting` branch and populates it with a small, real, pre-fetched `@AnnexTubeTesting` archive, committing video files directly to git (unannexed) so GitHub Pages can serve them without special-remote support. **This branch does not exist on `origin`** (verified: absent from `git branch -a`, `git ls-remote --heads origin`, and the GitHub API) — the script only creates it in whoever's local clone runs it. |
| `tools/deploy-demo.sh` | **Local-only**, and depends on the branch above. `git archive annextubetesting` → `annextube generate-web` → checks out `gh-pages`, wipes it (`git rm -rf .` + `git clean -fd`), copies in the new build, and **commits** — but never pushes. It prints `git push origin gh-pages --force` as a manual next step for the human running it. |
| `.github/workflows/deploy-demo.yml` | **Not related to `annextubetesting` at all.** Its "Generate demo archive" step runs `annextube init … --all-to-git`, `annextube backup`, `annextube generate-web` inline — a fresh, live YouTube fetch, from scratch, every run. It *does* perform the real `git push origin gh-pages --force`. Its automatic `push:` trigger is commented out specifically because that live fetch gets blocked by YouTube's datacenter-IP bot detection on CI runners; today it only runs via manual `workflow_dispatch`. |

And, checked directly against the live branch: **the demo currently published
at `con.github.io/annextube/` is not built from `@AnnexTubeTesting`/
`annextubetesting` at all** — its `README.md` on `gh-pages` describes "3
sample videos from Distribits 2024" from the DataLad YouTube channel. So
today there is exactly one, manually-produced deployment, using a third
dataset that is different again from either script's target.

**What this means for the feature**: none of the three pieces above can be
"reused" as-is to get a working per-PR preview pipeline. What can be reused
is their *approach* (archive a known-good dataset → `generate-web` →
publish to `gh-pages`) and, once actually pushed to `origin`,
`annextubetesting` as *the* shared dataset. Two things this feature must
now explicitly do that were incorrectly assumed to already exist in the
first draft of this document:

- **Publish `annextubetesting` to `origin`** (one-time), and add a
  scheduled (not purely manual) job to refresh it, so it doesn't silently
  go stale the way the current manual-only process would.
- **Replace, not reuse, the publish step** in `deploy-demo.sh`/
  `deploy-demo.yml`: both wipe the entire `gh-pages` tree before
  committing, which is exactly wrong for a model where N PRs must each own
  a `pr-<number>/` subpath that survives every other PR's rebuild (see §3
  and the corresponding `spec.md` requirement).

## 2. Which dataset to use for previews

Considered:

- **`@AnnexTubeTesting`**: small, maintained specifically for annextube
  testing (per `CLAUDE.md`'s "Test Channel" section), has playlists and
  captions. Already has tooling written for it
  (`tools/setup_demo_branch.sh`), even though that tooling has not yet been
  run against `origin`.
- **The channel currently used for the live demo** (DataLad YouTube
  channel / Distribits 2024 talks): rejected as the preview data source —
  it exists only as a one-off manual `gh-pages` deployment with no
  branch/script maintaining it, so there is nothing to "reuse" here either.
- **Any other real channel**: rejected — would need its own fetch/refresh
  story, larger size, and no CI-safe way to keep it current without hitting
  the same bot-detection wall `deploy-demo.yml` already hit.

**Decision**: `@AnnexTubeTesting`, via the `annextubetesting` branch —
once it is actually published to `origin` and kept fresh by a scheduled
job (new work, not existing infrastructure). All previews build against
whatever that branch currently holds, via `git archive`, exactly the
mechanism `deploy-demo.sh` already demonstrates locally (this part of the
first draft's "symlinking the dataset" idea holds up fine — it's the
*existence* of the branch on `origin` that was wrong, not the mechanism).

## 3. Hosting approach: Netlify vs. GitHub Pages subpath

| | Netlify (à la `stamped-paper`) | GitHub Pages subpath (`gh-pages`) |
|---|---|---|
| New account/service | Yes — Netlify site + auth token as a repo secret | No — reuses the `gh-pages` branch already published at `con.github.io/annextube/` |
| Preview isolation | Native (Netlify deploy previews), each on its own subdomain/origin | Manual: one subfolder per PR (`pr-<number>/`), **same origin** as the production demo — see §4's same-origin caveat |
| Concurrent-update safety | Handled by Netlify | Must be built by us: the publish step MUST update only its own `pr-<number>/` path and MUST NOT wipe the branch the way today's scripts do (§1) |
| Cleanup on PR close | Netlify expires/removes deploy previews automatically | Must be built by us: a `pull_request: closed` job that removes just `pr-<number>/` |
| Secrets/token architecture for fork PRs | Netlify's own token, scoped to Netlify, not the repo | See §4 — nontrivial either way, but achievable with `GITHUB_TOKEN` if the build/publish split below is followed |

**Decision**: GitHub Pages subpath, following the archive→generate-web
approach demonstrated by `deploy-demo.sh`, but with a **new, from-scratch
publish step** (scoped to `pr-<number>/`, never a full-tree wipe) and a
**new, from-scratch security architecture** (§4) — not a drop-in reuse of
either existing script. This still avoids a new external service/account,
which was the main appeal, but the first draft substantially understated
the amount of new engineering this actually requires; that correction is
reflected in `spec.md`'s requirements.

Netlify remains worth revisiting if the concurrency/publish-scoping work
below turns out to be more fragile in practice than expected.

## 4. Security architecture: this is the load-bearing decision, not a footnote

The first draft of this document contained a direct self-contradiction here
(flagged in review): the comparison table claimed "`GITHUB_TOKEN`'s default
permissions are enough to push to `gh-pages`" for fork PRs, while a later
section correctly noted that a fork PR's `GITHUB_TOKEN` is **read-only by
default** under the safe `pull_request` trigger. Only one of those can be
true, and it matters because it decides whether this design is safe to
build at all.

**The actual constraint**: rendering "this PR's version of the UI" requires
executing this PR's own code (`uv run annextube generate-web` against
whatever `annextube/`/`frontend/` now contains, `npm`/`uv` dependency
resolution, etc.). If that execution happens in a job that also holds a
`GITHUB_TOKEN` with `contents: write` (as `deploy-demo.yml` already uses for
its own, trusted-code-only, deploy), a malicious fork PR can use that
execution to do anything a repo-write token can do — force-push over other
branches, delete tags, etc. This is the well-known "pwn request" pattern
for `pull_request_target` (or any workflow that checks out and *executes*
fork content under an elevated token); it is not a matter of care/discipline
around a single `run:` step, since the arbitrary-code-execution step *is*
the feature (FR-001 requires actually building the PR's code).

**Required architecture** (now a hard requirement in `spec.md`, not left
open): split build and publish into two jobs/workflows with different
trust levels.

1. **Build job** — triggered by plain `pull_request` (default, read-only
   `GITHUB_TOKEN`, no `contents: write`). Checks out the PR's own ref,
   archives the shared `annextubetesting` data, runs `annextube
   generate-web`, and uploads the static result as a workflow artifact.
   This is the only job that ever executes PR-authored code, and it never
   has write access to anything.
2. **Publish job** — triggered by `workflow_run` on completion of (1), so
   it always runs the *base* repository's own workflow definition with a
   privileged `GITHUB_TOKEN` (`contents: write`), regardless of what the PR
   changed. It downloads the artifact from (1) — never checks out, builds,
   or executes anything from the PR's ref — copies it into
   `pr-<number>/` on `gh-pages` (touching nothing else), and posts/updates
   the PR comment.

This is the standard mitigation for this exact scenario (see GitHub's own
guidance on "pwn requests"), and it is the only way to satisfy "no fork PR
should get write access to the repo" given that `GITHUB_TOKEN` permissions
are repository-wide, not branch-scoped — there is no `contents: write, but
only for gh-pages` permission to fall back on.

**Two risks that remain even with the split**, both now recorded in
`spec.md` as accepted risks rather than left unmentioned:

- **Same-origin content**: a `pr-<number>/` preview is served from the same
  origin as the production demo (`con.github.io/annextube/`), unlike
  Netlify's per-preview subdomains. A fork PR's JS runs on a trusted
  project domain. This is a known, generally-accepted tradeoff for
  path-based preview hosting, but should be a conscious choice, not an
  oversight.
- **`gh-pages` size growth**: `setup_demo_branch.sh` commits real video
  files (unannexed) so Pages can serve them; every open PR's preview
  duplicates that same binary content into `gh-pages` history, which
  neither script ever squashes. Cleanup-on-close bounds the number of
  *live* copies, not history growth.

## Open questions for `/speckit.plan`

- Concrete `workflow_run` wiring (artifact name/retention, how the publish
  job recovers the PR number from the triggering build run) — mechanical,
  but needs to be gotten right for the split in §4 to actually hold.
- Whether the scoped `pr-<number>/`-only publish step is a small
  git-worktree-based update-in-place, or a switch to existing tooling
  (e.g. `peaceiris/actions-gh-pages`'s `destination_dir` + non-wiping mode)
  that already handles subpath-scoped, non-destructive publishing.
- The concrete scheduled-refresh mechanism and cadence for
  `annextubetesting` once it is published to `origin`.
