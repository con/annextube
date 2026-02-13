"""Generate web command for annextube."""

import shutil
from pathlib import Path

import click

from annextube._version import __version__
from annextube.lib.archive_discovery import discover_annextube
from annextube.lib.logging_config import get_logger
from annextube.services.export import ExportService

logger = get_logger(__name__)

# Placeholder baked into the Vite build (must match frontend/vite.config.ts)
FRONTEND_VERSION_PLACEHOLDER = "0.0.0-unknown"

# Path to frontend build (relative to this file)
FRONTEND_BUILD_DIR = Path(__file__).parent.parent.parent / "web"


def _inject_version(web_dir: Path, version: str) -> bool:
    """Replace placeholder version in built JS files with actual annextube version.

    Returns True if the placeholder was found and replaced.
    """
    assets_dir = web_dir / "assets"
    if not assets_dir.exists():
        return False

    replaced = False
    for js_file in assets_dir.glob("*.js"):
        content = js_file.read_text()
        # Vite inlines the placeholder as "v0.0.0-unknown" in the JS bundle.
        # Replace it with the real annextube version.
        new_content = content.replace(
            f"v{FRONTEND_VERSION_PLACEHOLDER}",
            f"v{version}",
        )
        if new_content != content:
            js_file.write_text(new_content)
            logger.debug(f"Injected version v{version} into {js_file.name}")
            replaced = True
    return replaced


def deploy_frontend(web_dir: Path) -> None:
    """Copy the built frontend to *web_dir* and inject the annextube version.

    This is the single code-path used by both ``generate-web`` and
    ``serve --regenerate``.  It:

    1. Verifies that the frontend build exists.
    2. Replaces *web_dir* with a fresh copy of the build.
    3. Injects ``__version__`` into the JS bundle so the UI shows the
       correct annextube version.

    Raises
    ------
    click.Abort
        If the frontend build directory does not exist.
    """
    if not FRONTEND_BUILD_DIR.exists():
        click.echo(
            f"Error: Frontend build not found at {FRONTEND_BUILD_DIR}",
            err=True,
        )
        click.echo()
        click.echo("The web frontend is not included in this installation.")
        click.echo()
        click.echo("Options to fix this:")
        click.echo("  1. Development: Run 'cd frontend && npm run build' to build the frontend")
        click.echo("  2. Production: Install from a release that includes the built frontend")
        click.echo("  3. Manual: Copy a pre-built web/ directory to your installation")
        click.echo()
        click.echo(f"Expected location: {FRONTEND_BUILD_DIR}")
        raise click.Abort()

    if web_dir.exists():
        shutil.rmtree(web_dir)
    shutil.copytree(FRONTEND_BUILD_DIR, web_dir)

    if _inject_version(web_dir, __version__):
        click.echo(f"  [ok] web/ (v{__version__})")
    else:
        click.echo(
            f"  Warning: could not inject version v{__version__} "
            f"(placeholder '{FRONTEND_VERSION_PLACEHOLDER}' not found in JS bundle)",
            err=True,
        )


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Archive directory (default: current directory)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing web directory",
)
@click.pass_context
def generate_web(ctx: click.Context, output_dir: Path, force: bool):
    """Generate interactive web browser for the archive.

    Copies the web frontend to the archive's web/ directory and ensures
    TSV metadata files are up to date.

    The web browser provides:
    - Video grid with thumbnails
    - Search, filter, and sort capabilities
    - Playlist browsing
    - Video detail view with comments
    - All static files (works with file:// or HTTP server)

    Examples:

        # Generate web browser for current archive
        annextube generate-web

        # Generate for specific archive
        annextube generate-web --output-dir ~/my-archive

        # Overwrite existing web directory
        annextube generate-web --force
    """
    logger.info("Starting web browser generation")

    # Discover archive type
    archive_info = discover_annextube(output_dir)
    if archive_info is None:
        click.echo(
            f"Error: {output_dir} is not an annextube archive. Run 'annextube init' first.",
            err=True,
        )
        raise click.Abort()

    is_multi_channel = archive_info.type == "multi-channel"

    try:
        web_dir = output_dir / "web"

        # Check if web directory exists
        if web_dir.exists() and not force:
            click.echo(
                f"Error: {web_dir} already exists. Use --force to overwrite.",
                err=True,
            )
            raise click.Abort()

        if is_multi_channel:
            # Multi-channel collection: channels.tsv already exists, just copy frontend
            click.echo("Multi-channel collection detected (channels.tsv found)")
            click.echo(f"Channels overview: {archive_info.channels_tsv}")
        else:
            # Single-channel archive: ensure TSV metadata files are up to date
            click.echo("Updating metadata files...")
            export_service = ExportService(output_dir)
            videos_tsv, playlists_tsv, authors_tsv = export_service.generate_all()
            click.echo(f"  [ok] {videos_tsv.name}")
            click.echo(f"  [ok] {playlists_tsv.name}")
            click.echo(f"  [ok] {authors_tsv.name}")

        # Deploy frontend (copy + version injection)
        click.echo(f"Copying web browser to {web_dir}...")
        deploy_frontend(web_dir)

        click.echo()
        click.echo("[ok] Web browser generated successfully!")
        click.echo()
        click.echo("To view the archive:")
        click.echo(f"  1. cd {output_dir}")
        click.echo("  2. python3 -m http.server 8000")
        click.echo("  3. Open http://localhost:8000/web/")
        click.echo()
        click.echo("Note: Do NOT use file:// URLs - they don't work due to CORS restrictions.")

    except Exception as e:
        logger.error(f"Web generation failed: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e
