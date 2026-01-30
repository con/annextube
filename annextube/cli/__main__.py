"""CLI entry point for annextube."""

import sys
from pathlib import Path
from typing import Optional

import click

from annextube.lib.logging_config import setup_logging

# Version
__version__ = "0.1.0"


@click.group()
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to config file (default: .annextube/config.toml)",
)
@click.option(
    "--log-level",
    type=click.Choice(["debug", "info", "warning", "error", "critical"]),
    default="info",
    help="Log level",
)
@click.option("--json", "json_output", is_flag=True, help="JSON output mode")
@click.option("--quiet", is_flag=True, help="Suppress console output")
@click.version_option(version=__version__, prog_name="annextube")
@click.pass_context
def cli(
    ctx: click.Context,
    config: Optional[Path],
    log_level: str,
    json_output: bool,
    quiet: bool,
):
    """annextube - YouTube archive system using git-annex.

    Complete channel archival with metadata, comments, captions, and incremental updates.
    """
    # Setup logging
    logger = setup_logging(
        level=log_level,
        json_format=json_output,
        quiet=quiet,
    )

    # Store context
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["logger"] = logger
    ctx.obj["json_output"] = json_output


# Import commands
from annextube.cli.init import init
from annextube.cli.backup import backup
from annextube.cli.export import export
from annextube.cli.generate_web import generate_web
from annextube.cli.info import info
from annextube.cli.check import check

cli.add_command(init)
cli.add_command(backup)
cli.add_command(export)
cli.add_command(generate_web)
cli.add_command(info)
cli.add_command(check)


def main():
    """Main entry point."""
    try:
        cli(obj={})
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
