/**
 * FilterService Unit Tests
 */

import { describe, test, expect, beforeEach } from '@jest/globals';
import { FilterService } from '../../src/services/filter';
import type { Video, Playlist } from '../../src/types/models';

describe('FilterService', () => {
  let filterService: FilterService;
  let mockVideos: Video[];
  let mockPlaylists: Playlist[];

  beforeEach(() => {
    filterService = new FilterService();

    // Create mock videos
    mockVideos = [
      {
        video_id: '1',
        title: 'Video 1',
        channel_id: 'CH1',
        channel_name: 'Channel One',
        published_at: '2024-01-15T00:00:00Z',
        duration: 300,
        view_count: 1000,
        like_count: 50,
        comment_count: 10,
        thumbnail_url: 'https://example.com/1.jpg',
        license: 'standard',
        privacy_status: 'public',
        availability: 'public',
        tags: ['music', 'rock'],
        categories: ['Music'],
        captions_available: [],
        has_auto_captions: false,
        download_status: 'downloaded',
        source_url: 'https://youtube.com/watch?v=1',
        fetched_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      {
        video_id: '2',
        title: 'Video 2',
        channel_id: 'CH2',
        channel_name: 'Channel Two',
        published_at: '2024-06-20T00:00:00Z',
        duration: 600,
        view_count: 5000,
        like_count: 200,
        comment_count: 50,
        thumbnail_url: 'https://example.com/2.jpg',
        license: 'standard',
        privacy_status: 'public',
        availability: 'public',
        tags: ['music', 'jazz'],
        categories: ['Music'],
        captions_available: [],
        has_auto_captions: false,
        download_status: 'tracked',
        source_url: 'https://youtube.com/watch?v=2',
        fetched_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      {
        video_id: '3',
        title: 'Video 3',
        channel_id: 'CH1',
        channel_name: 'Channel One',
        published_at: '2023-12-01T00:00:00Z',
        duration: 450,
        view_count: 3000,
        like_count: 100,
        comment_count: 25,
        thumbnail_url: 'https://example.com/3.jpg',
        license: 'standard',
        privacy_status: 'public',
        availability: 'public',
        tags: ['tutorial', 'education'],
        categories: ['Education'],
        captions_available: [],
        has_auto_captions: false,
        download_status: 'not_downloaded',
        source_url: 'https://youtube.com/watch?v=3',
        fetched_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    ];

    // Create mock playlists
    mockPlaylists = [
      {
        playlist_id: 'PL1',
        title: 'Music Playlist',
        channel_id: 'CH1',
        channel_name: 'Channel One',
        video_ids: ['1', '2'],
        video_count: 2,
        total_duration: 900,
        privacy_status: 'public',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        last_sync: '2024-01-01T00:00:00Z',
        fetched_at: '2024-01-01T00:00:00Z',
      },
      {
        playlist_id: 'PL2',
        title: 'Tutorial Playlist',
        channel_id: 'CH1',
        channel_name: 'Channel One',
        video_ids: ['3'],
        video_count: 1,
        total_duration: 450,
        privacy_status: 'public',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        last_sync: '2024-01-01T00:00:00Z',
        fetched_at: '2024-01-01T00:00:00Z',
      },
    ];
  });

  test('returns all videos when no criteria provided', () => {
    const filtered = filterService.filter(mockVideos, {});
    expect(filtered.length).toBe(3);
  });

  test('filters by date range', () => {
    const filtered = filterService.filter(mockVideos, {
      dateRange: { from: '2024-01-01', to: '2024-12-31' },
    });
    expect(filtered.length).toBe(2); // Videos 1 and 2
    expect(filtered.every((v) => {
      const year = new Date(v.published_at).getFullYear();
      return year === 2024;
    })).toBe(true);
  });

  test('filters by date range (from only)', () => {
    const filtered = filterService.filter(mockVideos, {
      dateRange: { from: '2024-01-01', to: '' },
    });
    expect(filtered.length).toBe(2); // Videos 1 and 2
  });

  test('filters by date range (to only)', () => {
    const filtered = filterService.filter(mockVideos, {
      dateRange: { from: '', to: '2023-12-31' },
    });
    expect(filtered.length).toBe(1); // Video 3
  });

  test('filters by channel (single)', () => {
    const filtered = filterService.filter(mockVideos, {
      channels: ['CH1'],
    });
    expect(filtered.length).toBe(2); // Videos 1 and 3
    expect(filtered.every((v) => v.channel_id === 'CH1')).toBe(true);
  });

  test('filters by channel (multiple - OR logic)', () => {
    const filtered = filterService.filter(mockVideos, {
      channels: ['CH1', 'CH2'],
    });
    expect(filtered.length).toBe(3); // All videos
  });

  test('filters by tags (single)', () => {
    const filtered = filterService.filter(mockVideos, {
      tags: ['music'],
    });
    expect(filtered.length).toBe(2); // Videos 1 and 2
  });

  test('filters by tags (multiple - OR logic)', () => {
    const filtered = filterService.filter(mockVideos, {
      tags: ['rock', 'tutorial'],
    });
    expect(filtered.length).toBe(2); // Videos 1 and 3
  });

  test('filters by download status (single)', () => {
    const filtered = filterService.filter(mockVideos, {
      downloadStatus: ['downloaded'],
    });
    expect(filtered.length).toBe(1); // Video 1
    expect(filtered[0].download_status).toBe('downloaded');
  });

  test('filters by download status (multiple - OR logic)', () => {
    const filtered = filterService.filter(mockVideos, {
      downloadStatus: ['downloaded', 'tracked'],
    });
    expect(filtered.length).toBe(2); // Videos 1 and 2
  });

  test('filters by playlist (single)', () => {
    const filtered = filterService.filter(
      mockVideos,
      { playlists: ['PL1'] },
      mockPlaylists
    );
    expect(filtered.length).toBe(2); // Videos 1 and 2
    expect(filtered.map((v) => v.video_id).sort()).toEqual(['1', '2']);
  });

  test('filters by playlist (multiple - OR logic)', () => {
    const filtered = filterService.filter(
      mockVideos,
      { playlists: ['PL1', 'PL2'] },
      mockPlaylists
    );
    expect(filtered.length).toBe(3); // All videos
  });

  test('combines multiple filters (AND logic)', () => {
    const filtered = filterService.filter(mockVideos, {
      dateRange: { from: '2024-01-01', to: '2024-12-31' },
      channels: ['CH1'],
    });
    expect(filtered.length).toBe(1); // Video 1 only
    expect(filtered[0].video_id).toBe('1');
  });

  test('combines filters with playlist', () => {
    const filtered = filterService.filter(
      mockVideos,
      {
        playlists: ['PL1'],
        downloadStatus: ['downloaded'],
      },
      mockPlaylists
    );
    expect(filtered.length).toBe(1); // Video 1 only
    expect(filtered[0].video_id).toBe('1');
  });

  test('returns empty array when no matches', () => {
    const filtered = filterService.filter(mockVideos, {
      channels: ['NONEXISTENT'],
    });
    expect(filtered.length).toBe(0);
  });

  test('extracts unique channels', () => {
    const channels = filterService.getUniqueChannels(mockVideos);
    expect(channels.length).toBe(2);
    expect(channels[0]).toEqual({ id: 'CH1', name: 'Channel One' });
    expect(channels[1]).toEqual({ id: 'CH2', name: 'Channel Two' });
  });

  test('extracts unique channels sorted by name', () => {
    const channels = filterService.getUniqueChannels(mockVideos);
    expect(channels[0].name).toBe('Channel One');
    expect(channels[1].name).toBe('Channel Two');
  });

  test('extracts unique tags', () => {
    const tags = filterService.getUniqueTags(mockVideos);
    expect(tags.length).toBe(5);
    expect(tags).toContain('music');
    expect(tags).toContain('rock');
    expect(tags).toContain('jazz');
    expect(tags).toContain('tutorial');
    expect(tags).toContain('education');
  });

  test('extracts unique tags sorted alphabetically', () => {
    const tags = filterService.getUniqueTags(mockVideos);
    const sorted = [...tags].sort();
    expect(tags).toEqual(sorted);
  });

  test('gets playlist video counts', () => {
    const counts = filterService.getPlaylistVideoCounts(
      mockPlaylists,
      mockVideos
    );
    expect(counts.get('PL1')).toBe(2);
    expect(counts.get('PL2')).toBe(1);
  });

  test('handles empty video array', () => {
    const filtered = filterService.filter([], { channels: ['CH1'] });
    expect(filtered.length).toBe(0);
  });

  test('handles empty playlists array', () => {
    // When playlists array is empty, playlist filter cannot be applied
    // So it returns no results (can't find videos in non-existent playlists)
    const filtered = filterService.filter(
      mockVideos,
      { playlists: ['PL1'] },
      []
    );
    // Since playlists is empty, the filter should skip playlist filtering
    // and return all videos (no playlist data to filter against)
    expect(filtered.length).toBe(0);
  });

  test('handles videos without tags', () => {
    const videoWithoutTags = { ...mockVideos[0], tags: [] };
    const tags = filterService.getUniqueTags([videoWithoutTags]);
    expect(tags.length).toBe(0);
  });
});
