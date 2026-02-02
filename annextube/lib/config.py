"""Configuration file handling for annextube.

Loads configuration from .annextube/config.toml or ~/.config/annextube/config.toml
in TOML format (similar to mykrok pattern).

User-wide configuration (authentication, network settings) is loaded from
platform-specific config directory using platformdirs.
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from platformdirs import user_config_dir

# Handle tomli/tomllib compatibility
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """Configuration for a YouTube source (channel or playlist)."""

    url: str
    type: str  # 'channel' or 'playlist'
    enabled: bool = True
    include_playlists: str = "none"  # "all", "none", or regex pattern for auto-discovery
    exclude_playlists: Optional[str] = None  # Regex pattern to exclude playlists
    include_podcasts: str = "none"  # "all", "none", or regex pattern for podcast auto-discovery


@dataclass
class ComponentsConfig:
    """Configuration for what components to backup."""

    videos: bool = False  # Track URLs only by default
    metadata: bool = True
    comments_depth: Optional[int] = None  # Maximum comments to fetch (None = unlimited, 0 = disabled)
    captions: bool = True
    thumbnails: bool = True
    caption_languages: str = ".*"  # Regex pattern for caption languages (default: all)
    auto_translated_captions: List[str] = field(default_factory=list)  # Auto-translated languages to download (empty = only auto-generated)


@dataclass
class FiltersConfig:
    """Configuration for filtering videos."""

    limit: Optional[int] = None  # Limit to N most recent videos
    date_start: Optional[str] = None  # ISO 8601 date
    date_end: Optional[str] = None  # ISO 8601 date
    license: Optional[str] = None  # 'standard' or 'creativeCommon'
    min_duration: Optional[int] = None  # Seconds
    max_duration: Optional[int] = None  # Seconds
    min_views: Optional[int] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class OrganizationConfig:
    """Configuration for repository organization and file paths."""

    video_path_pattern: str = "{year}/{month}/{date}_{sanitized_title}"  # Default: hierarchical by year/month
    channel_path_pattern: str = "{channel_id}"
    playlist_path_pattern: str = "{playlist_id}"
    video_filename: str = "video.mkv"  # Filename for video file within video directory
    playlist_prefix_width: int = 4  # Zero-padded width for playlist symlink prefixes (e.g., 0001)
    playlist_prefix_separator: str = "_"  # Separator between index and path (underscore, not hyphen)


@dataclass
class UserConfig:
    """User-wide configuration (authentication, network, global preferences).

    Loaded from platform-specific user config directory:
    - Linux: ~/.config/annextube/config.toml
    - macOS: ~/Library/Application Support/annextube/config.toml
    - Windows: %APPDATA%/annextube/config.toml
    """

    # Authentication
    cookies_file: Optional[str] = None  # Path to Netscape cookies.txt
    cookies_from_browser: Optional[str] = None  # e.g., "firefox", "chrome:Profile 1"
    api_key: Optional[str] = None  # YouTube Data API key (fallback if env var not set)

    # Network settings
    proxy: Optional[str] = None  # e.g., "socks5://127.0.0.1:9050"
    limit_rate: Optional[str] = None  # e.g., "500K" - bandwidth limit
    sleep_interval: Optional[int] = None  # Min seconds between downloads
    max_sleep_interval: Optional[int] = None  # Max seconds between downloads

    # Advanced
    ytdlp_extra_opts: List[str] = field(default_factory=list)  # Extra CLI options for yt-dlp

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserConfig":
        """Create UserConfig from dictionary (loaded from TOML)."""
        return cls(
            cookies_file=data.get("cookies_file"),
            cookies_from_browser=data.get("cookies_from_browser"),
            api_key=data.get("api_key"),
            proxy=data.get("proxy"),
            limit_rate=data.get("limit_rate"),
            sleep_interval=data.get("sleep_interval"),
            max_sleep_interval=data.get("max_sleep_interval"),
            ytdlp_extra_opts=data.get("ytdlp_extra_opts", []),
        )


@dataclass
class Config:
    """Main configuration for annextube."""

    # User-wide settings (loaded from user config dir)
    user: UserConfig = field(default_factory=UserConfig)

    # Archive-specific settings
    sources: List[SourceConfig] = field(default_factory=list)
    components: ComponentsConfig = field(default_factory=ComponentsConfig)
    filters: FiltersConfig = field(default_factory=FiltersConfig)
    organization: OrganizationConfig = field(default_factory=OrganizationConfig)

    # Convenience properties for backward compatibility
    @property
    def api_key(self) -> Optional[str]:
        """Get API key from user config."""
        return self.user.api_key

    @property
    def cookies_file(self) -> Optional[str]:
        """Get cookies file path from user config."""
        return self.user.cookies_file

    @property
    def cookies_from_browser(self) -> Optional[str]:
        """Get cookies browser from user config."""
        return self.user.cookies_from_browser

    @staticmethod
    def _normalize_include_podcasts(value: Any) -> str:
        """Normalize include_podcasts value from various formats to canonical string."""
        if isinstance(value, bool):
            # Backward compatibility: bool → "all" or "none"
            return "all" if value else "none"
        return str(value) if value else "none"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary (loaded from TOML)."""
        sources = [
            SourceConfig(
                url=s["url"],
                type=s.get("type", "channel"),
                enabled=s.get("enabled", True),
                include_playlists=s.get("include_playlists", "none"),
                exclude_playlists=s.get("exclude_playlists"),
                include_podcasts=cls._normalize_include_podcasts(s.get("include_podcasts", "none")),
            )
            for s in data.get("sources", [])
        ]

        components_data = data.get("components", {})

        # Handle backward compatibility: comments: bool → comments_depth: Optional[int]
        comments_depth = components_data.get("comments_depth", None)  # None = unlimited (new default)
        if "comments" in components_data and "comments_depth" not in components_data:
            # Legacy config with comments: bool
            comments_depth = None if components_data["comments"] else 0  # None = unlimited

        components = ComponentsConfig(
            videos=components_data.get("videos", False),
            metadata=components_data.get("metadata", True),
            comments_depth=comments_depth,
            captions=components_data.get("captions", True),
            thumbnails=components_data.get("thumbnails", True),
            caption_languages=components_data.get("caption_languages", ".*"),
            auto_translated_captions=components_data.get("auto_translated_captions", []),
        )

        filters_data = data.get("filters", {})
        filters = FiltersConfig(
            limit=filters_data.get("limit"),
            date_start=filters_data.get("date_start"),
            date_end=filters_data.get("date_end"),
            license=filters_data.get("license"),
            min_duration=filters_data.get("min_duration"),
            max_duration=filters_data.get("max_duration"),
            min_views=filters_data.get("min_views"),
            tags=filters_data.get("tags", []),
        )

        organization_data = data.get("organization", {})
        organization = OrganizationConfig(
            video_path_pattern=organization_data.get(
                "video_path_pattern", "{date}_{sanitized_title}"
            ),
            channel_path_pattern=organization_data.get("channel_path_pattern", "{channel_id}"),
            playlist_path_pattern=organization_data.get("playlist_path_pattern", "{playlist_id}"),
            video_filename=organization_data.get("video_filename", "video.mkv"),
            playlist_prefix_width=organization_data.get("playlist_prefix_width", 4),
            playlist_prefix_separator=organization_data.get("playlist_prefix_separator", "_"),
        )

        return cls(
            sources=sources,
            components=components,
            filters=filters,
            organization=organization,
        )


def get_user_config_path() -> Path:
    """Get user config file path using platformdirs.

    Returns:
        Path to user config file (may not exist)

    Examples:
        - Linux: ~/.config/annextube/config.toml
        - macOS: ~/Library/Application Support/annextube/config.toml
        - Windows: %APPDATA%/annextube/config.toml
    """
    config_dir = Path(user_config_dir("annextube", appauthor=False))
    return config_dir / "config.toml"


def load_user_config() -> UserConfig:
    """Load user-wide configuration from platform-specific config directory.

    Environment variables override user config file settings:
    - ANNEXTUBE_COOKIES_FILE
    - ANNEXTUBE_COOKIES_FROM_BROWSER
    - YOUTUBE_API_KEY
    - ANNEXTUBE_PROXY

    Returns:
        UserConfig object (with defaults if file doesn't exist)
    """
    config_path = get_user_config_path()

    if not config_path.exists():
        # No user config file - return defaults
        logger.debug(f"No user config found at {config_path}, using defaults")
        user_config = UserConfig()
    else:
        # Load user config
        logger.debug(f"Loading user config from {config_path}")
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
            user_config = UserConfig.from_dict(data)
            logger.info(f"Loaded user config from {config_path}")
        except Exception as e:
            # Log warning but don't fail - use defaults
            logger.warning(f"Failed to load user config from {config_path}: {e}")
            user_config = UserConfig()

    # Override with environment variables (highest precedence)
    cookies_file = os.environ.get('ANNEXTUBE_COOKIES_FILE')
    if cookies_file:
        user_config.cookies_file = cookies_file
        logger.debug(f"Using cookies file from env: {cookies_file}")

    cookies_from_browser = os.environ.get('ANNEXTUBE_COOKIES_FROM_BROWSER')
    if cookies_from_browser:
        user_config.cookies_from_browser = cookies_from_browser
        logger.debug(f"Using cookies from browser: {cookies_from_browser}")

    api_key = os.environ.get('YOUTUBE_API_KEY')
    if api_key:
        user_config.api_key = api_key
        logger.debug("Using API key from YOUTUBE_API_KEY env var")

    proxy = os.environ.get('ANNEXTUBE_PROXY')
    if proxy:
        user_config.proxy = proxy
        logger.debug(f"Using proxy from env: {proxy}")

    return user_config


def load_config(config_path: Optional[Path] = None, repo_path: Optional[Path] = None) -> Config:
    """Load configuration from TOML files (user + archive).

    Loads user-wide config first (authentication, network settings),
    then archive-specific config (sources, components, filters).

    Config hierarchy (precedence: highest to lowest):
    1. Environment variables (YOUTUBE_API_KEY, ANNEXTUBE_COOKIES_FILE, etc.)
    2. Archive config (.annextube/config.toml)
    3. User config (platform-specific user config dir)
    4. Built-in defaults

    Args:
        config_path: Optional path to archive config file. If not provided, searches:
            1. {repo_path}/.annextube/config.toml (if repo_path provided)
            2. .annextube/config.toml (current directory)
        repo_path: Optional path to repository root (for searching config file)

    Returns:
        Config object with merged user + archive settings

    Raises:
        FileNotFoundError: If no archive config file found
        ValueError: If config file is invalid
    """
    # Step 1: Load user-wide config (authentication, network, etc.)
    user_config = load_user_config()

    # Step 2: Load archive-specific config (sources, components, filters)
    if config_path is None:
        # Search for archive config file
        search_paths = []

        # If repo_path provided, search there first
        if repo_path is not None:
            search_paths.append(Path(repo_path) / ".annextube" / "config.toml")

        # Then try current directory
        search_paths.append(Path.cwd() / ".annextube" / "config.toml")

        for path in search_paths:
            if path.exists():
                config_path = path
                break
        else:
            raise FileNotFoundError(
                "No archive config file found. Expected .annextube/config.toml"
            )

    # Load archive config
    logger.debug(f"Loading archive config from {config_path}")
    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse archive config {config_path}: {e}")

    # Parse archive-specific sections
    config = Config.from_dict(data)

    # Step 3: Merge user config into main config
    config.user = user_config

    logger.info(f"Loaded config: archive={config_path}, user={get_user_config_path()}")
    return config


def generate_config_template(urls: list[str] = None, enable_videos: bool = True,
                            comments_depth: Optional[int] = None, enable_captions: bool = True,
                            enable_thumbnails: bool = True, limit: Optional[int] = None,
                            include_playlists: str = "none",
                            video_path_pattern: str = "{year}/{month}/{date}_{sanitized_title}") -> str:
    """Generate a template configuration file in TOML format.

    Args:
        urls: List of YouTube channel/playlist URLs to add
        enable_videos: Enable video downloading (default: True)
        comments_depth: Comments to fetch (None=unlimited, 0=disabled, default: None)
        enable_captions: Enable captions (default: True)
        enable_thumbnails: Enable thumbnails (default: True)
        limit: Limit to N most recent videos (default: None = no limit)
        include_playlists: Playlist inclusion ("none", "all", or regex pattern, default: "none")
        video_path_pattern: Path pattern for video directories (default: "{year}/{month}/{date}_{sanitized_title}")

    Returns:
        TOML configuration template as string
    """
    # Convert values to TOML format
    videos_str = str(enable_videos).lower()
    captions_str = str(enable_captions).lower()
    thumbnails_str = str(enable_thumbnails).lower()

    # Build organization section separately to avoid f-string brace escaping issues
    organization_section = f'''# Repository organization and file paths
[organization]
video_path_pattern = "{video_path_pattern}"  # Path pattern for videos (video_id tracked in TSV)
# Available placeholders:
#   {{{{year}}}} - Publication year (YYYY)
#   {{{{month}}}} - Publication month (MM)
#   {{{{date}}}} - Publication date (YYYY-MM-DD)
#   {{{{video_id}}}} - YouTube video ID (optional, tracked in videos.tsv)
#   {{{{sanitized_title}}}} - Video title (filesystem-safe, hyphens for words)
#   {{{{channel_id}}}} - Channel ID
#   {{{{channel_name}}}} - Channel name (sanitized)
# Examples:
#   "{{{{year}}}}/{{{{month}}}}/{{{{date}}}}_{{{{sanitized_title}}}}" - Hierarchical by year/month (default)
#   "{{{{date}}}}_{{{{sanitized_title}}}}" - Flat layout with date + title
#   "{{{{date}}}}_{{{{video_id}}}}_{{{{sanitized_title}}}}" - Include ID
#   "{{{{video_id}}}}" - Just video ID (compact)

channel_path_pattern = "{{channel_id}}"  # Path pattern for channels
playlist_path_pattern = "{{playlist_id}}"  # Path pattern for playlists (uses sanitized name in practice)

video_filename = "video.mkv"  # Filename for video file (use .mkv for best compatibility)

# Playlist organization
playlist_prefix_width = 4  # Zero-padding width for playlist symlinks (e.g., 0001_, 0023_)
                           # Supports playlists up to 10^width - 1 videos
                           # 4 digits = up to 9999 videos per playlist

playlist_prefix_separator = "_"  # Separator between index and path (underscore, not hyphen)
                                 # Example: 0001_2020-01-10_video-title (not 0001-2020-01-10...)
'''

    # Handle comments_depth: None means don't set it (use default = unlimited)
    if comments_depth is None:
        comments_str = "# comments_depth = 10000  # Uncomment to limit (None = unlimited)"
    else:
        comments_str = f"comments_depth = {comments_depth}"

    # Generate sources section
    if urls:
        sources_section = ""
        for url in urls:
            # Detect if playlist or channel
            url_type = "playlist" if ("playlist?" in url or "list=" in url) else "channel"
            playlist_line = f'\ninclude_playlists = "{include_playlists}"' if url_type == "channel" and include_playlists != "none" else ""
            sources_section += f'''
[[sources]]
url = "{url}"
type = "{url_type}"
enabled = true{playlist_line}
'''
        sources_section += '''
# Add more sources by adding [[sources]] sections above
'''
    else:
        # No URLs provided - show examples only
        sources_section = '''
# Sources to backup (channels or playlists)
# Add [[sources]] sections below for each channel/playlist

# Example: Channel
# [[sources]]
# url = "https://www.youtube.com/@channel"
# type = "channel"
# enabled = true

# Example: Playlist
# [[sources]]
# url = "https://www.youtube.com/playlist?list=PLxxx"
# type = "playlist"
# enabled = true
'''

    # Build filters section
    if limit is not None:
        filters_section = f'''
# Filters for selective archival
[filters]
limit = {limit}  # Limit to {limit} most recent videos (by upload date, newest first)
'''
    else:
        filters_section = '''
# Filters for selective archival
[filters]
# limit = 10  # Uncomment to limit to N most recent videos (by upload date, newest first)
'''

    return f'''# annextube Configuration File
# This file configures sources, components, and filters for YouTube archival

# YouTube Data API v3 key (REQUIRED)
# Get from: https://console.cloud.google.com/apis/credentials
# IMPORTANT: Set via environment variable, DO NOT store in this file!
#
#   export YOUTUBE_API_KEY="your-api-key-here"
#
# Never commit API keys to version control!
{sources_section}
# Optional playlist/podcast discovery settings (for channel sources):
# include_playlists = "all"  # Auto-discover and backup ALL playlists from this channel
# include_playlists = ".*tutorial.*"  # Only playlists matching regex pattern
# exclude_playlists = ".*shorts.*|.*old.*"  # Exclude playlists matching regex
# include_podcasts = "all"  # Auto-discover ALL podcasts from channel's Podcasts tab
# include_podcasts = ".*interview.*"  # Only podcasts matching regex pattern

# Components to backup
[components]
videos = {videos_str}           # Track URLs only (no video downloads) - saves storage
metadata = true          # Fetch video metadata
{comments_str}           # Comments: None = unlimited (fetches ALL, incrementally)
                         #           0 = disabled
                         #           N = limit to N comments
                         # Note: Incremental - merges new comments with existing
captions = {captions_str}          # Fetch captions matching language filter
thumbnails = {thumbnails_str}        # Download thumbnails

caption_languages = ".*"  # Regex pattern for caption languages to download
                          # Examples:
                          #   ".*" - All available languages (default)
                          #   "en.*" - All English variants (en, en-US, en-GB, etc.)
                          #   "en|es|fr" - English, Spanish, French only
                          #   "en-US" - US English only

{organization_section}{filters_section}
# Optional date range filter
# date_start = "2024-01-01"  # ISO 8601 date
# date_end = "2024-12-31"

# Optional license filter
# license = "creativeCommon"  # or "standard"

# Optional duration filters (in seconds)
# min_duration = 60    # Minimum 1 minute
# max_duration = 3600  # Maximum 1 hour

# Optional view count filter
# min_views = 1000

# Optional tags filter (OR logic)
# tags = ["python", "tutorial"]
'''


def save_config_template(config_dir: Path, urls: list[str] = None,
                        enable_videos: bool = True, comments_depth: Optional[int] = None,
                        enable_captions: bool = True, enable_thumbnails: bool = True,
                        limit: Optional[int] = None, include_playlists: str = "none",
                        video_path_pattern: str = "{year}/{month}/{date}_{sanitized_title}") -> Path:
    """Save configuration template to directory.

    Args:
        config_dir: Directory to save config template (e.g., .annextube/)
        urls: List of YouTube channel/playlist URLs to add
        enable_videos: Enable video downloading (default: True)
        comments_depth: Comments to fetch (None=unlimited, 0=disabled, default: None)
        enable_captions: Enable captions (default: True)
        enable_thumbnails: Enable thumbnails (default: True)
        limit: Limit to N most recent videos (default: None = no limit)
        include_playlists: Playlist inclusion ("none", "all", or regex pattern, default: "none")
        video_path_pattern: Path pattern for video directories (default: "{year}/{month}/{date}_{sanitized_title}")

    Returns:
        Path to created config file
    """
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.toml"

    with open(config_path, "w") as f:
        f.write(generate_config_template(urls, enable_videos, comments_depth, enable_captions,
                                        enable_thumbnails, limit, include_playlists, video_path_pattern))

    return config_path


def generate_user_config_template() -> str:
    """Generate user-wide configuration template.

    Returns:
        TOML configuration template as string
    """
    return '''# annextube User Configuration
# This file contains user-wide settings (authentication, network, preferences)
# Location: Platform-specific user config directory
#   - Linux: ~/.config/annextube/config.toml
#   - macOS: ~/Library/Application Support/annextube/config.toml
#   - Windows: %APPDATA%/annextube/config.toml

# ============================================================================
# Authentication (for age-restricted, members-only, or private content)
# ============================================================================

# YouTube cookies for authenticated access
# Option 1: Use cookie file (Netscape format)
# cookies_file = "~/.config/annextube/cookies/youtube.txt"

# Option 2: Extract cookies from browser (requires browser to be installed)
# cookies_from_browser = "firefox"  # or "chrome", "chrome:Profile 1", etc.

# YouTube Data API v3 key (for comment replies and playlist metadata)
# RECOMMENDED: Use environment variable instead!
#   export YOUTUBE_API_KEY="your-key-here"
# Only set here if you can't use environment variables
# api_key = "your-api-key-here"

# ============================================================================
# Network Settings
# ============================================================================

# Proxy server (useful for privacy or bypassing restrictions)
# proxy = "socks5://127.0.0.1:9050"  # Tor proxy example
# proxy = "http://proxy.example.com:8080"  # HTTP proxy example

# Bandwidth limit (prevents overwhelming your connection)
# limit_rate = "500K"   # 500 KB/s
# limit_rate = "1M"     # 1 MB/s

# Rate limiting (delays between downloads to avoid YouTube throttling)
# sleep_interval = 3      # Minimum seconds between downloads
# max_sleep_interval = 5  # Maximum seconds (random delay between min and max)

# ============================================================================
# Advanced yt-dlp Options
# ============================================================================

# Extra options to pass to yt-dlp CLI (for git-annex integration)
# ytdlp_extra_opts = [
#     "--extractor-args", "youtube:player_client=android",  # Use Android client
#     "--format-sort", "+size,+br",  # Prefer smaller files
# ]

# ============================================================================
# Security Notes
# ============================================================================
# - NEVER commit this file to version control if it contains secrets!
# - Use environment variables for API keys and cookies in CI/CD
# - Cookie files should have permissions 600 (read/write owner only)
# - Cookies expire periodically - you'll need to refresh them
'''


def save_user_config_template() -> Path:
    """Save user configuration template to platform-specific config directory.

    Returns:
        Path to created config file

    Raises:
        FileExistsError: If user config file already exists
    """
    config_path = get_user_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        # Don't overwrite existing user config
        raise FileExistsError(
            f"User config already exists at {config_path}. "
            "Delete it first if you want to regenerate."
        )

    with open(config_path, "w") as f:
        f.write(generate_user_config_template())

    logger.info(f"Created user config template at {config_path}")
    return config_path
