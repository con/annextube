"""Backup command for annextube."""

import asyncio
import json as json_mod
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from annextube.lib.archive_discovery import discover_annextube
from annextube.lib.config import load_config
from annextube.lib.date_utils import parse_date
from annextube.lib.logging_config import get_logger
from annextube.services.archiver import Archiver
from annextube.services.export import ExportService
from annextube.services.search_index import build_caption_index

logger = get_logger(__name__)


def _echo(msg: str = "", json_output: bool = False, **kwargs: Any) -> None:
    """Print message only in human-readable mode."""
    if not json_output:
        click.echo(msg, **kwargs)


def _json_error(command: str, code: int, message: str, details: str = "") -> str:
    """Build JSON error response string."""
    result: dict[str, Any] = {
        "status": "error",
        "command": command,
        "timestamp": datetime.now().isoformat(),
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details:
        result["error"]["details"] = details
    return json_mod.dumps(result, indent=2)


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
        "all-incremental",      # New videos + social for recent (default)
        "videos-incremental",  # New videos only
        "all-force",            # Re-process everything
        "social",               # Comments + captions only (shortcut)
        "playlists",            # Playlists only
        "comments",             # Comments only
        "captions",             # Captions only
        "tsv_metadata"          # Regenerate TSVs only (no downloads)
    ], case_sensitive=False),
    default="all-incremental",
    show_default=True,
    help="Update mode: all-incremental (new videos + social for recent), videos-incremental (new videos only), all-force (re-process all), social (comments+captions), playlists/comments/captions (specific components), tsv_metadata (regenerate TSV files from existing JSON)",
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
    "--comments-depth",
    type=int,
    default=None,
    help="Override comments depth: -1=unlimited, 0=disabled, N=limit to N",
)
@click.option(
    "--yt-dlp-max-parallel",
    type=int,
    default=None,
    help="Max parallel yt-dlp calls per cookie file (default: 1)",
)
@click.option(
    "--skip-existing",
    is_flag=True,
    hidden=True,  # Deprecated, replaced by --update=all-incremental
    help="(Deprecated: use --update=all-incremental instead)",
)
@click.option(
    "--search-index/--no-search-index",
    default=None,
    help="Build caption search index after backup (default: use [search] config)",
)
@click.pass_context
def backup(ctx: click.Context, url: str, output_dir: Path, limit: int, update: str, from_date: str, to_date: str, comments_depth: int | None, yt_dlp_max_parallel: int | None, skip_existing: bool, search_index: bool | None):
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
    json_output: bool = ctx.obj.get("json_output", False)
    start_time = time.monotonic()

    # Log versions at INFO level (like duct does)
    try:
        from annextube._version import version as annextube_version
    except ImportError:
        annextube_version = "unknown"

    try:
        import yt_dlp
        ytdlp_version = yt_dlp.version.__version__
    except Exception:
        ytdlp_version = "unknown"

    logger.info(f"annextube {annextube_version} with yt-dlp {ytdlp_version}")
    logger.info("Starting backup operation")

    # Check if this is an annextube archive
    archive_info = discover_annextube(output_dir)
    if archive_info is None or archive_info.type == "multi-channel":
        error_msg = (
            f"{output_dir} is not a single-channel annextube archive."
            if archive_info
            else f"{output_dir} is not an annextube archive. Run 'annextube init' first."
        )
        if json_output:
            click.echo(_json_error("backup", 4, error_msg))
        else:
            click.echo(f"Error: {error_msg}", err=True)
        raise click.Abort()

    try:
        # Load configuration
        config_path = ctx.obj.get("config_path")
        config = load_config(config_path, repo_path=output_dir)

        # Override limit if specified
        if limit:
            config.filters.limit = limit

        # Override comments_depth if specified
        if comments_depth is not None:
            # Convert -1 (unlimited) to None, same as init does
            config.components.comments_depth = None if comments_depth == -1 else comments_depth
            _echo(f"Comments depth override: {comments_depth} ({'unlimited' if comments_depth == -1 else 'disabled' if comments_depth == 0 else f'up to {comments_depth}'})", json_output)

        # Override yt_dlp_max_parallel if specified
        if yt_dlp_max_parallel is not None:
            config.user.yt_dlp_max_parallel = yt_dlp_max_parallel

        # Handle deprecated --skip-existing flag
        if skip_existing:
            update = "all-incremental"
            _echo("Note: --skip-existing is deprecated, use --update=all-incremental instead", json_output)

        # Default update mode if not specified
        if not update:
            update = "all-incremental"

        _echo(f"Update mode: {update}", json_output)

        # Handle tsv_metadata mode - regenerate TSVs only
        if update == "tsv_metadata":
            _echo("Regenerating TSV metadata files from existing JSON...", json_output)
            exporter = ExportService(output_dir)
            videos_tsv, playlists_tsv, authors_tsv = exporter.generate_all()
            if json_output:
                click.echo(json_mod.dumps({
                    "status": "success",
                    "command": "backup",
                    "timestamp": datetime.now().isoformat(),
                    "update_mode": "tsv_metadata",
                    "files_generated": [str(videos_tsv), str(playlists_tsv), str(authors_tsv)],
                }, indent=2))
            else:
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
                _echo(f"From date: {date_from.strftime('%Y-%m-%d')}", json_output)
            except ValueError as e:
                if json_output:
                    click.echo(_json_error("backup", 2, f"Invalid --from-date: {e}"))
                else:
                    click.echo(f"Error: Invalid --from-date: {e}", err=True)
                raise click.Abort() from None

        if to_date:
            try:
                date_to = parse_date(to_date)
                _echo(f"To date: {date_to.strftime('%Y-%m-%d')}", json_output)
            except ValueError as e:
                if json_output:
                    click.echo(_json_error("backup", 2, f"Invalid --to-date: {e}"))
                else:
                    click.echo(f"Error: Invalid --to-date: {e}", err=True)
                raise click.Abort() from None

        # For all-incremental mode, default to 1 week window for social updates if no dates specified
        if update == "all-incremental" and not from_date:
            from annextube.lib.date_utils import parse_duration
            date_from = datetime.now() - parse_duration("1 week")
            _echo(f"Default social window: {date_from.strftime('%Y-%m-%d')} to now", json_output)

        # Initialize archiver with update mode and date filters
        archiver = Archiver(output_dir, config, update_mode=update, date_from=date_from, date_to=date_to)

        # Collect all errors/warnings across sources for final summary
        all_errors: list[str] = []
        all_warnings: list[str] = []
        # Collect per-source stats for JSON output
        source_results: list[dict[str, Any]] = []

        # Determine what to backup
        if url:
            # Ad-hoc mode: backup single URL
            _echo(f"Backing up: {url}", json_output)
            if config.filters.limit:
                _echo(f"Limit: {config.filters.limit} most recent videos", json_output)

            # Detect if URL is a playlist or channel
            if _is_playlist_url(url):
                stats = archiver.backup_playlist(url)
                source_type = "playlist"
            else:
                stats = archiver.backup_channel(url)
                source_type = "channel"
            _print_stats(stats, json_output=json_output)
            all_errors.extend(stats["errors"])
            all_warnings.extend(stats.get("warnings", []))
            source_results.append({
                "url": url,
                "type": source_type,
                "videos_tracked": stats["videos_tracked"],
                "metadata_saved": stats["metadata_saved"],
                "captions_downloaded": stats.get("captions_downloaded", 0),
                "errors": len(stats["errors"]),
            })

            # Generate channel.json for multi-channel collection integration
            try:
                exporter = ExportService(output_dir)
                channel_json_path = exporter.generate_channel_json()
                logger.info(f"Generated channel.json at {channel_json_path}")
            except Exception as e:
                # Don't fail the entire backup if channel.json generation fails
                logger.warning(f"Could not generate channel.json: {e}")

        else:
            # Config mode: backup all enabled sources
            enabled_sources = [s for s in config.sources if s.enabled]

            if not enabled_sources:
                if json_output:
                    click.echo(_json_error("backup", 6, "No enabled sources found in configuration"))
                else:
                    click.echo("No enabled sources found in configuration", err=True)
                    click.echo("Edit .annextube/config.toml to add sources")
                raise click.Abort()

            _echo(f"Found {len(enabled_sources)} enabled source(s)", json_output)
            if config.filters.limit:
                _echo(f"Limit: {config.filters.limit} videos per source (most recent)", json_output)
            _echo(json_output=json_output)

            total_stats: dict[str, Any] = {
                "sources_processed": 0,
                "videos_processed": 0,
                "videos_tracked": 0,
                "metadata_saved": 0,
                "errors": [],
                "warnings": [],
            }

            for i, source in enumerate(enabled_sources, 1):
                _echo(f"[{i}/{len(enabled_sources)}] {source.type.capitalize()}: {source.url}", json_output)

                # Route to appropriate backup method
                if source.type == "playlist":
                    stats = archiver.backup_playlist(source.url, source_config=source)
                else:
                    stats = archiver.backup_channel(source.url, source_config=source)
                _print_stats(stats, prefix="  ", json_output=json_output)

                total_stats["sources_processed"] += 1
                total_stats["videos_processed"] += stats["videos_processed"]
                total_stats["videos_tracked"] += stats["videos_tracked"]
                total_stats["metadata_saved"] += stats["metadata_saved"]
                total_stats["errors"].extend(stats["errors"])
                total_stats["warnings"].extend(stats.get("warnings", []))

                source_results.append({
                    "url": source.url,
                    "type": source.type,
                    "videos_tracked": stats["videos_tracked"],
                    "metadata_saved": stats["metadata_saved"],
                    "captions_downloaded": stats.get("captions_downloaded", 0),
                    "errors": len(stats["errors"]),
                })

                _echo(json_output=json_output)

            # Print total summary
            _echo("=" * 60, json_output)
            _echo("Total Summary:", json_output)
            _echo(f"  Sources processed: {total_stats['sources_processed']}", json_output)
            _echo(f"  Videos tracked: {total_stats['videos_tracked']}", json_output)
            _echo(f"  Metadata files saved: {total_stats['metadata_saved']}", json_output)

            if total_stats["warnings"]:
                _echo(f"  Warnings: {len(total_stats['warnings'])}", json_output)
            if total_stats["errors"]:
                _echo(f"  Errors: {len(total_stats['errors'])}", json_output)

            all_errors.extend(total_stats["errors"])
            all_warnings.extend(total_stats["warnings"])

        # Generate channel.json for multi-channel collection integration
        try:
            exporter = ExportService(output_dir)
            channel_json_path = exporter.generate_channel_json()
            logger.info(f"Generated channel.json at {channel_json_path}")
        except Exception as e:
            # Don't fail the entire backup if channel.json generation fails
            logger.warning(f"Could not generate channel.json: {e}")

        # Build caption search index if enabled
        # CLI flag overrides config: True=force, False=skip, None=use config
        do_search = config.search.enabled if search_index is None else search_index
        if do_search:
            try:
                from pagefind.index import PagefindIndex  # noqa: F401
            except ImportError:
                _echo(
                    "Error: pagefind package required for search index. "
                    "Install with: pip install 'annextube[search]'",
                    json_output, err=True,
                )
                if not json_output:
                    ctx.exit(1)
            else:
                try:
                    _echo(json_output=json_output)
                    _echo("Building caption search index...", json_output)
                    search_stats = asyncio.run(build_caption_index(output_dir))
                    if not json_output:
                        if search_stats.videos_indexed == 0 and search_stats.chunks_created == 0:
                            click.echo("  [ok] Search index up to date (no changes)")
                        else:
                            size_mb = search_stats.index_size_bytes / (1024 * 1024)
                            click.echo(
                                f"  [ok] {search_stats.videos_indexed} videos "
                                f"({search_stats.videos_curated} curated, {search_stats.videos_original} original), "
                                f"{search_stats.chunks_created:,} chunks, {size_mb:.1f} MB"
                            )
                        if search_stats.videos_skipped:
                            click.echo(f"  (skipped {search_stats.videos_skipped} videos without captions)")
                except Exception as e:
                    if not json_output:
                        click.echo(f"Warning: search index build failed: {e}", err=True)
                    else:
                        logger.warning(f"Search index build failed: {e}")

        duration_seconds = round(time.monotonic() - start_time, 1)

        # Emit JSON output
        if json_output:
            has_errors = len(all_errors) > 0
            total_videos = sum(s["videos_tracked"] for s in source_results)
            total_metadata = sum(s["metadata_saved"] for s in source_results)
            total_captions = sum(s["captions_downloaded"] for s in source_results)
            result: dict[str, Any] = {
                "status": "error" if has_errors else "success",
                "command": "backup",
                "timestamp": datetime.now().isoformat(),
                "sources_processed": len(source_results),
                "sources": source_results,
                "summary": {
                    "videos_tracked": total_videos,
                    "metadata_saved": total_metadata,
                    "captions_downloaded": total_captions,
                    "duration_seconds": duration_seconds,
                },
            }
            if all_errors:
                result["errors"] = all_errors
            if all_warnings:
                result["warnings"] = all_warnings
            click.echo(json_mod.dumps(result, indent=2))
            if has_errors:
                ctx.exit(1)
            return

        # Human-readable final output
        click.echo()
        if all_warnings:
            n = len(all_warnings)
            click.echo(f"[~] {n} warning(s):")
            max_shown = 10
            for w in all_warnings[:max_shown]:
                click.echo(f"  - {w}")
            if n > max_shown:
                click.echo(f"  ... and {n - max_shown} more")
        if all_errors:
            n = len(all_errors)
            click.echo(f"[!] Backup completed with {n} error(s):", err=True)
            max_shown = 10
            for err_msg in all_errors[:max_shown]:
                click.echo(f"  - {err_msg}", err=True)
            if n > max_shown:
                click.echo(f"  ... and {n - max_shown} more (check logs for details)", err=True)
            ctx.exit(1)
        else:
            click.echo("[ok] Backup complete!")

    except click.exceptions.Exit:
        raise  # Let Click handle exit codes from ctx.exit()

    except FileNotFoundError as e:
        if json_output:
            click.echo(_json_error("backup", 5, str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
            click.echo("Edit .annextube/config.toml to configure sources")
        raise click.Abort() from e

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        if json_output:
            click.echo(_json_error("backup", 1, str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e


def _print_stats(stats: dict, prefix: str = "", json_output: bool = False) -> None:
    """Print backup statistics in human-readable mode.

    Args:
        stats: Statistics dictionary
        prefix: Optional prefix for each line
        json_output: If True, suppress output (JSON emitted at end)
    """
    if json_output:
        return

    click.echo(f"{prefix}Summary:")
    click.echo(f"{prefix}  Videos processed: {stats['videos_processed']}")
    click.echo(f"{prefix}  Videos tracked: {stats['videos_tracked']}")
    click.echo(f"{prefix}  Metadata files: {stats['metadata_saved']}")
    click.echo(f"{prefix}  Captions downloaded: {stats.get('captions_downloaded', 0)}")

    if stats.get("warnings"):
        click.echo(f"{prefix}  [~] Warnings: {len(stats['warnings'])}")
        for warn_msg in stats["warnings"]:
            click.echo(f"{prefix}    - {warn_msg}")
    if stats["errors"]:
        click.echo(f"{prefix}  [!] Errors: {len(stats['errors'])}")
        for err_msg in stats["errors"]:
            click.echo(f"{prefix}    - {err_msg}")


def _is_playlist_url(url: str) -> bool:
    """Detect if URL is a playlist.

    Args:
        url: YouTube URL

    Returns:
        True if URL appears to be a playlist
    """
    return "playlist?" in url or "list=" in url
