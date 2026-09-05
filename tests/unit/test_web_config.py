"""Unit tests for WebConfig parsing (auto-regenerate web/ on version upgrade)."""

from __future__ import annotations

import pytest

from annextube.lib.config import Config, WebConfig


@pytest.mark.ai_generated
class TestWebConfigDefaults:
    """Test WebConfig default values."""

    def test_default_auto_regenerate_is_true(self) -> None:
        config = WebConfig()
        assert config.auto_regenerate is True


@pytest.mark.ai_generated
class TestWebConfigFromDict:
    """Test [web] section parsing via Config.from_dict."""

    def test_defaults_when_section_absent(self) -> None:
        config = Config.from_dict({})
        assert config.web.auto_regenerate is True

    def test_parses_auto_regenerate_false(self) -> None:
        config = Config.from_dict({"web": {"auto_regenerate": False}})
        assert config.web.auto_regenerate is False

    def test_parses_auto_regenerate_true(self) -> None:
        config = Config.from_dict({"web": {"auto_regenerate": True}})
        assert config.web.auto_regenerate is True
