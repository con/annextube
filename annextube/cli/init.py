"""Init command for annextube."""

from pathlib import Path

import click

from annextube.lib.archive_discovery import discover_annextube
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
@click.option("--comments", type=int, default=-1, show_default=True, help="Comments depth: -1=unlimited, 0=disabled, N=limit to N")
@click.option("--captions/--no-captions", default=True, help="Enable captions (default: enabled)")
@click.option("--thumbnails/--no-thumbnails", default=True, help="Enable thumbnails (default: enabled)")
@click.option("--limit", type=int, default=None, help="Limit to N most recent videos")
@click.option("--include-playlists", default="all", show_default=True, help="Playlist inclusion: 'all', 'none', or regex pattern")
@click.option("--include-podcasts", default="all", show_default=True, help="Podcast inclusion: 'all', 'none', or regex pattern")
@click.option("--video-path-pattern", default="{year}/{month}/{date}_{sanitized_title}", show_default=True, help="Path pattern for video directories")
@click.option("--all-to-git", is_flag=True, default=False, help="Keep all files in git (no annexing). Use for demos/GitHub Pages.")
@click.pass_context
def init(ctx: click.Context, directory: Path, urls: tuple, videos: bool, comments: int, captions: bool, thumbnails: bool, limit: int, include_playlists: str, include_podcasts: str, video_path_pattern: str, all_to_git: bool):
    """Initialize a new YouTube archive repository.

    Creates git-annex repository with URL backend for tracking video URLs,
    configures file tracking rules, and generates configuration template.

    Arguments:
        DIRECTORY: Directory to initialize (default: current directory)
        URLS: YouTube channel or playlist URLs to add to configuration
    """
    # Log version at INFO level
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

    output_dir = directory
    logger.info(f"Initializing annextube archive at {output_dir}")

    # Ensure directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if already initialized
    archive_info = discover_annextube(output_dir)
    if archive_info is not None:
        error_msg = (
            f"Error: {output_dir} is already a multi-channel collection."
            if archive_info.type == "multi-channel"
            else f"Error: {output_dir} is already a single-channel annextube archive."
        )
        click.echo(error_msg, err=True)
        return

    git_annex = GitAnnexService(output_dir)

    try:
        # Initialize git-annex
        git_annex.init_repo(description="annextube YouTube archive")

        # Configure .gitattributes
        git_annex.configure_gitattributes(all_to_git=all_to_git)

        # Create config directory and template
        config_dir = output_dir / ".annextube"
        # Convert -1 (unlimited) to None
        comments_depth_value = None if comments == -1 else comments
        config_path = save_config_template(
            config_dir,
            urls=list(urls),
            enable_videos=videos,
            comments_depth=comments_depth_value,
            enable_captions=captions,
            enable_thumbnails=thumbnails,
            limit=limit,
            include_playlists=include_playlists,
            include_podcasts=include_podcasts,
            video_path_pattern=video_path_pattern
        )

        # Initial commit
        git_annex.add_and_commit("Initial annextube repository setup")

        # Success message
        click.echo("Initialized YouTube archive repository in current directory")
        click.echo("Git-annex backend: URL (for video URLs)")
        if all_to_git:
            click.echo("Tracking configuration: ALL FILES IN GIT (demo mode)")
        else:
            click.echo("Tracking configuration:")
            click.echo("  - *.json, *.tsv, *.md, *.vtt -> git")
            click.echo("  - *.mp4, *.webm, *.jpg, *.png -> git-annex")
        click.echo()
        click.echo(f"Configuration created: {config_path}")
        if urls:
            click.echo(f"Added {len(urls)} source(s):")
            for url in urls:
                click.echo(f"  - {url}")
        else:
            click.echo("  No sources added - edit config to add channels/playlists")
        click.echo()
        click.echo("Component settings:")
        click.echo(f"  - Videos: {'enabled' if videos else 'disabled'}")
        if comments == 0:
            click.echo("  - Comments: disabled")
        elif comments == -1:
            click.echo("  - Comments: unlimited (fetches all, incrementally)")
        else:
            click.echo(f"  - Comments: up to {comments}")
        click.echo(f"  - Captions: {'enabled' if captions else 'disabled'}")
        click.echo(f"  - Thumbnails: {'enabled' if thumbnails else 'disabled'}")
        if limit:
            click.echo(f"  - Limit: {limit} most recent videos")
        if include_playlists != "none":
            click.echo(f"  - Playlists: {include_playlists}")
        if include_podcasts != "none":
            click.echo(f"  - Podcasts: {include_podcasts}")
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
        raise click.Abort() from e
