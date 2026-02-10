/**
 * Unescape special characters in TSV field value.
 *
 * Replaces escape sequences with actual characters:
 * - \\n -> Newline
 * - \\r -> Carriage return
 * - \\t -> Tab
 * - \\\\ -> Backslash
 *
 * CRITICAL: Must unescape backslash FIRST to avoid double-unescaping.
 * Example: "Path\\\\to\\\\file" should become "Path\to\file", not "Path<tab>o<tab>file"
 *
 * @param value - Escaped field value from TSV
 * @returns Unescaped string
 */
function unescapeTSVField(value: string): string {
  if (!value) return '';

  // Unescape backslash first using a placeholder to avoid double-unescaping
  return value
    .replace(/\\\\/g, '\x00')  // Temporarily replace \\\\ with null byte
    .replace(/\\t/g, '\t')
    .replace(/\\r/g, '\r')
    .replace(/\\n/g, '\n')
    .replace(/\x00/g, '\\');   // Replace null byte with single backslash
}

/**
 * Lightweight TSV parser with no dependencies.
 * Inspired by mykrok's proven 632-byte implementation.
 *
 * Parses tab-separated values into an array of objects.
 * - Handles Unix (LF) and Windows (CRLF) line endings
 * - Supports empty fields
 * - Unescapes special characters (\\n, \\t, \\r, \\\\)
 * - Returns all values as strings (caller handles type conversion)
 *
 * @param tsvText - Raw TSV file content
 * @returns Array of objects with header keys and row values
 *
 * @example
 * const tsv = 'video_id\ttitle\tduration\nabc123\tTest Video\t300';
 * const result = parseTSV(tsv);
 * // [{ video_id: 'abc123', title: 'Test Video', duration: '300' }]
 */
export function parseTSV(tsvText: string): Record<string, string>[] {
  const lines = tsvText.split(/\r?\n/);

  // Need at least a header row
  if (lines.length < 2) {
    return [];
  }

  const headers = lines[0].split('\t');

  return (
    lines
      .slice(1)
      // Skip empty lines
      .filter((line) => line.trim())
      .map((line) => {
        const values = line.split('\t');
        return Object.fromEntries(
          headers.map((header, i) => [header, unescapeTSVField(values[i] || '')])
        );
      })
  );
}

/**
 * Parse integer field from TSV row, with fallback.
 *
 * @param value - String value from TSV
 * @param fallback - Default value if parsing fails
 * @returns Parsed integer or fallback
 */
export function parseIntField(value: string, fallback: number = 0): number {
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? fallback : parsed;
}

/**
 * Parse boolean field from TSV row.
 * Accepts: 'true', 'false', '1', '0'
 *
 * @param value - String value from TSV
 * @returns Boolean value
 */
export function parseBooleanField(value: string): boolean {
  return value === 'true' || value === '1';
}
