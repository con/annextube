# GitHub Pages Archive Sharing - Phase 1 Implementation Plan

**Feature Branch**: `enh-gh_pages`
**Status**: Planning
**Created**: 2026-02-07

## Overview

Phase 1 implements the foundation for sharing annextube archives via GitHub Pages:
- Unannex workflow to make content directly available in git
- GitHub Pages deployment preparation and tooling
- Full demonstration using AnnexTubeTesting channel

## Prerequisites

- **Test Repository**: https://github.com/con/annextubetesting
- **Local Clone**: `/home/yoh/proj/annextubes/annextubetesting`
- **Test Channel**: https://www.youtube.com/@AnnexTubeTesting
- **Existing Frontend**: Svelte-based web interface (already implemented in main)

## Success Criteria

- [ ] Users can unannex files by pattern/size with one command
- [ ] AnnexTubeTesting archive fully deployed to GitHub Pages
- [ ] Web interface works on GitHub Pages without git-annex dependency
- [ ] Documentation covers complete sharing workflow
- [ ] All tests pass including integration tests with real deployment

---

## Phase 1 Tasks

### Task Group A: Unannex Command Implementation

#### A1: Design CLI Interface (2 hours)

**Task**: Define command signature and options

**Implementation**:
```python
# annextube/cli/unannex.py
@click.command()
@click.option('--output-dir', required=True, type=click.Path(exists=True),
              help='Path to archive repository')
@click.option('--pattern', multiple=True,
              help='Glob pattern for files to unannex (can be specified multiple times)')
@click.option('--max-size', type=str,
              help='Maximum file size to unannex (e.g., "10M", "100K", "1G")')
@click.option('--dry-run', is_flag=True,
              help='Show what would be unannexed without making changes')
@click.option('--update-gitattributes', is_flag=True, default=True,
              help='Update .gitattributes to prevent re-annexing')
@click.option('--force', is_flag=True,
              help='Proceed even if files exceed GitHub limits')
def unannex(output_dir, pattern, max_size, dry_run, update_gitattributes, force):
    """Unannex files to make them directly available in git."""
    pass
```

**Acceptance Criteria**:
- [ ] Command accessible via `annextube unannex --help`
- [ ] All options documented with clear help text
- [ ] Pattern matching supports multiple patterns
- [ ] Size parsing handles K/M/G suffixes

**Testing**:
- [ ] Unit test: Parse size strings ("10M" → 10485760 bytes)
- [ ] Unit test: Multiple patterns combine correctly
- [ ] Integration test: `--help` displays all options

---

#### A2: Implement File Discovery (3 hours)

**Task**: Find annexed files matching patterns and size constraints

**Implementation**:
```python
# annextube/services/unannex.py

from pathlib import Path
from datasalad.runners import call_git_success

def find_annexed_files(
    repo_path: Path,
    patterns: list[str],
    max_size: int | None = None
) -> list[tuple[Path, int]]:
    """
    Find annexed files matching criteria.

    Returns:
        List of (file_path, size_bytes) tuples
    """
    # 1. Find all annexed files
    result = call_git_success(
        ['git', 'annex', 'find', '--include', '*'],
        cwd=repo_path,
        capture_output=True
    )
    annexed_files = result.stdout.strip().split('\n')

    # 2. Filter by patterns
    matching_files = []
    for file_path in annexed_files:
        path = Path(file_path)
        if any(path.match(pattern) for pattern in patterns):
            # Get file size
            size = get_annexed_file_size(repo_path, path)
            if max_size is None or size <= max_size:
                matching_files.append((path, size))

    return matching_files


def get_annexed_file_size(repo_path: Path, file_path: Path) -> int:
    """Get size of annexed file without downloading it."""
    # git annex info --json <file> | jq .size
    result = call_git_success(
        ['git', 'annex', 'info', '--json', str(file_path)],
        cwd=repo_path,
        capture_output=True
    )
    import json
    info = json.loads(result.stdout)
    return info.get('size', 0)
```

**Acceptance Criteria**:
- [ ] Finds all annexed files in repository
- [ ] Pattern matching works with glob syntax (*, **, ?)
- [ ] Size filtering excludes files above threshold
- [ ] Returns accurate file sizes without downloading content
- [ ] Handles repositories with no annexed files gracefully

**Testing**:
- [ ] Unit test: Pattern matching edge cases (empty, wildcards, nested paths)
- [ ] Unit test: Size parsing and comparison
- [ ] Integration test: Find files in annextubetesting clone
  - Test pattern: `videos/*/thumbnail.jpg`
  - Test pattern: `videos/*/video.mkv` with `--max-size 10M`
- [ ] Test: Repository with 0 annexed files returns empty list

---

#### A3: Implement Unannex Operation (4 hours)

**Task**: Unannex files and optionally update .gitattributes

**Implementation**:
```python
def unannex_files(
    repo_path: Path,
    files: list[Path],
    update_gitattributes: bool = True,
    dry_run: bool = False
) -> dict:
    """
    Unannex files and update .gitattributes.

    Returns:
        {
            'unannexed': list[Path],
            'failed': list[tuple[Path, str]],  # (path, error)
            'total_size': int
        }
    """
    result = {
        'unannexed': [],
        'failed': [],
        'total_size': 0
    }

    for file_path in files:
        try:
            if not dry_run:
                # git annex unannex <file>
                call_git_success(
                    ['git', 'annex', 'unannex', str(file_path)],
                    cwd=repo_path
                )
                # git add <file>
                call_git_success(
                    ['git', 'add', str(file_path)],
                    cwd=repo_path
                )

            size = get_annexed_file_size(repo_path, file_path)
            result['unannexed'].append(file_path)
            result['total_size'] += size

        except Exception as e:
            result['failed'].append((file_path, str(e)))

    if update_gitattributes and not dry_run:
        update_gitattributes_for_unannexed(repo_path, files)

    return result


def update_gitattributes_for_unannexed(
    repo_path: Path,
    unannexed_files: list[Path]
) -> None:
    """
    Update .gitattributes to prevent re-annexing.

    Adds patterns like:
        videos/*/thumbnail.jpg annex.largefiles=nothing
    """
    gitattributes_path = repo_path / '.gitattributes'

    # Extract unique patterns from file list
    patterns = extract_patterns(unannexed_files)

    # Read existing .gitattributes
    if gitattributes_path.exists():
        content = gitattributes_path.read_text()
    else:
        content = ""

    # Append new patterns
    new_lines = []
    for pattern in patterns:
        rule = f"{pattern} annex.largefiles=nothing"
        if rule not in content:
            new_lines.append(rule)

    if new_lines:
        if content and not content.endswith('\n'):
            content += '\n'
        content += '\n'.join(new_lines) + '\n'
        gitattributes_path.write_text(content)

        # git add .gitattributes
        call_git_success(['git', 'add', '.gitattributes'], cwd=repo_path)


def extract_patterns(files: list[Path]) -> set[str]:
    """
    Extract minimal set of patterns covering unannexed files.

    Example: [videos/v1/thumb.jpg, videos/v2/thumb.jpg] → videos/*/thumb.jpg
    """
    # Simple implementation: group by directory structure
    patterns = set()

    # Group files by extension and depth
    by_extension = {}
    for file_path in files:
        ext = file_path.suffix
        depth = len(file_path.parts)
        key = (ext, depth)
        if key not in by_extension:
            by_extension[key] = []
        by_extension[key].append(file_path)

    # Generate patterns
    for (ext, depth), paths in by_extension.items():
        # If all files have same structure, use wildcard pattern
        if depth >= 2:
            # e.g., videos/*/thumbnail.jpg
            pattern_parts = paths[0].parts[:-1] + ('*',) + (paths[0].name,)
            patterns.add(str(Path(*pattern_parts)))
        else:
            # Shallow files, use exact names
            for path in paths:
                patterns.add(str(path))

    return patterns
```

**Acceptance Criteria**:
- [ ] Unannex operation succeeds for valid files
- [ ] .gitattributes updated with correct patterns
- [ ] Dry-run mode shows actions without making changes
- [ ] Failed operations reported with error details
- [ ] Total size calculated correctly
- [ ] Unannexed files are directly in git (not symlinks)

**Testing**:
- [ ] Unit test: Pattern extraction from file list
- [ ] Unit test: .gitattributes update logic (append, deduplicate)
- [ ] Integration test: Unannex thumbnails in annextubetesting
  ```bash
  annextube unannex --output-dir /home/yoh/proj/annextubes/annextubetesting \
                    --pattern "videos/*/thumbnail.jpg" \
                    --dry-run
  ```
- [ ] Integration test: Verify files are unannexed
  ```bash
  cd /home/yoh/proj/annextubes/annextubetesting
  # Check that thumbnails are real files, not symlinks
  test ! -L videos/*/thumbnail.jpg
  git status  # Should show thumbnails as modified/added
  ```
- [ ] Integration test: Verify .gitattributes contains `videos/*/thumbnail.jpg annex.largefiles=nothing`
- [ ] Test: Re-running `git annex add` does not re-annex excluded files

---

#### A4: Add GitHub Size Validation (2 hours)

**Task**: Warn when unannexed files exceed GitHub limits

**Implementation**:
```python
# GitHub limits
GITHUB_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
GITHUB_MAX_REPO_SIZE = 100 * 1024 * 1024 * 1024  # 100 GB (soft limit)
GITHUB_RECOMMENDED_REPO_SIZE = 1 * 1024 * 1024 * 1024  # 1 GB

def validate_github_limits(
    files: list[tuple[Path, int]],
    repo_path: Path,
    force: bool = False
) -> dict:
    """
    Check if unannexing would violate GitHub limits.

    Returns:
        {
            'ok': bool,
            'warnings': list[str],
            'errors': list[str],
            'total_size': int,
            'large_files': list[tuple[Path, int]]
        }
    """
    result = {
        'ok': True,
        'warnings': [],
        'errors': [],
        'total_size': 0,
        'large_files': []
    }

    # Check individual file sizes
    for file_path, size in files:
        result['total_size'] += size

        if size > GITHUB_MAX_FILE_SIZE:
            result['large_files'].append((file_path, size))
            msg = f"{file_path}: {format_size(size)} exceeds GitHub limit (100 MB)"
            result['errors'].append(msg)
            result['ok'] = False

    # Check total repository size
    current_repo_size = get_repo_size(repo_path)
    projected_size = current_repo_size + result['total_size']

    if projected_size > GITHUB_RECOMMENDED_REPO_SIZE:
        msg = f"Repository size will be {format_size(projected_size)} (GitHub recommends <1 GB)"
        result['warnings'].append(msg)

    if projected_size > GITHUB_MAX_REPO_SIZE:
        msg = f"Repository size will be {format_size(projected_size)} (GitHub soft limit: 100 GB)"
        result['warnings'].append(msg)

    if not force and not result['ok']:
        result['errors'].append("Use --force to proceed despite size violations")

    return result


def get_repo_size(repo_path: Path) -> int:
    """Get current repository size (git objects)."""
    git_dir = repo_path / '.git'
    total_size = 0

    for item in git_dir.rglob('*'):
        if item.is_file():
            total_size += item.stat().st_size

    return total_size


def format_size(size_bytes: int) -> str:
    """Format size in human-readable form."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
```

**Acceptance Criteria**:
- [ ] Detects files >100MB and reports as errors
- [ ] Warns when total size >1GB
- [ ] Warns when total size >100GB
- [ ] --force flag bypasses size errors
- [ ] Human-readable size formatting (KB, MB, GB)

**Testing**:
- [ ] Unit test: Size formatting (bytes → human readable)
- [ ] Unit test: Validation logic with mock file sizes
- [ ] Integration test: Try to unannex large video (>100MB) without --force
  - Should fail with clear error message
- [ ] Integration test: With --force flag, operation proceeds despite warnings

---

#### A5: Add Progress Reporting (2 hours)

**Task**: Show progress during unannex operations

**Implementation**:
```python
import click
from tqdm import tqdm

def unannex_with_progress(
    repo_path: Path,
    files: list[Path],
    dry_run: bool = False
) -> dict:
    """Unannex files with progress bar."""

    with tqdm(total=len(files), desc="Unannexing files", unit="file") as pbar:
        result = {
            'unannexed': [],
            'failed': [],
            'total_size': 0
        }

        for file_path in files:
            try:
                size = get_annexed_file_size(repo_path, file_path)

                if not dry_run:
                    call_git_success(
                        ['git', 'annex', 'unannex', str(file_path)],
                        cwd=repo_path
                    )
                    call_git_success(
                        ['git', 'add', str(file_path)],
                        cwd=repo_path
                    )

                result['unannexed'].append(file_path)
                result['total_size'] += size

                pbar.set_postfix_str(f"{format_size(size)}")
                pbar.update(1)

            except Exception as e:
                result['failed'].append((file_path, str(e)))
                pbar.update(1)

        return result
```

**Acceptance Criteria**:
- [ ] Progress bar shows current file being processed
- [ ] Progress bar shows total files and completion percentage
- [ ] Progress bar shows current file size
- [ ] Progress bar clears after completion
- [ ] Dry-run mode also shows progress

**Testing**:
- [ ] Integration test: Progress bar appears during unannex
- [ ] Integration test: Progress completes at 100%
- [ ] Visual test: Progress output is readable and informative

---

### Task Group B: GitHub Pages Deployment

#### B1: Frontend Build Configuration (3 hours)

**Task**: Update frontend build to support GitHub Pages deployment

**Implementation**:
```javascript
// frontend/vite.config.ts
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig(({ mode }) => {
  const isGitHubPages = mode === 'gh-pages';

  return {
    plugins: [svelte()],
    base: isGitHubPages ? '/annextubetesting/' : '/',
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      emptyOutDir: true,
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['svelte']
          }
        }
      }
    }
  };
});
```

```javascript
// frontend/src/config.ts
export const BASE_PATH = import.meta.env.BASE_URL;

export function resolveDataPath(relativePath: string): string {
  // Handle both local file:// and GitHub Pages
  if (window.location.protocol === 'file:') {
    // Local development: data is in parent directory
    return `../${relativePath}`;
  } else {
    // GitHub Pages: data is at BASE_PATH
    return `${BASE_PATH}${relativePath}`;
  }
}
```

**Acceptance Criteria**:
- [ ] Build creates optimized production bundle
- [ ] Base path configurable for GitHub Pages
- [ ] Asset paths resolve correctly on GitHub Pages
- [ ] Data file paths work for both file:// and https://
- [ ] Build includes all necessary files in dist/

**Testing**:
- [ ] Build test: `npm run build -- --mode gh-pages`
- [ ] Test: dist/ contains index.html, assets/, and all chunks
- [ ] Test: index.html references assets with correct base path
- [ ] Local test: Open dist/index.html in browser (file://)
- [ ] Manual test: Deploy to GitHub Pages, verify all resources load

---

#### B2: Create prepare-ghpages Command (4 hours)

**Task**: CLI command to prepare deployment-ready gh-pages branch

**Implementation**:
```python
# annextube/cli/ghpages.py

@click.command()
@click.option('--output-dir', required=True, type=click.Path(exists=True))
@click.option('--repo-name', help='GitHub repository name (e.g., "annextubetesting")')
@click.option('--gh-branch', default='gh-pages', help='Target branch name')
@click.option('--build-frontend', is_flag=True, default=True)
def prepare_ghpages(output_dir, repo_name, gh_branch, build_frontend):
    """Prepare archive for GitHub Pages deployment."""

    repo_path = Path(output_dir).resolve()

    # 1. Detect or prompt for repo name
    if not repo_name:
        # Try to infer from git remote
        repo_name = get_github_repo_name(repo_path)
        if not repo_name:
            click.echo("Error: --repo-name required (e.g., 'annextubetesting')")
            return 1

    # 2. Build frontend with GitHub Pages config
    if build_frontend:
        click.echo(f"Building frontend for GitHub Pages (/{repo_name}/)...")
        build_frontend_for_ghpages(repo_path, repo_name)

    # 3. Create/update gh-pages branch
    click.echo(f"Creating {gh_branch} branch...")
    create_ghpages_branch(repo_path, gh_branch)

    # 4. Copy frontend build to gh-pages branch
    copy_frontend_to_ghpages(repo_path, gh_branch)

    # 5. Provide deployment instructions
    print_deployment_instructions(repo_name, gh_branch)


def get_github_repo_name(repo_path: Path) -> str | None:
    """Extract GitHub repo name from git remote."""
    result = call_git_success(
        ['git', 'remote', 'get-url', 'origin'],
        cwd=repo_path,
        capture_output=True
    )
    url = result.stdout.strip()

    # Parse: https://github.com/con/annextubetesting.git
    # or: git@github.com:con/annextubetesting.git
    import re
    match = re.search(r'github\.com[:/][\w-]+/([\w-]+)(?:\.git)?$', url)
    if match:
        return match.group(1)
    return None


def build_frontend_for_ghpages(repo_path: Path, repo_name: str) -> None:
    """Build frontend with GitHub Pages base path."""
    frontend_dir = repo_path.parent.parent / 'frontend'  # Assuming project structure

    if not frontend_dir.exists():
        raise FileNotFoundError(f"Frontend directory not found: {frontend_dir}")

    # Set base path via environment variable
    env = os.environ.copy()
    env['VITE_BASE_PATH'] = f'/{repo_name}/'

    # npm run build -- --mode gh-pages
    subprocess.run(
        ['npm', 'run', 'build', '--', '--mode', 'gh-pages'],
        cwd=frontend_dir,
        env=env,
        check=True
    )


def create_ghpages_branch(repo_path: Path, branch_name: str) -> None:
    """Create orphan gh-pages branch."""

    # Check if branch exists
    result = subprocess.run(
        ['git', 'rev-parse', '--verify', f'refs/heads/{branch_name}'],
        cwd=repo_path,
        capture_output=True
    )

    if result.returncode != 0:
        # Branch doesn't exist, create orphan
        call_git_success(['git', 'checkout', '--orphan', branch_name], cwd=repo_path)
        call_git_success(['git', 'rm', '-rf', '.'], cwd=repo_path)
        call_git_success(['git', 'checkout', 'master'], cwd=repo_path)


def copy_frontend_to_ghpages(repo_path: Path, branch_name: str) -> None:
    """Copy built frontend to gh-pages branch."""

    frontend_dist = repo_path.parent.parent / 'frontend' / 'dist'

    # Checkout gh-pages branch
    call_git_success(['git', 'checkout', branch_name], cwd=repo_path)

    # Copy frontend files
    import shutil
    for item in frontend_dist.iterdir():
        dest = repo_path / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    # Copy data files (videos.tsv, playlists.tsv, etc.)
    # These should be in the main branch
    call_git_success(['git', 'checkout', 'master', '--', 'videos/videos.tsv'], cwd=repo_path)
    call_git_success(['git', 'checkout', 'master', '--', 'playlists/playlists.tsv'], cwd=repo_path)

    # Also copy video folders (for metadata and unannexed content)
    call_git_success(['git', 'checkout', 'master', '--', 'videos/'], cwd=repo_path)
    call_git_success(['git', 'checkout', 'master', '--', 'playlists/'], cwd=repo_path)

    # Add and commit
    call_git_success(['git', 'add', '.'], cwd=repo_path)
    call_git_success(
        ['git', 'commit', '-m', 'Deploy frontend to GitHub Pages'],
        cwd=repo_path
    )

    # Return to master
    call_git_success(['git', 'checkout', 'master'], cwd=repo_path)


def print_deployment_instructions(repo_name: str, branch_name: str):
    """Print next steps for user."""
    click.echo("\n" + "="*60)
    click.echo("GitHub Pages branch prepared successfully!")
    click.echo("="*60)
    click.echo(f"\nBranch: {branch_name}")
    click.echo(f"\nNext steps:")
    click.echo(f"  1. Push the {branch_name} branch to GitHub:")
    click.echo(f"       git push origin {branch_name}")
    click.echo(f"\n  2. Enable GitHub Pages in repository settings:")
    click.echo(f"       https://github.com/con/{repo_name}/settings/pages")
    click.echo(f"       - Source: Deploy from a branch")
    click.echo(f"       - Branch: {branch_name}")
    click.echo(f"       - Folder: / (root)")
    click.echo(f"\n  3. Your site will be available at:")
    click.echo(f"       https://con.github.io/{repo_name}/")
    click.echo("="*60 + "\n")
```

**Acceptance Criteria**:
- [ ] Command creates gh-pages branch (orphan, no history)
- [ ] Frontend built with correct base path for repo
- [ ] Data files (TSV, JSON) copied to gh-pages branch
- [ ] Unannexed content (thumbnails, videos) copied to gh-pages
- [ ] Clear deployment instructions printed
- [ ] Repository name auto-detected from git remote

**Testing**:
- [ ] Integration test: Run on annextubetesting clone
  ```bash
  annextube prepare-ghpages --output-dir /home/yoh/proj/annextubes/annextubetesting
  ```
- [ ] Test: gh-pages branch exists and contains:
  - index.html
  - assets/
  - videos/videos.tsv
  - videos/*/metadata.json
  - videos/*/thumbnail.jpg (unannexed)
- [ ] Test: Checkout gh-pages and open index.html locally
- [ ] Test: No git history from master branch in gh-pages

---

#### B3: Add .nojekyll and 404.html (1 hour)

**Task**: GitHub Pages configuration files

**Implementation**:
```python
def setup_ghpages_config(repo_path: Path, branch_name: str) -> None:
    """Create GitHub Pages configuration files."""

    call_git_success(['git', 'checkout', branch_name], cwd=repo_path)

    # Create .nojekyll to disable Jekyll processing
    nojekyll = repo_path / '.nojekyll'
    nojekyll.touch()
    call_git_success(['git', 'add', '.nojekyll'], cwd=repo_path)

    # Create 404.html for client-side routing
    html_404 = repo_path / '404.html'
    html_404.write_text("""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>AnnexTube Archive</title>
  <script>
    // Redirect to index.html with hash-based path
    var path = window.location.pathname.split('/').slice(2).join('/');
    var redirect = window.location.origin + window.location.pathname.split('/').slice(0, 2).join('/') + '/#/' + path;
    window.location.replace(redirect);
  </script>
</head>
<body>
  Redirecting...
</body>
</html>
""")
    call_git_success(['git', 'add', '404.html'], cwd=repo_path)

    call_git_success(['git', 'commit', '--amend', '--no-edit'], cwd=repo_path)
    call_git_success(['git', 'checkout', 'master'], cwd=repo_path)
```

**Acceptance Criteria**:
- [ ] .nojekyll file created in gh-pages branch
- [ ] 404.html handles client-side routing
- [ ] Direct URLs redirect to hash-based routes

**Testing**:
- [ ] Test: .nojekyll exists in gh-pages branch
- [ ] Test: 404.html exists and contains redirect script
- [ ] Manual test: After deployment, test direct URL navigation

---

### Task Group C: Testing with AnnexTubeTesting

#### C1: Prepare Test Repository (1 hour)

**Task**: Ensure annextubetesting is ready for testing

**Checklist**:
- [ ] Repository cloned at `/home/yoh/proj/annextubes/annextubetesting`
- [ ] Contains archived videos from @AnnexTubeTesting
- [ ] Has videos/, playlists/, metadata files
- [ ] Git annex initialized
- [ ] Remote origin points to https://github.com/con/annextubetesting

**Validation**:
```bash
cd /home/yoh/proj/annextubes/annextubetesting
git remote -v  # Should show con/annextubetesting
git annex info  # Should show annexed files
ls videos/*.tsv  # Should show videos.tsv
```

---

#### C2: Test Unannex Workflow (2 hours)

**Test Plan**:

**Test C2.1: Unannex all thumbnails**
```bash
cd /home/yoh/proj/annextubes/annextubetesting

# Dry run first
annextube unannex --output-dir . --pattern "videos/*/thumbnail.jpg" --dry-run

# Expected output:
# Would unannex 5 files (total: 256 KB):
#   videos/video1/thumbnail.jpg (48 KB)
#   videos/video2/thumbnail.jpg (52 KB)
#   ...
# Would update .gitattributes with:
#   videos/*/thumbnail.jpg annex.largefiles=nothing

# Actual unannex
annextube unannex --output-dir . --pattern "videos/*/thumbnail.jpg"

# Verify
ls -lh videos/*/thumbnail.jpg  # Should NOT be symlinks
git status  # Should show thumbnails modified
cat .gitattributes  # Should contain thumbnails pattern
```

**Expected Results**:
- [ ] All thumbnails unannexed successfully
- [ ] .gitattributes updated
- [ ] Files are real files, not symlinks
- [ ] Git status shows modified files

---

**Test C2.2: Unannex small videos (<10MB)**
```bash
# Find small videos
annextube unannex --output-dir . --pattern "videos/*/video.mkv" --max-size 10M --dry-run

# If any exist, unannex them
annextube unannex --output-dir . --pattern "videos/*/video.mkv" --max-size 10M

# Verify
git status
```

**Expected Results**:
- [ ] Only videos <10MB unannexed
- [ ] Larger videos remain annexed
- [ ] Size filtering works correctly

---

**Test C2.3: Test size validation**
```bash
# Try to unannex large video (should fail without --force)
annextube unannex --output-dir . --pattern "videos/large-video/video.mkv"

# Expected error:
# Error: videos/large-video/video.mkv (150.2 MB) exceeds GitHub limit (100 MB)
# Use --force to proceed despite size violations

# With --force (should proceed with warning)
annextube unannex --output-dir . --pattern "videos/large-video/video.mkv" --force
```

**Expected Results**:
- [ ] Large files rejected without --force
- [ ] --force allows operation with warnings
- [ ] Clear error messages displayed

---

#### C3: Test GitHub Pages Deployment (3 hours)

**Test Plan**:

**Test C3.1: Prepare gh-pages branch**
```bash
cd /home/yoh/proj/annextubes/annextubetesting

# Prepare deployment
annextube prepare-ghpages --output-dir .

# Verify gh-pages branch
git checkout gh-pages
ls -la
# Should contain:
# - index.html
# - assets/
# - videos/videos.tsv
# - videos/*/metadata.json
# - videos/*/thumbnail.jpg
# - .nojekyll
# - 404.html

git checkout master
```

**Expected Results**:
- [ ] gh-pages branch created
- [ ] All necessary files present
- [ ] No .git/annex directory in gh-pages
- [ ] Frontend built with correct base path

---

**Test C3.2: Local testing of gh-pages**
```bash
git checkout gh-pages

# Test with local server (simulates GitHub Pages)
python3 -m http.server 8000

# Open in browser: http://localhost:8000/
# Test:
# - Homepage loads
# - Videos list appears
# - Thumbnails display
# - Video metadata accessible
# - Search works
# - Filtering works
```

**Expected Results**:
- [ ] Web interface loads without errors
- [ ] All thumbnails visible
- [ ] Video metadata displays correctly
- [ ] Search and filtering functional
- [ ] No console errors

---

**Test C3.3: Deploy to GitHub Pages**
```bash
git checkout gh-pages
git push origin gh-pages

# Enable GitHub Pages in settings:
# https://github.com/con/annextubetesting/settings/pages
# Source: gh-pages branch, / (root)

# Wait for deployment (~1 min)
# Visit: https://con.github.io/annextubetesting/
```

**Manual Testing**:
- [ ] Page loads at https://con.github.io/annextubetesting/
- [ ] Thumbnails display correctly
- [ ] Video metadata accessible
- [ ] Search works
- [ ] Filter by date works
- [ ] Direct URLs work (test 404.html redirect)
- [ ] No broken links or missing assets
- [ ] Browser console shows no errors

---

### Task Group D: Documentation

#### D1: User Guide - Sharing Archives (3 hours)

**File**: `docs/content/how-to/share-archive-github-pages.md`

**Content Outline**:
```markdown
# How to Share Your Archive on GitHub Pages

## Overview
Learn how to publish your annextube archive to GitHub Pages for public access.

## Prerequisites
- Existing annextube archive
- GitHub account
- Git repository for your archive

## Step 1: Unannex Content for Direct Access

### Unannex Thumbnails (Recommended)
```bash
annextube unannex --output-dir ~/my-archive --pattern "videos/*/thumbnail.jpg"
```

### Unannex Small Videos (Optional)
```bash
annextube unannex --output-dir ~/my-archive \
                  --pattern "videos/*/video.mkv" \
                  --max-size 10M
```

### Understanding GitHub Limits
- Maximum file size: 100 MB
- Recommended repo size: < 1 GB
- Soft limit: 100 GB

## Step 2: Prepare GitHub Pages Deployment

```bash
annextube prepare-ghpages --output-dir ~/my-archive
```

This command:
- Builds optimized frontend
- Creates gh-pages branch
- Copies frontend and data files
- Sets up GitHub Pages config

## Step 3: Push to GitHub

```bash
cd ~/my-archive
git push origin gh-pages
```

## Step 4: Enable GitHub Pages

1. Go to repository settings: `https://github.com/YOUR_USERNAME/YOUR_REPO/settings/pages`
2. Source: **Deploy from a branch**
3. Branch: **gh-pages**
4. Folder: **/ (root)**
5. Click **Save**

## Step 5: Access Your Archive

After ~1 minute, your archive will be available at:
`https://YOUR_USERNAME.github.io/YOUR_REPO/`

## Deployment Models

### Model 1: Fully Contained (Demo Archives)
Unannex all content for complete offline access.
- Best for: Small channels, demos, educational content
- Limit: GitHub repo size limits

### Model 2: Metadata Only
Keep videos annexed, only unannex thumbnails and metadata.
- Best for: Large archives, preview/browse without video playback
- Benefits: Fast to clone, low storage

### Model 3: Hybrid (Coming in Phase 2)
Combine unannexed highlights with annexed content + remote URLs.
- Best for: Curated archives with featured content

## Troubleshooting

### Large Files Rejected
Error: `File exceeds 100 MB limit`

Solution: Either exclude large files or use Git LFS (advanced).

### Build Fails
Ensure frontend dependencies installed:
```bash
cd frontend && npm install
```

### Page Shows 404
Wait a few minutes after enabling GitHub Pages. Check deployment status in Actions tab.
```

**Testing**:
- [ ] Follow guide from scratch with test repository
- [ ] All commands work as documented
- [ ] Screenshots/examples match actual output
- [ ] Troubleshooting covers common issues

---

#### D2: CLI Reference Documentation (2 hours)

**File**: `docs/content/reference/cli-commands.md`

**Add sections**:

```markdown
## annextube unannex

Unannex files to make them directly available in git (not symlinked by git-annex).

### Usage

```bash
annextube unannex [OPTIONS]
```

### Options

- `--output-dir PATH` (required): Path to archive repository
- `--pattern PATTERN`: Glob pattern for files to unannex (can be specified multiple times)
- `--max-size SIZE`: Maximum file size to unannex (e.g., "10M", "100K", "1G")
- `--dry-run`: Show what would be unannexed without making changes
- `--update-gitattributes / --no-update-gitattributes`: Update .gitattributes to prevent re-annexing (default: true)
- `--force`: Proceed even if files exceed GitHub limits

### Examples

Unannex all thumbnails:
```bash
annextube unannex --output-dir ~/my-archive --pattern "videos/*/thumbnail.jpg"
```

Unannex small videos with size limit:
```bash
annextube unannex --output-dir ~/my-archive \
                  --pattern "videos/*/video.mkv" \
                  --max-size 10M
```

Dry run to preview changes:
```bash
annextube unannex --output-dir ~/my-archive \
                  --pattern "**/*.jpg" \
                  --dry-run
```

### Notes

- Unannexed files become regular git files (not symlinks)
- .gitattributes is updated to prevent re-annexing
- Use `--max-size` to respect GitHub file size limits
- Dry run mode shows exactly what will change

---

## annextube prepare-ghpages

Prepare archive for GitHub Pages deployment.

### Usage

```bash
annextube prepare-ghpages [OPTIONS]
```

### Options

- `--output-dir PATH` (required): Path to archive repository
- `--repo-name NAME`: GitHub repository name (auto-detected if not specified)
- `--gh-branch NAME`: Target branch name (default: "gh-pages")
- `--build-frontend / --no-build-frontend`: Build frontend before deployment (default: true)

### Examples

Basic usage (auto-detects repo name):
```bash
annextube prepare-ghpages --output-dir ~/my-archive
```

Specify repository name:
```bash
annextube prepare-ghpages --output-dir ~/my-archive --repo-name annextubetesting
```

### What It Does

1. Builds optimized frontend with GitHub Pages config
2. Creates orphan gh-pages branch (no history from main branch)
3. Copies frontend build and data files
4. Sets up .nojekyll and 404.html for routing
5. Commits changes to gh-pages branch
6. Prints deployment instructions

### Next Steps

After running this command:

1. Push gh-pages branch: `git push origin gh-pages`
2. Enable GitHub Pages in repository settings
3. Access your archive at `https://USERNAME.github.io/REPO/`
```

---

#### D3: Explanation - Deployment Models (2 hours)

**File**: `docs/content/explanation/github-pages-deployment.md`

**Content**: Explain the different deployment models, trade-offs, and architecture

**Testing**:
- [ ] Peer review for clarity
- [ ] Technical accuracy verified
- [ ] Links to related documentation

---

### Task Group E: Integration & Quality Assurance

#### E1: End-to-End Test Suite (4 hours)

**File**: `tests/integration/test_ghpages.py`

```python
import pytest
from pathlib import Path
import subprocess
from annextube.services.unannex import find_annexed_files, unannex_files
from annextube.cli.ghpages import prepare_ghpages


@pytest.fixture
def test_repo(tmp_path):
    """Create minimal test repository with annexed files."""
    repo = tmp_path / "test-archive"
    repo.mkdir()

    # Initialize git and git-annex
    subprocess.run(['git', 'init'], cwd=repo, check=True)
    subprocess.run(['git', 'annex', 'init'], cwd=repo, check=True)

    # Create test files
    videos_dir = repo / 'videos' / 'test-video'
    videos_dir.mkdir(parents=True)

    # Create small thumbnail (annex then unannex in test)
    thumb = videos_dir / 'thumbnail.jpg'
    thumb.write_bytes(b'fake thumbnail data')
    subprocess.run(['git', 'annex', 'add', str(thumb)], cwd=repo, check=True)

    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo, check=True)

    return repo


def test_find_annexed_files_pattern(test_repo):
    """Test finding annexed files by pattern."""
    files = find_annexed_files(
        test_repo,
        patterns=['videos/*/thumbnail.jpg']
    )

    assert len(files) == 1
    assert files[0][0].name == 'thumbnail.jpg'


def test_unannex_updates_gitattributes(test_repo):
    """Test that unannex updates .gitattributes."""
    files = find_annexed_files(test_repo, patterns=['*.jpg'])

    result = unannex_files(
        test_repo,
        [f[0] for f in files],
        update_gitattributes=True
    )

    assert len(result['unannexed']) == 1
    assert len(result['failed']) == 0

    gitattributes = test_repo / '.gitattributes'
    assert gitattributes.exists()
    content = gitattributes.read_text()
    assert 'annex.largefiles=nothing' in content


def test_unannex_dry_run(test_repo):
    """Test dry-run mode doesn't modify files."""
    files = find_annexed_files(test_repo, patterns=['*.jpg'])
    thumb_path = test_repo / files[0][0]

    # Check it's a symlink before
    assert thumb_path.is_symlink()

    result = unannex_files(
        test_repo,
        [f[0] for f in files],
        dry_run=True
    )

    # Still a symlink after dry run
    assert thumb_path.is_symlink()
    assert len(result['unannexed']) == 1


@pytest.mark.integration
def test_full_ghpages_workflow(test_repo):
    """Test complete GitHub Pages preparation workflow."""

    # 1. Unannex thumbnails
    files = find_annexed_files(test_repo, patterns=['*.jpg'])
    result = unannex_files(test_repo, [f[0] for f in files])
    assert len(result['unannexed']) > 0

    # 2. Commit changes
    subprocess.run(['git', 'add', '.'], cwd=test_repo, check=True)
    subprocess.run(['git', 'commit', '-m', 'Unannex thumbnails'], cwd=test_repo, check=True)

    # 3. Prepare gh-pages (requires frontend - skip in unit test)
    # This would be tested in E2E test with real repository


@pytest.mark.integration
@pytest.mark.slow
def test_annextubetesting_deployment():
    """Integration test with real annextubetesting repository."""

    repo_path = Path('/home/yoh/proj/annextubes/annextubetesting')

    if not repo_path.exists():
        pytest.skip("AnnexTubeTesting repository not found")

    # Test unannex command
    from click.testing import CliRunner
    from annextube.cli.unannex import unannex

    runner = CliRunner()
    result = runner.invoke(unannex, [
        '--output-dir', str(repo_path),
        '--pattern', 'videos/*/thumbnail.jpg',
        '--dry-run'
    ])

    assert result.exit_code == 0
    assert 'Would unannex' in result.output
```

**Testing**:
- [ ] All unit tests pass
- [ ] Integration test with test_repo passes
- [ ] Slow test with real annextubetesting repository passes (when available)

---

#### E2: Manual QA Checklist (2 hours)

**Checklist for Final Validation**:

**Unannex Command**:
- [ ] `--help` displays clear documentation
- [ ] Pattern matching works with wildcards
- [ ] Size filtering excludes large files
- [ ] Dry-run shows accurate preview
- [ ] Progress bar displays during operation
- [ ] .gitattributes updated correctly
- [ ] GitHub size warnings appear for large files
- [ ] --force bypasses size errors

**GitHub Pages Deployment**:
- [ ] Frontend builds without errors
- [ ] Base path configured correctly
- [ ] gh-pages branch created (orphan, no history)
- [ ] All data files copied
- [ ] .nojekyll created
- [ ] 404.html created
- [ ] Deployment instructions printed

**Live Deployment (annextubetesting)**:
- [ ] Page loads at https://con.github.io/annextubetesting/
- [ ] Thumbnails display
- [ ] Videos list appears
- [ ] Metadata accessible
- [ ] Search functional
- [ ] Filters work
- [ ] Direct URLs redirect correctly
- [ ] No console errors
- [ ] Mobile responsive

**Documentation**:
- [ ] How-to guide complete and accurate
- [ ] CLI reference up to date
- [ ] Examples tested and verified
- [ ] Troubleshooting covers common issues

---

## Timeline Estimate

| Task Group | Tasks | Estimated Time |
|------------|-------|----------------|
| A: Unannex Command | A1-A5 | 13 hours |
| B: GitHub Pages | B1-B3 | 8 hours |
| C: Testing (AnnexTubeTesting) | C1-C3 | 6 hours |
| D: Documentation | D1-D3 | 7 hours |
| E: Integration & QA | E1-E2 | 6 hours |
| **Total** | | **40 hours** (~1 week) |

## Definition of Done

Phase 1 is complete when:

- [ ] All tasks A1-E2 completed
- [ ] All tests pass (unit + integration)
- [ ] AnnexTubeTesting successfully deployed to GitHub Pages
- [ ] Documentation published and reviewed
- [ ] Manual QA checklist 100% complete
- [ ] Code reviewed and merged to enh-gh_pages branch
- [ ] User can follow documentation to deploy their own archive

## Risks & Mitigations

**Risk**: GitHub rate limits during testing
- **Mitigation**: Use local test repository for unit tests, minimal API calls during integration tests

**Risk**: Frontend build configuration complex for different base paths
- **Mitigation**: Test both file:// and https:// thoroughly, provide clear examples

**Risk**: Large files exceed GitHub limits
- **Mitigation**: Size validation implemented, clear warnings, --force option for override

**Risk**: git-annex quirks with unannex operation
- **Mitigation**: Comprehensive testing, document edge cases, provide troubleshooting guide

## Next Steps After Phase 1

Once Phase 1 is complete and validated with AnnexTubeTesting deployment:

1. Gather user feedback on deployment workflow
2. Begin Phase 2 design: Annex remote URL integration
3. Document lessons learned and edge cases
4. Consider additional deployment targets (GitLab Pages, Codeberg Pages)
