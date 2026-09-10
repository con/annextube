"""HTTP server with proper Range request support for video seeking.

NOTE: This server is NOT needed to use or host an annextube archive. It
backs ``annextube serve`` for looking at an archive on your own machine,
and for development and testing. To actually host an archive, use a real,
production-grade HTTP server (e.g. Apache, nginx) -- any modern server
already supports Range requests.
"""

import contextlib
import http.server
import os
import sys


class RangeHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with proper range support for video files.

    This extends Python's SimpleHTTPRequestHandler to support HTTP Range requests,
    which are essential for video seeking. Without range support, browsers cannot
    seek/scrub through videos - they must download the entire file first.

    Range requests allow the browser to request specific byte ranges of a file:
    - Request: Range: bytes=1000000-2000000
    - Response: HTTP 206 Partial Content
    - Response: Content-Range: bytes 1000000-2000000/323798245

    This enables instant seeking to any point in the video.
    """

    def end_headers(self):
        """Add range support header to all responses."""
        self.send_header('Accept-Ranges', 'bytes')
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_GET(self):
        """Serve a GET request - handle tuple return from send_head."""
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            # copyfile closes the file for tuples, only close for non-tuples
            if not isinstance(f, tuple):
                f.close()

    def send_head(self):
        """Common code for GET and HEAD commands with range support."""
        path = self.translate_path(self.path)
        f = None

        if os.path.isdir(path):
            # Redirect to add trailing slash if missing
            if not self.path.endswith('/'):
                self.send_response(301)
                self.send_header('Location', self.path + '/')
                self.end_headers()
                return None
            # Look for index files
            for index in "index.html", "index.htm":
                index_path = os.path.join(path, index)
                if os.path.exists(index_path):
                    path = index_path
                    break
            else:
                return self.list_directory(path)

        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            file_len = fs[6]

            # Handle range requests (essential for video seeking)
            if "Range" in self.headers:
                range_header = self.headers["Range"]
                if range_header.startswith("bytes="):
                    range_spec = range_header[6:]
                    range_parts = range_spec.split('-')

                    if len(range_parts) == 2:
                        start = int(range_parts[0]) if range_parts[0] else 0
                        end = int(range_parts[1]) if range_parts[1] else file_len - 1

                        if start >= file_len:
                            self.send_error(416, "Requested Range Not Satisfiable")
                            f.close()
                            return None

                        end = min(end, file_len - 1)
                        length = end - start + 1

                        # Send partial content response (HTTP 206)
                        self.send_response(206)
                        self.send_header("Content-type", self.guess_type(path))
                        self.send_header("Content-Range", f"bytes {start}-{end}/{file_len}")
                        self.send_header("Content-Length", str(length))
                        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
                        self.end_headers()

                        f.seek(start)

                        # For HEAD requests, close file and return None
                        # (headers already sent, no body needed)
                        if self.command == 'HEAD':
                            f.close()
                            return None

                        # For GET requests, return tuple for copyfile to handle
                        return (f, start, length)

            # Normal response (no range request)
            self.send_response(200)
            self.send_header("Content-type", self.guess_type(path))
            self.send_header("Content-Length", str(file_len))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()

            # For HEAD requests, close file and return None
            if self.command == 'HEAD':
                f.close()
                return None

            # For GET requests, return tuple for copyfile
            return (f, 0, file_len)

        except Exception:
            f.close()
            raise

    def copyfile(self, source, outputfile):
        """Copy data with range support.

        A client that aborts an in-flight request -- e.g. quickly moving the
        pointer off a hover-preview video, or a browser cancelling/seeking a
        video mid-download -- closes the connection while we are still
        writing to it. That is a normal, expected occurrence rather than a
        server error, so it is swallowed here instead of propagating up into
        socketserver's "Exception occurred during processing of request"
        traceback dump (which would otherwise fill the server log for every
        such abort).
        """
        with contextlib.suppress(ConnectionError):
            if isinstance(source, tuple):
                f, start, length = source
                try:
                    remaining = length
                    while remaining > 0:
                        chunk_size = min(remaining, 8192)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        outputfile.write(chunk)
                        remaining -= len(chunk)
                finally:
                    f.close()
            else:
                # Original behavior for non-range requests
                super().copyfile(source, outputfile)

    def log_message(self, format, *args):
        """Log all HTTP requests for monitoring."""
        # Log all requests (helpful for debugging and monitoring)
        super().log_message(format, *args)


class ThreadedRangeHTTPServer(http.server.ThreadingHTTPServer):
    """Range-capable HTTP server that serves requests concurrently.

    Concurrency is not a nicety here, it is required for correctness of the
    web UI. A ``<video>`` element keeps its connection open and stops
    reading once it has buffered enough, which leaves the server blocked in
    ``sendall()`` on that socket. Serving requests one at a time (plain
    ``socketserver.TCPServer``) therefore means a single hovered/paused
    video wedges the *whole* server until the browser aborts that download:
    every other request -- thumbnails, other previews, the search index --
    just queues up. One thread per request keeps a parked video stream from
    blocking everything else.
    """

    def handle_error(self, request, client_address):
        """Do not dump a traceback when a client simply went away.

        Browsers abort in-flight media requests constantly: moving the
        pointer off a hover preview, seeking, navigating away. ``copyfile()``
        already handles that for the response body; this covers the same
        disconnect surfacing anywhere else in the handler, e.g. while the
        response headers are being written.
        """
        if isinstance(sys.exc_info()[1], ConnectionError):
            return
        super().handle_error(request, client_address)
