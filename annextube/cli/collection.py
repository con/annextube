"""CLI commands for multi-channel collection management."""

import sys
from pathlib import Path

import click

from annextube.lib.logging_config import get_logger
from annextube.services.collection import (
    add_channel,
    backup_all,
)

logger = get_logger(__name__)


@click.group()
def collection():
    """Manage multi-channel collections.

    Commands for adding channels to a collection and performing
    batch backups across all channels in the collection.
    """


@collection.command()
@click.argument("url")
@click.option(
    "--name",
    default=None,
    help="Override the subdataset directory name (default: derived from @handle)",
)
@click.option(
    "--no-backup",
    is_flag=True,
    default=False,
    help="Skip the initial backup (init only)",
)
@click.option(
    "--output-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd(),
    help="Collection directory (default: current directory)",
)
@click.pass_context
def add(ctx: click.Context, url: str, name: str | None, no_backup: bool, output_dir: Path):
    """Add a new YouTube channel to the collection.

    Creates a DataLad subdataset, initializes annextube, and optionally
    performs the initial backup.

    Examples:

        annextube collection add https://www.youtube.com/@ChannelName

        annextube collection add https://www.youtube.com/@ChannelName --name my-channel

        annextube collection add https://www.youtube.com/@ChannelName --no-backup
    """
    try:
        add_channel(
            collection_dir=output_dir,
            url=url,
            name=name,
            no_backup=no_backup,
        )
    except (ValueError, RuntimeError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@collection.command("backup")
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd(),
    required=False,
)
@click.option(
    "--parallel",
    type=int,
    default=1,
    show_default=True,
    help="Update up to N channels concurrently",
)
@click.option(
    "--save",
    is_flag=True,
    default=False,
    help="Save changes at collection level after all updates",
)
@click.option(
    "--push",
    is_flag=True,
    default=False,
    help="Push to configured remote after updates (requires --save)",
)
@click.pass_context
def backup_cmd(ctx: click.Context, directory: Path, parallel: int, save: bool, push: bool):
    """Batch update all channels in a collection.

    Discovers channel subdatasets and runs backup + export on each one.
    Channels that fail are logged and skipped; remaining channels continue.

    Examples:

        annextube collection backup

        annextube collection backup --parallel 4 --save

        annextube collection backup /path/to/collection --save --push
    """
    if push and not save:
        click.echo("Error: --push requires --save", err=True)
        sys.exit(1)

    try:
        results = backup_all(
            collection_dir=directory,
            parallel=parallel,
            save=save,
            push=push,
        )
    except (ValueError, RuntimeError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    # Exit 1 if any channel failed
    if results and any(not r.success for r in results):
        sys.exit(1)
