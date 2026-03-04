"""Build search index command for annextube."""

import asyncio
from pathlib import Path

import click

from annextube.lib.archive_discovery import discover_annextube
from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)


@click.command("build-search-index")
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Archive directory (default: current directory)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force full rebuild (ignore incremental cache)",
)
@click.pass_context
def build_search_index(ctx: click.Context, output_dir: Path, force: bool):
    """Build Pagefind caption search index.

    Indexes VTT caption files to enable full-text search across
    video captions in the web browser.  Curated captions are
    preferred; original YouTube captions serve as a fallback.

    Requires the 'search' extras: pip install 'annextube[search]'

    Examples:

        # Build index for current archive
        annextube build-search-index

        # Build for specific archive
        annextube build-search-index --output-dir ~/my-archive

        # Force full rebuild
        annextube build-search-index --force
    """
    archive_info = discover_annextube(output_dir)
    if archive_info is None:
        click.echo(
            f"Error: {output_dir} is not an annextube archive. "
            "Run 'annextube init' first.",
            err=True,
        )
        raise click.Abort()

    try:
        from pagefind.index import PagefindIndex  # noqa: F401
    except ImportError as exc:
        click.echo(
            "Error: pagefind package required for search index. "
            "Install with: pip install 'annextube[search]'",
            err=True,
        )
        raise click.Abort() from exc

    from annextube.services.search_index import build_caption_index

    click.echo("Building caption search index...")
    stats = asyncio.run(build_caption_index(output_dir, force=force))

    if stats.videos_indexed == 0 and stats.chunks_created == 0:
        click.echo("  [ok] Search index up to date (no changes)")
    else:
        size_mb = stats.index_size_bytes / (1024 * 1024)
        click.echo(
            f"  [ok] {stats.videos_indexed} videos "
            f"({stats.videos_curated} curated, {stats.videos_original} original), "
            f"{stats.chunks_created:,} chunks, {size_mb:.1f} MB"
        )
    if stats.videos_skipped:
        click.echo(f"  (skipped {stats.videos_skipped} videos without captions)")
