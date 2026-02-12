"""TSV utility functions for proper handling of special characters.

TSV files use tabs as delimiters and newlines as record separators.
Fields containing these characters must be escaped to avoid breaking the format.
"""


def escape_tsv_field(value: str | int | float | None) -> str:
    """Escape special characters in TSV field value.

    Replaces control characters with escape sequences:
    - Newline (\n) -> \\n
    - Carriage return (\r) -> \\r
    - Tab (\t) -> \\t
    - Backslash (\\) -> \\\\

    Args:
        value: Field value to escape

    Returns:
        Escaped string suitable for TSV field

    Examples:
        >>> escape_tsv_field("Hello\\nWorld")
        'Hello\\\\nWorld'
        >>> escape_tsv_field("Tab\\there")
        'Tab\\\\there'
        >>> escape_tsv_field(123)
        '123'
        >>> escape_tsv_field(None)
        ''
    """
    if value is None:
        return ""

    # Convert to string if not already
    value_str = str(value)

    # Escape backslash first (so we don't double-escape)
    value_str = value_str.replace("\\", "\\\\")

    # Escape newlines
    value_str = value_str.replace("\n", "\\n")

    # Escape carriage returns
    value_str = value_str.replace("\r", "\\r")

    # Escape tabs
    value_str = value_str.replace("\t", "\\t")

    return value_str


def unescape_tsv_field(value: str) -> str:
    """Unescape special characters in TSV field value.

    Replaces escape sequences with actual characters:
    - \\n -> Newline (\n)
    - \\r -> Carriage return (\r)
    - \\t -> Tab (\t)
    - \\\\ -> Backslash (\\)

    Args:
        value: Escaped field value from TSV

    Returns:
        Unescaped string

    Examples:
        >>> unescape_tsv_field("Hello\\\\nWorld")
        'Hello\\nWorld'
        >>> unescape_tsv_field("Tab\\\\there")
        'Tab\\there'
    """
    if not value:
        return ""

    # CRITICAL: Unescape backslash FIRST to avoid double-unescaping
    # Example: "Path\\\\to\\\\file" -> "Path\to\file" (not "Path<tab>o<tab>file")
    # Must do \\\\ before \\t, \\n, \\r to avoid misinterpreting escaped backslashes
    value = value.replace("\\\\", "\x00")  # Temporarily replace with null byte
    value = value.replace("\\t", "\t")
    value = value.replace("\\r", "\r")
    value = value.replace("\\n", "\n")
    value = value.replace("\x00", "\\")  # Replace null byte with single backslash

    return value


def write_tsv_row(f, values: list[str | int | float | None]) -> None:
    """Write a TSV row with proper escaping.

    Args:
        f: File object to write to
        values: List of field values
    """
    escaped = [escape_tsv_field(v) for v in values]
    f.write("\t".join(escaped) + "\n")


def read_tsv_row(line: str) -> list[str]:
    """Read a TSV row with proper unescaping.

    Args:
        line: Raw TSV line (without trailing newline)

    Returns:
        List of unescaped field values
    """
    fields = line.rstrip("\n\r").split("\t")
    return [unescape_tsv_field(f) for f in fields]
