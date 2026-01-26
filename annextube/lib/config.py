"""Configuration file handling for annextube.

Loads configuration from .annextube/config.toml or ~/.config/annextube/config.toml
in TOML format (similar to mykrok pattern).
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Handle tomli/tomllib compatibility
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class SourceConfig:
    """Configuration for a YouTube source (channel or playlist)."""

    url: str
    type: str  # 'channel' or 'playlist'
    enabled: bool = True
    include_playlists: str = "none"  # "all", "none", or regex pattern for auto-discovery
    exclude_playlists: Optional[str] = None  # Regex pattern to exclude playlists
    include_podcasts: bool = False  # Auto-discover podcasts from channel


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

    video_path_pattern: str = "{date}_{sanitized_title}"  # Default: no video_id (tracked in TSV)
    channel_path_pattern: str = "{channel_id}"
    playlist_path_pattern: str = "{playlist_id}"
    video_filename: str = "video.mkv"  # Filename for video file within video directory
    playlist_prefix_width: int = 4  # Zero-padded width for playlist symlink prefixes (e.g., 0001)
    playlist_prefix_separator: str = "_"  # Separator between index and path (underscore, not hyphen)


@dataclass
class Config:
    """Main configuration for annextube."""

    api_key: Optional[str] = None  # YouTube Data API v3 key
    sources: List[SourceConfig] = field(default_factory=list)
    components: ComponentsConfig = field(default_factory=ComponentsConfig)
    filters: FiltersConfig = field(default_factory=FiltersConfig)
    organization: OrganizationConfig = field(default_factory=OrganizationConfig)

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
                include_podcasts=s.get("include_podcasts", False),
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
            api_key=data.get("api_key"),
            sources=sources,
            components=components,
            filters=filters,
            organization=organization,
        )


def load_config(config_path: Optional[Path] = None, repo_path: Optional[Path] = None) -> Config:
    """Load configuration from TOML file.

    API key is read from YOUTUBE_API_KEY environment variable, not from config file.

    Args:
        config_path: Optional path to config file. If not provided, searches:
            1. {repo_path}/.annextube/config.toml (if repo_path provided)
            2. .annextube/config.toml (current directory)
            3. ~/.config/annextube/config.toml (user config)
        repo_path: Optional path to repository root (for searching config file)

    Returns:
        Config object

    Raises:
        FileNotFoundError: If no config file found
        ValueError: If config file is invalid
    """
    import os

    if config_path is None:
        # Search for config file
        search_paths = []

        # If repo_path provided, search there first
        if repo_path is not None:
            search_paths.append(Path(repo_path) / ".annextube" / "config.toml")

        # Then try current directory
        search_paths.append(Path.cwd() / ".annextube" / "config.toml")

        # Finally try user config
        search_paths.append(Path.home() / ".config" / "annextube" / "config.toml")

        for path in search_paths:
            if path.exists():
                config_path = path
                break
        else:
            raise FileNotFoundError(
                "No config file found. Expected .annextube/config.toml or "
                "~/.config/annextube/config.toml"
            )

    # Load TOML
    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse config file {config_path}: {e}")

    config = Config.from_dict(data)

    # Override api_key with environment variable (never store in config!)
    api_key = os.environ.get('YOUTUBE_API_KEY')
    if api_key:
        config.api_key = api_key

    return config


def generate_config_template(urls: list[str] = None, enable_videos: bool = True,
                            comments_depth: Optional[int] = None, enable_captions: bool = True) -> str:
    """Generate a template configuration file in TOML format.

    Args:
        urls: List of YouTube channel/playlist URLs to add
        enable_videos: Enable video downloading (default: True)
        comments_depth: Comments to fetch (None=unlimited, 0=disabled, default: None)
        enable_captions: Enable captions (default: True)

    Returns:
        TOML configuration template as string
    """
    # Convert values to TOML format
    videos_str = str(enable_videos).lower()
    captions_str = str(enable_captions).lower()

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
            sources_section += f'''
[[sources]]
url = "{url}"
type = "{url_type}"
enabled = true
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
# Optional playlist discovery settings (for channel sources):
# include_playlists = "all"  # Auto-discover and backup ALL playlists from this channel
# include_playlists = ".*tutorial.*"  # Only playlists matching regex pattern
# exclude_playlists = ".*shorts.*|.*old.*"  # Exclude playlists matching regex
# include_podcasts = true  # Also discover podcasts from channel's Podcasts tab

# Components to backup
[components]
videos = {videos_str}           # Track URLs only (no video downloads) - saves storage
metadata = true          # Fetch video metadata
{comments_str}           # Comments: None = unlimited (fetches ALL, incrementally)
                         #           0 = disabled
                         #           N = limit to N comments
                         # Note: Incremental - merges new comments with existing
captions = {captions_str}          # Fetch captions matching language filter
thumbnails = true        # Download thumbnails

caption_languages = ".*"  # Regex pattern for caption languages to download
                          # Examples:
                          #   ".*" - All available languages (default)
                          #   "en.*" - All English variants (en, en-US, en-GB, etc.)
                          #   "en|es|fr" - English, Spanish, French only
                          #   "en-US" - US English only

# Repository organization and file paths
[organization]
video_path_pattern = "{{date}}_{{sanitized_title}}"  # Path pattern for videos (video_id tracked in TSV)
# Available placeholders:
#   {{date}} - Publication date (YYYY-MM-DD)
#   {{video_id}} - YouTube video ID (optional, tracked in videos.tsv)
#   {{sanitized_title}} - Video title (filesystem-safe, hyphens for words)
#   {{channel_id}} - Channel ID
#   {{channel_name}} - Channel name (sanitized)
# Examples:
#   "{{date}}_{{sanitized_title}}" - Date + title (default, ID in TSV)
#   "{{date}}_{{video_id}}_{{sanitized_title}}" - Include ID (legacy)
#   "{{video_id}}" - Just video ID (compact)

channel_path_pattern = "{{channel_id}}"  # Path pattern for channels
playlist_path_pattern = "{{playlist_id}}"  # Path pattern for playlists (uses sanitized name in practice)

video_filename = "video.mkv"  # Filename for video file (use .mkv for best compatibility)

# Playlist organization
playlist_prefix_width = 4  # Zero-padding width for playlist symlinks (e.g., 0001_, 0023_)
                           # Supports playlists up to 10^width - 1 videos
                           # 4 digits = up to 9999 videos per playlist

playlist_prefix_separator = "_"  # Separator between index and path (underscore, not hyphen)
                                 # Example: 0001_2020-01-10_video-title (not 0001-2020-01-10...)

# Filters for selective archival
[filters]
limit = 10  # Limit to N most recent videos (by upload date, newest first)
            # Remove or comment out to backup all videos

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
                        enable_captions: bool = True) -> Path:
    """Save configuration template to directory.

    Args:
        config_dir: Directory to save config template (e.g., .annextube/)
        urls: List of YouTube channel/playlist URLs to add
        enable_videos: Enable video downloading (default: True)
        comments_depth: Comments to fetch (None=unlimited, 0=disabled, default: None)
        enable_captions: Enable captions (default: True)

    Returns:
        Path to created config file
    """
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.toml"

    with open(config_path, "w") as f:
        f.write(generate_config_template(urls, enable_videos, comments_depth, enable_captions))

    return config_path
