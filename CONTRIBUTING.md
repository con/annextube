# Contributing to annextube

## Development Setup

See the [README](README.md) and [CLAUDE.md](CLAUDE.md) for the full development environment setup.

Quick start:

```bash
uv pip install -e ".[devel]"
uv run tox            # full test sweep (lint + type + tests)
uv run tox -e py3     # unit tests only
```

---

## Release Process

Releases are automated via [intuit/auto](https://intuit.github.io/auto/).
Every push to `master` triggers the `Release` GitHub Actions workflow; a new release is
cut only when the merged PR carries **both** a version-bump label **and** the `release`
label (controlled by `onlyPublishWithReleaseLabel: true` in `.autorc`).

### Labels

**Version-bump labels** (control *what kind* of release — prefixed `release-` to avoid Dependabot conflicts):

| Label           | Changelog section    | Version bump | When to use                         |
| --------------- | -------------------- | ------------ | ----------------------------------- |
| `release-major` | 💥 Breaking Change   | X.0.0        | Breaking API or CLI changes         |
| `release-minor` | 🚀 Enhancement       | 0.X.0        | New backward-compatible features    |
| `release-patch` | 🐛 Bug Fix           | 0.0.X        | Bug fixes, minor improvements       |
| `performance`   | 🏎 Performance       | 0.0.X        | Performance improvements            |

**Changelog-only labels** (appear in CHANGELOG but do not bump the version):

| Label           | Changelog section    | When to use                                |
| --------------- | -------------------- | ------------------------------------------ |
| `internal`      | 🏠 Internal          | Internal refactoring, no user-facing change |
| `documentation` | 📝 Documentation     | Docs-only changes                          |
| `tests`         | 🧪 Tests             | Test additions or improvements             |

**Trigger / control labels**:

| Label          | Effect       | When to use                            |
| -------------- | ------------ | -------------------------------------- |
| `release`      | (trigger)    | Required alongside a bump label        |
| `skip-release` | (none)       | Merge without cutting a release        |
| `released`     | (auto-set)   | Applied by auto after a release is cut |

> **Both labels are required.** A PR with only `release-patch` will not cut a
> release. A PR with only `release` will not cut a release. You need **both** a
> version-bump label (`release-major`/`release-minor`/`release-patch`) **and**
> the `release` trigger label on the same PR.

> **Why the `release-` prefix?** Dependabot adds plain `major`, `minor`, and `patch`
> labels to its own PRs. Using `release-major`/`release-minor`/`release-patch` avoids
> accidentally triggering a release when a Dependabot PR is merged.

### Cutting a Release

1. Open (or update) a PR that represents the release intent.
2. Add the appropriate version-bump label (`release-major`, `release-minor`, or
   `release-patch`) **and** the `release` label.
3. Merge the PR.
4. The `Release` workflow triggers automatically and will:
   - Compute the next version from the label.
   - Prepend a changelog entry to `CHANGELOG.md` and push the commit.
   - Create a git tag (`vX.Y.Z`).
   - Publish a GitHub Release with the changelog as release notes.
   - Build the Python package and upload to PyPI.
   - Apply the `released` label to all PRs included in this release and post a
     comment with the release version.

### First-Time Repository Setup (maintainers only)

After merging the auto-release PR, do these steps once:

1. **Create GitHub labels** (requires write access to the repo):

   ```bash
   bash .github/create-labels.sh
   ```

2. **Add repository secrets** (Settings → Secrets and variables → Actions):

   | Secret                           | Value                                                                |
   | -------------------------------- | -------------------------------------------------------------------- |
   | `GH_TOKEN`                       | PAT with `contents: write` + `pull-requests: write` scopes          |
   | `PYPI_TOKEN`                     | PyPI API token scoped to the `annextube` project                     |

   > Note: the built-in `GITHUB_TOKEN` cannot push new commits back to a protected
   > branch or trigger subsequent workflows, which is why a personal PAT is needed.

### If Automated Release Fails

auto is robust but occasionally fails. Here are the common failure modes:

**GitHub API / token issues**
- Symptom: `Error: Resource not accessible by integration` or `403 Forbidden`
- Fix: Verify `GH_TOKEN` is set and the PAT has `contents: write` + `pull-requests: write`.
  Re-run the failed workflow after updating the secret.

**CHANGELOG too large (GitHub release body limit ~125 KB)**
- Symptom: `422 Unprocessable Entity` or `RequestError: body is too long` in the release
  step (auto calls the GitHub Releases API which has a body-size cap).
- Fix: First check whether auto already staged a CHANGELOG commit:

  ```bash
  git log --oneline -3
  ```

  If the top commit is auto's CHANGELOG update (message like `Update CHANGELOG.md`),
  push it and create the release manually:

  ```bash
  git push origin master
  gh release create vX.Y.Z --title "vX.Y.Z" --notes "See CHANGELOG.md for details."
  ```

  If auto did NOT commit yet, update `CHANGELOG.md` manually, commit it, then run
  the two commands above.

**PyPI upload fails**
- Symptom: `twine upload` error; the git tag and GitHub Release are already created.
- Fix: Upload manually:

  ```bash
  python -m build
  TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-token> twine upload dist/*
  ```

- Verify `PYPI_TOKEN` secret is set and scoped to the `annextube` project on PyPI.

**Protected branch blocks auto's commit**
- Symptom: `remote: error: GH006: Protected branch update failed`
- Fix option A: Add `"protected-branch"` plugin to `.autorc` (first entry in `plugins`)
  and add a `PROTECTED_BRANCH_REVIEWER_TOKEN` secret (PAT with admin rights).
- Fix option B: Exempt the `github-actions[bot]` from the branch protection rules in
  Settings → Branches → Protection rules → "Allow specific actors to bypass".

**Duplicate release / tag already exists**
- Symptom: `fatal: tag 'vX.Y.Z' already exists`
- Fix: Delete the orphaned tag and re-run:

  ```bash
  git tag -d vX.Y.Z
  git push origin :refs/tags/vX.Y.Z
  ```

**Dry run (preview without releasing)**

```bash
# Download auto locally first (one-time)
curl -fsSL https://github.com/intuit/auto/releases/download/v11.3.6/auto-linux.gz \
  | gunzip > ~/auto && chmod a+x ~/auto

GH_TOKEN=<your-token> ~/auto version    # prints next version
GH_TOKEN=<your-token> ~/auto changelog  # prints CHANGELOG diff
```

### Manual Release (bypass auto)

If auto is unavailable or broken:

```bash
NEW_VERSION=X.Y.Z

# Edit CHANGELOG.md with the release notes, then:
git add CHANGELOG.md
git commit -m "chore: release $NEW_VERSION"
git tag "v$NEW_VERSION"
git push origin master "v$NEW_VERSION"

# GitHub Release
gh release create "v$NEW_VERSION" --title "v$NEW_VERSION" --notes-file CHANGELOG_snippet.md

# PyPI
python -m build
TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-token> twine upload dist/*
```
