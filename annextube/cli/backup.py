"""Backup command for annextube."""

from datetime import datetime
from pathlib import Path
from typing import Any

import click

from annextube.lib.config import load_config
from annextube.lib.date_utils import parse_date
from annextube.lib.logging_config import get_logger
from annextube.services.archiver import Archiver
from annextube.services.export import ExportService
from annextube.services.git_annex import GitAnnexService

logger = get_logger(__name__)


@click.command()
@click.argument("url", required=False)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Archive directory (default: current directory)",
)
@click.option("--limit", type=int, help="Limit number of videos (most recent)")
@click.option(
    "--update",
    type=click.Choice([
        "videos-incremental",  # New videos only
        "all-incremental",      # New videos + social for recent (default)
        "all-force",            # Re-process everything
        "social",               # Comments + captions only (shortcut)
        "playlists",            # Playlists only
        "comments",             # Comments only
        "captions",             # Captions only
        "tsv_metadata"          # Regenerate TSVs only (no downloads)
    ], case_sensitive=False),
    default="all-incremental",
    help="Update mode: all-incremental (new videos + social for recent, default), videos-incremental (new videos only), all-force (re-process all), social (comments+captions), playlists/comments/captions (specific components), tsv_metadata (regenerate TSV files from existing JSON)",
)
@click.option(
    "--from-date",
    type=str,
    help="Start date for update window (ISO format or duration like '1 week', '2 days')",
)
@click.option(
    "--to-date",
    type=str,
    help="End date for update window (ISO format or duration like '1 week', '2 days')",
)
@click.option(
    "--skip-existing",
    is_flag=True,
    hidden=True,  # Deprecated, replaced by --update=all-incremental
    help="(Deprecated: use --update=all-incremental instead)",
)
@click.pass_context
def backup(ctx: click.Context, url: str, output_dir: Path, limit: int, update: str, from_date: str, to_date: str, skip_existing: bool):
    """Backup YouTube channel or playlist.

    If URL is provided, backs up that specific channel/playlist (ad-hoc mode).
    Otherwise, backs up all enabled sources from configuration file.

    Examples:

        # Backup configured sources
        annextube backup

        # Backup specific channel (ad-hoc)
        annextube backup https://www.youtube.com/@RickAstleyYT

        # Backup with limit
        annextube backup --limit 10
    """
    # Log versions for debugging
    try:
        from annextube._version import version as annextube_version
    except ImportError:
        annextube_version = "unknown"

    try:
        import yt_dlp
        ytdlp_version = yt_dlp.version.__version__
    except Exception:
        ytdlp_version = "unknown"

    logger.info(f"Starting backup operation")
    logger.debug(f"annextube version: {annextube_version}")
    logger.debug(f"yt-dlp version: {ytdlp_version}")

    # Check if this is a git-annex repo
    git_annex = GitAnnexService(output_dir)
    if not git_annex.is_annex_repo():
        click.echo(
            f"Error: {output_dir} is not an annextube archive. Run 'annextube init' first.",
            err=True,
        )
        raise click.Abort()

    try:
        # Load configuration
        config_path = ctx.obj.get("config_path")
        config = load_config(config_path, repo_path=output_dir)

        # Override limit if specified
        if limit:
            config.filters.limit = limit

        # Handle deprecated --skip-existing flag
        if skip_existing:
            update = "all-incremental"
            click.echo("Note: --skip-existing is deprecated, use --update=all-incremental instead")

        # Default update mode if not specified
        if not update:
            update = "all-incremental"

        click.echo(f"Update mode: {update}")

        # Handle tsv_metadata mode - regenerate TSVs only
        if update == "tsv_metadata":
            click.echo("Regenerating TSV metadata files from existing JSON...")
            exporter = ExportService(output_dir)
            videos_tsv, playlists_tsv, authors_tsv = exporter.generate_all()
            click.echo(f"[ok] Generated: {videos_tsv}")
            click.echo(f"[ok] Generated: {playlists_tsv}")
            click.echo(f"[ok] Generated: {authors_tsv}")
            click.echo()
            click.echo("[ok] TSV metadata regeneration complete!")
            return

        # Parse date range (for all-incremental mode)
        date_from: datetime | None = None
        date_to: datetime | None = None

        if from_date:
            try:
                date_from = parse_date(from_date)
                click.echo(f"From date: {date_from.strftime('%Y-%m-%d')}")
            except ValueError as e:
                click.echo(f"Error: Invalid --from-date: {e}", err=True)
                raise click.Abort() from None

        if to_date:
            try:
                date_to = parse_date(to_date)
                click.echo(f"To date: {date_to.strftime('%Y-%m-%d')}")
            except ValueError as e:
                click.echo(f"Error: Invalid --to-date: {e}", err=True)
                raise click.Abort() from None

        # For all-incremental mode, default to 1 week window for social updates if no dates specified
        if update == "all-incremental" and not from_date:
            from annextube.lib.date_utils import parse_duration
            date_from = datetime.now() - parse_duration("1 week")
            click.echo(f"Default social window: {date_from.strftime('%Y-%m-%d')} to now")

        # Initialize archiver with update mode and date filters
        archiver = Archiver(output_dir, config, update_mode=update, date_from=date_from, date_to=date_to)

        # Determine what to backup
        if url:
            # Ad-hoc mode: backup single URL
            click.echo(f"Backing up: {url}")
            if config.filters.limit:
                click.echo(f"Limit: {config.filters.limit} most recent videos")

            # Detect if URL is a playlist or channel
            if _is_playlist_url(url):
                stats = archiver.backup_playlist(url)
            else:
                stats = archiver.backup_channel(url)
            _print_stats(stats)

        else:
            # Config mode: backup all enabled sources
            enabled_sources = [s for s in config.sources if s.enabled]

            if not enabled_sources:
                click.echo("No enabled sources found in configuration", err=True)
                click.echo("Edit .annextube/config.toml to add sources")
                raise click.Abort()

            click.echo(f"Found {len(enabled_sources)} enabled source(s)")
            if config.filters.limit:
                click.echo(f"Limit: {config.filters.limit} videos per source (most recent)")
            click.echo()

            total_stats: dict[str, Any] = {
                "sources_processed": 0,
                "videos_processed": 0,
                "videos_tracked": 0,
                "metadata_saved": 0,
                "errors": [],
            }

            for i, source in enumerate(enabled_sources, 1):
                click.echo(f"[{i}/{len(enabled_sources)}] {source.type.capitalize()}: {source.url}")

                # Route to appropriate backup method
                if source.type == "playlist":
                    stats = archiver.backup_playlist(source.url, source_config=source)
                else:
                    stats = archiver.backup_channel(source.url, source_config=source)
                _print_stats(stats, prefix="  ")

                total_stats["sources_processed"] += 1
                total_stats["videos_processed"] += stats["videos_processed"]
                total_stats["videos_tracked"] += stats["videos_tracked"]
                total_stats["metadata_saved"] += stats["metadata_saved"]
                total_stats["errors"].extend(stats["errors"])

                click.echo()

            # Print total summary
            click.echo("=" * 60)
            click.echo("Total Summary:")
            click.echo(f"  Sources processed: {total_stats['sources_processed']}")
            click.echo(f"  Videos tracked: {total_stats['videos_tracked']}")
            click.echo(f"  Metadata files saved: {total_stats['metadata_saved']}")

            if total_stats["errors"]:
                click.echo(f"  Errors: {len(total_stats['errors'])}")

        click.echo()
        click.echo("[ok] Backup complete!")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Edit .annextube/config.toml to configure sources")
        raise click.Abort() from e

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e


def _print_stats(stats: dict, prefix: str = ""):
    """Print backup statistics.

    Args:
        stats: Statistics dictionary
        prefix: Optional prefix for each line
    """
    click.echo(f"{prefix}Summary:")
    click.echo(f"{prefix}  Videos processed: {stats['videos_processed']}")
    click.echo(f"{prefix}  Videos tracked: {stats['videos_tracked']}")
    click.echo(f"{prefix}  Metadata files: {stats['metadata_saved']}")
    click.echo(f"{prefix}  Captions downloaded: {stats.get('captions_downloaded', 0)}")

    if stats["errors"]:
        click.echo(f"{prefix}  [!] Errors: {len(stats['errors'])}")


def _is_playlist_url(url: str) -> bool:
    """Detect if URL is a playlist.

    Args:
        url: YouTube URL

    Returns:
        True if URL appears to be a playlist
    """
    return "playlist?" in url or "list=" in url
