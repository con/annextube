#!/bin/bash
# Mutate step for the gh-pages retry loop (see gh_pages_push_retry.sh):
# re-verifies the build is still fresh -- guarding the window between the
# publish job's own earlier freshness check and this point (artifact
# download, Python setup) and between successive retry attempts, not just
# the one check made at job start -- immediately before regenerating
# pr-<number>/ in the given gh-pages worktree, so a stale build can never
# race past a newer one (FR-007).
#
# If the build has gone stale (a newer commit is now this PR's head), skips
# publishing and marks itself as skipped via $PREVIEW_SKIP_MARKER (default:
# /tmp/preview-stale-skip) so the calling workflow step can avoid updating
# the PR comment to point at content that was never actually published.
# Always exits 0 in the skip case -- staleness is an expected outcome, not
# a failure -- so the retry wrapper's subsequent push becomes a harmless
# no-op.
#
# Usage: tools/gh_pages_publish_preview.sh <head_sha> <source_dir> <worktree_dir>
#
# Run from the main checkout (not the worktree) -- resolves
# tools/pr_preview_resolve_target.sh relative to the current directory.

set -eu

head_sha="${1:?Usage: $0 <head_sha> <source_dir> <worktree_dir>}"
source_dir="${2:?Usage: $0 <head_sha> <source_dir> <worktree_dir>}"
worktree_dir="${3:?Usage: $0 <head_sha> <source_dir> <worktree_dir>}"
marker="${PREVIEW_SKIP_MARKER:-/tmp/preview-stale-skip}"

rm -f "$marker"

if ! pr_number=$(tools/pr_preview_resolve_target.sh "$head_sha"); then
    echo "Build for ${head_sha} is no longer current; skipping publish."
    touch "$marker"
    exit 0
fi

annextube prepare-ghpages \
    --output-dir "$worktree_dir" \
    --source-dir "$source_dir" \
    --gh-branch gh-pages \
    --subpath "pr-${pr_number}"
