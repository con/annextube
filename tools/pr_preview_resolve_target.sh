#!/bin/bash
# Resolve the PR number a preview build's commit belongs to, and check that
# commit is still that PR's current head, before the publish step is allowed
# to overwrite anything on gh-pages.
#
# Both the PR number and the freshness check are derived entirely from
# GitHub-authoritative API calls keyed on the commit SHA -- never from
# anything the (possibly untrusted, fork-originated) build job itself
# reports. See specs/004-pr-webui-preview/research.md, "Decision: Fork-PR
# trust boundary and build-freshness check" for why: trusting a
# self-reported PR number would let a malicious fork PR overwrite a
# different, victim PR's preview.
#
# Usage:
#   tools/pr_preview_resolve_target.sh <head_sha>
#
# Requires: gh CLI, authenticated (GH_TOKEN/GITHUB_TOKEN in the environment,
# as GitHub Actions runners already provide), run from within the target
# repository's checkout (uses `gh`'s repo auto-detection).
#
# On success (the given commit is still its PR's current head): prints the
# PR number to stdout and exits 0.
# On failure (no PR found for the commit, or a newer commit already exists on
# that PR): prints a message to stderr and exits 1 -- the caller MUST NOT
# publish in this case.

set -u

usage() {
    echo "Usage: $0 <head_sha>" >&2
}

head_sha="${1:-}"
if [ -z "$head_sha" ]; then
    usage
    exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
    echo "ERROR: gh CLI not found" >&2
    exit 2
fi

# Derive the PR number from the commit itself (GitHub-authoritative), not
# from anything the build job self-reports.
pr_numbers=$(gh api "repos/{owner}/{repo}/commits/${head_sha}/pulls" \
    --jq '.[].number' 2>/dev/null)
pr_count=$(printf '%s' "$pr_numbers" | grep -c . || true)

if [ "$pr_count" -eq 0 ]; then
    echo "ERROR: no pull request found for commit ${head_sha}" >&2
    exit 1
fi
if [ "$pr_count" -gt 1 ]; then
    # Only plausible if the same commit object is the head of more than one
    # open PR (e.g. two forks both pointed at the exact same upstream
    # commit) -- their content is byte-identical by construction, but pick
    # neither rather than silently resolving to an unverified one.
    echo "ERROR: commit ${head_sha} is associated with more than one" \
        "pull request ($(printf '%s' "$pr_numbers" | tr '\n' ' '))," \
        "refusing to guess which one to publish for" >&2
    exit 1
fi
pr_number="$pr_numbers"

# Fetch that PR's *current* head SHA and compare -- if a newer commit has
# since been pushed, this build is stale and must not publish (FR-007).
current_head_sha=$(gh pr view "$pr_number" --json headRefOid \
    --jq '.headRefOid' 2>/dev/null)

if [ -z "$current_head_sha" ]; then
    echo "ERROR: could not fetch current head SHA for PR #${pr_number}" >&2
    exit 1
fi

if [ "$current_head_sha" != "$head_sha" ]; then
    echo "SKIP: build commit ${head_sha} is no longer PR #${pr_number}'s" \
        "current head (${current_head_sha}) -- a newer build supersedes" \
        "this one, not publishing" >&2
    exit 1
fi

echo "$pr_number"
