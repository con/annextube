"""CLI command for preparing GitHub Pages deployment."""

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

import click

logger = logging.getLogger(__name__)


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
@click.pass_context
def prepare_ghpages(
    ctx: click.Context,
    output_dir: Path,
    repo_name: str | None,
    gh_branch: str,
    build_frontend: bool,
    copy_data: bool
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
    """
    repo_path = output_dir.resolve()

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

    # 2. Build frontend with GitHub Pages config
    if build_frontend:
        click.echo(f"\nBuilding frontend for GitHub Pages (/{repo_name}/)...")
        try:
            build_frontend_for_ghpages(repo_path, repo_name)
            click.echo("✓ Frontend build completed")
        except Exception as e:
            raise click.ClickException(f"Frontend build failed: {e}") from e

    # 3. Create/update gh-pages branch
    click.echo(f"\nPreparing {gh_branch} branch...")
    try:
        create_ghpages_branch(repo_path, gh_branch)
        click.echo(f"✓ {gh_branch} branch ready")
    except Exception as e:
        raise click.ClickException(f"Failed to create {gh_branch} branch: {e}") from e

    # 4. Copy frontend build to gh-pages branch
    click.echo(f"\nCopying frontend to {gh_branch} branch...")
    try:
        copy_frontend_to_ghpages(repo_path, gh_branch, build_frontend)
        click.echo("✓ Frontend copied")
    except Exception as e:
        raise click.ClickException(f"Failed to copy frontend: {e}") from e

    # 5. Copy data files if requested
    if copy_data:
        click.echo(f"\nCopying data files to {gh_branch} branch...")
        try:
            copy_data_to_ghpages(repo_path, gh_branch)
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
            text=True,
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


def build_frontend_for_ghpages(repo_path: Path, repo_name: str) -> None:
    """Build frontend with GitHub Pages base path.

    Args:
        repo_path: Path to repository
        repo_name: GitHub repository name
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
    env['VITE_BASE_PATH'] = f'/{repo_name}/'

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
    was_built: bool
) -> None:
    """Copy built frontend to gh-pages branch.

    Args:
        repo_path: Path to repository
        branch_name: Target branch name
        was_built: Whether frontend was just built
    """
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

    # Copy all files from dist/ to repository root
    for item in dist_dir.iterdir():
        dest = repo_path / item.name

        # Remove existing
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()

        # Copy new
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

        logger.debug(f"Copied: {item.name}")


def copy_data_to_ghpages(repo_path: Path, branch_name: str) -> None:
    """Copy data files from master branch to gh-pages.

    Copies both unannexed files and git-annex symlinks. The symlinks can be
    resolved later by running 'git annex get' or removed if content is unavailable.

    Args:
        repo_path: Path to repository
        branch_name: Target branch name
    """
    # List of data directories/files to copy
    data_items = ['videos/', 'playlists/', 'authors.tsv']

    for item in data_items:
        try:
            # Check out item from master/main branch
            subprocess.run(
                ['git', 'checkout', 'origin/master', '--', item],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            logger.debug(f"Copied from master: {item}")
        except subprocess.CalledProcessError:
            try:
                # Try main branch
                subprocess.run(
                    ['git', 'checkout', 'origin/main', '--', item],
                    cwd=repo_path,
                    check=True,
                    capture_output=True
                )
                logger.debug(f"Copied from main: {item}")
            except subprocess.CalledProcessError:
                logger.warning(f"Could not copy {item} (not found in master/main)")
                continue

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
