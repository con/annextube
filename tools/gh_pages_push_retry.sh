#!/bin/bash
# Fetch gh-pages into a separate git worktree, run the given mutate-and-commit
# command against it, and push -- retrying (up to a bound) when the push
# loses a race against a concurrent publish/teardown for a different PR
# (each PR's subpath is independent, but they share one branch/commit
# history, so two concurrent writers can race on the push itself).
#
# A worktree (rather than `git checkout` inside the same working directory
# this script and the rest of tools/ live in) is deliberate: gh-pages is an
# unrelated orphan branch with no tools/ directory at all, so checking it
# out in-place would delete the very scripts this workflow step is still
# running out of mid-execution. The worktree keeps the calling checkout
# (and this script) untouched throughout.
#
# Assumes `origin/gh-pages` already exists (true for this repository today
# -- it already hosts the public demo). If it doesn't, this fails with a
# plain git error rather than attempting to bootstrap one; that is an
# out-of-scope, one-time setup step, not something this retry loop handles.
#
# Shared by the preview publish and teardown workflows so the retry
# behavior is defined and tested in exactly one place, per CLAUDE.md's DRY
# convention.
#
# Usage:
#   tools/gh_pages_push_retry.sh <worktree_dir> -- <command> [args...]
#
# <command> is invoked with `<worktree_dir>` freshly reset to
# origin/gh-pages on every attempt (so no state from a previous, losing
# attempt leaks into the next one) -- NOT with that directory as cwd; it
# must operate on it explicitly (e.g. `git -C <worktree_dir>`, or an
# `--output-dir <worktree_dir>`-style option). It MUST leave that worktree
# clean, with any change already committed, or make no commit at all if
# there is nothing to do -- in the latter case the subsequent push is a
# harmless no-op ("Everything up-to-date").
#
# Exits 0 once the push succeeds (including the no-op case). Exits 1 if it
# never succeeds within the attempt budget.

set -eu

worktree_dir="${1:?Usage: $0 <worktree_dir> -- <command> [args...]}"
shift
if [ "${1:-}" != "--" ]; then
    echo "Usage: $0 <worktree_dir> -- <command> [args...]" >&2
    exit 2
fi
shift

cleanup() {
    git worktree remove --force "$worktree_dir" >/dev/null 2>&1 || rm -rf "$worktree_dir"
}
trap cleanup EXIT

max_attempts=5
attempt=1

while true; do
    cleanup
    git fetch origin gh-pages
    git worktree add -B gh-pages "$worktree_dir" origin/gh-pages

    "$@"

    if git -C "$worktree_dir" push origin gh-pages; then
        exit 0
    fi

    attempt=$((attempt + 1))
    if [ "$attempt" -gt "$max_attempts" ]; then
        echo "ERROR: gh-pages push kept losing the race after" \
            "$max_attempts attempts" >&2
        exit 1
    fi
    echo "Push rejected (concurrent publish/teardown), retrying" \
        "($attempt/$max_attempts)..."
done
