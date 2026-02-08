"""Aggregate command for multi-channel collections."""

import csv
import json
from pathlib import Path

import click

from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)


def discover_channels(root_dir: Path, depth: int = 1) -> list[tuple[Path, Path]]:
    """Discover channel.json files up to specified depth.

    Args:
        root_dir: Root directory to search
        depth: Maximum depth to search (1-3)

    Returns:
        List of (channel_dir, channel_json_path) tuples
    """
    channels = []

    # Build glob pattern based on depth
    if depth == 1:
        pattern = "*/channel.json"
    elif depth == 2:
        pattern = "*/*/channel.json"
    elif depth == 3:
        pattern = "*/*/*/channel.json"
    else:
        raise ValueError(f"Depth must be 1-3, got {depth}")

    for channel_json in root_dir.glob(pattern):
        channel_dir = channel_json.parent
        # Make path relative to root_dir
        rel_channel_dir = channel_dir.relative_to(root_dir)
        channels.append((rel_channel_dir, channel_json))

    return sorted(channels, key=lambda x: x[0])


def compute_archive_stats(channel_dir: Path) -> dict:
    """Compute archive statistics from videos.tsv.

    Args:
        channel_dir: Channel directory path

    Returns:
        Archive stats dictionary
    """
    videos_tsv = channel_dir / "videos" / "videos.tsv"

    stats = {
        "total_videos_archived": 0,
        "first_video_date": None,
        "last_video_date": None,
        "total_duration_seconds": 0,
        "total_size_bytes": 0,
    }

    if not videos_tsv.exists():
        logger.warning(f"videos/videos.tsv not found in {channel_dir}, archive_stats will be empty")
        return stats

    try:
        with open(videos_tsv, encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            rows = list(reader)

            stats["total_videos_archived"] = len(rows)

            if rows:
                # Get date range (published_at is YYYY-MM-DD format in TSV)
                dates = [row.get('published_at') for row in rows if row.get('published_at')]
                if dates:
                    stats["first_video_date"] = min(dates)
                    stats["last_video_date"] = max(dates)

                # Sum duration (in seconds)
                for row in rows:
                    duration_str = row.get('duration', '0')
                    try:
                        stats["total_duration_seconds"] += int(duration_str)
                    except (ValueError, TypeError):
                        pass

                # Sum file size (in bytes)
                for row in rows:
                    size_str = row.get('file_size', '0')
                    try:
                        stats["total_size_bytes"] += int(size_str)
                    except (ValueError, TypeError):
                        pass

    except Exception as e:
        logger.warning(f"Error reading videos.tsv in {channel_dir}: {e}")

    return stats


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd(),
    required=False,
)
@click.option(
    "--depth",
    type=click.IntRange(1, 3),
    default=1,
    help="Discovery depth for */channel.json (default: 1, max: 3)",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path (default: DIRECTORY/channels.tsv)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing channels.tsv",
)
def aggregate(directory: Path, depth: int, output: Path | None, force: bool):
    """Aggregate channel metadata from multi-channel collection.

    Discovers channel.json files in subdirectories, computes archive statistics
    from each channel's videos.tsv, and generates a summary channels.tsv file.

    Examples:

        # Discover channels in current directory (flat structure)
        annextube aggregate

        # Discover channels with nested structure (up to 2 levels deep)
        annextube aggregate --depth 2

        # Specify directory and output file
        annextube aggregate /path/to/collection --output summary.tsv
    """
    root_dir = directory
    output_file = output or (root_dir / "channels.tsv")

    logger.info(f"Discovering channels in {root_dir} (depth: {depth})")

    # Check if output exists
    if output_file.exists() and not force:
        click.echo(
            f"Error: {output_file} already exists. Use --force to overwrite.",
            err=True,
        )
        raise click.Abort()

    # Discover channels
    discovered = discover_channels(root_dir, depth)

    if not discovered:
        click.echo(f"No channels found in {root_dir} (depth: {depth})")
        click.echo("Channels must have a channel.json file.")
        return

    logger.info(f"Found {len(discovered)} channel(s)")

    # Parse each channel and compute stats
    channels_data = []

    for rel_channel_dir, channel_json_path in discovered:
        logger.debug(f"Processing {rel_channel_dir}")

        try:
            # Load channel.json
            with open(channel_json_path, encoding='utf-8') as f:
                channel_data = json.load(f)

            # Compute archive stats
            channel_dir_abs = root_dir / rel_channel_dir
            archive_stats = compute_archive_stats(channel_dir_abs)

            # Build row for TSV
            row = {
                "channel_id": channel_data.get("channel_id", ""),
                "title": channel_data.get("name", ""),
                "custom_url": channel_data.get("custom_url", ""),
                "description": channel_data.get("description", ""),
                "subscriber_count": channel_data.get("subscriber_count", 0),
                "video_count": channel_data.get("video_count", 0),
                "playlist_count": len(channel_data.get("playlists", [])),
                "total_videos_archived": archive_stats["total_videos_archived"],
                "first_video_date": archive_stats["first_video_date"] or "",
                "last_video_date": archive_stats["last_video_date"] or "",
                "last_sync": channel_data.get("last_sync", ""),
                "channel_dir": str(rel_channel_dir),
            }

            channels_data.append(row)

        except Exception as e:
            logger.error(f"Error processing {rel_channel_dir}: {e}")
            continue

    if not channels_data:
        click.echo("No valid channels found")
        return

    # Sort by title
    channels_data.sort(key=lambda x: x["title"].lower())

    # Write channels.tsv
    logger.info(f"Writing {output_file}")

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = [
            "channel_id",
            "title",
            "custom_url",
            "description",
            "subscriber_count",
            "video_count",
            "playlist_count",
            "total_videos_archived",
            "first_video_date",
            "last_video_date",
            "last_sync",
            "channel_dir",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(channels_data)

    click.echo(f"Generated {output_file} with {len(channels_data)} channel(s)")

    # Display summary
    click.echo()
    click.echo("Channels discovered:")
    for row in channels_data:
        click.echo(f"  - {row['title']} ({row['channel_dir']}): {row['total_videos_archived']} videos")
