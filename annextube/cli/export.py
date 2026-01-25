"""Export command for annextube."""

from pathlib import Path

import click

from annextube.lib.logging_config import get_logger
from annextube.services.export import ExportService
from annextube.services.git_annex import GitAnnexService

logger = get_logger(__name__)


@click.command()
@click.argument(
    "what",
    type=click.Choice(["videos", "playlists", "all"], case_sensitive=False),
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
@click.pass_context
def export(ctx: click.Context, what: str, output_dir: Path, output: Path):
    """Export metadata to TSV format.

    Generates tab-separated value (TSV) files with summary metadata
    for videos and playlists. These files enable fast loading by web
    interfaces without parsing individual JSON files.

    Arguments:
        WHAT: What to export - 'videos', 'playlists', or 'all' (default)

    Examples:

        # Export all metadata
        annextube export

        # Export only videos
        annextube export videos

        # Export to custom location
        annextube export --output /tmp/videos.tsv videos
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
            click.echo(f"✓ Generated {output_path}")

        elif what == "playlists":
            output_path = export_service.generate_playlists_tsv(output)
            click.echo(f"✓ Generated {output_path}")

        elif what == "all":
            if output:
                click.echo("Error: Cannot specify --output with 'all' export", err=True)
                raise click.Abort()

            videos_path, playlists_path = export_service.generate_all()
            click.echo(f"✓ Generated {videos_path}")
            click.echo(f"✓ Generated {playlists_path}")

        click.echo()
        click.echo("✓ Export complete!")

    except Exception as e:
        logger.error(f"Export failed: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
