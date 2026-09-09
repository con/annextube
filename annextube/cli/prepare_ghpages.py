"""CLI command for preparing GitHub Pages deployment."""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import click

logger = logging.getLogger(__name__)


def _replace_dest(dest: Path) -> None:
    """Remove whatever currently exists at ``dest`` (file, dir, or symlink)."""
    if dest.is_symlink():
        dest.unlink()
    elif dest.is_dir():
        shutil.rmtree(dest)
    elif dest.exists():
        dest.unlink()


def _copy_tree_no_symlinks(src: Path, dest: Path) -> None:
    """Recursively copy ``src`` to ``dest``, refusing to follow or
    materialize any symlink anywhere in the tree.

    Used specifically when copying from an untrusted ``--source-dir`` (e.g.
    a CI build artifact built from a fork PR's own code, uploaded via
    ``actions/upload-artifact`` which preserves symlinks as-is).
    ``shutil.copytree()``/``copy2()`` dereference symlinks by default, so a
    maliciously crafted symlink in such an artifact (e.g. pointing at an
    absolute host path) would otherwise have its target's content silently
    copied and committed to the public gh-pages branch. This helper is not
    used for the trusted (non-``--source-dir``) code paths, which
    legitimately need to preserve git-annex symlinks.
    """
    if src.is_symlink():
        raise ValueError(
            f"Refusing to copy symlink from untrusted --source-dir: {src}"
        )
    if src.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        for child in src.iterdir():
            _copy_tree_no_symlinks(child, dest / child.name)
    else:
        shutil.copy2(src, dest)


@click.command()
@click.option(
    '--output-dir',
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help='Path to archive repository'
)
@click.option(
    '--repo-name',
    help='GitHub repository name (e.g., "annextubetesting"). Auto-detected if not specified.'
)
@click.option(
    '--gh-branch',
    default='gh-pages',
    help='Target branch name for GitHub Pages (default: gh-pages)'
)
@click.option(
    '--build-frontend/--no-build-frontend',
    default=True,
    help='Build frontend before deployment (default: enabled)'
)
@click.option(
    '--copy-data/--no-copy-data',
    default=True,
    help='Copy data files (videos/, playlists/, etc.) to gh-pages branch (default: enabled)'
)
@click.option(
    '--subpath',
    default=None,
    help=(
        'Publish under this subdirectory of the target branch '
        '(e.g. "pr-42") instead of the branch root. Only this subpath is '
        'written to -- the branch root and any other subpath (e.g. other '
        'PRs\' previews) are left untouched.'
    )
)
@click.option(
    '--source-dir',
    default=None,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help=(
        'Copy the frontend build and data files from this directory '
        'instead of building fresh and reading data from --output-dir\'s '
        'own origin/master (or origin/main). The directory must already '
        'contain a built "web/" subdirectory (e.g. the output of '
        '`annextube generate-web`) alongside the data files. Implies '
        'skipping the frontend build step.'
    )
)
@click.pass_context
def prepare_ghpages(
    ctx: click.Context,
    output_dir: Path,
    repo_name: str | None,
    gh_branch: str,
    build_frontend: bool,
    copy_data: bool,
    subpath: str | None,
    source_dir: Path | None,
):
    """Prepare archive for GitHub Pages deployment.

    This command:
    1. Builds the frontend with GitHub Pages configuration
    2. Creates/updates gh-pages branch
    3. Copies frontend and data files to gh-pages branch
    4. Sets up .nojekyll and 404.html for proper routing
    5. Provides deployment instructions

    Examples:

        # Basic usage (auto-detects repo name from git remote)
        annextube prepare-ghpages --output-dir ~/my-archive

        # Specify repository name explicitly
        annextube prepare-ghpages --output-dir ~/my-archive --repo-name annextubetesting

        # Skip data copy (metadata only, useful for large archives)
        annextube prepare-ghpages --output-dir ~/my-archive --no-copy-data

        # Publish a pre-built preview under a subpath, from an already-built
        # source directory (e.g. a downloaded CI build artifact), leaving
        # everything else on the branch untouched
        annextube prepare-ghpages --output-dir ~/annextube-checkout \\
            --source-dir /tmp/pr-42-build --subpath pr-42
    """
    repo_path = output_dir.resolve()
    source_path = source_dir.resolve() if source_dir else None

    if subpath is not None:
        # Defense in depth: the branch-root/sibling-subpath isolation this
        # option promises only holds if `subpath` really is a single,
        # relative path component. Every caller in this codebase only ever
        # passes `pr-<number>` (a GitHub-assigned integer), but this is a
        # public CLI option -- reject anything else outright rather than
        # relying on callers to keep constructing it safely.
        if (
            not subpath
            or '/' in subpath
            or '\\' in subpath
            or subpath in ('.', '..')
            or Path(subpath).is_absolute()
        ):
            raise click.ClickException(
                f"--subpath must be a single relative path component "
                f"(e.g. 'pr-42'), got: {subpath!r}"
            )

    # 1. Detect or validate repo name
    if not repo_name:
        click.echo("Detecting repository name from git remote...")
        repo_name = get_github_repo_name(repo_path)
        if not repo_name:
            raise click.ClickException(
                "Could not detect repository name from git remote. "
                "Please specify --repo-name (e.g., 'annextubetesting')"
            )
        click.echo(f"Detected repository: {repo_name}")

    # 2. Build frontend with GitHub Pages config -- skipped when --source-dir
    # is given, since it must already contain a pre-built web/ directory
    do_build_frontend = build_frontend and source_path is None
    if do_build_frontend:
        base_path = f'/{repo_name}/{subpath}/' if subpath else f'/{repo_name}/'
        click.echo(f"\nBuilding frontend for GitHub Pages ({base_path})...")
        try:
            build_frontend_for_ghpages(repo_path, repo_name, subpath=subpath)
            click.echo("✓ Frontend build completed")
        except Exception as e:
            raise click.ClickException(f"Frontend build failed: {e}") from e
    elif source_path is not None:
        click.echo(
            "\nSkipping frontend build: using pre-built content from "
            f"--source-dir ({source_path})"
        )

    # 3. Create/update gh-pages branch
    click.echo(f"\nPreparing {gh_branch} branch...")
    try:
        create_ghpages_branch(repo_path, gh_branch)
        click.echo(f"✓ {gh_branch} branch ready")
    except Exception as e:
        raise click.ClickException(f"Failed to create {gh_branch} branch: {e}") from e

    # 4. Copy frontend build to gh-pages branch (into --subpath if given)
    dest = f"{gh_branch}/{subpath}" if subpath else gh_branch
    click.echo(f"\nCopying frontend to {dest}...")
    try:
        copy_frontend_to_ghpages(
            repo_path, gh_branch, do_build_frontend,
            subpath=subpath, source_dir=source_path,
        )
        click.echo("✓ Frontend copied")
    except Exception as e:
        raise click.ClickException(f"Failed to copy frontend: {e}") from e

    # 5. Copy data files if requested (into --subpath if given)
    if copy_data:
        click.echo(f"\nCopying data files to {dest}...")
        try:
            copy_data_to_ghpages(
                repo_path, gh_branch, subpath=subpath, source_dir=source_path,
            )
            click.echo("✓ Data files copied")
        except Exception as e:
            raise click.ClickException(f"Failed to copy data files: {e}") from e

    # 6. Setup GitHub Pages config files
    click.echo("\nSetting up GitHub Pages configuration...")
    try:
        setup_ghpages_config(repo_path, gh_branch)
        click.echo("✓ .nojekyll and 404.html created")
    except Exception as e:
        raise click.ClickException(f"Failed to setup config files: {e}") from e

    # 7. Commit changes
    click.echo(f"\nCommitting changes to {gh_branch}...")
    try:
        commit_ghpages(repo_path, gh_branch)
        click.echo("✓ Changes committed")
    except Exception as e:
        raise click.ClickException(f"Failed to commit changes: {e}") from e

    # 8. Return to original branch
    try:
        subprocess.run(
            ['git', 'checkout', '-'],
            cwd=repo_path,
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError:
        # Try master/main as fallback
        try:
            subprocess.run(
                ['git', 'checkout', 'master'],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            subprocess.run(
                ['git', 'checkout', 'main'],
                cwd=repo_path,
                check=True,
                capture_output=True
            )

    # 9. Print deployment instructions
    print_deployment_instructions(repo_name, gh_branch)


def get_github_repo_name(repo_path: Path) -> str | None:
    """Extract GitHub repository name from git remote.

    Args:
        repo_path: Path to git repository

    Returns:
        Repository name (e.g., 'annextubetesting') or None if not found
    """
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=repo_path,
            capture_output=True,
            encoding="utf-8",
            check=True
        )
        url = result.stdout.strip()

        # Parse: https://github.com/con/annextubetesting.git
        # or: git@github.com:con/annextubetesting.git
        match = re.search(r'github\.com[:/][\w-]+/([\w-]+?)(?:\.git)?$', url)
        if match:
            return match.group(1)

    except subprocess.CalledProcessError:
        pass

    return None


def build_frontend_for_ghpages(
    repo_path: Path, repo_name: str, subpath: str | None = None
) -> None:
    """Build frontend with GitHub Pages base path.

    Args:
        repo_path: Path to repository
        repo_name: GitHub repository name
        subpath: If given, build for `/{repo_name}/{subpath}/` instead of
            `/{repo_name}/`, so the built assets resolve correctly when
            published under a subdirectory of the branch (e.g. a per-PR
            preview).
    """
    # Find frontend directory
    # Try multiple locations:
    # 1. Environment variable ANNEXTUBE_FRONTEND_DIR (for GitHub Actions)
    # 2. In the annextube project (for development)
    # 3. Relative to target repository (for deployed installations)

    search_paths = []

    # Check environment variable first (set by GitHub Action)
    env_frontend = os.environ.get('ANNEXTUBE_FRONTEND_DIR')
    if env_frontend:
        search_paths.append(Path(env_frontend))

    # Check if __file__ is available (running from source)
    import annextube
    if hasattr(annextube, '__file__') and annextube.__file__:
        # Running from source - frontend is in project root
        annextube_root = Path(annextube.__file__).parent.parent
        search_paths.append(annextube_root / 'frontend')

    # Also try relative to repo_path
    search_paths.extend([
        repo_path.parent.parent / 'frontend',
        repo_path.parent / 'frontend',
        repo_path / 'frontend'
    ])

    frontend_dir = None
    for path in search_paths:
        if path.exists() and (path / 'package.json').exists():
            frontend_dir = path
            break

    if not frontend_dir:
        search_str = '\n'.join(f"  - {p}" for p in search_paths)
        raise FileNotFoundError(
            f"Frontend directory not found. Searched:\n{search_str}"
        )

    logger.info(f"Building frontend from: {frontend_dir}")

    # Set base path via environment variable
    env = os.environ.copy()
    env['VITE_BASE_PATH'] = f'/{repo_name}/{subpath}/' if subpath else f'/{repo_name}/'

    # Install dependencies if needed
    if not (frontend_dir / 'node_modules').exists():
        logger.info("Installing frontend dependencies...")
        subprocess.run(
            ['npm', 'install'],
            cwd=frontend_dir,
            env=env,
            check=True
        )

    # Build with gh-pages mode
    subprocess.run(
        ['npm', 'run', 'build', '--', '--mode', 'gh-pages'],
        cwd=frontend_dir,
        env=env,
        check=True
    )


def create_ghpages_branch(repo_path: Path, branch_name: str) -> None:
    """Create or switch to gh-pages branch.

    Args:
        repo_path: Path to repository
        branch_name: Branch name (e.g., 'gh-pages')
    """
    # Check if local branch exists
    result = subprocess.run(
        ['git', 'rev-parse', '--verify', f'refs/heads/{branch_name}'],
        cwd=repo_path,
        capture_output=True
    )

    if result.returncode != 0:
        # Local branch doesn't exist - check if remote branch exists
        remote_result = subprocess.run(
            ['git', 'rev-parse', '--verify', f'refs/remotes/origin/{branch_name}'],
            cwd=repo_path,
            capture_output=True
        )

        if remote_result.returncode == 0:
            # Remote branch exists - create local tracking branch
            logger.info(f"Creating local branch {branch_name} from origin/{branch_name}")
            subprocess.run(
                ['git', 'checkout', '-b', branch_name, f'origin/{branch_name}'],
                cwd=repo_path,
                check=True
            )
        else:
            # Neither local nor remote exists - create orphan
            logger.info(f"Creating new orphan branch: {branch_name}")
            subprocess.run(
                ['git', 'checkout', '--orphan', branch_name],
                cwd=repo_path,
                check=True
            )
            # Remove all files from index
            subprocess.run(
                ['git', 'rm', '-rf', '.'],
                cwd=repo_path,
                capture_output=True
            )
    else:
        # Local branch exists, just checkout
        logger.info(f"Switching to existing branch: {branch_name}")
        subprocess.run(
            ['git', 'checkout', branch_name],
            cwd=repo_path,
            check=True
        )


def copy_frontend_to_ghpages(
    repo_path: Path,
    branch_name: str,
    was_built: bool,
    subpath: str | None = None,
    source_dir: Path | None = None,
) -> None:
    """Copy built frontend to gh-pages branch.

    Args:
        repo_path: Path to repository
        branch_name: Target branch name
        was_built: Whether frontend was just built
        subpath: If given, copy into `<repo_path>/<subpath>/` instead of
            `<repo_path>/`, leaving everything else on the branch untouched.
        source_dir: If given, copy from `<source_dir>/web` instead of
            searching the usual build-output locations (used when the
            frontend was already built elsewhere, e.g. by an untrusted CI
            build job whose artifact this is).
    """
    if source_dir is not None:
        dist_dir = source_dir / 'web'
        if dist_dir.is_symlink():
            raise ValueError(
                f"Refusing to follow symlink from untrusted --source-dir: {dist_dir}"
            )
        if not dist_dir.exists():
            raise FileNotFoundError(
                f"--source-dir given but no 'web/' directory found in it: "
                f"{source_dir}"
            )
    else:
        # Find frontend dist directory using same logic as build
        import annextube

        search_paths = []

        # Check environment variable first (same as build step)
        env_frontend = os.environ.get('ANNEXTUBE_FRONTEND_DIR')
        if env_frontend:
            search_paths.append(Path(env_frontend))

        if hasattr(annextube, '__file__') and annextube.__file__:
            annextube_root = Path(annextube.__file__).parent.parent
            search_paths.append(annextube_root / 'frontend')

        search_paths.extend([
            repo_path.parent.parent / 'frontend',
            repo_path.parent / 'frontend',
            repo_path / 'frontend'
        ])

        dist_dir = None
        for path in search_paths:
            # Check dist/ (gh-pages mode), web/ subdir, and ../web (vite outDir: '../web')
            for candidate in (path / 'dist', path / 'web', path.parent / 'web'):
                if candidate.exists():
                    dist_dir = candidate
                    break
            if dist_dir:
                break

        if not dist_dir:
            raise FileNotFoundError(
                "Frontend dist directory not found.\n"
                "Run with --build-frontend to build first."
            )

    assert dist_dir is not None  # guaranteed by the branches above (else they raise)

    dest_root = (repo_path / subpath) if subpath else repo_path
    dest_root.mkdir(parents=True, exist_ok=True)

    # Copy all files from dist/ to the destination root -- never touches
    # anything outside dest_root, so sibling subpaths are left alone
    for item in dist_dir.iterdir():
        dest = dest_root / item.name
        _replace_dest(dest)

        if source_dir is not None:
            # Untrusted content (e.g. a fork PR's build artifact) -- never
            # follow symlinks.
            _copy_tree_no_symlinks(item, dest)
        elif item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

        logger.debug(f"Copied: {item.name}")


def copy_data_to_ghpages(
    repo_path: Path,
    branch_name: str,
    subpath: str | None = None,
    source_dir: Path | None = None,
) -> None:
    """Copy data files (videos/, playlists/, authors.tsv) to gh-pages.

    Without --source-dir, copies both unannexed files and git-annex symlinks
    from `--output-dir`'s own `origin/master`/`origin/main`. The symlinks
    can be resolved later by running 'git annex get' or removed if content
    is unavailable.

    With --source-dir, copies real files directly from that directory
    instead (used when the data comes from a separate export, e.g. the
    `annextubetesting` branch's content, not this repo's own default
    branch).

    Args:
        repo_path: Path to repository
        branch_name: Target branch name
        subpath: If given, copy into `<repo_path>/<subpath>/` instead of
            `<repo_path>/`, leaving everything else on the branch untouched.
        source_dir: If given, copy directly from this directory instead of
            checking out from `origin/master`/`origin/main`.
    """
    # List of data directories/files to copy
    data_items = ['videos/', 'playlists/', 'authors.tsv']
    dest_root = (repo_path / subpath) if subpath else repo_path
    dest_root.mkdir(parents=True, exist_ok=True)

    if source_dir is not None:
        for item in data_items:
            item_name = item.rstrip('/')
            src = source_dir / item_name
            if src.is_symlink():
                raise ValueError(
                    f"Refusing to copy symlink from untrusted --source-dir: {src}"
                )
            if not src.exists():
                logger.warning(f"Could not copy {item} (not found in {source_dir})")
                continue
            dest = dest_root / item_name
            _replace_dest(dest)
            _copy_tree_no_symlinks(src, dest)
            logger.debug(f"Copied from --source-dir: {item}")
        logger.info(f"Data files copied to {branch_name} from {source_dir}")
        return

    # No --source-dir: read from --output-dir's own origin/master (or
    # origin/main). Extracted via `git archive` into a scratch directory
    # rather than `git checkout -- <item>` directly into repo_path -- the
    # latter always lands at the repo root, so satisfying `subpath` would
    # otherwise require checking it out onto whatever real content already
    # lives at the branch root and then moving it aside, clobbering that
    # root content in the process. Going through a scratch directory keeps
    # repo_path (and any existing content on the target branch) untouched
    # until the copy into dest_root itself.
    with tempfile.TemporaryDirectory() as scratch:
        scratch_path = Path(scratch)
        for item in data_items:
            item_name = item.rstrip('/')
            copied_from = None
            for candidate_branch in ('origin/master', 'origin/main'):
                archive = subprocess.run(
                    ['git', 'archive', candidate_branch, '--', item],
                    cwd=repo_path,
                    capture_output=True,
                )
                if archive.returncode == 0 and archive.stdout:
                    subprocess.run(
                        ['tar', '-x'],
                        cwd=scratch_path,
                        input=archive.stdout,
                        check=True,
                    )
                    copied_from = candidate_branch
                    break

            if not copied_from:
                logger.warning(f"Could not copy {item} (not found in master/main)")
                continue

            extracted = scratch_path / item_name
            if not extracted.exists():
                logger.warning(f"Could not copy {item} (not found in master/main)")
                continue

            dest = dest_root / item_name
            _replace_dest(dest)
            if extracted.is_dir():
                shutil.copytree(extracted, dest, symlinks=True)
            else:
                shutil.copy2(extracted, dest)

            logger.debug(f"Copied from {copied_from}: {item}")

    logger.info(f"Data files copied to {branch_name} (including any git-annex symlinks)")
    logger.info("Run 'git annex get' to fetch annexed content, or remove symlinks if content is unavailable")


def setup_ghpages_config(repo_path: Path, branch_name: str) -> None:
    """Create GitHub Pages configuration files.

    Creates:
    - .nojekyll: Disable Jekyll processing
    - 404.html: Handle client-side routing

    Args:
        repo_path: Path to repository
        branch_name: Target branch name
    """
    # Create .nojekyll
    nojekyll = repo_path / '.nojekyll'
    nojekyll.touch()
    logger.debug("Created .nojekyll")

    # Create .gitignore to exclude build artifacts
    gitignore = repo_path / '.gitignore'
    gitignore.write_text("""# Exclude annextube source checkout (used only for building)
_annextube_source/
""")
    logger.debug("Created .gitignore")

    # Create 404.html for client-side routing
    html_404 = repo_path / '404.html'
    html_404.write_text("""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Redirecting...</title>
  <script>
    // GitHub Pages 404 handler for client-side routing
    // Redirects to index.html with hash-based path
    const segments = window.location.pathname.split('/').slice(1);
    const repoName = segments[0];
    const path = segments.slice(1).join('/');

    if (path) {
      const redirect = window.location.origin + '/' + repoName + '/#/' + path + window.location.search;
      window.location.replace(redirect);
    } else {
      const redirect = window.location.origin + '/' + repoName + '/';
      window.location.replace(redirect);
    }
  </script>
</head>
<body>
  <p>Redirecting...</p>
</body>
</html>
""")
    logger.debug("Created 404.html")


def commit_ghpages(repo_path: Path, branch_name: str) -> None:
    """Commit changes to gh-pages branch.

    Args:
        repo_path: Path to repository
        branch_name: Branch name
    """
    # Add all files
    subprocess.run(
        ['git', 'add', '-A'],
        cwd=repo_path,
        check=True
    )

    # Check if there are changes to commit
    result = subprocess.run(
        ['git', 'diff', '--cached', '--quiet'],
        cwd=repo_path
    )

    if result.returncode == 0:
        logger.info("No changes to commit")
        return

    # Commit
    subprocess.run(
        ['git', 'commit', '-m', 'Deploy frontend to GitHub Pages'],
        cwd=repo_path,
        check=True
    )


def print_deployment_instructions(repo_name: str, branch_name: str):
    """Print next steps for user.

    Args:
        repo_name: GitHub repository name
        branch_name: Branch name
    """
    click.echo("\n" + "=" * 70)
    click.echo("✓ GitHub Pages branch prepared successfully!")
    click.echo("=" * 70)
    click.echo(f"\nBranch: {branch_name}")
    click.echo("\nNext steps:")
    click.echo(f"  1. Push the {branch_name} branch to GitHub:")
    click.echo(f"       git push origin {branch_name}")
    click.echo("\n  2. Enable GitHub Pages in repository settings:")
    click.echo(f"       https://github.com/con/{repo_name}/settings/pages")
    click.echo("       - Source: Deploy from a branch")
    click.echo(f"       - Branch: {branch_name}")
    click.echo("       - Folder: / (root)")
    click.echo("\n  3. Your site will be available at (after ~1 minute):")
    click.echo(f"       https://con.github.io/{repo_name}/")
    click.echo("\n" + "=" * 70 + "\n")
