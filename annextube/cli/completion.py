"""Shell completion command for annextube."""

import os

import click
from click.shell_completion import get_completion_class

SUPPORTED_SHELLS = ("bash", "zsh", "fish")


@click.command()
@click.argument("shell", required=False, type=click.Choice(SUPPORTED_SHELLS))
def completion(shell: str | None) -> None:
    """Output shell completion script.

    Auto-detects the current shell when SHELL argument is omitted.

    To enable completions, add to your shell profile:

    \b
        # bash (~/.bashrc)
        eval "$(annextube completion bash)"
    \b
        # zsh (~/.zshrc)
        eval "$(annextube completion zsh)"
    \b
        # fish (~/.config/fish/config.fish)
        annextube completion fish | source
    """
    if shell is None:
        shell = _detect_shell()
        if shell is None:
            click.echo(
                "Error: Could not detect shell from $SHELL. "
                f"Specify one of: {', '.join(SUPPORTED_SHELLS)}",
                err=True,
            )
            raise SystemExit(1)

    comp_cls = get_completion_class(shell)
    if comp_cls is None:
        click.echo(f"Error: Unsupported shell: {shell}", err=True)
        raise SystemExit(1)

    # Get the parent CLI group (annextube) from the current context
    ctx = click.get_current_context()
    cli = ctx.find_root().command

    comp = comp_cls(cli, {}, "annextube", "_ANNEXTUBE_COMPLETE")
    click.echo(comp.source())


def _detect_shell() -> str | None:
    """Detect the current shell from $SHELL environment variable.

    Returns:
        Shell name (bash, zsh, fish) or None if unrecognized.
    """
    shell_path = os.environ.get("SHELL", "")
    shell_name = os.path.basename(shell_path)
    if shell_name in SUPPORTED_SHELLS:
        return shell_name
    return None
