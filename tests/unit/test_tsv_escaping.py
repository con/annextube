"""Unit tests for TSV field escaping."""

import pytest

from annextube.lib.tsv_utils import escape_tsv_field, unescape_tsv_field


@pytest.mark.ai_generated
def test_escape_newlines():
    """Test that newlines are properly escaped."""
    value = "Line 1\nLine 2\nLine 3"
    escaped = escape_tsv_field(value)
    assert escaped == "Line 1\\nLine 2\\nLine 3"
    assert "\n" not in escaped


@pytest.mark.ai_generated
def test_escape_tabs():
    """Test that tabs are properly escaped."""
    value = "Column1\tColumn2\tColumn3"
    escaped = escape_tsv_field(value)
    assert escaped == "Column1\\tColumn2\\tColumn3"
    assert "\t" not in escaped


@pytest.mark.ai_generated
def test_escape_carriage_returns():
    """Test that carriage returns are properly escaped."""
    value = "Line 1\r\nLine 2\r\nLine 3"
    escaped = escape_tsv_field(value)
    assert escaped == "Line 1\\r\\nLine 2\\r\\nLine 3"
    assert "\r" not in escaped


@pytest.mark.ai_generated
def test_escape_backslashes():
    """Test that backslashes are properly escaped."""
    value = "Path\\to\\file"
    escaped = escape_tsv_field(value)
    assert escaped == "Path\\\\to\\\\file"


@pytest.mark.ai_generated
def test_escape_mixed_special_characters():
    """Test escaping of mixed special characters."""
    value = "Line 1\nTab:\there\rBackslash:\\end"
    escaped = escape_tsv_field(value)
    assert escaped == "Line 1\\nTab:\\there\\rBackslash:\\\\end"


@pytest.mark.ai_generated
def test_escape_multiline_description():
    """Test escaping of real-world multiline description (like apopyk channel)."""
    description = """Стріми 20:30 кожного вечора!

❤️ПІДТРИМАТИ КАНАЛ:❤️
💲PAYPAL : apopykpaypal@gmail.com
❤️Patreon: https://www.patreon.com/apopyk

🔵🟡Донат з виводом на стрімі https://apopyk.donatik.io
✅Підпишіться в Telegram ✅ https://t.me/apopyk

"""
    escaped = escape_tsv_field(description)

    # Should not contain literal newlines
    assert "\n" not in escaped

    # Should contain escaped newlines
    assert "\\n" in escaped

    # Should preserve other content
    assert "ПІДТРИМАТИ КАНАЛ" in escaped


@pytest.mark.ai_generated
def test_unescape_newlines():
    """Test that escaped newlines are properly unescaped."""
    escaped = "Line 1\\nLine 2\\nLine 3"
    unescaped = unescape_tsv_field(escaped)
    assert unescaped == "Line 1\nLine 2\nLine 3"


@pytest.mark.ai_generated
def test_unescape_tabs():
    """Test that escaped tabs are properly unescaped."""
    escaped = "Column1\\tColumn2\\tColumn3"
    unescaped = unescape_tsv_field(escaped)
    assert unescaped == "Column1\tColumn2\tColumn3"


@pytest.mark.ai_generated
def test_unescape_carriage_returns():
    """Test that escaped carriage returns are properly unescaped."""
    escaped = "Line 1\\r\\nLine 2\\r\\nLine 3"
    unescaped = unescape_tsv_field(escaped)
    assert unescaped == "Line 1\r\nLine 2\r\nLine 3"


@pytest.mark.ai_generated
def test_unescape_backslashes():
    """Test that escaped backslashes are properly unescaped."""
    # In TSV file: Path\\to\\file (with literal backslash-backslash sequences)
    # In Python string: Path\\\\to\\\\file (need to escape backslashes for Python)
    # After unescaping: Path\to\file (single backslash - one level of escaping)
    escaped = r"Path\\to\\file"  # Use raw string to avoid Python escaping confusion
    unescaped = unescape_tsv_field(escaped)
    assert unescaped == "Path\\to\\file"  # Single backslash between Path and to


@pytest.mark.ai_generated
def test_round_trip_escaping():
    """Test that escape -> unescape is reversible."""
    original = "Line 1\nTab:\there\rBackslash:\\end"
    escaped = escape_tsv_field(original)
    unescaped = unescape_tsv_field(escaped)
    assert unescaped == original


@pytest.mark.ai_generated
def test_escape_none_value():
    """Test that None is converted to empty string."""
    assert escape_tsv_field(None) == ""


@pytest.mark.ai_generated
def test_escape_integer():
    """Test that integers are converted to strings."""
    assert escape_tsv_field(123) == "123"


@pytest.mark.ai_generated
def test_escape_float():
    """Test that floats are converted to strings."""
    assert escape_tsv_field(12.34) == "12.34"


@pytest.mark.ai_generated
def test_escape_empty_string():
    """Test that empty strings are handled correctly."""
    assert escape_tsv_field("") == ""


@pytest.mark.ai_generated
def test_unescape_empty_string():
    """Test that empty strings are handled correctly."""
    assert unescape_tsv_field("") == ""
