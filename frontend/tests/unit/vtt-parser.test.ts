import { parseVtt, type VttCue } from '../../src/utils/vtt-parser';
import { formatDuration } from '../../src/utils/format';

/** @ai_generated */
describe('VTT Parser', () => {
  describe('parseVtt', () => {
    test('parses basic VTT with WEBVTT header', () => {
      const vtt = `WEBVTT

00:00:00.000 --> 00:00:05.000
Hello world

00:00:05.000 --> 00:00:10.000
Second cue`;

      const cues = parseVtt(vtt);
      expect(cues).toHaveLength(2);
      expect(cues[0]).toEqual({
        index: 0,
        startTime: 0,
        endTime: 5,
        text: 'Hello world',
      });
      expect(cues[1]).toEqual({
        index: 1,
        startTime: 5,
        endTime: 10,
        text: 'Second cue',
      });
    });

    test('returns empty array for empty input', () => {
      expect(parseVtt('')).toEqual([]);
      expect(parseVtt('   ')).toEqual([]);
      expect(parseVtt('WEBVTT\n\n')).toEqual([]);
    });

    test('handles multi-line cue text', () => {
      const vtt = `WEBVTT

00:00:00.000 --> 00:00:05.000
Line one
Line two
Line three`;

      const cues = parseVtt(vtt);
      expect(cues).toHaveLength(1);
      expect(cues[0].text).toBe('Line one\nLine two\nLine three');
    });

    test('strips HTML tags from cue text', () => {
      const vtt = `WEBVTT

00:00:00.000 --> 00:00:05.000
<b>Bold</b> and <i>italic</i> text

00:00:05.000 --> 00:00:10.000
<font color="white">Colored text</font>`;

      const cues = parseVtt(vtt);
      expect(cues[0].text).toBe('Bold and italic text');
      expect(cues[1].text).toBe('Colored text');
    });

    test('handles CRLF line endings', () => {
      const vtt = 'WEBVTT\r\n\r\n00:00:00.000 --> 00:00:05.000\r\nHello\r\n\r\n00:00:05.000 --> 00:00:10.000\r\nWorld';

      const cues = parseVtt(vtt);
      expect(cues).toHaveLength(2);
      expect(cues[0].text).toBe('Hello');
      expect(cues[1].text).toBe('World');
    });

    test('handles optional cue identifiers (numbers)', () => {
      const vtt = `WEBVTT

1
00:00:00.000 --> 00:00:05.000
First cue

2
00:00:05.000 --> 00:00:10.000
Second cue`;

      const cues = parseVtt(vtt);
      expect(cues).toHaveLength(2);
      expect(cues[0].text).toBe('First cue');
      expect(cues[1].text).toBe('Second cue');
    });

    test('handles MM:SS.mmm format (no hours)', () => {
      const vtt = `WEBVTT

01:30.000 --> 02:00.000
Short format`;

      const cues = parseVtt(vtt);
      expect(cues).toHaveLength(1);
      expect(cues[0].startTime).toBe(90);
      expect(cues[0].endTime).toBe(120);
    });

    test('parses fractional seconds correctly', () => {
      const vtt = `WEBVTT

00:01:23.456 --> 00:02:34.789
Precise timing`;

      const cues = parseVtt(vtt);
      expect(cues[0].startTime).toBeCloseTo(83.456, 3);
      expect(cues[0].endTime).toBeCloseTo(154.789, 3);
    });

    test('deduplicates overlapping auto-caption cues', () => {
      // YouTube auto-captions often repeat text with overlapping timestamps
      const vtt = `WEBVTT

00:00:00.000 --> 00:00:03.000
Hello world

00:00:02.000 --> 00:00:05.000
Hello world

00:00:05.000 --> 00:00:08.000
Different text`;

      const cues = parseVtt(vtt);
      expect(cues).toHaveLength(2);
      expect(cues[0].text).toBe('Hello world');
      expect(cues[0].startTime).toBe(0);
      expect(cues[0].endTime).toBe(5); // Extended to max of overlapping
      expect(cues[1].text).toBe('Different text');
    });

    test('deduplicates progressive auto-caption cues (rolling pattern)', () => {
      // YouTube auto-captions show partial text then extend it
      const vtt = `WEBVTT

00:01:18.000 --> 00:01:21.000
aspects or Yoda principles to be

00:01:18.000 --> 00:01:24.000
aspects or Yoda principles to be precise. And uh another reality kind of

00:01:21.000 --> 00:01:24.000
precise. And uh another reality kind of

00:01:21.000 --> 00:01:27.000
precise. And uh another reality kind of check or disclaimer before you proceed.

00:01:24.000 --> 00:01:27.000
check or disclaimer before you proceed.

00:01:24.000 --> 00:01:30.000
check or disclaimer before you proceed. Uh actually let me see if we can`;

      const cues = parseVtt(vtt);
      // Should collapse each pair to only the longer version
      expect(cues).toHaveLength(3);
      expect(cues[0].text).toBe('aspects or Yoda principles to be precise. And uh another reality kind of');
      expect(cues[0].startTime).toBe(78);
      expect(cues[1].text).toBe('precise. And uh another reality kind of check or disclaimer before you proceed.');
      expect(cues[1].startTime).toBe(81);
      expect(cues[2].text).toBe('check or disclaimer before you proceed. Uh actually let me see if we can');
      expect(cues[2].startTime).toBe(84);
    });

    test('does not deduplicate non-overlapping cues with same text', () => {
      const vtt = `WEBVTT

00:00:00.000 --> 00:00:03.000
Repeated text

00:00:05.000 --> 00:00:08.000
Repeated text`;

      const cues = parseVtt(vtt);
      expect(cues).toHaveLength(2);
    });

    test('handles WEBVTT header with metadata', () => {
      const vtt = `WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:05.000
Caption text`;

      const cues = parseVtt(vtt);
      expect(cues).toHaveLength(1);
      expect(cues[0].text).toBe('Caption text');
    });

    test('handles trailing blank lines', () => {
      const vtt = `WEBVTT

00:00:00.000 --> 00:00:05.000
Only cue


`;

      const cues = parseVtt(vtt);
      expect(cues).toHaveLength(1);
      expect(cues[0].text).toBe('Only cue');
    });

    test('assigns sequential 0-based indices', () => {
      const vtt = `WEBVTT

00:00:00.000 --> 00:00:01.000
A

00:00:01.000 --> 00:00:02.000
B

00:00:02.000 --> 00:00:03.000
C`;

      const cues = parseVtt(vtt);
      expect(cues.map(c => c.index)).toEqual([0, 1, 2]);
    });
  });

  describe('formatDuration integration', () => {
    test('VTT seconds can be formatted with formatDuration', () => {
      // parseVtt gives seconds as floats; Math.floor before formatDuration
      expect(formatDuration(Math.floor(0))).toBe('0:00');
      expect(formatDuration(Math.floor(65.5))).toBe('1:05');
      expect(formatDuration(Math.floor(3661.999))).toBe('1:01:01');
    });
  });
});
