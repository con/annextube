"""Check command for annextube."""

import subprocess
from pathlib import Path

import click

from annextube.lib.archive_discovery import discover_annextube
from annextube.lib.config import load_config
from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)


@click.command()
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), default=Path.cwd(), help="Archive directory (default: current directory)")
@click.option("--skip-git-status", is_flag=True, help="Skip git status check")
@click.option("--skip-config", is_flag=True, help="Skip config validation")
@click.option("--skip-tsv", is_flag=True, help="Skip TSV consistency checks")
@click.option("--skip-large-files", is_flag=True, help="Skip large files in git check")
@click.option("--skip-fsck", is_flag=True, help="Skip git-annex fsck")
@click.pass_context
def check(ctx: click.Context, output_dir: Path, skip_git_status: bool, skip_config: bool, skip_tsv: bool, skip_large_files: bool, skip_fsck: bool):
    """Check the integrity and completeness of an annextube archive.

    Validates:
    - Git repository status (committed vs uncommitted changes)
    - Configuration file exists and is valid
    - TSV files match underlying directory structure
    - Component expectations (captions, comments, thumbnails, playlists)
    - No large files committed directly to git
    - git-annex file integrity (fsck)
    """
    output_dir = output_dir.resolve()
    logger.info(f"Checking annextube archive at {output_dir}")

    issues = []
    warnings = []

    # Check if this is an annextube archive
    archive_info = discover_annextube(output_dir)
    if archive_info is None or archive_info.type == "multi-channel":
        error_msg = (
            f"[FAIL] Error: {output_dir} is not a single-channel annextube archive."
            if archive_info
            else f"[FAIL] Error: {output_dir} is not an annextube archive. Run 'annextube init' first."
        )
        click.echo(error_msg, err=True)
        raise click.Abort()

    click.echo(f"Checking annextube archive: {output_dir}")
    click.echo()

    # 1. Git status check
    if not skip_git_status:
        click.echo("[ ] Checking git status...", nl=False)
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=output_dir,
                capture_output=True,
                text=True,
                check=True
            )
            if result.stdout.strip():
                issues.append("Git working tree has uncommitted changes")
                click.echo("\r[FAIL] Git status: DIRTY")
                click.echo(f"  Uncommitted changes:\n{result.stdout}")
            else:
                click.echo("\r[ok] Git status: CLEAN")
        except Exception as e:
            issues.append(f"Failed to check git status: {e}")
            click.echo(f"\r[FAIL] Git status check failed: {e}")

    # 2. Config validation
    if not skip_config:
        click.echo("[ ] Checking configuration...", nl=False)
        config_path = output_dir / ".annextube" / "config.toml"
        if not config_path.exists():
            issues.append(f"Configuration file missing: {config_path}")
            click.echo(f"\r[FAIL] Configuration: MISSING ({config_path})")
        else:
            try:
                config = load_config(repo_path=output_dir)
                if not config.sources:
                    warnings.append("No sources configured")
                    click.echo("\r[!] Configuration: No sources configured")
                else:
                    click.echo(f"\r[ok] Configuration: {len(config.sources)} source(s)")
            except Exception as e:
                issues.append(f"Failed to load config: {e}")
                click.echo(f"\r[FAIL] Configuration: INVALID ({e})")

    # 3. TSV consistency checks
    if not skip_tsv:
        click.echo("[ ] Checking TSV consistency...", nl=False)
        try:
            # Check videos.tsv
            videos_tsv = output_dir / "videos" / "videos.tsv"
            if videos_tsv.exists():
                lines = videos_tsv.read_text().strip().split('\n')
                tsv_count = len(lines) - 1  # Exclude header
                videos_dir = output_dir / "videos"
                actual_dirs = [d for d in videos_dir.iterdir() if d.is_dir()] if videos_dir.exists() else []
                actual_count = len(actual_dirs)
                if tsv_count != actual_count:
                    issues.append(f"videos.tsv mismatch: {tsv_count} rows vs {actual_count} directories")
                    click.echo(f"\r[FAIL] TSV consistency: videos.tsv has {tsv_count} rows but {actual_count} video directories exist")
                else:
                    click.echo(f"\r[ok] TSV consistency: {tsv_count} videos")
            else:
                warnings.append("videos.tsv not found")
                click.echo("\r[!] TSV: videos.tsv not found")

            # Check playlists.tsv if config expects playlists
            playlists_tsv = output_dir / "playlists" / "playlists.tsv"
            if playlists_tsv.exists():
                lines = playlists_tsv.read_text().strip().split('\n')
                tsv_count = len(lines) - 1
                playlists_dir = output_dir / "playlists"
                # Only count directories that have playlist.json (empty playlists might not have it)
                actual_dirs = [d for d in playlists_dir.iterdir() if d.is_dir() and (d / "playlist.json").exists()] if playlists_dir.exists() else []
                actual_count = len(actual_dirs)
                if tsv_count != actual_count:
                    issues.append(f"playlists.tsv mismatch: {tsv_count} rows vs {actual_count} directories")
                    click.echo(f"  [FAIL] playlists.tsv has {tsv_count} rows but {actual_count} playlist directories exist")
                else:
                    click.echo(f"  [ok] playlists.tsv: {tsv_count} playlists")

        except Exception as e:
            issues.append(f"TSV check failed: {e}")
            click.echo(f"\r[FAIL] TSV check failed: {e}")

    # 4. Component expectations
    click.echo("[ ] Checking component expectations...", nl=False)
    try:
        if not skip_config and config_path.exists():
            config = load_config(repo_path=output_dir)
            components = config.components

            # Check captions
            if components.captions:
                vtt_count = len(list(output_dir.rglob("*.vtt")))
                if vtt_count == 0:
                    warnings.append("Captions enabled but no .vtt files found")
                    click.echo("\r[!] Components: Captions enabled but no .vtt files found")
                else:
                    click.echo(f"\r[ok] Components: {vtt_count} caption files")

            # Check comments
            if components.comments_depth is None or (components.comments_depth and components.comments_depth > 0):
                comment_files = list(output_dir.rglob("comments.json"))
                if len(comment_files) == 0:
                    warnings.append("Comments enabled but no comments.json files found")
                    click.echo("  [!] Comments enabled but no comments.json found")
                else:
                    click.echo(f"  [ok] {len(comment_files)} comment files")

            # Check thumbnails
            if components.thumbnails:
                thumb_count = len(list(output_dir.rglob("thumbnail.jpg")))
                if thumb_count == 0:
                    warnings.append("Thumbnails enabled but no thumbnail.jpg files found")
                    click.echo("  [!] Thumbnails enabled but no thumbnail.jpg found")
                else:
                    click.echo(f"  [ok] {thumb_count} thumbnails")

            # Check playlists
            if any(s.include_playlists != "none" for s in config.sources if hasattr(s, 'include_playlists')):
                playlists_dir = output_dir / "playlists"
                if not playlists_dir.exists() or not list(playlists_dir.iterdir()):
                    warnings.append("Playlists enabled but no playlists directory found")
                    click.echo("  [!] Playlists enabled but no playlists found")
                else:
                    playlist_count = len([d for d in playlists_dir.iterdir() if d.is_dir()])
                    click.echo(f"  [ok] {playlist_count} playlists")
        else:
            click.echo("\r[!] Components: Config not available, skipping")
    except Exception as e:
        warnings.append(f"Component check failed: {e}")
        click.echo(f"\r[!] Component check failed: {e}")

    # 5. Large files in git check
    if not skip_large_files:
        click.echo("[ ] Checking for large files in git...", nl=False)
        try:
            # Get list of files tracked by git (not annex) - exclude symlinks (120000 mode = annex)
            result = subprocess.run(
                ["git", "ls-files", "-s", "--", "*.mp4", "*.webm", "*.mkv", "*.jpg", "*.png"],
                cwd=output_dir,
                capture_output=True,
                text=True,
                check=True
            )
            # Filter out symlinks (mode 120000 = git-annex symlinks)
            large_files = []
            for line in result.stdout.strip().split('\n'):
                if line and not line.startswith('120000'):
                    # Extract filename from "mode hash stage filename"
                    parts = line.split(maxsplit=3)
                    if len(parts) >= 4:
                        large_files.append(parts[3])
            if large_files:
                issues.append(f"Found {len(large_files)} large files committed directly to git (should be in annex)")
                click.echo(f"\r[FAIL] Large files: {len(large_files)} files in git (should be in annex)")
                for f in large_files[:5]:  # Show first 5
                    click.echo(f"    {f}")
                if len(large_files) > 5:
                    click.echo(f"    ... and {len(large_files) - 5} more")
            else:
                click.echo("\r[ok] Large files: All large files in annex")
        except Exception as e:
            warnings.append(f"Large files check failed: {e}")
            click.echo(f"\r[!] Large files check failed: {e}")

    # 6. git-annex fsck
    if not skip_fsck:
        click.echo("[ ] Running git-annex fsck...", nl=False)
        try:
            result = subprocess.run(
                ["git", "annex", "fsck", "--fast", "--quiet"],
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                click.echo("\r[ok] git-annex fsck: PASSED")
            else:
                issues.append("git-annex fsck found issues")
                click.echo(f"\r[FAIL] git-annex fsck: FAILED\n{result.stderr}")
        except subprocess.TimeoutExpired:
            warnings.append("git-annex fsck timed out (>60s)")
            click.echo("\r[!] git-annex fsck: TIMEOUT (skipped)")
        except Exception as e:
            warnings.append(f"git-annex fsck failed: {e}")
            click.echo(f"\r[!] git-annex fsck failed: {e}")

    # Summary
    click.echo()
    click.echo("=" * 60)
    if issues:
        click.echo(f"[FAIL] Check FAILED with {len(issues)} issue(s):")
        for issue in issues:
            click.echo(f"  - {issue}")
    else:
        click.echo("[ok] All checks PASSED")

    if warnings:
        click.echo(f"\n[!] {len(warnings)} warning(s):")
        for warning in warnings:
            click.echo(f"  - {warning}")

    click.echo()

    if issues:
        raise click.Abort()
