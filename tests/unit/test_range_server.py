"""Tests for annextube.lib.range_server — HTTP range server tolerant of client disconnects."""

import http.client
import io
import socket
import threading
import time
from functools import partial

import pytest

from annextube.lib.range_server import RangeHTTPRequestHandler, ThreadedRangeHTTPServer


def _server():
    """Build a server instance without binding a socket (see _handler())."""
    return ThreadedRangeHTTPServer.__new__(ThreadedRangeHTTPServer)


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


@pytest.fixture
def stalled_video_server(tmp_path):
    """A running ThreadedRangeHTTPServer with one client stalled mid-download.

    This is the shape of a hover preview (or any paused <video>): the browser
    opens the connection, buffers what it wants and then simply stops
    reading, leaving the server blocked writing to that socket.
    """
    video = tmp_path / "video.mkv"
    with video.open("wb") as f:
        f.truncate(32 * 1024 * 1024)  # sparse: bigger than any socket buffer

    handler = partial(RangeHTTPRequestHandler, directory=str(tmp_path))
    httpd = ThreadedRangeHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    stalled = socket.create_connection(("127.0.0.1", port), timeout=5)
    stalled.sendall(b"GET /video.mkv HTTP/1.1\r\nHost: localhost\r\nRange: bytes=0-\r\n\r\n")
    stalled.recv(4096)  # take the headers, then read nothing more
    time.sleep(0.2)  # let the server fill the socket buffer and block

    try:
        yield port
    finally:
        stalled.close()
        httpd.shutdown()
        httpd.server_close()


@pytest.mark.ai_generated
class TestConcurrentRequests:
    """A stalled video stream must not wedge the whole server.

    Regression test for hover previews (and thumbnails, and the search
    index) silently failing to load: served serially, one parked <video>
    connection blocks every subsequent request until the browser gives up.
    """

    def test_a_second_video_can_be_fetched_while_the_first_is_stalled(
        self, stalled_video_server
    ):
        conn = http.client.HTTPConnection("127.0.0.1", stalled_video_server, timeout=5)
        try:
            conn.putrequest("GET", "/video.mkv")
            conn.putheader("Range", "bytes=0-1023")
            conn.endheaders()
            response = conn.getresponse()

            assert response.status == 206
            assert len(response.read()) == 1024
        finally:
            conn.close()


@pytest.mark.ai_generated
class TestHandleError:
    """Client disconnects are routine; anything else is still a real error."""

    @pytest.mark.parametrize(
        "exc",
        [
            ConnectionResetError(104, "Connection reset by peer"),
            BrokenPipeError(32, "Broken pipe"),
            ConnectionAbortedError(103, "Software caused connection abort"),
        ],
    )
    def test_disconnect_is_not_reported(self, exc, capsys):
        # A disconnect while writing headers lands here rather than in
        # copyfile(); it must not dump a traceback either.
        try:
            raise exc
        except OSError:
            _server().handle_error(None, ("127.0.0.1", 12345))

        assert capsys.readouterr().err == ""

    def test_real_errors_are_still_reported(self, capsys):
        try:
            raise ValueError("something actually broke")
        except ValueError:
            _server().handle_error(None, ("127.0.0.1", 12345))

        assert "something actually broke" in capsys.readouterr().err
