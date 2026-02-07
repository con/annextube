"""Export command for annextube."""

import csv
import json
from pathlib import Path

import click

from annextube.lib.config import load_config
from annextube.lib.logging_config import get_logger
from annextube.services.export import ExportService
from annextube.services.git_annex import GitAnnexService

logger = get_logger(__name__)


def _generate_channel_json(output_dir: Path) -> Path:
    """Generate channel.json with channel metadata and archive statistics.

    Args:
        output_dir: Archive directory

    Returns:
        Path to generated channel.json
    """
    # Load config to get channel info
    config = load_config(repo_path=output_dir)

    if not config.sources:
        raise click.ClickException("No sources configured. Cannot generate channel.json.")

    # Get first channel source
    channel_source = None
    for source in config.sources:
        if source.type == "channel":
            channel_source = source
            break

    if not channel_source:
        raise click.ClickException("No channel sources found in config.")

    # Parse channel ID from URL
    # Format: https://www.youtube.com/@username or https://www.youtube.com/channel/UCxxxxxx
    url = channel_source.url
    custom_url = None
    channel_id = None

    if "@" in url:
        # Custom URL format
        custom_url = url.split("@")[-1].split("/")[0].split("?")[0]
    elif "/channel/" in url:
        # Channel ID format
        channel_id = url.split("/channel/")[-1].split("/")[0].split("?")[0]

    # Try to get channel metadata from existing video
    # (We'll use the first video's channel metadata)
    videos_dir = output_dir / "videos"
    channel_name = ""
    channel_desc = ""
    subscriber_count = 0
    video_count = 0

    if videos_dir.exists():
        # Find first video metadata.json
        for metadata_file in videos_dir.rglob("metadata.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    video_data = json.load(f)
                    channel_id = channel_id or video_data.get("channel_id", "")
                    channel_name = video_data.get("channel_name", "")
                    break
            except Exception:
                continue

    # Compute archive stats from videos.tsv
    videos_tsv = output_dir / "videos" / "videos.tsv"
    archive_stats = {
        "total_videos_archived": 0,
        "first_video_date": None,
        "last_video_date": None,
        "total_duration_seconds": 0,
        "total_size_bytes": 0,
    }

    if videos_tsv.exists():
        try:
            with open(videos_tsv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                rows = list(reader)

                archive_stats["total_videos_archived"] = len(rows)

                if rows:
                    dates = [row.get('published_at') for row in rows if row.get('published_at')]
                    if dates:
                        archive_stats["first_video_date"] = min(dates)
                        archive_stats["last_video_date"] = max(dates)

                    for row in rows:
                        try:
                            archive_stats["total_duration_seconds"] += int(row.get('duration', 0))
                        except (ValueError, TypeError):
                            pass

                        try:
                            archive_stats["total_size_bytes"] += int(row.get('file_size', 0))
                        except (ValueError, TypeError):
                            pass
        except Exception as e:
            logger.warning(f"Error reading videos.tsv: {e}")

    # Count playlists
    playlists_dir = output_dir / "playlists"
    playlist_count = 0
    if playlists_dir.exists():
        playlist_count = len(list(playlists_dir.glob("*/playlist.json")))

    # Build channel.json
    from datetime import datetime
    now = datetime.now().isoformat()

    channel_data = {
        "channel_id": channel_id or "",
        "name": channel_name,
        "description": channel_desc,
        "custom_url": custom_url or "",
        "subscriber_count": subscriber_count,
        "video_count": video_count,
        "avatar_url": "",
        "banner_url": "",
        "country": "",
        "videos": [],
        "playlists": [],
        "last_sync": now,
        "created_at": "",
        "fetched_at": now,
        "archive_stats": archive_stats,
    }

    # Write channel.json
    output_path = output_dir / "channel.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(channel_data, f, indent=2)

    return output_path


@click.command()
@click.argument(
    "what",
    type=click.Choice(["videos", "playlists", "authors", "all"], case_sensitive=False),
    default="all",
    required=False,
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Archive directory (default: current directory)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Custom output file path",
)
@click.option(
    "--channel-json",
    is_flag=True,
    help="Generate channel.json with archive statistics (for multi-channel collections)",
)
@click.pass_context
def export(ctx: click.Context, what: str, output_dir: Path, output: Path, channel_json: bool):
    """Export metadata to TSV format.

    Generates tab-separated value (TSV) files with summary metadata
    for videos and playlists. These files enable fast loading by web
    interfaces without parsing individual JSON files.

    Arguments:
        WHAT: What to export - 'videos', 'playlists', 'authors', or 'all' (default)

    Examples:

        # Export all metadata
        annextube export

        # Export only videos
        annextube export videos

        # Export to custom location
        annextube export --output /tmp/videos.tsv videos

        # Generate channel.json for multi-channel collection
        annextube export --channel-json
    """
    logger.info(f"Starting export: {what}")

    # Check if this is a git-annex repo
    git_annex = GitAnnexService(output_dir)
    if not git_annex.is_annex_repo():
        click.echo(
            f"Error: {output_dir} is not an annextube archive. Run 'annextube init' first.",
            err=True,
        )
        raise click.Abort()

    try:
        export_service = ExportService(output_dir)

        if what == "videos":
            output_path = export_service.generate_videos_tsv(output)
            click.echo(f"[ok] Generated {output_path}")

        elif what == "playlists":
            output_path = export_service.generate_playlists_tsv(output)
            click.echo(f"[ok] Generated {output_path}")

        elif what == "authors":
            from annextube.services.authors import AuthorsService
            authors_service = AuthorsService(output_dir)
            output_path = authors_service.generate_authors_tsv()
            click.echo(f"[ok] Generated {output_path}")

        elif what == "all":
            if output:
                click.echo("Error: Cannot specify --output with 'all' export", err=True)
                raise click.Abort()

            videos_path, playlists_path, authors_path = export_service.generate_all()
            click.echo(f"[ok] Generated {videos_path}")
            click.echo(f"[ok] Generated {playlists_path}")
            click.echo(f"[ok] Generated {authors_path}")

        # Generate channel.json if requested
        if channel_json:
            channel_json_path = _generate_channel_json(output_dir)
            click.echo(f"[ok] Generated {channel_json_path}")

        click.echo()
        click.echo("[ok] Export complete!")

    except Exception as e:
        logger.error(f"Export failed: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e
