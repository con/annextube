/**
 * Zero-dependency WebVTT parser for yt-dlp generated VTT files.
 *
 * Handles simple VTT: `HH:MM:SS.mmm --> HH:MM:SS.mmm` timestamps with plain text.
 * Strips HTML tags, deduplicates overlapping auto-caption cues.
 */

export interface VttCue {
  index: number;       // 0-based sequential
  startTime: number;   // seconds (float)
  endTime: number;     // seconds (float)
  text: string;        // cue text (may contain newlines)
}

/**
 * Parse a VTT timestamp string into seconds.
 * Supports `HH:MM:SS.mmm` and `MM:SS.mmm` formats.
 */
function parseTimestamp(ts: string): number {
  const parts = ts.trim().split(':');
  if (parts.length === 3) {
    const hours = parseInt(parts[0], 10);
    const minutes = parseInt(parts[1], 10);
    const seconds = parseFloat(parts[2]);
    return hours * 3600 + minutes * 60 + seconds;
  } else if (parts.length === 2) {
    const minutes = parseInt(parts[0], 10);
    const seconds = parseFloat(parts[1]);
    return minutes * 60 + seconds;
  }
  return 0;
}

/** Strip HTML tags from cue text */
function stripHtml(text: string): string {
  return text.replace(/<[^>]+>/g, '');
}

const TIMESTAMP_RE = /^(\d{1,2}:)?\d{2}:\d{2}\.\d{3}\s+-->\s+(\d{1,2}:)?\d{2}:\d{2}\.\d{3}/;

/**
 * Parse a WebVTT string into an array of VttCue objects.
 *
 * - Skips `WEBVTT` header and metadata before the first cue
 * - Supports optional cue identifiers (numbers before timestamps)
 * - Collects multi-line cue text, trims trailing whitespace
 * - Strips HTML tags from cue text
 * - Handles CRLF, empty files, trailing blank lines
 * - Deduplicates overlapping auto-caption cues (same text + overlapping times)
 */
export function parseVtt(vttText: string): VttCue[] {
  if (!vttText || !vttText.trim()) return [];

  // Normalize line endings
  const lines = vttText.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');

  const rawCues: VttCue[] = [];
  let i = 0;

  // Skip WEBVTT header and any metadata lines until first blank line or timestamp
  while (i < lines.length) {
    const line = lines[i].trim();
    if (TIMESTAMP_RE.test(line)) break;
    i++;
  }

  // Parse cues
  while (i < lines.length) {
    const line = lines[i].trim();

    // Skip blank lines
    if (!line) {
      i++;
      continue;
    }

    // Check if this is a timestamp line (may be preceded by a cue identifier)
    let timestampLine = line;
    if (!TIMESTAMP_RE.test(line)) {
      // Could be a cue identifier — check next line
      i++;
      if (i < lines.length && TIMESTAMP_RE.test(lines[i].trim())) {
        timestampLine = lines[i].trim();
      } else {
        continue;
      }
    }

    // Parse timestamp
    const arrowIdx = timestampLine.indexOf('-->');
    if (arrowIdx === -1) {
      i++;
      continue;
    }

    const startStr = timestampLine.substring(0, arrowIdx).trim();
    // endTime may have position metadata after it (e.g., "00:01:00.000 position:10%")
    const afterArrow = timestampLine.substring(arrowIdx + 3).trim();
    const endStr = afterArrow.split(/\s+/)[0];

    const startTime = parseTimestamp(startStr);
    const endTime = parseTimestamp(endStr);
    i++;

    // Collect cue text lines until blank line or next timestamp
    const textLines: string[] = [];
    while (i < lines.length) {
      const textLine = lines[i];
      const trimmed = textLine.trim();
      if (trimmed === '') break;
      if (TIMESTAMP_RE.test(trimmed)) break;
      // Check if it's a cue identifier followed by a timestamp
      if (i + 1 < lines.length && TIMESTAMP_RE.test(lines[i + 1].trim())) {
        // This line is a cue identifier for the next cue, stop here
        break;
      }
      textLines.push(trimmed);
      i++;
    }

    const text = stripHtml(textLines.join('\n')).trim();
    if (text) {
      rawCues.push({ index: 0, startTime, endTime, text });
    }
  }

  // Deduplicate YouTube auto-caption cues.
  //
  // YouTube auto-captions use a 3-cue rolling pattern:
  //   Display:  3.600→6.869  [blank]\n Uh<ts> I would like</ts>...  (HTML animation)
  //   Snapshot: 6.869→6.879  "Uh I would like to welcome everyone to"  (10ms, clean)
  //   Display:  6.879→11.27  "Uh I would like...\nthis month's webinar..."  (carry-over + new)
  //   Snapshot: 11.27→11.28  "this month's webinar. Uh we are"           (10ms, clean)
  //
  // After HTML stripping the display cues become multi-line text.
  // We merge adjacent/overlapping cues (<=) that extend each other,
  // then strip carry-over lines (first line of cue N = last line of cue N-1).

  // Pass 1: merge overlapping/adjacent cues
  const deduped: VttCue[] = [];
  for (const cue of rawCues) {
    const prev = deduped[deduped.length - 1];
    if (prev && cue.startTime <= prev.endTime) {
      if (prev.text === cue.text) {
        // Exact duplicate: extend end time
        prev.endTime = Math.max(prev.endTime, cue.endTime);
        continue;
      }
      if (cue.text.startsWith(prev.text)) {
        // Progressive caption: next cue extends previous — keep longer
        prev.text = cue.text;
        prev.endTime = Math.max(prev.endTime, cue.endTime);
        continue;
      }
      if (prev.text.endsWith(cue.text)) {
        // Carry-over: next cue is a suffix of previous — skip it
        continue;
      }
    }
    deduped.push(cue);
  }

  // Pass 2: strip carry-over lines.
  // In the rolling pattern each cue's first line repeats the previous cue's
  // last line.  Remove that redundant first line.
  for (let k = 1; k < deduped.length; k++) {
    const prevLines = deduped[k - 1].text.split('\n');
    const curLines = deduped[k].text.split('\n');
    if (curLines.length > 1 && curLines[0] === prevLines[prevLines.length - 1]) {
      deduped[k].text = curLines.slice(1).join('\n');
    }
  }

  // Re-index
  deduped.forEach((cue, idx) => { cue.index = idx; });

  return deduped;
}
