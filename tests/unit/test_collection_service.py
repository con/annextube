"""Unit tests for the collection service."""

import pytest

from annextube.services.collection import (
    discover_subdatasets,
    extract_handle,
)


class TestExtractHandle:
    """Tests for extract_handle()."""

    @pytest.mark.ai_generated
    def test_at_handle(self) -> None:
        assert extract_handle("https://www.youtube.com/@ChannelName") == "ChannelName"

    @pytest.mark.ai_generated
    def test_at_handle_with_path(self) -> None:
        assert extract_handle("https://www.youtube.com/@ChannelName/videos") == "ChannelName"

    @pytest.mark.ai_generated
    def test_c_style_url(self) -> None:
        assert extract_handle("https://www.youtube.com/c/MyChannel") == "MyChannel"

    @pytest.mark.ai_generated
    def test_channel_id_url(self) -> None:
        assert extract_handle("https://www.youtube.com/channel/UCxxxxxxxx") == "UCxxxxxxxx"

    @pytest.mark.ai_generated
    def test_no_www(self) -> None:
        assert extract_handle("https://youtube.com/@Handle") == "Handle"

    @pytest.mark.ai_generated
    def test_with_query_params(self) -> None:
        assert extract_handle("https://www.youtube.com/@Handle?sub_confirmation=1") == "Handle"

    @pytest.mark.ai_generated
    def test_unrecognized_url(self) -> None:
        assert extract_handle("https://example.com/notahandle") is None

    @pytest.mark.ai_generated
    def test_empty_string(self) -> None:
        assert extract_handle("") is None

    @pytest.mark.ai_generated
    def test_playlist_url(self) -> None:
        assert extract_handle("https://www.youtube.com/playlist?list=PLxxx") is None


class TestDiscoverSubdatasets:
    """Tests for discover_subdatasets()."""

    @pytest.mark.ai_generated
    def test_discovers_channels(self, tmp_path) -> None:
        """Directories with .annextube/config.toml are discovered."""
        # Create two channel-like directories
        for name in ["ch-alpha", "ch-beta"]:
            config_dir = tmp_path / name / ".annextube"
            config_dir.mkdir(parents=True)
            (config_dir / "config.toml").write_text("[sources]\n")

        # And one directory without config
        (tmp_path / "not-a-channel").mkdir()

        result = discover_subdatasets(tmp_path)
        assert len(result) == 2
        assert result[0].name == "ch-alpha"
        assert result[1].name == "ch-beta"

    @pytest.mark.ai_generated
    def test_empty_collection(self, tmp_path) -> None:
        """Empty directory returns empty list."""
        result = discover_subdatasets(tmp_path)
        assert result == []

    @pytest.mark.ai_generated
    def test_skips_files(self, tmp_path) -> None:
        """Regular files are ignored."""
        (tmp_path / "channels.tsv").write_text("header\n")
        result = discover_subdatasets(tmp_path)
        assert result == []

    @pytest.mark.ai_generated
    def test_sorted_order(self, tmp_path) -> None:
        """Results are sorted alphabetically."""
        for name in ["zeta", "alpha", "mid"]:
            config_dir = tmp_path / name / ".annextube"
            config_dir.mkdir(parents=True)
            (config_dir / "config.toml").write_text("")

        result = discover_subdatasets(tmp_path)
        names = [p.name for p in result]
        assert names == ["alpha", "mid", "zeta"]
