#!/bin/bash
# SPDX-FileCopyrightText: 2026 Yaroslav Halchenko <yaroslav.o.halchenko@dartmouth.edu>
# SPDX-License-Identifier: MIT
#
# Generated with Claude Code 2.1.259 / Claude Sonnet 4.6

# Create intuit/auto release labels for this repository.
# Run once after setting up auto-release:
#   bash .github/create-labels.sh
# Requires: gh auth login (your own GitHub account with write access)
set -euo pipefail

REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
echo "Creating auto-release labels for $REPO ..."

create_label() {
  local name=$1 color=$2 description=$3
  gh label create "$name" --color "$color" --description "$description" \
    --repo "$REPO" --force
  echo "  ✓ $name"
}

# Version-bump labels (prefixed with 'release-' to avoid conflicts with
# Dependabot's own major/minor/patch labels)
create_label "release-major"  "C5000B" "Increment the major version when merged"
create_label "release-minor"  "F1A60E" "Increment the minor version when merged"
create_label "release-patch"  "870048" "Increment the patch version when merged"

# Trigger/control labels
create_label "release"        "16a34a" "Create a release when this PR is merged"
create_label "skip-release"   "bf5416" "Preserve the current version when merged"
create_label "released"       "84cc16" "This PR has been released"

# Changelog-categorization labels (no release-bump, appear in CHANGELOG sections)
# No prefix needed — Dependabot does not use these label names
create_label "internal"       "696969" "Changes only affect the internal API"
create_label "documentation"  "cfd3d7" "Changes only affect the documentation"
create_label "tests"          "e4e669" "Add or improve existing tests"

# Performance: triggers a patch bump + appears under '🏎 Performance' in CHANGELOG
create_label "performance"    "f4b2d8" "Improve performance of an existing feature"

echo "Done."
