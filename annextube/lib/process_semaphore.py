"""Cross-process concurrency limiter using file locks.

Prevents multiple ``annextube backup`` processes that share the same cookies
file from overwhelming YouTube with concurrent requests and triggering a
session ban.

Lock files live under ``$XDG_RUNTIME_DIR/annextube/`` (Linux) or
``/tmp/annextube-locks-$UID/`` as a fallback.  We use ``fcntl.flock()`` so
locks are automatically released when the process exits or crashes.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path

from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)

_NO_COOKIES_SENTINEL = "no-cookies"


def _lock_dir() -> Path:
    """Return (and create) the directory used for lock files."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        d = Path(runtime) / "annextube"
    else:
        d = Path(f"/tmp/annextube-locks-{os.getuid()}")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _namespace_for_cookies(cookies_file: str | None) -> str:
    """Derive a short, stable namespace from a cookies file path.

    Returns ``"no-cookies"`` when no file is configured, otherwise the
    first 16 hex chars of the SHA-256 of the canonical path.
    """
    if not cookies_file:
        return _NO_COOKIES_SENTINEL
    canonical = str(Path(cookies_file).expanduser().resolve())
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class CookieFileSemaphore:
    """Cross-process semaphore keyed on the cookies file path.

    ``max_parallel`` numbered lock files are created.  ``acquire()`` tries
    each slot with a non-blocking ``flock``; if all are busy it blocks on
    slot 0.  ``release()`` unlocks and closes the file descriptor.

    Intended usage::

        sem = CookieFileSemaphore(cookies_file="/path/to/cookies.txt",
                                   max_parallel=1)
        with sem:
            # only one process with this cookie file runs here
            ...

    If ``max_parallel <= 0`` the semaphore is a no-op (always succeeds
    immediately).
    """

    def __init__(
        self,
        cookies_file: str | None = None,
        max_parallel: int = 1,
    ) -> None:
        self._cookies_file = cookies_file
        self._max_parallel = max_parallel
        self._fd: int | None = None
        self._lock_path: Path | None = None

        if max_parallel <= 0:
            self._disabled = True
        else:
            self._disabled = False
            ns = _namespace_for_cookies(cookies_file)
            self._base = _lock_dir() / ns

    # -- context-manager interface -------------------------------------------

    def __enter__(self) -> CookieFileSemaphore:
        self.acquire()
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()

    # -- public API ----------------------------------------------------------

    def acquire(self) -> None:
        """Acquire a slot (blocking if all are busy)."""
        if self._disabled:
            return

        # Try each slot non-blocking
        for slot in range(self._max_parallel):
            lock_path = Path(f"{self._base}.{slot}")
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_WRONLY, 0o600)
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Got the lock
                self._fd = fd
                self._lock_path = lock_path
                logger.debug(
                    "Acquired lock slot %d/%d (%s)",
                    slot, self._max_parallel, lock_path.name,
                )
                return
            except OSError:
                # Slot busy — close fd and try next
                os.close(fd)

        # All slots busy: block on slot 0
        lock_path = Path(f"{self._base}.0")
        logger.info(
            "All %d slot(s) busy for cookies %s — waiting for a slot...",
            self._max_parallel,
            self._cookies_file or "(none)",
        )
        fd = os.open(str(lock_path), os.O_CREAT | os.O_WRONLY, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)  # blocking
        self._fd = fd
        self._lock_path = lock_path
        logger.debug("Acquired lock slot 0 (after blocking) (%s)", lock_path.name)

    def release(self) -> None:
        """Release the held slot."""
        if self._disabled or self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None
            self._lock_path = None
            logger.debug("Released lock slot")
