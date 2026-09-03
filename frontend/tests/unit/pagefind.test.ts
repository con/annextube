/**
 * Pagefind Service Unit Tests
 *
 * @ai_generated
 */

import { describe, test, expect, beforeEach, vi } from 'vitest';
import {
  initPagefind,
  searchFull,
  sanitizeExcerpt,
  formatTimestamp,
  _resetForTesting,
  type PagefindResult,
  type PagefindResultData,
  type PagefindInstance,
} from '../../src/services/pagefind';

/** Build a minimal PagefindResultData for testing */
function makeData(overrides: Partial<PagefindResultData> & { meta: Record<string, string> }): PagefindResultData {
  return {
    url: '/videos/abc123/video.en.vtt#t=42',
    content: 'some caption text',
    excerpt: 'some <mark>caption</mark> text',
    filters: {},
    ...overrides,
  };
}

/** Build a PagefindResult whose data() resolves to the given data */
function makeResult(data: PagefindResultData): PagefindResult {
  return {
    id: data.meta?.video_id || 'unknown',
    data: () => Promise.resolve(data),
  };
}

/** Create a mock PagefindInstance with a controllable search function */
function makeMockPagefind(results: PagefindResult[]): PagefindInstance {
  return {
    search: vi.fn().mockResolvedValue({ results }),
  };
}

// ---------- sanitizeExcerpt (XSS in YouTube-sourced excerpts) ----------

describe('sanitizeExcerpt', () => {
  test('keeps Pagefind <mark> highlights', () => {
    expect(sanitizeExcerpt('some <mark>caption</mark> text')).toBe(
      'some <mark>caption</mark> text'
    );
  });

  test('leaves an already-escaped Pagefind excerpt untouched', () => {
    // What Pagefind 1.x actually returns for a description containing
    // `<img src=x onerror=...>` -- it must render as the text the author
    // typed, not as doubly-escaped entities.
    const pagefindExcerpt =
      'Payload &lt;img src=x onerror="alert(1)"&gt; <mark>ambush</mark>';
    expect(sanitizeExcerpt(pagefindExcerpt)).toBe(pagefindExcerpt);
  });

  test('escapes raw markup should an excerpt ever carry it', () => {
    const safe = sanitizeExcerpt('see <img src=x onerror=alert(1)> now');
    expect(safe).toBe('see &lt;img src=x onerror=alert(1)&gt; now');
    expect(safe).not.toContain('<img');
  });

  test('escapes a raw script tag around a highlight', () => {
    expect(sanitizeExcerpt('<script>alert(1)</script> <mark>hit</mark>')).toBe(
      '&lt;script&gt;alert(1)&lt;/script&gt; <mark>hit</mark>'
    );
  });

  test('does not touch ampersands (entities cannot form elements)', () => {
    expect(sanitizeExcerpt('a & b "q" <mark>c</mark>')).toBe(
      'a & b "q" <mark>c</mark>'
    );
  });

  test('a mark tag carrying attributes is escaped, not rendered', () => {
    expect(sanitizeExcerpt('<mark onmouseover=alert(1)>x</mark>')).toBe(
      '&lt;mark onmouseover=alert(1)&gt;x</mark>'
    );
  });

  test('literal <mark> text in a description is inert markup at worst', () => {
    // Restoring it can only ever produce a bare <mark> element
    expect(sanitizeExcerpt('I typed <mark> myself')).toBe('I typed <mark> myself');
  });
});

describe('searchFull sanitizes excerpts at the boundary', () => {
  beforeEach(() => {
    _resetForTesting(null);
  });

  test('description and caption excerpts are sanitized', async () => {
    const attack = '<img src=x onerror=alert(1)> <mark>hit</mark>';
    const meta = { video_id: 'abc123', title: 'T' };
    const metadataRecord = makeData({
      url: '#/video/abc123',
      excerpt: attack,
      meta: { ...meta, record_type: 'metadata' },
    });
    const captionRecord = makeData({
      url: '/videos/abc123/video.en.vtt#t=10',
      excerpt: attack,
      meta: { ...meta, record_type: 'caption' },
    });
    _resetForTesting(
      makeMockPagefind([makeResult(metadataRecord), makeResult(captionRecord)])
    );

    const groups = await searchFull('hit');

    const expected = '&lt;img src=x onerror=alert(1)&gt; <mark>hit</mark>';
    expect(groups[0].descriptionMatch?.excerpt).toBe(expected);
    expect(groups[0].allMatches[0].excerpt).toBe(expected);
    // primaryExcerpt is taken from those, so it is sanitized too
    expect(groups[0].primaryExcerpt).toBe(expected);
  });
});

// ---------- formatTimestamp ----------

describe('formatTimestamp', () => {
  test('formats 0 as 00:00', () => {
    expect(formatTimestamp(0)).toBe('00:00');
  });

  test('formats seconds under a minute', () => {
    expect(formatTimestamp(5)).toBe('00:05');
    expect(formatTimestamp(59)).toBe('00:59');
  });

  test('formats minutes and seconds', () => {
    expect(formatTimestamp(65)).toBe('01:05');
    expect(formatTimestamp(600)).toBe('10:00');
    expect(formatTimestamp(3599)).toBe('59:59');
  });

  test('formats hours when >= 3600', () => {
    expect(formatTimestamp(3600)).toBe('1:00:00');
    expect(formatTimestamp(3661)).toBe('1:01:01');
    expect(formatTimestamp(7200)).toBe('2:00:00');
    expect(formatTimestamp(36000)).toBe('10:00:00');
  });

  test('floors fractional seconds', () => {
    expect(formatTimestamp(65.7)).toBe('01:05');
    expect(formatTimestamp(3661.9)).toBe('1:01:01');
  });

  test('formats mixed hour:min:sec', () => {
    expect(formatTimestamp(3723)).toBe('1:02:03');
  });
});

// ---------- initPagefind ----------

describe('initPagefind', () => {
  beforeEach(() => {
    _resetForTesting();
  });

  test('returns false when pagefind.js is not available', async () => {
    // Without an actual /pagefind/pagefind.js the dynamic import will fail
    const result = await initPagefind();
    expect(result).toBe(false);
  });

  test('caches the result so subsequent calls do not retry', async () => {
    const result1 = await initPagefind();
    expect(result1).toBe(false);

    // Second call returns cached false without re-attempting
    const result2 = await initPagefind();
    expect(result2).toBe(false);
  });

  test('returns true when a mock instance is injected', async () => {
    const mock = makeMockPagefind([]);
    _resetForTesting(mock);
    // initPagefind should see the pre-loaded instance
    const result = await initPagefind();
    expect(result).toBe(true);
  });
});

// ---------- searchFull ----------

describe('searchFull', () => {
  beforeEach(() => {
    _resetForTesting();
  });

  test('returns empty array for empty query', async () => {
    const mock = makeMockPagefind([]);
    _resetForTesting(mock);

    const results = await searchFull('');
    expect(results).toEqual([]);
  });

  test('returns empty array for whitespace-only query', async () => {
    const mock = makeMockPagefind([]);
    _resetForTesting(mock);

    const results = await searchFull('   ');
    expect(results).toEqual([]);
  });

  test('returns empty array when pagefind is not available', async () => {
    // _resetForTesting() was called without a mock, so pagefind is unavailable
    const results = await searchFull('test query');
    expect(results).toEqual([]);
  });

  test('groups results by video_id from meta', async () => {
    const d1 = makeData({
      url: '/videos/vid1/video.en.vtt#t=10',
      excerpt: 'first <mark>match</mark>',
      meta: { video_id: 'vid1', title: 'Video One', channel_name: 'Ch A', upload_date: '2024-01-01', thumbnail_url: 'th1.jpg' },
    });
    const d2 = makeData({
      url: '/videos/vid2/video.en.vtt#t=30',
      excerpt: '<mark>match</mark> in vid2',
      meta: { video_id: 'vid2', title: 'Video Two', channel_name: 'Ch B', upload_date: '2024-02-01', thumbnail_url: 'th2.jpg' },
    });
    const d3 = makeData({
      url: '/videos/vid1/video.en.vtt#t=50',
      excerpt: 'second <mark>match</mark>',
      meta: { video_id: 'vid1', title: 'Video One', channel_name: 'Ch A', upload_date: '2024-01-01', thumbnail_url: 'th1.jpg' },
    });

    const mock = makeMockPagefind([makeResult(d1), makeResult(d2), makeResult(d3)]);
    _resetForTesting(mock);

    const results = await searchFull('match');

    // Should produce 2 groups: vid1 (first seen) and vid2
    expect(results).toHaveLength(2);

    // First group: vid1
    expect(results[0].videoId).toBe('vid1');
    expect(results[0].title).toBe('Video One');
    expect(results[0].channelName).toBe('Ch A');
    expect(results[0].matchCount).toBe(2);

    // Second group: vid2
    expect(results[1].videoId).toBe('vid2');
    expect(results[1].title).toBe('Video Two');
    expect(results[1].matchCount).toBe(1);
  });

  test('sorts matches within a group by timestamp (earliest first)', async () => {
    // Send results in reverse timestamp order to verify sorting
    const d1 = makeData({
      url: '/videos/vid1/video.en.vtt#t=90',
      excerpt: 'late match',
      meta: { video_id: 'vid1', title: 'V', channel_name: 'C', upload_date: '', thumbnail_url: '' },
    });
    const d2 = makeData({
      url: '/videos/vid1/video.en.vtt#t=5',
      excerpt: 'early match',
      meta: { video_id: 'vid1', title: 'V', channel_name: 'C', upload_date: '', thumbnail_url: '' },
    });
    const d3 = makeData({
      url: '/videos/vid1/video.en.vtt#t=45',
      excerpt: 'middle match',
      meta: { video_id: 'vid1', title: 'V', channel_name: 'C', upload_date: '', thumbnail_url: '' },
    });

    const mock = makeMockPagefind([makeResult(d1), makeResult(d2), makeResult(d3)]);
    _resetForTesting(mock);

    const results = await searchFull('match');
    expect(results).toHaveLength(1);

    const group = results[0];
    expect(group.matchCount).toBe(3);
    expect(group.allMatches[0].timestamp).toBe(5);
    expect(group.allMatches[1].timestamp).toBe(45);
    expect(group.allMatches[2].timestamp).toBe(90);

    // Primary match should be the earliest
    expect(group.primaryTimestamp).toBe(5);
    expect(group.primaryExcerpt).toBe('early match');
  });

  test('preserves group order based on Pagefind result ordering (relevance)', async () => {
    // vid2 appears first in Pagefind results = more relevant
    const d1 = makeData({
      url: '/videos/vid2/video.en.vtt#t=10',
      excerpt: 'relevant',
      meta: { video_id: 'vid2', title: 'V2', channel_name: 'C', upload_date: '', thumbnail_url: '' },
    });
    const d2 = makeData({
      url: '/videos/vid1/video.en.vtt#t=20',
      excerpt: 'less relevant',
      meta: { video_id: 'vid1', title: 'V1', channel_name: 'C', upload_date: '', thumbnail_url: '' },
    });

    const mock = makeMockPagefind([makeResult(d1), makeResult(d2)]);
    _resetForTesting(mock);

    const results = await searchFull('test');
    expect(results[0].videoId).toBe('vid2');
    expect(results[1].videoId).toBe('vid1');
  });

  test('skips results without video_id in meta', async () => {
    const d1 = makeData({
      url: '/some/path',
      excerpt: 'no video id',
      meta: { title: 'Orphan' },
    });
    const d2 = makeData({
      url: '/videos/vid1/video.en.vtt#t=10',
      excerpt: 'has video id',
      meta: { video_id: 'vid1', title: 'V1', channel_name: 'C', upload_date: '', thumbnail_url: '' },
    });

    const mock = makeMockPagefind([makeResult(d1), makeResult(d2)]);
    _resetForTesting(mock);

    const results = await searchFull('test');
    expect(results).toHaveLength(1);
    expect(results[0].videoId).toBe('vid1');
  });

  test('parses timestamps from URL fragment', async () => {
    const d1 = makeData({
      url: '/videos/vid1/video.en.vtt#t=123',
      excerpt: 'at 2:03',
      meta: { video_id: 'vid1', title: 'V', channel_name: 'C', upload_date: '', thumbnail_url: '' },
    });

    const mock = makeMockPagefind([makeResult(d1)]);
    _resetForTesting(mock);

    const results = await searchFull('test');
    expect(results[0].primaryTimestamp).toBe(123);
  });

  test('defaults timestamp to 0 when URL has no fragment', async () => {
    const d1 = makeData({
      url: '/videos/vid1/video.en.vtt',
      excerpt: 'no timestamp',
      meta: { video_id: 'vid1', title: 'V', channel_name: 'C', upload_date: '', thumbnail_url: '' },
    });

    const mock = makeMockPagefind([makeResult(d1)]);
    _resetForTesting(mock);

    const results = await searchFull('test');
    expect(results[0].primaryTimestamp).toBe(0);
  });

  test('passes filters to pagefind search', async () => {
    const searchFn = vi.fn().mockResolvedValue({ results: [] });
    const mock: PagefindInstance = { search: searchFn };
    _resetForTesting(mock);

    const filters = { language: ['en'] };
    await searchFull('test', filters);

    expect(searchFn).toHaveBeenCalledWith('test', { filters });
  });
});

// ---------- metadata records (FR-042f) ----------

describe('searchFull with metadata records', () => {
  beforeEach(() => {
    _resetForTesting();
  });

  function makeMetadataData(videoId: string, excerpt: string): PagefindResultData {
    return makeData({
      url: `#/video/${videoId}`,
      excerpt,
      meta: {
        video_id: videoId,
        title: `Title ${videoId}`,
        channel_name: 'Ch',
        upload_date: '2024-01-01',
        record_type: 'metadata',
      },
    });
  }

  function makeCaptionData(
    videoId: string, t: number, excerpt: string
  ): PagefindResultData {
    return makeData({
      url: `#/video/${videoId}?t=${t}`,
      excerpt,
      meta: {
        video_id: videoId,
        title: `Title ${videoId}`,
        channel_name: 'Ch',
        upload_date: '2024-01-01',
        record_type: 'caption',
      },
    });
  }

  test('description-only match produces a group without caption matches', async () => {
    const mock = makeMockPagefind([
      makeResult(makeMetadataData('vid1', 'by <mark>Halchenko</mark>')),
    ]);
    _resetForTesting(mock);

    const results = await searchFull('Halchenko');

    expect(results).toHaveLength(1);
    const group = results[0];
    expect(group.videoId).toBe('vid1');
    expect(group.descriptionMatch?.excerpt).toBe('by <mark>Halchenko</mark>');
    expect(group.allMatches).toHaveLength(0);
    expect(group.matchCount).toBe(1);
    // No timestamp for a description match
    expect(group.primaryTimestamp).toBe(-1);
    expect(group.primaryExcerpt).toBe('by <mark>Halchenko</mark>');
  });

  test('metadata and caption matches merge into one group', async () => {
    const mock = makeMockPagefind([
      makeResult(makeMetadataData('vid1', 'description <mark>hit</mark>')),
      makeResult(makeCaptionData('vid1', 42, 'caption <mark>hit</mark>')),
    ]);
    _resetForTesting(mock);

    const results = await searchFull('hit');

    expect(results).toHaveLength(1);
    const group = results[0];
    expect(group.descriptionMatch?.excerpt).toBe('description <mark>hit</mark>');
    expect(group.allMatches).toHaveLength(1);
    expect(group.matchCount).toBe(2);
    // Primary stays the earliest caption match when captions matched
    expect(group.primaryTimestamp).toBe(42);
    expect(group.primaryExcerpt).toBe('caption <mark>hit</mark>');
  });

  test('records without record_type are treated as captions (old indexes)', async () => {
    const mock = makeMockPagefind([
      makeResult(makeData({
        url: '/videos/vid1/video.en.vtt#t=10',
        excerpt: 'legacy record',
        meta: { video_id: 'vid1', title: 'V', channel_name: 'C', upload_date: '' },
      })),
    ]);
    _resetForTesting(mock);

    const results = await searchFull('legacy');

    expect(results).toHaveLength(1);
    expect(results[0].descriptionMatch).toBeUndefined();
    expect(results[0].allMatches).toHaveLength(1);
    expect(results[0].matchCount).toBe(1);
  });
});

// ---------- approximate match detection ----------
//
// Pagefind never returns zero results for a query it half-knows: for
// "reprostim" it returns every chunk containing "repro" (the indexed
// word is a truncation of the query). balanced_score tiers observed
// with pagefind 1.x: ~512 whole-word/stemmed, ~389 query-is-prefix,
// ~221 truncated-word fallback. Only the last is approximate.

describe('searchFull approximate detection', () => {
  beforeEach(() => {
    _resetForTesting();
  });

  const meta = { video_id: 'vid1', title: 'V', channel_name: 'C', upload_date: '', thumbnail_url: '' };

  function locations(...scores: number[]) {
    return scores.map((balanced_score, i) => ({ weight: 1, balanced_score, location: i }));
  }

  test('flags truncated-word fallback as approximate (query "reprostim" matching only "repro")', async () => {
    const d = makeData({
      content: 'the repro nim project',
      excerpt: 'the <mark>repro</mark> nim project',
      meta,
      weighted_locations: locations(221.42),
    });
    _resetForTesting(makeMockPagefind([makeResult(d)]));

    const results = await searchFull('reprostim');
    expect(results).toHaveLength(1);
    expect(results[0].approximate).toBe(true);
  });

  test('whole-word and stemmed matches are genuine ("pizzas" finding "pizza")', async () => {
    const d = makeData({
      content: 'we ate pizza today',
      excerpt: 'we ate <mark>pizza</mark> today',
      meta,
      weighted_locations: locations(512.14),
    });
    _resetForTesting(makeMockPagefind([makeResult(d)]));

    const results = await searchFull('pizzas');
    expect(results[0].approximate).toBe(false);
  });

  test('prefix queries are genuine ("datala" finding "datalad")', async () => {
    const d = makeData({
      content: 'install datalad first',
      excerpt: 'install <mark>datalad</mark> first',
      meta,
      weighted_locations: locations(388.63),
    });
    _resetForTesting(makeMockPagefind([makeResult(d)]));

    const results = await searchFull('datala');
    expect(results[0].approximate).toBe(false);
  });

  test('results without weighted_locations are treated as genuine', async () => {
    const d = makeData({ meta });
    _resetForTesting(makeMockPagefind([makeResult(d)]));

    const results = await searchFull('caption');
    expect(results[0].approximate).toBe(false);
  });

  test('results with an empty weighted_locations array are approximate', async () => {
    // A record can match with no word-level evidence -- e.g. a metadata
    // record hit only via a tag. Distinct from the field being absent.
    const d = makeData({ meta, weighted_locations: [] });
    _resetForTesting(makeMockPagefind([makeResult(d)]));

    const results = await searchFull('reprostim');
    expect(results[0].approximate).toBe(true);
  });

  test('one genuine chunk makes the whole video genuine; approximate-only videos stay flagged', async () => {
    const approx1 = makeData({
      url: '/videos/vid1/video.en.vtt#t=10',
      meta,
      weighted_locations: locations(221.42),
    });
    const genuine = makeData({
      url: '/videos/vid1/video.en.vtt#t=50',
      meta,
      weighted_locations: locations(221.42, 512.14),
    });
    const approx2 = makeData({
      url: '/videos/vid2/video.en.vtt#t=20',
      meta: { ...meta, video_id: 'vid2' },
      weighted_locations: locations(221.42),
    });
    _resetForTesting(makeMockPagefind([makeResult(approx1), makeResult(genuine), makeResult(approx2)]));

    const results = await searchFull('reprostim');
    expect(results).toHaveLength(2);
    expect(results[0].videoId).toBe('vid1');
    expect(results[0].approximate).toBe(false);
    expect(results[1].videoId).toBe('vid2');
    expect(results[1].approximate).toBe(true);
  });

  test('orders genuine videos before approximate ones regardless of Pagefind order', async () => {
    const approx = makeData({
      url: '/videos/loose/video.en.vtt#t=10',
      meta: { ...meta, video_id: 'loose' },
      weighted_locations: locations(221.42),
    });
    const genuine = makeData({
      url: '/videos/tight/video.en.vtt#t=20',
      meta: { ...meta, video_id: 'tight' },
      weighted_locations: locations(512.14),
    });
    // Pagefind ranks the approximate video first (e.g. more fallback hits)
    _resetForTesting(makeMockPagefind([makeResult(approx), makeResult(genuine)]));

    const results = await searchFull('reprostim');
    expect(results.map((r) => r.videoId)).toEqual(['tight', 'loose']);
  });
});
