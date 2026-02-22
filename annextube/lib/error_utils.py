"""Error formatting utilities."""

from __future__ import annotations

import subprocess


def format_subprocess_error(e: Exception) -> str:
    """Format an exception for error reporting, extracting subprocess output.

    For CalledProcessError, includes stdout/stderr (the actual diagnostic
    info that is otherwise lost).  For other exceptions, returns str(e).

    Args:
        e: Exception to format

    Returns:
        Human-readable error string with subprocess output when available
    """
    if not isinstance(e, subprocess.CalledProcessError):
        return str(e)

    parts = [str(e)]
    for stream_name, stream in [("stdout", e.stdout), ("stderr", e.stderr)]:
        if stream is None:
            continue
        text = stream.decode("utf-8", errors="replace") if isinstance(stream, bytes) else stream
        text = text.strip()
        if text:
            parts.append(f"{stream_name}: {text}")
    return "\n".join(parts)
