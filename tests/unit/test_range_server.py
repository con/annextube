"""Tests for annextube.lib.range_server — HTTP range server tolerant of client disconnects."""

import io

import pytest

from annextube.lib.range_server import RangeHTTPRequestHandler


def _handler():
    """Build a handler instance without running BaseRequestHandler.__init__.

    __init__ would try to actually service a live socket, which these tests
    have no need for -- they only exercise copyfile().
    """
    return RangeHTTPRequestHandler.__new__(RangeHTTPRequestHandler)


class _DisconnectingWriter:
    """A writable stream that simulates a client disconnecting mid-transfer."""

    def __init__(self, fail_after=0):
        self.fail_after = fail_after
        self.writes = 0

    def write(self, data):
        if self.writes >= self.fail_after:
            raise ConnectionResetError(104, "Connection reset by peer")
        self.writes += 1


class _BrokenPipeWriter:
    def write(self, data):
        raise BrokenPipeError(32, "Broken pipe")


@pytest.mark.ai_generated
class TestCopyfileClientDisconnect:
    """A client aborting a hover-preview/seek mid-transfer must not raise."""

    def test_range_response_swallows_connection_reset(self):
        source_file = io.BytesIO(b"x" * 100)

        # Should not raise -- a client disconnect mid-transfer is expected,
        # not a server error.
        _handler().copyfile((source_file, 0, 100), _DisconnectingWriter())

        assert source_file.closed

    def test_range_response_swallows_broken_pipe(self):
        source_file = io.BytesIO(b"x" * 100)

        _handler().copyfile((source_file, 0, 100), _BrokenPipeWriter())

        assert source_file.closed

    def test_range_response_closes_source_even_on_disconnect(self):
        # A disconnect partway through must not leak the open file handle.
        source_file = io.BytesIO(b"x" * 100)

        _handler().copyfile((source_file, 0, 100), _DisconnectingWriter(fail_after=1))

        assert source_file.closed

    def test_non_range_response_swallows_connection_reset(self):
        # The non-tuple path delegates to SimpleHTTPRequestHandler.copyfile()
        # (shutil.copyfileobj), which must not blow up on disconnect either.
        source_file = io.BytesIO(b"x" * 100)

        _handler().copyfile(source_file, _DisconnectingWriter())


@pytest.mark.ai_generated
class TestCopyfileNormalTransfer:
    """Sanity check: the fix must not change behavior for a connected client."""

    def test_range_response_writes_requested_bytes(self):
        source_file = io.BytesIO(b"hello world")
        outputfile = io.BytesIO()

        _handler().copyfile((source_file, 0, len(b"hello world")), outputfile)

        assert outputfile.getvalue() == b"hello world"
        assert source_file.closed

    def test_non_range_response_writes_all_bytes(self):
        source_file = io.BytesIO(b"hello world")
        outputfile = io.BytesIO()

        _handler().copyfile(source_file, outputfile)

        assert outputfile.getvalue() == b"hello world"
