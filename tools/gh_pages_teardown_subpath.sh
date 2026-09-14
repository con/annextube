#!/bin/bash
# Mutate step for the gh-pages retry loop (see gh_pages_push_retry.sh):
# removes pr-<number>/ from the given gh-pages worktree if present,
# committing the removal. Idempotent and safe to call when there is
# nothing to do (subpath was already removed, or never published) --
# always exits 0 in that case, so the retry wrapper's subsequent `git push`
# becomes a harmless no-op.
#
# Usage: tools/gh_pages_teardown_subpath.sh <worktree_dir> <pr_number>

set -eu

worktree_dir="${1:?Usage: $0 <worktree_dir> <pr_number>}"
pr_number="${2:?Usage: $0 <worktree_dir> <pr_number>}"
subpath="pr-${pr_number}"

if [ ! -d "${worktree_dir}/${subpath}" ]; then
    echo "${subpath}/ not present (never published, or already torn down)."
    exit 0
fi

git -C "$worktree_dir" rm -rf "$subpath" >/dev/null
git -C "$worktree_dir" commit -m "Retire preview for closed PR #${pr_number}"
