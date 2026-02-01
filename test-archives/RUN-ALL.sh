#!/bin/bash
set -e

echo "======================================================================"
echo "Complete Cookie Implementation Test"
echo "======================================================================"
echo

TEST_DIR="$(cd "$(dirname "$0")" && pwd)"

# Step 1: Clean up git
echo "[1/3] Cleaning up git history"
bash "$TEST_DIR/cleanup-git.sh"
echo
echo "Press Enter to continue..."
read

# Step 2: Commit the fix
echo "[2/3] Committing git-annex fix"
bash "$TEST_DIR/commit-fix.sh"
echo
echo "Press Enter to continue..."
read

# Step 3: Run complete test
echo "[3/3] Running complete test with miniconda + deno"
bash "$TEST_DIR/complete-test.sh" 2>&1 | tee "$TEST_DIR/test-output.log"

echo
echo "======================================================================"
echo "Test complete! Output saved to: $TEST_DIR/test-output.log"
echo "======================================================================"
