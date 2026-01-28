import { parseTSV, parseIntField, parseBooleanField } from '../../src/utils/tsv-parser';

describe('TSV Parser', () => {
  describe('parseTSV', () => {
    test('parses simple TSV with Unix line endings', () => {
      const tsv = 'video_id\ttitle\tduration\nabc123\tTest Video\t300';
      const result = parseTSV(tsv);

      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({
        video_id: 'abc123',
        title: 'Test Video',
        duration: '300',
      });
    });

    test('parses TSV with Windows CRLF line endings', () => {
      const tsv = 'id\tname\r\n1\tAlice\r\n2\tBob';
      const result = parseTSV(tsv);

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({ id: '1', name: 'Alice' });
      expect(result[1]).toEqual({ id: '2', name: 'Bob' });
    });

    test('handles empty fields', () => {
      const tsv = 'id\tname\tcity\n1\tAlice\t\n2\t\tBoston';
      const result = parseTSV(tsv);

      expect(result[0]).toEqual({ id: '1', name: 'Alice', city: '' });
      expect(result[1]).toEqual({ id: '2', name: '', city: 'Boston' });
    });

    test('skips empty lines', () => {
      const tsv = 'id\tname\n1\tAlice\n\n2\tBob\n\n';
      const result = parseTSV(tsv);

      expect(result).toHaveLength(2);
      expect(result[0].name).toBe('Alice');
      expect(result[1].name).toBe('Bob');
    });

    test('returns empty array for header-only TSV', () => {
      const tsv = 'id\tname';
      const result = parseTSV(tsv);

      expect(result).toEqual([]);
    });

    test('returns empty array for empty string', () => {
      const result = parseTSV('');
      expect(result).toEqual([]);
    });

    test('handles multiple columns', () => {
      const tsv =
        'video_id\ttitle\tchannel\tduration\tviews\n' +
        'abc\tVideo 1\tChannel A\t120\t1000\n' +
        'def\tVideo 2\tChannel B\t240\t2000';

      const result = parseTSV(tsv);

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({
        video_id: 'abc',
        title: 'Video 1',
        channel: 'Channel A',
        duration: '120',
        views: '1000',
      });
    });

    test('handles real videos.tsv format', () => {
      const tsv =
        'video_id\ttitle\tchannel_name\tpublished_at\tduration\tview_count\n' +
        'dQw4w9WgXcQ\tNever Gonna Give You Up\tRick Astley\t2009-10-25T06:57:33Z\t213\t1400000000';

      const result = parseTSV(tsv);

      expect(result[0]).toEqual({
        video_id: 'dQw4w9WgXcQ',
        title: 'Never Gonna Give You Up',
        channel_name: 'Rick Astley',
        published_at: '2009-10-25T06:57:33Z',
        duration: '213',
        view_count: '1400000000',
      });
    });
  });

  describe('parseIntField', () => {
    test('parses valid integer', () => {
      expect(parseIntField('42')).toBe(42);
      expect(parseIntField('0')).toBe(0);
      expect(parseIntField('-5')).toBe(-5);
    });

    test('returns fallback for invalid input', () => {
      expect(parseIntField('', 0)).toBe(0);
      expect(parseIntField('abc', 10)).toBe(10);
      expect(parseIntField('12.5', 0)).toBe(12); // parseInt truncates
    });

    test('uses default fallback of 0', () => {
      expect(parseIntField('invalid')).toBe(0);
    });
  });

  describe('parseBooleanField', () => {
    test('parses boolean strings', () => {
      expect(parseBooleanField('true')).toBe(true);
      expect(parseBooleanField('false')).toBe(false);
    });

    test('parses numeric boolean strings', () => {
      expect(parseBooleanField('1')).toBe(true);
      expect(parseBooleanField('0')).toBe(false);
    });

    test('returns false for other values', () => {
      expect(parseBooleanField('')).toBe(false);
      expect(parseBooleanField('yes')).toBe(false);
      expect(parseBooleanField('True')).toBe(false); // case-sensitive
    });
  });
});
