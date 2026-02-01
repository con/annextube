#!/bin/bash
set -e

cd /home/yoh/proj/annextube

echo "==> Removing test-archives/ files from git history"

# Check if any test-archives files are in git
if git ls-files test-archives/ | grep -q .; then
    echo "Found test-archives files in git:"
    git ls-files test-archives/
    echo

    # Remove from git but keep in filesystem
    git rm --cached -r test-archives/

    echo "✓ Removed from git index"

    # Commit the removal
    git commit -m "Remove test-archives/ files from git tracking

test-archives/ is in .gitignore and should not be tracked.
All demo files and results belong in the working directory only.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

    echo "✓ Committed removal"
else
    echo "No test-archives files found in git - nothing to remove"
fi

echo
echo "Current status:"
git status test-archives/ || echo "test-archives/ is not tracked (correct)"
