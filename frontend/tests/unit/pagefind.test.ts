/**
 * Pagefind Service Unit Tests
 *
 * @ai_generated
 */

import { describe, test, expect, beforeEach, vi } from 'vitest';
import {
  initPagefind,
  searchCaptions,
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

// ---------- searchCaptions ----------

describe('searchCaptions', () => {
  beforeEach(() => {
    _resetForTesting();
  });

  test('returns empty array for empty query', async () => {
    const mock = makeMockPagefind([]);
    _resetForTesting(mock);

    const results = await searchCaptions('');
    expect(results).toEqual([]);
  });

  test('returns empty array for whitespace-only query', async () => {
    const mock = makeMockPagefind([]);
    _resetForTesting(mock);

    const results = await searchCaptions('   ');
    expect(results).toEqual([]);
  });

  test('returns empty array when pagefind is not available', async () => {
    // _resetForTesting() was called without a mock, so pagefind is unavailable
    const results = await searchCaptions('test query');
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

    const results = await searchCaptions('match');

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

    const results = await searchCaptions('match');
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

    const results = await searchCaptions('test');
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

    const results = await searchCaptions('test');
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

    const results = await searchCaptions('test');
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

    const results = await searchCaptions('test');
    expect(results[0].primaryTimestamp).toBe(0);
  });

  test('passes filters to pagefind search', async () => {
    const searchFn = vi.fn().mockResolvedValue({ results: [] });
    const mock: PagefindInstance = { search: searchFn };
    _resetForTesting(mock);

    const filters = { language: ['en'] };
    await searchCaptions('test', filters);

    expect(searchFn).toHaveBeenCalledWith('test', { filters });
  });
});
