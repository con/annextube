"""Init command for annextube."""

from pathlib import Path

import click

from annextube.lib.config import save_config_template
from annextube.lib.logging_config import get_logger
from annextube.services.git_annex import GitAnnexService

logger = get_logger(__name__)


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Directory to initialize (default: current directory)",
)
@click.pass_context
def init(ctx: click.Context, output_dir: Path):
    """Initialize a new YouTube archive repository.

    Creates git-annex repository with URL backend for tracking video URLs,
    configures file tracking rules, and generates configuration template.
    """
    logger.info(f"Initializing annextube archive at {output_dir}")

    # Ensure directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if already initialized
    git_annex = GitAnnexService(output_dir)
    if git_annex.is_annex_repo():
        click.echo(f"Error: {output_dir} is already a git-annex repository", err=True)
        return

    try:
        # Initialize git-annex
        git_annex.init_repo(description="annextube YouTube archive")

        # Configure .gitattributes
        git_annex.configure_gitattributes()

        # Create config directory and template
        config_dir = output_dir / ".annextube"
        config_path = save_config_template(config_dir)

        # Initial commit
        git_annex.add_and_commit("Initial annextube repository setup")

        # Success message
        click.echo("✓ Initialized YouTube archive repository in current directory")
        click.echo("✓ Git-annex backend: URL (for video URLs)")
        click.echo("✓ Tracking configuration:")
        click.echo("  - *.json, *.tsv, *.md, *.vtt → git")
        click.echo("  - *.mp4, *.webm, *.jpg, *.png → git-annex")
        click.echo()
        click.echo(f"✓ Template configuration created: {config_path}")
        click.echo("  Edit this file to configure channels, playlists, and filters.")
        click.echo()
        click.echo("Next steps:")
        click.echo("  1. Edit .annextube/config.toml to add channels/playlists")
        click.echo("  2. Add your YouTube Data API key (get from Google Cloud Console)")
        click.echo("  3. Run: annextube backup")

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
