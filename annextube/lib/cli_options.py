"""Shared Click option definitions.

Consolidates option boilerplate that would otherwise repeat verbatim across
CLI commands.  Use as decorators, e.g.::

    from annextube.lib.cli_options import output_dir_option

    @click.command()
    @output_dir_option()
    def my_cmd(output_dir: Path) -> None:
        ...
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import click

F = TypeVar("F", bound=Callable[..., Any])


def output_dir_option(
    *,
    short: bool = False,
    help: str = "Archive directory (default: current directory)",
    **click_kwargs: Any,
) -> Callable[[F], F]:
    """Standard ``--output-dir`` option accepted by most annextube commands.

    Args:
        short: If True, also expose the ``-o`` short flag.
        help: Override the help text (defaults to the standard phrasing).
        **click_kwargs: Additional keyword arguments forwarded to
            ``click.option``.  Explicit keys here win over the defaults —
            useful for e.g. ``default=None`` or ``exists=True``.

    Returns:
        A decorator applying the option.
    """
    names: tuple[str, ...] = ("--output-dir", "-o") if short else ("--output-dir",)
    kwargs: dict[str, Any] = {
        "type": click.Path(path_type=Path),
        "default": Path.cwd(),
        "help": help,
    }
    kwargs.update(click_kwargs)
    return click.option(*names, **kwargs)
