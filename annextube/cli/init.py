"""Init command for annextube."""

from pathlib import Path

import click

from annextube.lib.config import save_config_template
from annextube.lib.logging_config import get_logger
from annextube.services.git_annex import GitAnnexService

logger = get_logger(__name__)


@click.command()
@click.argument(
    "directory",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    required=False,
)
@click.argument("urls", nargs=-1)
@click.option("--videos/--no-videos", default=True, help="Enable video downloading (default: enabled)")
@click.option("--comments", type=int, default=10000, help="Comments depth (0=disabled, default: 10000)")
@click.option("--captions/--no-captions", default=True, help="Enable captions (default: enabled)")
@click.pass_context
def init(ctx: click.Context, directory: Path, urls: tuple, videos: bool, comments: int, captions: bool):
    """Initialize a new YouTube archive repository.

    Creates git-annex repository with URL backend for tracking video URLs,
    configures file tracking rules, and generates configuration template.

    Arguments:
        DIRECTORY: Directory to initialize (default: current directory)
        URLS: YouTube channel or playlist URLs to add to configuration
    """
    output_dir = directory
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
        config_path = save_config_template(
            config_dir,
            urls=list(urls),
            enable_videos=videos,
            comments_depth=comments,
            enable_captions=captions
        )

        # Initial commit
        git_annex.add_and_commit("Initial annextube repository setup")

        # Success message
        click.echo("✓ Initialized YouTube archive repository in current directory")
        click.echo("✓ Git-annex backend: URL (for video URLs)")
        click.echo("✓ Tracking configuration:")
        click.echo("  - *.json, *.tsv, *.md, *.vtt → git")
        click.echo("  - *.mp4, *.webm, *.jpg, *.png → git-annex")
        click.echo()
        click.echo(f"✓ Configuration created: {config_path}")
        if urls:
            click.echo(f"✓ Added {len(urls)} source(s):")
            for url in urls:
                click.echo(f"  - {url}")
        else:
            click.echo("  No sources added - edit config to add channels/playlists")
        click.echo()
        click.echo("Component settings:")
        click.echo(f"  - Videos: {'enabled' if videos else 'disabled'}")
        click.echo(f"  - Comments: {'disabled' if comments == 0 else f'up to {comments}'}")
        click.echo(f"  - Captions: {'enabled' if captions else 'disabled'}")
        click.echo()
        click.echo("Next steps:")
        if not urls:
            click.echo("  1. Edit .annextube/config.toml to add channels/playlists")
            click.echo("  2. Run: annextube backup")
        else:
            click.echo("  Run: annextube backup")

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
