/**
 * SortService Unit Tests
 */

import { describe, test, expect } from '@jest/globals';
import { SortService } from '../../src/services/sort';
import type { Video } from '../../src/types/models';

describe('SortService', () => {
  const mockVideos: Video[] = [
    {
      video_id: '1',
      title: 'Zebra Video',
      channel_id: 'CH1',
      channel_name: 'Channel',
      published_at: '2024-03-01T00:00:00Z',
      duration: 300,
      view_count: 1000,
      like_count: 50,
      comment_count: 10,
      thumbnail_url: '',
      license: 'standard',
      privacy_status: 'public',
      availability: 'public',
      tags: [],
      categories: [],
      captions_available: [],
      has_auto_captions: false,
      download_status: 'tracked',
      source_url: '',
      fetched_at: '',
      updated_at: '',
    },
    {
      video_id: '2',
      title: 'Apple Video',
      channel_id: 'CH1',
      channel_name: 'Channel',
      published_at: '2024-01-01T00:00:00Z',
      duration: 600,
      view_count: 5000,
      like_count: 200,
      comment_count: 50,
      thumbnail_url: '',
      license: 'standard',
      privacy_status: 'public',
      availability: 'public',
      tags: [],
      categories: [],
      captions_available: [],
      has_auto_captions: false,
      download_status: 'tracked',
      source_url: '',
      fetched_at: '',
      updated_at: '',
    },
  ];

  const sortService = new SortService();

  test('sorts by views ascending', () => {
    const sorted = sortService.sort(mockVideos, {
      field: 'views',
      direction: 'asc',
    });
    expect(sorted[0].view_count).toBe(1000);
    expect(sorted[1].view_count).toBe(5000);
  });

  test('sorts by views descending', () => {
    const sorted = sortService.sort(mockVideos, {
      field: 'views',
      direction: 'desc',
    });
    expect(sorted[0].view_count).toBe(5000);
    expect(sorted[1].view_count).toBe(1000);
  });

  test('sorts by date ascending', () => {
    const sorted = sortService.sort(mockVideos, {
      field: 'date',
      direction: 'asc',
    });
    expect(sorted[0].published_at).toBe('2024-01-01T00:00:00Z');
    expect(sorted[1].published_at).toBe('2024-03-01T00:00:00Z');
  });

  test('sorts by duration ascending', () => {
    const sorted = sortService.sort(mockVideos, {
      field: 'duration',
      direction: 'asc',
    });
    expect(sorted[0].duration).toBe(300);
    expect(sorted[1].duration).toBe(600);
  });

  test('sorts by title ascending', () => {
    const sorted = sortService.sort(mockVideos, {
      field: 'title',
      direction: 'asc',
    });
    expect(sorted[0].title).toBe('Apple Video');
    expect(sorted[1].title).toBe('Zebra Video');
  });

  test('does not mutate original array', () => {
    const original = [...mockVideos];
    sortService.sort(mockVideos, { field: 'views', direction: 'desc' });
    expect(mockVideos).toEqual(original);
  });
});
