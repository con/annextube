#!/bin/bash
set -e

cd /home/yoh/proj/annextube

echo "==> Committing git-annex cookie path fix"
git add annextube/services/git_annex.py
git commit -m "Fix git-annex cookie path - remove quotes

Remove quotes around cookie path and proxy in git config options.
Git config doesn't need quotes for paths and they can cause issues.

Before: --cookies \"/path/to/cookies.txt\"
After:  --cookies /path/to/cookies.txt

This fixes potential issues with git-annex reading the cookie file path.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

echo "✓ Committed fix"
git log -1 --oneline
