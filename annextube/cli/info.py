"""Info command for annextube - show archive contents."""

import json
from pathlib import Path

import click

from annextube.lib.logging_config import get_logger
from annextube.services.git_annex import GitAnnexService

logger = get_logger(__name__)


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Archive directory (default: current directory)",
)
@click.pass_context
def info(ctx: click.Context, output_dir: Path):
    """Show information about the archive.

    Displays statistics about videos, metadata, captions, and thumbnails
    in the current archive.
    """
    # Check if this is a git-annex repo
    git_annex = GitAnnexService(output_dir)
    if not git_annex.is_annex_repo():
        click.echo(
            f"Error: {output_dir} is not an annextube archive. Run 'annextube init' first.",
            err=True,
        )
        raise click.Abort()

    try:
        # Scan archive directory
        videos_dir = output_dir / "videos"

        if not videos_dir.exists():
            click.echo("Archive is empty - no videos backed up yet.")
            return

        # Collect statistics
        stats = {
            "videos": 0,
            "metadata_files": 0,
            "thumbnails": 0,
            "captions": 0,
            "channels": set(),
        }

        videos = []

        # Scan video directories
        for video_dir in videos_dir.iterdir():
            if not video_dir.is_dir():
                continue

            stats["videos"] += 1

            # Check for metadata
            metadata_file = video_dir / "metadata.json"
            if metadata_file.exists():
                stats["metadata_files"] += 1

                # Load metadata for more details
                try:
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                        videos.append(metadata)
                        stats["channels"].add(metadata.get("channel_name", "Unknown"))
                except Exception:
                    pass

            # Check for thumbnail
            for ext in ["jpg", "jpeg", "png", "webp"]:
                if (video_dir / f"thumbnail.{ext}").exists():
                    stats["thumbnails"] += 1
                    break

            # Count captions
            captions_dir = video_dir / "captions"
            if captions_dir.exists():
                caption_files = list(captions_dir.glob("*.vtt"))
                stats["captions"] += len(caption_files)

        # Display results
        click.echo("=" * 60)
        click.echo("Archive Information")
        click.echo("=" * 60)
        click.echo(f"Location: {output_dir.absolute()}")
        click.echo()
        click.echo("Statistics:")
        click.echo(f"  Videos: {stats['videos']}")
        click.echo(f"  Metadata files: {stats['metadata_files']}")
        click.echo(f"  Thumbnails: {stats['thumbnails']}")
        click.echo(f"  Caption files: {stats['captions']}")
        click.echo(f"  Channels: {len(stats['channels'])}")
        click.echo()

        if stats["channels"]:
            click.echo("Channels:")
            for channel in sorted(stats["channels"]):
                channel_videos = [v for v in videos if v.get("channel_name") == channel]
                click.echo(f"  - {channel} ({len(channel_videos)} videos)")

        click.echo()

        if videos:
            click.echo("Recent Videos:")
            # Sort by fetched_at
            recent = sorted(videos, key=lambda v: v.get("fetched_at", ""), reverse=True)[:5]
            for v in recent:
                title = v.get("title", "Unknown")
                video_id = v.get("video_id", "Unknown")
                duration = v.get("duration", 0)
                minutes = duration // 60
                seconds = duration % 60
                click.echo(f"  - [{video_id}] {title}")
                click.echo(f"    Duration: {minutes}m {seconds}s | Views: {v.get('view_count', 0):,}")

        click.echo()
        click.echo("Use 'git log' to see backup history")
        click.echo("Use 'git annex info' for git-annex details")

    except Exception as e:
        logger.error(f"Failed to read archive info: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e
