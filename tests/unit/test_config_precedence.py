"""Unit tests for per-channel config precedence over collection defaults (FR-022).

The collection-level [collection] section provides defaults for new channels,
but a channel's own .annextube/config.toml always takes precedence.  This
test verifies the structural separation: load_collection_config reads the
collection root, load_config reads the channel directory, and they produce
independent results.
"""

import pytest

from annextube.lib.config import CollectionConfig, load_collection_config, load_config


class TestConfigPrecedence:
    """FR-022: Per-channel configuration MUST override collection defaults."""

    @pytest.mark.ai_generated
    def test_collection_defaults_loaded(self, tmp_path) -> None:
        """Collection config is loaded from collection root."""
        config_dir = tmp_path / ".annextube"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text(
            "[collection]\n"
            "comments_depth = 5\n"
            "curation = true\n"
            'include_playlists = "all"\n'
            'include_podcasts = "none"\n'
        )

        coll_cfg = load_collection_config(tmp_path)
        assert coll_cfg is not None
        assert coll_cfg.comments_depth == 5
        assert coll_cfg.curation is True
        assert coll_cfg.include_playlists == "all"

    @pytest.mark.ai_generated
    def test_channel_config_independent_of_collection(self, tmp_path) -> None:
        """Channel config is loaded from its own directory, not the collection."""
        # Set up collection config with defaults
        coll_config_dir = tmp_path / ".annextube"
        coll_config_dir.mkdir()
        (coll_config_dir / "config.toml").write_text(
            "[collection]\n"
            "comments_depth = 5\n"
            "curation = true\n"
        )

        # Set up channel with DIFFERENT config
        channel_dir = tmp_path / "ch-test"
        channel_dir.mkdir()
        ch_config_dir = channel_dir / ".annextube"
        ch_config_dir.mkdir()
        (ch_config_dir / "config.toml").write_text(
            "[[sources]]\n"
            'url = "https://www.youtube.com/@Test"\n'
            'type = "channel"\n'
            "\n"
            "[components]\n"
            "comments_depth = 0\n"
        )

        # Load collection defaults
        coll_cfg = load_collection_config(tmp_path)
        assert coll_cfg is not None
        assert coll_cfg.comments_depth == 5

        # Load channel config (independent)
        ch_cfg = load_config(repo_path=channel_dir)
        # Channel reads its own config, NOT the collection's
        assert ch_cfg.components.comments_depth == 0

    @pytest.mark.ai_generated
    def test_channel_without_collection_section(self, tmp_path) -> None:
        """A channel directory does not have a [collection] section."""
        channel_dir = tmp_path / "ch-test"
        channel_dir.mkdir()
        ch_config_dir = channel_dir / ".annextube"
        ch_config_dir.mkdir()
        (ch_config_dir / "config.toml").write_text(
            "[[sources]]\n"
            'url = "https://www.youtube.com/@Test"\n'
            'type = "channel"\n'
        )

        # load_collection_config on a channel dir returns None
        # (channels don't have [collection] sections)
        coll_cfg = load_collection_config(channel_dir)
        assert coll_cfg is None

    @pytest.mark.ai_generated
    def test_no_config_file_returns_none(self, tmp_path) -> None:
        """Missing config file returns None for collection config."""
        assert load_collection_config(tmp_path) is None

    @pytest.mark.ai_generated
    def test_collection_config_from_dict(self) -> None:
        """CollectionConfig.from_dict uses provided values over defaults."""
        data = {
            "comments_depth": 10,
            "curation": False,
            "search": True,
            "include_playlists": "all",
            "include_podcasts": "rss",
            "common_config": "common.toml",
            "push_remote": "origin",
        }
        cfg = CollectionConfig.from_dict(data)
        assert cfg.comments_depth == 10
        assert cfg.curation is False
        assert cfg.search is True
        assert cfg.include_playlists == "all"
        assert cfg.include_podcasts == "rss"
        assert cfg.common_config == "common.toml"
        assert cfg.push_remote == "origin"

    @pytest.mark.ai_generated
    def test_collection_config_from_dict_defaults(self) -> None:
        """CollectionConfig.from_dict fills in defaults for missing keys."""
        cfg = CollectionConfig.from_dict({})
        assert cfg.comments_depth == 0
        assert cfg.curation is True
        assert cfg.search is False
        assert cfg.include_playlists == "none"
        assert cfg.include_podcasts == "none"
        assert cfg.common_config is None
        assert cfg.push_remote is None
