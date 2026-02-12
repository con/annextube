"""Export command for annextube."""

from pathlib import Path

import click

from annextube.lib.archive_discovery import discover_annextube
from annextube.lib.logging_config import get_logger
from annextube.services.export import ExportService

logger = get_logger(__name__)




@click.command()
@click.argument(
    "what",
    type=click.Choice(["all", "videos", "playlists", "authors"], case_sensitive=False),
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

    # Check if this is a single-channel archive
    archive_info = discover_annextube(output_dir)
    if archive_info is None or archive_info.type == "multi-channel":
        error_msg = (
            f"Error: {output_dir} is not a single-channel annextube archive."
            if archive_info
            else f"Error: {output_dir} is not an annextube archive. Run 'annextube init' first."
        )
        click.echo(error_msg, err=True)
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
            try:
                channel_json_path = export_service.generate_channel_json()
                click.echo(f"[ok] Generated {channel_json_path}")
            except ValueError as e:
                logger.error(f"Failed to generate channel.json: {e}")
                click.echo(f"Error: {e}", err=True)

        click.echo()
        click.echo("[ok] Export complete!")

    except Exception as e:
        logger.error(f"Export failed: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e
