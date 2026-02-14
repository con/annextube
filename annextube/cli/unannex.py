"""Unannex command - thin wrapper around git-annex unannex."""

import subprocess
from pathlib import Path

import click

from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)


@click.command()
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Archive directory (default: current directory)",
)
@click.option(
    "--update-gitattributes/--no-update-gitattributes",
    default=True,
    help="Set annex.largefiles=nothing for unannexed paths in .gitattributes",
)
@click.option("--dry-run", is_flag=True, help="Preview which annexed files would be unannexed")
@click.argument("paths", nargs=-1, type=click.Path())
@click.pass_context
def unannex(
    ctx: click.Context,
    output_dir: Path,
    update_gitattributes: bool,
    dry_run: bool,
    paths: tuple[str, ...],
):
    """Unannex files, converting them from git-annex symlinks to regular files.

    Runs `git annex unannex` on the specified paths (or all annexed files if
    none given). Optionally updates .gitattributes so the files stay out of
    the annex on future commits.
    """
    output_dir = output_dir.resolve()

    if dry_run:
        # Preview: list annexed files that would be unannexed
        cmd = ["git", "annex", "find"] + list(paths)
        result = subprocess.run(cmd, cwd=output_dir, capture_output=True, encoding="utf-8")
        if result.returncode != 0:
            click.echo(f"Error: {result.stderr.strip()}", err=True)
            raise SystemExit(1)
        files = result.stdout.strip()
        if files:
            click.echo("Would unannex:")
            click.echo(files)
        else:
            click.echo("No annexed files found matching the given paths.")
        return

    # Run git annex unannex
    cmd = ["git", "annex", "unannex"] + list(paths)
    logger.info(f"Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=output_dir)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)

    if update_gitattributes:
        # Determine which paths to mark as largefiles=nothing
        targets = list(paths) if paths else ["."]
        gitattributes = output_dir / ".gitattributes"
        existing = gitattributes.read_text() if gitattributes.exists() else ""
        additions = []
        for target in targets:
            line = f"{target} annex.largefiles=nothing"
            if line not in existing:
                additions.append(line)
        if additions:
            with open(gitattributes, "a") as f:
                for line in additions:
                    f.write(f"{line}\n")
            click.echo(f"Updated .gitattributes with {len(additions)} largefiles=nothing rule(s)")
