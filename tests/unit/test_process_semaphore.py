"""Tests for annextube.lib.process_semaphore — cross-process lock."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from annextube.lib.process_semaphore import (
    CookieFileSemaphore,
    _lock_dir,
    _namespace_for_cookies,
)


@pytest.mark.ai_generated
class TestNamespaceForCookies:
    def test_no_cookies(self):
        assert _namespace_for_cookies(None) == "no-cookies"

    def test_none_string(self):
        assert _namespace_for_cookies("") == "no-cookies"

    def test_stable_hash(self):
        ns1 = _namespace_for_cookies("/tmp/cookies.txt")
        ns2 = _namespace_for_cookies("/tmp/cookies.txt")
        assert ns1 == ns2
        assert len(ns1) == 16
        assert ns1 != "no-cookies"

    def test_different_paths_different_hashes(self):
        ns1 = _namespace_for_cookies("/tmp/cookies_a.txt")
        ns2 = _namespace_for_cookies("/tmp/cookies_b.txt")
        assert ns1 != ns2


@pytest.mark.ai_generated
class TestLockDir:
    def test_creates_directory(self):
        d = _lock_dir()
        assert d.is_dir()

    def test_xdg_runtime_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"XDG_RUNTIME_DIR": tmpdir}):
                d = _lock_dir()
                assert d == Path(tmpdir) / "annextube"
                assert d.is_dir()

    def test_fallback_without_xdg(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove XDG_RUNTIME_DIR to trigger fallback
            os.environ.pop("XDG_RUNTIME_DIR", None)
            d = _lock_dir()
            assert "annextube-locks-" in str(d)
            assert d.is_dir()


@pytest.mark.ai_generated
class TestCookieFileSemaphore:
    def test_acquire_release(self):
        sem = CookieFileSemaphore(cookies_file=None, max_parallel=1)
        sem.acquire()
        sem.release()

    def test_context_manager(self):
        sem = CookieFileSemaphore(cookies_file=None, max_parallel=1)
        with sem:
            pass  # Should not raise

    def test_disabled_with_zero_parallel(self):
        sem = CookieFileSemaphore(cookies_file=None, max_parallel=0)
        with sem:
            pass  # Noop, should not raise

    def test_disabled_with_negative_parallel(self):
        sem = CookieFileSemaphore(cookies_file=None, max_parallel=-1)
        with sem:
            pass

    def test_reentrant_release(self):
        """Release without acquire should not raise."""
        sem = CookieFileSemaphore(cookies_file=None, max_parallel=1)
        sem.release()  # Should not raise

    def test_multiple_slots(self):
        sem1 = CookieFileSemaphore(cookies_file=None, max_parallel=2)
        sem2 = CookieFileSemaphore(cookies_file=None, max_parallel=2)
        sem1.acquire()
        sem2.acquire()
        sem1.release()
        sem2.release()

    def test_with_cookies_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            sem = CookieFileSemaphore(cookies_file=f.name, max_parallel=1)
            with sem:
                pass

    def test_lock_file_created(self):
        sem = CookieFileSemaphore(cookies_file=None, max_parallel=1)
        sem.acquire()
        try:
            # Lock file should exist
            assert sem._lock_path is not None
            assert sem._lock_path.exists()
        finally:
            sem.release()

    def test_double_acquire_same_process(self):
        """Same process can acquire and release cleanly."""
        sem1 = CookieFileSemaphore(cookies_file=None, max_parallel=1)
        sem1.acquire()
        sem1.release()
