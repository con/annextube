"""Unit tests for CurationConfig parsing."""

from __future__ import annotations

import pytest

from annextube.lib.config import Config, CurationConfig


@pytest.mark.ai_generated
class TestCurationConfigDefaults:
    """Test CurationConfig default values."""

    def test_default_values(self) -> None:
        """CurationConfig should have sensible defaults."""
        config = CurationConfig()
        assert config.enabled is True
        assert config.curated_suffix == "curated"
        assert config.max_words_per_cue == 12
        assert config.min_orphan_words == 3
        assert config.filler_removal is True
        assert config.command_quoting is True
        assert config.fuzzy_enabled is True
        assert config.fuzzy_threshold == 0.82
        assert config.glossary_path is None
        assert config.glossary_collate_parents is False
        assert config.llm_provider is None
        assert config.llm_model is None
        assert config.llm_base_url is None
        assert config.audio_align_method is None
        assert config.audio_align_model is None


@pytest.mark.ai_generated
class TestCurationConfigFromDict:
    """Test CurationConfig parsing from TOML-style dicts."""

    def test_parse_curation_section(self) -> None:
        """Config.from_dict should parse [curation] section."""
        data = {
            "curation": {
                "enabled": True,
                "curated_suffix": "fixed",
                "max_words_per_cue": 10,
                "fuzzy_threshold": 0.90,
                "llm_provider": "ollama",
                "llm_model": "llama3",
            }
        }
        config = Config.from_dict(data)
        assert config.curation.enabled is True
        assert config.curation.curated_suffix == "fixed"
        assert config.curation.max_words_per_cue == 10
        assert config.curation.fuzzy_threshold == 0.90
        assert config.curation.llm_provider == "ollama"
        assert config.curation.llm_model == "llama3"

    def test_missing_curation_section_uses_defaults(self) -> None:
        """Missing [curation] section should use defaults."""
        data = {}
        config = Config.from_dict(data)
        assert config.curation.enabled is True
        assert config.curation.curated_suffix == "curated"
        assert config.curation.fuzzy_threshold == 0.82

    def test_partial_curation_section(self) -> None:
        """Partial [curation] section should merge with defaults."""
        data = {
            "curation": {
                "enabled": False,
            }
        }
        config = Config.from_dict(data)
        assert config.curation.enabled is False
        # Other fields should be defaults
        assert config.curation.curated_suffix == "curated"
        assert config.curation.max_words_per_cue == 12

    def test_glossary_path_and_collate(self) -> None:
        """Config.from_dict should parse glossary_path and glossary_collate_parents."""
        data = {
            "curation": {
                "glossary_path": ".annextube/captions-glossary.yaml",
                "glossary_collate_parents": True,
            }
        }
        config = Config.from_dict(data)
        assert config.curation.glossary_path == ".annextube/captions-glossary.yaml"
        assert config.curation.glossary_collate_parents is True

    def test_source_curation_override(self) -> None:
        """Per-source curation override should be parsed."""
        data = {
            "sources": [{
                "url": "https://www.youtube.com/@test",
                "type": "channel",
                "curation": False,
            }],
        }
        config = Config.from_dict(data)
        assert config.sources[0].curation is False

    def test_source_curation_not_set(self) -> None:
        """Per-source curation should be None if not set."""
        data = {
            "sources": [{
                "url": "https://www.youtube.com/@test",
                "type": "channel",
            }],
        }
        config = Config.from_dict(data)
        assert config.sources[0].curation is None


@pytest.mark.ai_generated
class TestUserConfigGlossaryPath:
    """Test UserConfig glossary_path field."""

    def test_glossary_path_from_dict(self) -> None:
        """UserConfig.from_dict should parse glossary_path."""
        from annextube.lib.config import UserConfig

        data = {"glossary_path": "~/.config/annextube/glossary.yaml"}
        user_config = UserConfig.from_dict(data)
        assert user_config.glossary_path == "~/.config/annextube/glossary.yaml"

    def test_glossary_path_default_none(self) -> None:
        """glossary_path should default to None."""
        from annextube.lib.config import UserConfig

        user_config = UserConfig.from_dict({})
        assert user_config.glossary_path is None
