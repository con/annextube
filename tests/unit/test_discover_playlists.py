"""Unit tests for Archiver._discover_playlists."""

from pathlib import Path
from unittest.mock import patch

import pytest

from annextube.lib.config import Config
from annextube.services.archiver import Archiver


def _pl(pid: str, title: str) -> dict:
    return {
        "id": pid,
        "title": title,
        "url": f"https://www.youtube.com/playlist?list={pid}",
        "video_count": 0,
    }


@pytest.mark.ai_generated
def test_discover_playlists_dedupes_podcasts_already_in_playlists(tmp_path: Path) -> None:
    """A podcast that is also a regular playlist must be backed up only once.

    Otherwise every per-playlist operation (incl. the YouTube Data API
    cross-check) runs twice for it.
    """
    archiver = Archiver(tmp_path, Config())
    playlists = [_pl("PL_a", "A"), _pl("PL_b", "B")]
    podcasts = [_pl("PL_b", "B"), _pl("PL_c", "C")]

    with patch.object(archiver.youtube, "get_channel_playlists", return_value=playlists), \
         patch.object(archiver.youtube, "get_channel_podcasts", return_value=podcasts):
        urls = archiver._discover_playlists(
            "https://www.youtube.com/@chan", "all", None, "all",
        )

    assert urls == [
        "https://www.youtube.com/playlist?list=PL_a",
        "https://www.youtube.com/playlist?list=PL_b",
        "https://www.youtube.com/playlist?list=PL_c",
    ]
