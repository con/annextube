/**
 * CaptionSearchResults Component Unit Tests
 *
 * @ai_generated
 */

import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, fireEvent, act } from '@testing-library/svelte';
import { tick } from 'svelte';
import CaptionSearchResults from '../../src/components/CaptionSearchResults.svelte';
import type { GroupedCaptionResult } from '../../src/services/pagefind';

/** Build a minimal GroupedCaptionResult for testing */
function makeResult(overrides: Partial<GroupedCaptionResult> = {}): GroupedCaptionResult {
  return {
    videoId: 'vid1',
    title: 'Test Video Title',
    channelName: 'Test Channel',
    uploadDate: '2024-01-15',
    thumbnailUrl: 'https://example.com/thumb.jpg',
    matchCount: 1,
    primaryExcerpt: 'some <mark>test</mark> caption text',
    primaryTimestamp: 42,
    primaryUrl: '/videos/vid1/video.en.vtt#t=42',
    allMatches: [
      {
        excerpt: 'some <mark>test</mark> caption text',
        timestamp: 42,
        url: '/videos/vid1/video.en.vtt#t=42',
      },
    ],
    ...overrides,
  };
}

describe('CaptionSearchResults', () => {
  beforeEach(() => {
    // Reset location hash
    window.location.hash = '';
  });

  test('renders loading state when loading is true', () => {
    const { container } = render(CaptionSearchResults, {
      props: {
        results: [],
        query: 'test',
        loading: true,
      },
    });

    const loadingEl = container.querySelector('.loading-state');
    expect(loadingEl).not.toBeNull();
    expect(loadingEl?.textContent).toContain('Searching captions');
  });

  test('renders empty state when query is set but no results', () => {
    const { container } = render(CaptionSearchResults, {
      props: {
        results: [],
        query: 'nonexistent phrase',
        loading: false,
      },
    });

    const emptyEl = container.querySelector('.empty-state');
    expect(emptyEl).not.toBeNull();
    expect(emptyEl?.textContent).toContain("No caption matches found for 'nonexistent phrase'");
  });

  test('does not render empty state when query is empty', () => {
    const { container } = render(CaptionSearchResults, {
      props: {
        results: [],
        query: '',
        loading: false,
      },
    });

    const emptyEl = container.querySelector('.empty-state');
    expect(emptyEl).toBeNull();
  });

  test('renders result cards with title, excerpt, and timestamp', () => {
    const results = [
      makeResult({
        videoId: 'vid1',
        title: 'My Great Video',
        channelName: 'Cool Channel',
        uploadDate: '2024-03-15',
        primaryTimestamp: 125,
        primaryExcerpt: 'a <mark>matching</mark> line',
      }),
    ];

    const { container } = render(CaptionSearchResults, {
      props: { results, query: 'matching', loading: false },
    });

    // Title
    const title = container.querySelector('.result-title');
    expect(title?.textContent).toBe('My Great Video');

    // Channel name
    const channel = container.querySelector('.channel-name');
    expect(channel?.textContent).toBe('Cool Channel');

    // Timestamp badge -- 125s = 02:05
    const timestamp = container.querySelector('.timestamp-badge');
    expect(timestamp?.textContent).toBe('02:05');

    // Excerpt with mark highlight
    const excerpt = container.querySelector('.result-excerpt');
    expect(excerpt?.innerHTML).toContain('<mark>matching</mark>');
  });

  test('shows match count badge for multi-match videos', () => {
    const results = [
      makeResult({
        matchCount: 5,
        allMatches: [
          { excerpt: 'match 1', timestamp: 10, url: '#t=10' },
          { excerpt: 'match 2', timestamp: 20, url: '#t=20' },
          { excerpt: 'match 3', timestamp: 30, url: '#t=30' },
          { excerpt: 'match 4', timestamp: 40, url: '#t=40' },
          { excerpt: 'match 5', timestamp: 50, url: '#t=50' },
        ],
      }),
    ];

    const { container } = render(CaptionSearchResults, {
      props: { results, query: 'test', loading: false },
    });

    const badge = container.querySelector('.match-count-badge');
    expect(badge).not.toBeNull();
    expect(badge?.textContent).toContain('5 matches');
  });

  test('does not show match count badge for single-match videos', () => {
    const results = [makeResult({ matchCount: 1 })];

    const { container } = render(CaptionSearchResults, {
      props: { results, query: 'test', loading: false },
    });

    const badge = container.querySelector('.match-count-badge');
    expect(badge).toBeNull();
  });

  test('clicking a result navigates with correct URL params', async () => {
    const results = [
      makeResult({
        videoId: 'abc123',
        primaryTimestamp: 90,
      }),
    ];

    const { container } = render(CaptionSearchResults, {
      props: { results, query: 'hello world', loading: false },
    });

    const resultMain = container.querySelector('.result-main');
    expect(resultMain).not.toBeNull();

    await fireEvent.click(resultMain!);

    // Check that the hash was set correctly
    expect(window.location.hash).toBe('#/video/abc123?t=90&q=hello%20world&filter=1&autoplay=1');
  });

  test('shows result count header', () => {
    const results = [
      makeResult({ videoId: 'vid1' }),
      makeResult({ videoId: 'vid2', title: 'Another Video' }),
    ];

    const { container } = render(CaptionSearchResults, {
      props: { results, query: 'test', loading: false },
    });

    const header = container.querySelector('.result-count');
    expect(header?.textContent).toContain('2 videos with caption matches');
  });

  test('singular form for single video result', () => {
    const results = [makeResult()];

    const { container } = render(CaptionSearchResults, {
      props: { results, query: 'test', loading: false },
    });

    const header = container.querySelector('.result-count');
    expect(header?.textContent).toContain('1 video with caption matches');
  });

  test('expands match list when badge is clicked', async () => {
    const results = [
      makeResult({
        matchCount: 3,
        allMatches: [
          { excerpt: 'match at 10s', timestamp: 10, url: '#t=10' },
          { excerpt: 'match at 30s', timestamp: 30, url: '#t=30' },
          { excerpt: 'match at 60s', timestamp: 60, url: '#t=60' },
        ],
      }),
    ];

    const { container } = render(CaptionSearchResults, {
      props: { results, query: 'test', loading: false },
    });

    // Expanded matches should not be visible initially
    let expanded = container.querySelector('.expanded-matches');
    expect(expanded).toBeNull();

    // Click the badge to expand
    const badge = container.querySelector('.match-count-badge');
    await fireEvent.click(badge!);
    await tick();

    // Now expanded matches should be visible
    expanded = container.querySelector('.expanded-matches');
    expect(expanded).not.toBeNull();

    const matchItems = expanded!.querySelectorAll('.match-item');
    expect(matchItems).toHaveLength(3);
  });

  test('shows "Show more" button when more than 10 results', () => {
    const results = Array.from({ length: 15 }, (_, i) =>
      makeResult({ videoId: `vid${i}`, title: `Video ${i}` })
    );

    const { container } = render(CaptionSearchResults, {
      props: { results, query: 'test', loading: false },
    });

    // Should show only first 10 results
    const cards = container.querySelectorAll('.result-card');
    expect(cards).toHaveLength(10);

    // Should show "Show more" button
    const showMore = container.querySelector('.show-more-button');
    expect(showMore).not.toBeNull();
    expect(showMore?.textContent).toContain('5 remaining');
  });

  test('clicking "Show more" loads additional results', async () => {
    const results = Array.from({ length: 15 }, (_, i) =>
      makeResult({ videoId: `vid${i}`, title: `Video ${i}` })
    );

    const { container } = render(CaptionSearchResults, {
      props: { results, query: 'test', loading: false },
    });

    const showMore = container.querySelector('.show-more-button');
    await fireEvent.click(showMore!);

    // Now all 15 results should be visible
    const cards = container.querySelectorAll('.result-card');
    expect(cards).toHaveLength(15);

    // "Show more" button should be gone
    const showMoreAfter = container.querySelector('.show-more-button');
    expect(showMoreAfter).toBeNull();
  });

  test('formats upload date correctly', () => {
    const results = [
      makeResult({
        uploadDate: '2024-03-15',
      }),
    ];

    const { container } = render(CaptionSearchResults, {
      props: { results, query: 'test', loading: false },
    });

    const dateEl = container.querySelector('.upload-date');
    expect(dateEl?.textContent).toBe('Mar 15, 2024');
  });

  test('handles YYYYMMDD date format', () => {
    const results = [
      makeResult({
        uploadDate: '20240315',
      }),
    ];

    const { container } = render(CaptionSearchResults, {
      props: { results, query: 'test', loading: false },
    });

    const dateEl = container.querySelector('.upload-date');
    expect(dateEl?.textContent).toBe('Mar 15, 2024');
  });
});
