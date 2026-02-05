"""Init user config command for annextube."""

import click

from annextube.lib.config import get_user_config_path, save_user_config_template
from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)


@click.command("init-user-config")
def init_user_config():
    """Create user-wide configuration file template.

    Creates config file at platform-specific location:
    - Linux: ~/.config/annextube/config.toml
    - macOS: ~/Library/Application Support/annextube/config.toml
    - Windows: %APPDATA%/annextube/config.toml

    This file contains user-wide settings for authentication (cookies, API key),
    network settings (proxy, rate limiting), and global preferences.
    """
    try:
        config_path = save_user_config_template()
        click.echo(f"[ok] Created user config template: {config_path}")
        click.echo()
        click.echo("Edit this file to configure:")
        click.echo("  - YouTube cookies (for private/age-restricted content)")
        click.echo("  - API key (alternative to YOUTUBE_API_KEY env var)")
        click.echo("  - Proxy settings")
        click.echo("  - Rate limiting")
        click.echo()
        click.echo("Example cookie configuration:")
        click.echo('  cookies_file = "~/.config/annextube/cookies/youtube.txt"')
        click.echo("  # or")
        click.echo('  cookies_from_browser = "firefox"')
        click.echo()
        click.echo("Security note:")
        click.echo("  - Never commit this file to version control if it contains secrets!")
        click.echo("  - Use environment variables (YOUTUBE_API_KEY, ANNEXTUBE_COOKIES_FILE)")
        click.echo("    for sensitive values in CI/CD environments")

    except FileExistsError as e:
        config_path = get_user_config_path()
        click.echo(f"User config already exists: {config_path}", err=True)
        click.echo("Delete it first to regenerate, or edit directly.", err=True)
        raise click.Abort() from e
    except Exception as e:
        logger.error(f"Failed to create user config: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort() from e
