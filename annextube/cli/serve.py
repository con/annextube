"""Serve command for annextube - HTTP server with range support and auto-regeneration."""

import os
import shutil
import socketserver
import time
from pathlib import Path
from threading import Thread

import click

from annextube.cli.aggregate import discover_channels
from annextube.lib.archive_discovery import discover_annextube
from annextube.lib.logging_config import get_logger
from annextube.lib.range_server import RangeHTTPRequestHandler
from annextube.services.export import ExportService

logger = get_logger(__name__)

# Path to frontend build (relative to this file)
FRONTEND_BUILD_DIR = Path(__file__).parent.parent.parent / "web"


class ArchiveWatcher:
    """Watch for changes in archive metadata and regenerate TSVs/web UI."""

    def __init__(self, repo_path: Path, web_dir: Path, watch_interval: int = 5):
        """Initialize archive watcher.

        Args:
            repo_path: Path to archive root
            web_dir: Path to web directory
            watch_interval: Seconds between checks
        """
        self.repo_path = repo_path
        self.web_dir = web_dir
        self.watch_interval = watch_interval
        self.running = False
        self.last_mtimes: dict[str, float] = {}

        # Track metadata files
        self.watched_patterns = [
            "videos/**/metadata.json",
            "videos/**/comments.json",
            "playlists/**/playlist.json",
        ]

    def get_latest_mtime(self) -> float:
        """Get the latest modification time of watched files."""
        latest = 0.0
        for pattern in self.watched_patterns:
            for path in self.repo_path.glob(pattern):
                if path.is_file():
                    mtime = path.stat().st_mtime
                    latest = max(latest, mtime)
        return latest

    def regenerate(self):
        """Regenerate TSV files and web UI."""
        try:
            logger.info("Changes detected, regenerating TSV files...")
            export = ExportService(self.repo_path)
            videos_tsv, playlists_tsv, authors_tsv = export.generate_all()

            logger.info(f"[ok] Regenerated: {videos_tsv.name}, {playlists_tsv.name}, {authors_tsv.name}")

            # TODO: In future, could also regenerate web UI if needed
            # For now, TSVs are enough since web UI reads them dynamically

        except Exception as e:
            logger.error(f"Failed to regenerate: {e}")

    def watch(self):
        """Watch for changes and regenerate when needed."""
        self.running = True
        self.last_mtimes = {pattern: self.get_latest_mtime() for pattern in self.watched_patterns}

        logger.info(f"Watching for changes (checking every {self.watch_interval}s)...")

        while self.running:
            time.sleep(self.watch_interval)

            current_mtime = self.get_latest_mtime()
            if current_mtime > max(self.last_mtimes.values()):
                self.last_mtimes = dict.fromkeys(self.watched_patterns, current_mtime)
                self.regenerate()

    def stop(self):
        """Stop watching."""
        self.running = False


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Archive directory (default: current directory)",
)
@click.option(
    "--port",
    type=int,
    default=8080,
    help="Port to serve on (default: 8080)",
)
@click.option(
    "--host",
    type=str,
    default="0.0.0.0",
    help="Host to bind to (default: 0.0.0.0)",
)
@click.option(
    "--watch/--no-watch",
    default=True,
    help="Watch for changes and auto-regenerate (default: enabled)",
)
@click.option(
    "--watch-interval",
    type=int,
    default=5,
    help="Seconds between watch checks (default: 5)",
)
@click.option(
    "--regenerate",
    type=click.Choice(['tsv', 'web', 'all'], case_sensitive=False),
    default=None,
    help="Regenerate before serving: 'tsv' (TSV files only), 'web' (web UI only), 'all' (both)",
)
@click.pass_context
def serve(
    ctx: click.Context,
    output_dir: Path,
    port: int,
    host: str,
    watch: bool,
    watch_interval: int,
    regenerate: str,
):
    """Serve archive web UI with HTTP range support for video seeking.

    This command starts an HTTP server with proper range request support,
    which is essential for video seeking/scrubbing. Standard Python's
    http.server doesn't support ranges, preventing video timeline navigation.

    Features:
    - HTTP Range requests (enables video seeking)
    - Auto-regeneration of TSV files when metadata changes
    - CORS headers for local development
    - Quiet logging (only errors and range requests)

    Examples:

        # Serve current archive on port 8080
        annextube serve

        # Serve on custom port with auto-watch
        annextube serve --port 3000

        # Serve without watching for changes
        annextube serve --no-watch

        # Regenerate TSV files before serving
        annextube serve --regenerate=tsv

        # Regenerate web UI before serving
        annextube serve --regenerate=web

        # Regenerate everything before serving
        annextube serve --regenerate=all
    """
    # Discover archive type
    archive_info = discover_annextube(output_dir)
    if archive_info is None:
        click.echo(
            f"Error: {output_dir} is not an annextube archive. Run 'annextube init' first.",
            err=True,
        )
        raise click.Abort()

    is_multi_channel = archive_info.type == "multi-channel"
    web_dir = output_dir / "web"

    # Regenerate if requested
    if regenerate:
        try:
            # Regenerate TSV files
            if regenerate in ['tsv', 'all']:
                if is_multi_channel:
                    click.echo("Regenerating TSV files for multi-channel collection...")

                    # Discover all channels
                    channels = discover_channels(output_dir, depth=1)
                    if not channels:
                        click.echo("Warning: No channels found", err=True)
                    else:
                        click.echo(f"Found {len(channels)} channel(s)")

                        # Regenerate TSV files for each channel
                        for rel_channel_dir, _channel_json_path in channels:
                            channel_dir = output_dir / rel_channel_dir
                            click.echo(f"  Regenerating TSVs for {rel_channel_dir}...")

                            try:
                                export = ExportService(channel_dir)
                                videos_tsv, playlists_tsv, authors_tsv = export.generate_all()
                                click.echo(f"    [ok] {rel_channel_dir}/{videos_tsv.name}")
                                click.echo(f"    [ok] {rel_channel_dir}/{playlists_tsv.name}")
                                click.echo(f"    [ok] {rel_channel_dir}/{authors_tsv.name}")
                            except Exception as e:
                                click.echo(f"    [error] Failed to regenerate {rel_channel_dir}: {e}", err=True)
                                continue

                        # Regenerate top-level channels.tsv
                        click.echo("  Regenerating channels.tsv...")
                        # Import here to avoid circular dependency
                        from annextube.cli.aggregate import aggregate
                        ctx.invoke(aggregate, directory=output_dir, depth=1, output=None, force=True)
                        click.echo("    [ok] channels.tsv")

                else:
                    # Single-channel mode
                    click.echo("Regenerating TSV files...")
                    export = ExportService(output_dir)
                    videos_tsv, playlists_tsv, authors_tsv = export.generate_all()
                    click.echo(f"  [ok] {videos_tsv.name}")
                    click.echo(f"  [ok] {playlists_tsv.name}")
                    click.echo(f"  [ok] {authors_tsv.name}")

            # Regenerate web UI
            if regenerate in ['web', 'all']:
                click.echo("Regenerating web UI...")

                # Check if frontend build exists
                if not FRONTEND_BUILD_DIR.exists():
                    click.echo(
                        f"Error: Frontend build not found at {FRONTEND_BUILD_DIR}",
                        err=True,
                    )
                    click.echo("Run 'cd frontend && npm run build' to build the frontend first.")
                    raise click.Abort()

                # Copy frontend to web directory
                if web_dir.exists():
                    shutil.rmtree(web_dir)
                shutil.copytree(FRONTEND_BUILD_DIR, web_dir)
                click.echo("  [ok] web/")

        except Exception as e:
            click.echo(f"Error regenerating: {e}", err=True)
            raise click.Abort() from e

    # Check if web directory exists after regeneration
    if not web_dir.exists():
        click.echo(
            f"Error: Web UI not found at {web_dir}. Run 'annextube generate-web' first.",
            err=True,
        )
        raise click.Abort()

    # Start watcher thread if enabled (only for single-channel archives)
    watcher_thread = None
    watcher = None
    if watch:
        if is_multi_channel:
            click.echo(
                "Info: Auto-watch disabled for multi-channel collections. "
                "Watch individual channels instead."
            )
        else:
            watcher = ArchiveWatcher(output_dir, web_dir, watch_interval)
            watcher_thread = Thread(target=watcher.watch, daemon=True)
            watcher_thread.start()
            click.echo(f"[ok] Watching for changes (interval: {watch_interval}s)")

    # Change to archive directory
    os.chdir(output_dir)

    # Create server with socket reuse enabled
    try:
        # Enable SO_REUSEADDR to allow binding to recently-used ports
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer((host, port), RangeHTTPRequestHandler) as httpd:
            click.echo()
            if is_multi_channel:
                click.echo(f"Serving multi-channel collection at http://{host}:{port}/")
            else:
                click.echo(f"Serving annextube archive at http://{host}:{port}/")
            click.echo(f"Directory: {output_dir}")
            click.echo(f"Web UI: http://{host}:{port}/web/")
            click.echo()
            click.echo("Features:")
            click.echo("  [ok] HTTP Range requests (video seeking enabled)")
            if watch and not is_multi_channel:
                click.echo(f"  [ok] Auto-regenerate TSVs on changes ({watch_interval}s interval)")
            click.echo()
            click.echo("Press Ctrl+C to stop")
            click.echo()

            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                click.echo("\n\nShutting down...")
                if watcher:
                    watcher.stop()

    except OSError as e:
        if e.errno == 98:  # Address already in use
            click.echo(f"Error: Port {port} is already in use. Try a different port with --port", err=True)
        else:
            click.echo(f"Error starting server: {e}", err=True)
        raise click.Abort() from e
