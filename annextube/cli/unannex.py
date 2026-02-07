"""CLI command for unannexing files to make them directly available in git."""

import logging
from pathlib import Path

import click


@click.command()
@click.option(
    '--output-dir',
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help='Path to archive repository'
)
@click.option(
    '--pattern',
    multiple=True,
    help='Glob pattern for files to unannex (can be specified multiple times)'
)
@click.option(
    '--max-size',
    type=str,
    help='Maximum file size to unannex (e.g., "10M", "100K", "1G")'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be unannexed without making changes'
)
@click.option(
    '--update-gitattributes/--no-update-gitattributes',
    default=True,
    help='Update .gitattributes to prevent re-annexing (default: enabled)'
)
@click.option(
    '--force',
    is_flag=True,
    help='Proceed even if files exceed GitHub limits'
)
@click.pass_context
def unannex(
    ctx: click.Context,
    output_dir: Path,
    pattern: tuple[str, ...],
    max_size: str | None,
    dry_run: bool,
    update_gitattributes: bool,
    force: bool
):
    """Unannex files to make them directly available in git.

    This command makes annexed files regular git files (not symlinks),
    useful for sharing archives on platforms like GitHub Pages where
    git-annex is not available.

    Examples:

        # Unannex all thumbnails
        annextube unannex --output-dir ~/archive --pattern "videos/*/thumbnail.jpg"

        # Unannex small videos with size limit
        annextube unannex --output-dir ~/archive --pattern "**/*.mkv" --max-size 10M

        # Preview changes without making them
        annextube unannex --output-dir ~/archive --pattern "**/*.jpg" --dry-run
    """
    logger = logging.getLogger(__name__)

    # Import here to avoid circular dependencies
    from annextube.services.unannex import (
        parse_size,
        find_annexed_files,
        validate_github_limits,
        unannex_files
    )

    # Parse size if provided
    max_size_bytes = None
    if max_size:
        try:
            max_size_bytes = parse_size(max_size)
            logger.info(f"Size limit: {max_size} ({max_size_bytes:,} bytes)")
        except ValueError as e:
            raise click.ClickException(f"Invalid size format: {e}")

    # Validate patterns
    if not pattern:
        raise click.ClickException("At least one --pattern is required")

    logger.info(f"Searching for annexed files in {output_dir}")
    logger.info(f"Patterns: {', '.join(pattern)}")

    # Find files
    try:
        files = find_annexed_files(
            output_dir,
            list(pattern),
            max_size_bytes
        )
    except Exception as e:
        raise click.ClickException(f"Failed to find annexed files: {e}")

    if not files:
        click.echo("No annexed files match the specified criteria.")
        return

    logger.info(f"Found {len(files)} file(s) matching criteria")

    # Validate GitHub limits
    validation = validate_github_limits(files, output_dir, force)

    # Print warnings
    for warning in validation['warnings']:
        click.echo(f"Warning: {warning}", err=True)

    # Print errors
    for error in validation['errors']:
        click.echo(f"Error: {error}", err=True)

    # Stop if validation failed and not force
    if not validation['ok'] and not force:
        raise click.ClickException("Validation failed. Use --force to proceed anyway.")

    # Show what will be unannexed
    if dry_run:
        click.echo(f"\nWould unannex {len(files)} file(s) (total: {_format_size(validation['total_size'])}):")
        for file_path, size in files[:20]:  # Show first 20
            click.echo(f"  {file_path} ({_format_size(size)})")
        if len(files) > 20:
            click.echo(f"  ... and {len(files) - 20} more")

        if update_gitattributes:
            click.echo("\nWould update .gitattributes to prevent re-annexing.")

        click.echo("\nDry run complete. No changes made.")
        return

    # Perform unannex
    click.echo(f"Unannexing {len(files)} file(s)...")

    try:
        result = unannex_files(
            output_dir,
            [f[0] for f in files],
            update_gitattributes=update_gitattributes,
            dry_run=False
        )
    except Exception as e:
        raise click.ClickException(f"Unannex operation failed: {e}")

    # Report results
    if result['unannexed']:
        click.echo(f"\nSuccessfully unannexed {len(result['unannexed'])} file(s)")
        click.echo(f"Total size: {_format_size(result['total_size'])}")

    if result['failed']:
        click.echo(f"\nFailed to unannex {len(result['failed'])} file(s):", err=True)
        for file_path, error in result['failed'][:10]:
            click.echo(f"  {file_path}: {error}", err=True)
        if len(result['failed']) > 10:
            click.echo(f"  ... and {len(result['failed']) - 10} more", err=True)

    if update_gitattributes:
        click.echo("\nUpdated .gitattributes to prevent re-annexing.")

    click.echo("\nNext steps:")
    click.echo("  1. Review changes: git status")
    click.echo("  2. Commit changes: git commit -m 'Unannex files for sharing'")


def _format_size(size_bytes: int) -> str:
    """Format size in human-readable form."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
