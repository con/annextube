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


@dataclass
class ComponentsConfig:
    """Configuration for what components to backup."""

    videos: bool = False  # Track URLs only by default
    metadata: bool = True
    comments: bool = True
    captions: bool = True
    thumbnails: bool = True


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

    video_path_pattern: str = "{date}_{video_id}_{sanitized_title}"
    channel_path_pattern: str = "{channel_id}"
    playlist_path_pattern: str = "{playlist_id}"
    video_filename: str = "video.mkv"  # Filename for video file within video directory
    playlist_prefix_width: int = 4  # Zero-padded width for playlist symlink prefixes (e.g., 0001)


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
            )
            for s in data.get("sources", [])
        ]

        components_data = data.get("components", {})
        components = ComponentsConfig(
            videos=components_data.get("videos", False),
            metadata=components_data.get("metadata", True),
            comments=components_data.get("comments", True),
            captions=components_data.get("captions", True),
            thumbnails=components_data.get("thumbnails", True),
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
                "video_path_pattern", "{date}_{video_id}_{sanitized_title}"
            ),
            channel_path_pattern=organization_data.get("channel_path_pattern", "{channel_id}"),
            playlist_path_pattern=organization_data.get("playlist_path_pattern", "{playlist_id}"),
            video_filename=organization_data.get("video_filename", "video.mkv"),
            playlist_prefix_width=organization_data.get("playlist_prefix_width", 4),
        )

        return cls(
            api_key=data.get("api_key"),
            sources=sources,
            components=components,
            filters=filters,
            organization=organization,
        )


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from TOML file.

    Args:
        config_path: Optional path to config file. If not provided, searches:
            1. .annextube/config.toml (current directory)
            2. ~/.config/annextube/config.toml (user config)

    Returns:
        Config object

    Raises:
        FileNotFoundError: If no config file found
        ValueError: If config file is invalid
    """
    if config_path is None:
        # Search for config file
        local_config = Path.cwd() / ".annextube" / "config.toml"
        user_config = Path.home() / ".config" / "annextube" / "config.toml"

        if local_config.exists():
            config_path = local_config
        elif user_config.exists():
            config_path = user_config
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

    return Config.from_dict(data)


def generate_config_template() -> str:
    """Generate a template configuration file in TOML format.

    Returns:
        TOML configuration template as string
    """
    return '''# annextube Configuration File
# This file configures sources, components, and filters for YouTube archival

# YouTube Data API v3 key (REQUIRED)
# Get from: https://console.cloud.google.com/apis/credentials
api_key = "YOUR_API_KEY_HERE"

# Sources to backup (channels or playlists)
# Add multiple [[sources]] sections for multiple sources

[[sources]]
url = "https://www.youtube.com/@RickAstleyYT"
type = "channel"  # or "playlist"
enabled = true

# Example: Liked Videos playlist (HIGH PRIORITY test case)
# [[sources]]
# url = "https://www.youtube.com/playlist?list=LL"  # LL = Liked Videos
# type = "playlist"
# enabled = true

# Example: Multiple channels
# [[sources]]
# url = "https://youtube.com/c/datalad"
# type = "channel"
# enabled = true

# Components to backup
[components]
videos = false       # Track URLs only (no video downloads) - saves storage
metadata = true      # Fetch video metadata
comments = true      # Fetch comments
captions = true      # Fetch captions in all languages
thumbnails = true    # Download thumbnails

# Repository organization and file paths
[organization]
video_path_pattern = "{date}_{video_id}_{sanitized_title}"  # Path pattern for videos
# Available placeholders:
#   {date} - Publication date (YYYY-MM-DD)
#   {video_id} - YouTube video ID
#   {sanitized_title} - Video title (filesystem-safe)
#   {channel_id} - Channel ID
#   {channel_name} - Channel name (sanitized)
# Examples:
#   "{video_id}" - Just video ID (compact)
#   "{date}_{video_id}" - Date + video ID
#   "{date}_{video_id}_{sanitized_title}" - Full (recommended)

channel_path_pattern = "{channel_id}"  # Path pattern for channels
playlist_path_pattern = "{playlist_id}"  # Path pattern for playlists (NOTE: currently uses ID, will use sanitized name in future)

video_filename = "video.mkv"  # Filename for video file (use .mkv for best compatibility)

# Playlist organization
playlist_prefix_width = 4  # Zero-padding width for playlist symlinks (e.g., 0001-, 0023-)
                           # Supports playlists up to 10^width - 1 videos
                           # 4 digits = up to 9999 videos per playlist

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


def save_config_template(config_dir: Path) -> Path:
    """Save configuration template to directory.

    Args:
        config_dir: Directory to save config template (e.g., .annextube/)

    Returns:
        Path to created config file
    """
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.toml"

    with open(config_path, "w") as f:
        f.write(generate_config_template())

    return config_path
