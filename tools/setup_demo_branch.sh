#!/bin/bash
set -e  # Exit on error
set -u  # Exit on undefined variable

# Ensure we're in the project root
if [ ! -f "pyproject.toml" ] || [ ! -d "annextube" ]; then
    echo "Error: This script must be run from the annextube project root"
    exit 1
fi

# Parse command line arguments
FORCE_CLEAN=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --force-clean)
            FORCE_CLEAN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--force-clean]"
            echo "  --force-clean: Remove existing branch and start fresh (default: incremental update)"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "Setting up annextubetesting orphan branch"
echo "=========================================="
echo

# Handle existing worktree/branch based on --force-clean flag
if [ "$FORCE_CLEAN" = true ]; then
    echo "Force clean mode: Removing existing branch and worktree..."

    # Remove old worktree if exists
    if [ -d .worktrees/annextubetesting ]; then
        echo "Removing old worktree..."
        git worktree remove .worktrees/annextubetesting --force || true
        rm -rf .worktrees/annextubetesting
    fi

    # Remove old branch if exists
    if git show-ref --verify --quiet refs/heads/annextubetesting; then
        echo "Removing old annextubetesting branch..."
        git branch -D annextubetesting
    fi
else
    echo "Incremental update mode: Will update existing branch if present..."

    # Check if branch exists
    if git show-ref --verify --quiet refs/heads/annextubetesting; then
        echo "Branch 'annextubetesting' exists, will update it"

        # Remove worktree if exists (we'll re-add it)
        if [ -d .worktrees/annextubetesting ]; then
            git worktree remove .worktrees/annextubetesting --force || true
            rm -rf .worktrees/annextubetesting
        fi
    else
        echo "Branch 'annextubetesting' does not exist, will create it"
    fi
fi

# Create worktrees directory
mkdir -p .worktrees

# Create worktree
echo "Creating worktree for 'annextubetesting'..."
if git show-ref --verify --quiet refs/heads/annextubetesting; then
    # Branch exists, check it out
    git worktree add .worktrees/annextubetesting annextubetesting
else
    # New branch - create orphan branch with empty worktree
    git worktree add --orphan annextubetesting .worktrees/annextubetesting
fi

cd .worktrees/annextubetesting

echo "Working directory after creation:"
ls -la
echo

# Initialize annextube archive
echo "=========================================="
echo "Initializing annextube archive..."
echo "=========================================="
uv --directory ../.. run annextube init . https://www.youtube.com/@AnnexTubeTesting \
    --all-to-git

echo
echo "=========================================="
echo "Running backup..."
echo "=========================================="
uv --directory ../.. run annextube backup --output-dir .

echo
echo "=========================================="
echo "Unannexing video.mkv files..."
echo "=========================================="

# Check if video.mkv files exist
if find videos -name "video.mkv" -print -quit | grep -q .; then
    echo "Found video.mkv files, unannexing them..."

    # Try to use datalad (with uv if available, or system datalad)
    if command -v uv >/dev/null 2>&1; then
        echo "Using datalad via uv..."
        uv --directory ../.. run datalad run -m "unannexing and adding mkv directly into git for this demo" \
            --input 'videos/*/*/*/video.mkv' \
            'git annex unannex {inputs}'
    elif command -v datalad >/dev/null 2>&1; then
        echo "Using system datalad..."
        datalad run -m "unannexing and adding mkv directly into git for this demo" \
            --input 'videos/*/*/*/video.mkv' \
            'git annex unannex {inputs}'
    else
        echo "datalad not found, using git annex unannex directly..."
        find videos -name "video.mkv" -type l -print0 | xargs -0 git annex unannex
        git add videos/
        git commit -m "Unannex video.mkv files and add directly to git for demo"
    fi
else
    echo "UNEXPECTED: No video.mkv files found (expected even with --all-to-git mode)"
    exit 1
fi

echo
echo "=========================================="
echo "Creating README..."
echo "=========================================="
cat > README.md << 'EOF'
# annextube Demo Content Branch

This branch contains pre-populated demo content for the GitHub Pages deployment at https://con.github.io/annextube/

## Purpose

The `annextubetesting` branch is an **orphan branch** (no shared history with master) that stores YouTube archive content used to generate the live demo.

## Content

- **Videos** from the @AnnexTubeTesting channel (all available)
- **Metadata, thumbnails, and captions**
- **Video files** (unannexed, stored directly in git)
- **Playlists** with video symlinks

## How It Works

1. The `.github/workflows/deploy-demo.yml` workflow triggers on:
   - Changes to `frontend/**` in master branch
   - Changes to this `annextubetesting` branch (when content is updated)

2. The workflow:
   - Checks out this branch
   - Runs `annextube generate-web` to build the web UI from existing data
   - Deploys to `gh-pages` branch

3. **No YouTube fetching happens in CI**, avoiding bot detection issues

## Updating Demo Content

To update the demo content, run the setup script from the master branch:

\`\`\`bash
# From the master branch
git checkout master

# Run the setup script (incremental update by default)
./tools/setup_demo_branch.sh

# Or force a clean rebuild
./tools/setup_demo_branch.sh --force-clean

# Push the updated branch
git push origin annextubetesting
\`\`\`

The script will:
- Create/update the annextubetesting branch in a worktree
- Run \`annextube init\` and \`annextube backup\` to fetch latest content
- Unannex video files to store them directly in git
- Generate README and commit all changes

## Content Structure

```
annextubetesting/
├── .annextube/config.toml    # Archive configuration (--all-to-git mode)
├── .gitattributes             # All files in git (no annexing)
├── videos/                    # Video directories with metadata and files
├── playlists/                 # Playlist data with symlinks
├── authors.tsv               # Author metadata
└── README.md                 # This file
```

## Configuration

This branch uses `--all-to-git` mode, which means:
- All files are stored in regular git (not git-annex)
- Suitable for GitHub Pages deployment
- Video files are unannexed and committed directly

## Notes

- This is an orphan branch - it has no shared history with master
- Content was generated using:
  ```
  annextube init . https://www.youtube.com/@AnnexTubeTesting --all-to-git
  annextube backup --output-dir .
  datalad run -m "unannexing..." --input 'videos/*/*/*/video.mkv' 'git annex unannex {inputs}'
  ```
- The workflow automatically regenerates the web UI when this branch or the frontend code changes
EOF

git add README.md
git commit -m "Add README for demo branch"

echo
echo "=========================================="
echo "Final status:"
echo "=========================================="
git log --oneline -5
echo
echo "Files in branch:"
ls -lh videos/ playlists/ authors.tsv .annextube/ .gitattributes 2>/dev/null || true
echo

# Verify expected content
echo "=========================================="
echo "Verifying content..."
echo "=========================================="

# Count videos
video_count=$(find videos -type f -name "metadata.json" 2>/dev/null | wc -l)
echo "Videos found: $video_count"

# Count playlists
playlist_count=$(find playlists -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
echo "Playlists found: $playlist_count"

# Check video.mkv files are unannexed (regular files, not symlinks)
mkv_symlinks=$(find videos -name "video.mkv" -type l 2>/dev/null | wc -l)
mkv_files=$(find videos -name "video.mkv" -type f 2>/dev/null | wc -l)
echo "video.mkv files (unannexed): $mkv_files"
echo "video.mkv symlinks (should be 0): $mkv_symlinks"

# Verify expectations
if [ "$video_count" -gt 0 ] && [ "$playlist_count" -gt 0 ] && [ "$mkv_symlinks" -eq 0 ] && [ "$mkv_files" -eq "$video_count" ]; then
    echo "✓ Content verification passed!"
    echo "  Videos: $video_count, Playlists: $playlist_count, Unannexed files: $mkv_files"
else
    echo "⚠ WARNING: Content verification failed!"
    echo "  Expected: >0 videos, >0 playlists, 0 symlinks, mkv_files == video_count"
    echo "  Got: $video_count videos, $playlist_count playlists, $mkv_files files, $mkv_symlinks symlinks"
fi

echo
echo "Demo branch setup complete!"
echo "To push: git push origin annextubetesting"
echo
echo "To return to master:"
echo "  cd ../.."
echo "  git checkout master"

