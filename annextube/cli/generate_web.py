"""Generate web command for annextube."""

import re
import shutil
from pathlib import Path

import click

from annextube._version import __version__
from annextube.lib.archive_discovery import discover_annextube
from annextube.lib.cli_options import output_dir_option
from annextube.lib.logging_config import get_logger
from annextube.services.export import ExportService

logger = get_logger(__name__)

# Matches the quoted semver-like string `_inject_version()` writes in place
# of FRONTEND_VERSION_PLACEHOLDER (an optional "v" prefix is tolerated for
# forward/backward compatibility, though the placeholder itself has none).
_BUNDLED_VERSION_RE = re.compile(r'"v?(\d+\.\d+\.\d+(?:[.\-][0-9A-Za-z]+)*)"')

# Placeholder baked into the Vite build (must match frontend/vite.config.ts)
FRONTEND_VERSION_PLACEHOLDER = "0.0.0-unknown"

# Path to frontend build (relative to this file)
FRONTEND_BUILD_DIR = Path(__file__).parent.parent.parent / "web"

# Frontend sources -- only present in a development checkout
FRONTEND_SRC_DIR = Path(__file__).parent.parent.parent / "frontend" / "src"


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
        # Vite inlines the placeholder in the JS bundle.  Depending on
        # how the template references it, the bundle may contain either
        # the bare string "0.0.0-unknown" or "v0.0.0-unknown".  Replace
        # both patterns (the bare form first to avoid double-replacing).
        new_content = content.replace(
            FRONTEND_VERSION_PLACEHOLDER,
            version,
        )
        if new_content != content:
            js_file.write_text(new_content)
            logger.debug(f"Injected version v{version} into {js_file.name}")
            replaced = True
    return replaced


def _warn_if_bundle_stale() -> None:
    """Warn when a development checkout's built ``web/`` predates its sources.

    ``FRONTEND_BUILD_DIR`` is git-ignored and produced by ``hatch_build.py``
    at install time, not on later source edits.  Checking out a branch that
    changes ``frontend/src/`` therefore leaves the previously built bundle
    in place, and ``generate-web`` silently deploys the *old* UI -- the
    archive then lacks the frontend changes it was expected to carry.

    Only meaningful where ``frontend/src/`` exists; an installed wheel has
    no sources to compare against and is skipped.
    """
    if not FRONTEND_SRC_DIR.is_dir():
        return

    bundles = list((FRONTEND_BUILD_DIR / "assets").glob("*.js"))
    if not bundles:
        return
    built_at = max(f.stat().st_mtime for f in bundles)

    newer = sorted(
        (
            p
            for p in FRONTEND_SRC_DIR.rglob("*")
            if p.is_file() and p.stat().st_mtime > built_at
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not newer:
        return

    try:
        example = newer[0].relative_to(FRONTEND_SRC_DIR.parent.parent)
    except ValueError:  # pragma: no cover - defensive
        example = newer[0]
    click.echo(
        f"  Warning: web/ bundle is older than {len(newer)} frontend "
        f"source file(s) (newest: {example}).",
        err=True,
    )
    click.echo(
        "  Run 'cd frontend && npm run build' first, or the previously "
        "built UI is deployed.",
        err=True,
    )


def deploy_frontend(web_dir: Path) -> None:
    """Copy the built frontend to *web_dir* and inject the annextube version.

    This is the single code-path used by both ``generate-web`` and
    ``serve --regenerate``.  It:

    1. Verifies that the frontend build exists (and warns when it is
       older than the frontend sources of a development checkout).
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

    _warn_if_bundle_stale()

    # Preserve web/pagefind/ if it exists (may be a DataLad subdataset
    # with the search index that should survive frontend re-deploys).
    pagefind_dir = web_dir / "pagefind"
    pagefind_backup = None
    if pagefind_dir.exists():
        pagefind_backup = web_dir.parent / ".pagefind_backup"
        if pagefind_backup.exists():
            shutil.rmtree(pagefind_backup)
        pagefind_dir.rename(pagefind_backup)

    if web_dir.exists():
        shutil.rmtree(web_dir)
    shutil.copytree(FRONTEND_BUILD_DIR, web_dir)

    # Restore pagefind directory
    if pagefind_backup is not None and pagefind_backup.exists():
        target = web_dir / "pagefind"
        if target.exists():
            shutil.rmtree(target)
        pagefind_backup.rename(target)

    if _inject_version(web_dir, __version__):
        click.echo(f"  [ok] web/ (v{__version__})")
    else:
        click.echo(
            f"  Warning: could not inject version v{__version__} "
            f"(placeholder '{FRONTEND_VERSION_PLACEHOLDER}' not found in JS bundle)",
            err=True,
        )


def _extract_version_from_bundle(web_dir: Path) -> str | None:
    """Read the annextube version already baked into an existing web/ bundle.

    Scans ``web_dir/assets/*.js`` for the first quoted semver-like string --
    the same shape ``_inject_version()`` writes in place of
    ``FRONTEND_VERSION_PLACEHOLDER``.

    Returns:
        The version string (without a leading "v"), or None if there is no
        assets/ directory or no version-like string could be found.
    """
    assets_dir = web_dir / "assets"
    if not assets_dir.exists():
        return None

    for js_file in sorted(assets_dir.glob("*.js")):
        match = _BUNDLED_VERSION_RE.search(js_file.read_text())
        if match:
            return match.group(1)
    return None


def check_and_regenerate_web(archive_path: Path) -> bool:
    """Regenerate web/ if it was built with a different annextube version.

    Used by ``annextube backup`` so automated update workflows (cron jobs,
    CI) keep the archive's web UI in sync with the installed annextube
    version, without a manual ``generate-web --force`` after every upgrade.

    Returns:
        True if regeneration happened; False if web/ does not exist, its
        version could not be determined, or it already matches
        ``__version__``.
    """
    web_dir = archive_path / "web"
    if not web_dir.exists():
        return False

    stored_version = _extract_version_from_bundle(web_dir)
    if stored_version is None or stored_version == __version__:
        return False

    logger.info(f"web/ version changed: {stored_version} -> {__version__}, regenerating")
    click.echo(f"Regenerating web/ (v{stored_version} -> v{__version__})...")
    deploy_frontend(web_dir)
    return True


def _build_search_index(archive_path: Path, force: bool = False) -> None:
    """Build the Pagefind caption search index."""
    from annextube.cli.build_search_index import require_pagefind_and_build

    require_pagefind_and_build(archive_path, force=force)


@click.command()
@output_dir_option()
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing web directory",
)
@click.option(
    "--search-index",
    is_flag=True,
    default=False,
    help="Build Pagefind caption search index (requires 'annextube[search]')",
)
@click.option(
    "--force-reindex",
    is_flag=True,
    default=False,
    help="Force full search index rebuild (ignore incremental cache)",
)
@click.pass_context
def generate_web(
    ctx: click.Context,
    output_dir: Path,
    force: bool,
    search_index: bool,
    force_reindex: bool,
):
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

        # Build with caption search index
        annextube generate-web --force --search-index

        # Force full re-index
        annextube generate-web --force --search-index --force-reindex
    """
    logger.info("Starting web browser generation")

    # Discover archive type
    archive_info = discover_annextube(output_dir)

    # If not recognized but has channel.json files, auto-aggregate first
    if archive_info is None:
        from annextube.cli.aggregate import discover_channels

        channels = discover_channels(output_dir, depth=1)
        if channels:
            click.echo(
                f"No channels.tsv found, but {len(channels)} channel(s) "
                "discovered. Running aggregate..."
            )
            from annextube.cli.aggregate import aggregate as aggregate_cmd

            ctx.invoke(aggregate_cmd, directory=output_dir, depth=1, output=None, force=True)
            # Re-discover after aggregate
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

        # Optionally build caption search index
        if search_index:
            _build_search_index(output_dir, force=force_reindex)

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
