#!/bin/bash
# Spec consistency checks for pre-release validation.
# Run via: tox -e spec-check

set -u

SPEC_DIR="specs/001-youtube-backup"
ok=0

echo "=== Spec consistency checks ==="
echo

# 1. Check for unresolved [NEEDS CLARIFICATION] in primary spec artifacts
if grep -Fn '[NEEDS CLARIFICATION]' "$SPEC_DIR/spec.md" "$SPEC_DIR/plan.md" 2>/dev/null; then
    echo "FAIL: unresolved [NEEDS CLARIFICATION] items above"
    ok=1
else
    echo "OK: no unresolved clarifications"
fi
echo

# 2. Task completion stats
done_count=$(grep -cF -- '- [X]' "$SPEC_DIR/tasks.md" 2>/dev/null || echo 0)
total_count=$(grep -c -- '^- \[' "$SPEC_DIR/tasks.md" 2>/dev/null || echo 0)
echo "Tasks: $done_count done / $total_count total"
echo

# 3. CLI command vs spec FR coverage
cli_count=$(grep -rlE '@click\.(command|group)' annextube/cli/*.py 2>/dev/null | wc -l)
fr_cli=$(grep -cE 'FR-05[0-9]' "$SPEC_DIR/spec.md" 2>/dev/null || echo 0)
echo "CLI commands: $cli_count in code, $fr_cli FR entries in spec"
if [ "$cli_count" -gt "$fr_cli" ]; then
    echo "WARNING: more CLI commands than spec FRs -- run /speckit.analyze"
fi

exit $ok
