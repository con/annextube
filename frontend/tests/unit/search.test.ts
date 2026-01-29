/**
 * SearchService Unit Tests
 */

import { describe, test, expect, beforeEach } from '@jest/globals';
import { SearchService } from '../../src/services/search';
import type { Video } from '../../src/types/models';

describe('SearchService', () => {
  let searchService: SearchService;
  let mockVideos: Video[];

  beforeEach(() => {
    searchService = new SearchService();

    // Create mock videos for testing
    mockVideos = [
      {
        video_id: '1',
        title: 'PSY - GANGNAM STYLE',
        channel_id: 'UC1',
        channel_name: 'officialpsy',
        published_at: '2012-07-15T00:00:00Z',
        duration: 252,
        view_count: 4800000000,
        like_count: 28000000,
        comment_count: 4200000,
        thumbnail_url: 'https://example.com/thumb1.jpg',
        license: 'standard',
        privacy_status: 'public',
        availability: 'public',
        tags: ['kpop', 'dance', 'music'],
        categories: ['Music'],
        captions_available: ['en'],
        has_auto_captions: true,
        download_status: 'tracked',
        source_url: 'https://youtube.com/watch?v=1',
        fetched_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      {
        video_id: '2',
        title: 'Never Gonna Give You Up',
        channel_id: 'UC2',
        channel_name: 'Rick Astley',
        published_at: '2009-10-25T00:00:00Z',
        duration: 213,
        view_count: 1420000000,
        like_count: 14000000,
        comment_count: 850000,
        thumbnail_url: 'https://example.com/thumb2.jpg',
        license: 'standard',
        privacy_status: 'public',
        availability: 'public',
        tags: ['music', 'rickroll', '80s'],
        categories: ['Music'],
        captions_available: [],
        has_auto_captions: false,
        download_status: 'downloaded',
        source_url: 'https://youtube.com/watch?v=2',
        fetched_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      {
        video_id: '3',
        title: 'Baby Shark Dance',
        channel_id: 'UC3',
        channel_name: 'Pinkfong',
        published_at: '2016-06-17T00:00:00Z',
        duration: 136,
        view_count: 14000000000,
        like_count: 42000000,
        comment_count: 1200000,
        thumbnail_url: 'https://example.com/thumb3.jpg',
        license: 'standard',
        privacy_status: 'public',
        availability: 'public',
        tags: ['kids', 'children', 'dance'],
        categories: ['Education'],
        captions_available: ['en', 'es'],
        has_auto_captions: true,
        download_status: 'tracked',
        source_url: 'https://youtube.com/watch?v=3',
        fetched_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    ];
  });

  test('initializes search index', () => {
    searchService.initialize(mockVideos);
    expect(searchService.getIndexedCount()).toBe(3);
  });

  test('returns all videos when query is empty', () => {
    searchService.initialize(mockVideos);
    const results = searchService.search('');
    expect(results.length).toBe(3);
    expect(results[0].score).toBe(0);  // No scoring for empty query
  });

  test('returns all videos when query is only whitespace', () => {
    searchService.initialize(mockVideos);
    const results = searchService.search('   ');
    expect(results.length).toBe(3);
  });

  test('searches by title (fuzzy match)', () => {
    searchService.initialize(mockVideos);
    const results = searchService.search('gangnam');
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].video.title).toContain('GANGNAM');
  });

  test('searches by title (case insensitive)', () => {
    searchService.initialize(mockVideos);
    const results = searchService.search('GANGNAM');
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].video.title).toContain('GANGNAM');
  });

  test('searches by channel name', () => {
    searchService.initialize(mockVideos);
    const results = searchService.search('Rick Astley');
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].video.channel_name).toBe('Rick Astley');
  });

  test('searches by tags', () => {
    searchService.initialize(mockVideos);
    const results = searchService.search('kpop');
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].video.tags).toContain('kpop');
  });

  test('handles typos (fuzzy matching)', () => {
    searchService.initialize(mockVideos);
    // "gangam" is a typo for "gangnam"
    const results = searchService.search('gangam');
    expect(results.length).toBeGreaterThan(0);
    // Should still find GANGNAM STYLE
    const hasGangnam = results.some(r => r.video.title.includes('GANGNAM'));
    expect(hasGangnam).toBe(true);
  });

  test('returns results sorted by relevance (best match first)', () => {
    searchService.initialize(mockVideos);
    const results = searchService.search('dance');
    expect(results.length).toBeGreaterThanOrEqual(2);  // Baby Shark Dance and GANGNAM STYLE both have "dance"
    // First result should have lower score (better match)
    if (results.length > 1) {
      expect(results[0].score).toBeLessThanOrEqual(results[1].score);
    }
  });

  test('limits results when limit option provided', () => {
    searchService.initialize(mockVideos);
    const results = searchService.search('music', { limit: 1 });
    expect(results.length).toBe(1);
  });

  test('includes matched fields in results', () => {
    searchService.initialize(mockVideos);
    const results = searchService.search('gangnam');
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].matches.length).toBeGreaterThan(0);
  });

  test('clears search index', () => {
    searchService.initialize(mockVideos);
    expect(searchService.getIndexedCount()).toBe(3);
    searchService.clear();
    expect(searchService.getIndexedCount()).toBe(0);
  });

  test('returns empty array after clearing when searching', () => {
    searchService.initialize(mockVideos);
    searchService.clear();
    const results = searchService.search('gangnam');
    expect(results.length).toBe(0);
  });

  test('handles empty video list', () => {
    searchService.initialize([]);
    const results = searchService.search('test');
    expect(results.length).toBe(0);
  });

  test('handles special characters in query', () => {
    searchService.initialize(mockVideos);
    const results = searchService.search('PSY - GANGNAM');
    expect(results.length).toBeGreaterThan(0);
  });
});
