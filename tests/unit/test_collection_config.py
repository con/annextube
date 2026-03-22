"""Unit tests for CollectionConfig parsing."""

import pytest

from annextube.lib.config import CollectionConfig, load_collection_config


class TestCollectionConfig:
    """Tests for CollectionConfig dataclass."""

    @pytest.mark.ai_generated
    def test_defaults(self) -> None:
        cfg = CollectionConfig()
        assert cfg.comments_depth == 0
        assert cfg.curation is True
        assert cfg.search is False
        assert cfg.include_playlists == "none"
        assert cfg.include_podcasts == "none"
        assert cfg.common_config is None
        assert cfg.push_remote is None

    @pytest.mark.ai_generated
    def test_from_dict_full(self) -> None:
        data = {
            "comments_depth": 5,
            "curation": False,
            "search": True,
            "include_playlists": "all",
            "include_podcasts": ".*interview.*",
            "common_config": ".annextube/common.toml",
            "push_remote": "origin",
        }
        cfg = CollectionConfig.from_dict(data)
        assert cfg.comments_depth == 5
        assert cfg.curation is False
        assert cfg.search is True
        assert cfg.include_playlists == "all"
        assert cfg.include_podcasts == ".*interview.*"
        assert cfg.common_config == ".annextube/common.toml"
        assert cfg.push_remote == "origin"

    @pytest.mark.ai_generated
    def test_from_dict_partial(self) -> None:
        cfg = CollectionConfig.from_dict({"curation": False})
        assert cfg.curation is False
        # Other fields get defaults
        assert cfg.comments_depth == 0
        assert cfg.search is False

    @pytest.mark.ai_generated
    def test_from_dict_empty(self) -> None:
        cfg = CollectionConfig.from_dict({})
        assert cfg == CollectionConfig()


class TestLoadCollectionConfig:
    """Tests for load_collection_config()."""

    @pytest.mark.ai_generated
    def test_no_config_file(self, tmp_path) -> None:
        """Returns None when .annextube/config.toml does not exist."""
        assert load_collection_config(tmp_path) is None

    @pytest.mark.ai_generated
    def test_no_collection_section(self, tmp_path) -> None:
        """Returns None when config exists but has no [collection] section."""
        config_dir = tmp_path / ".annextube"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text('[sources]\nurl = "x"\n')
        assert load_collection_config(tmp_path) is None

    @pytest.mark.ai_generated
    def test_with_collection_section(self, tmp_path) -> None:
        """Parses [collection] section correctly."""
        config_dir = tmp_path / ".annextube"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text(
            '[collection]\ncomments_depth = 3\ncuration = false\npush_remote = "myremote"\n'
        )
        cfg = load_collection_config(tmp_path)
        assert cfg is not None
        assert cfg.comments_depth == 3
        assert cfg.curation is False
        assert cfg.push_remote == "myremote"

    @pytest.mark.ai_generated
    def test_malformed_toml(self, tmp_path) -> None:
        """Returns None for invalid TOML (logs warning, no crash)."""
        config_dir = tmp_path / ".annextube"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text("this is not valid toml [[[")
        assert load_collection_config(tmp_path) is None

    @pytest.mark.ai_generated
    def test_does_not_break_existing_config(self, tmp_path) -> None:
        """Config.from_dict still works when [collection] is absent."""
        from annextube.lib.config import Config

        data = {
            "sources": [{"url": "https://youtube.com/@test", "type": "channel"}],
            "components": {"metadata": True},
        }
        cfg = Config.from_dict(data)
        assert cfg.collection is None
        assert len(cfg.sources) == 1

    @pytest.mark.ai_generated
    def test_config_from_dict_with_collection(self, tmp_path) -> None:
        """Config.from_dict correctly parses [collection] when present."""
        from annextube.lib.config import Config

        data = {
            "sources": [],
            "collection": {
                "comments_depth": 10,
                "search": True,
            },
        }
        cfg = Config.from_dict(data)
        assert cfg.collection is not None
        assert cfg.collection.comments_depth == 10
        assert cfg.collection.search is True
