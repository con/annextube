/**
 * Tests for DataLoader service
 *
 * Using Jest + jsdom to test data loading logic
 */

import { jest } from '@jest/globals';
import { DataLoader } from '../../src/services/data-loader';

describe('DataLoader', () => {
  let dataLoader: DataLoader;

  beforeEach(() => {
    dataLoader = new DataLoader('../');
    (fetch as jest.Mock).mockClear();
  });

  describe('loadVideos', () => {
    test('loads and parses videos.tsv', async () => {
      const mockTSV = `video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\tduration\tview_count\tlike_count\tcomment_count\tthumbnail_url\tdownload_status\tsource_url
abc123\tTest Video\tUC123\tTest Channel\t2024-01-01T00:00:00Z\t300\t1000\t50\t10\thttp://example.com/thumb.jpg\ttracked\thttps://youtube.com/watch?v=abc123`;

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        text: async () => mockTSV,
      });

      const videos = await dataLoader.loadVideos();

      expect(fetch).toHaveBeenCalledWith('..//videos/videos.tsv');
      expect(videos).toHaveLength(1);
      expect(videos[0]).toMatchObject({
        video_id: 'abc123',
        title: 'Test Video',
        channel_id: 'UC123',
        channel_name: 'Test Channel',
        duration: 300,
        view_count: 1000,
        like_count: 50,
        comment_count: 10,
      });
    });

    test('caches videos after first load', async () => {
      const mockTSV = `video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\tduration\tview_count\tlike_count\tcomment_count\tthumbnail_url\tdownload_status\tsource_url
abc123\tTest\tUC123\tChannel\t2024-01-01T00:00:00Z\t300\t1000\t50\t10\thttp://example.com/thumb.jpg\ttracked\thttps://youtube.com/watch?v=abc123`;

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        text: async () => mockTSV,
      });

      // First call
      await dataLoader.loadVideos();
      expect(fetch).toHaveBeenCalledTimes(1);

      // Second call (should use cache)
      await dataLoader.loadVideos();
      expect(fetch).toHaveBeenCalledTimes(1); // Still 1, not 2
    });

    test('throws error if videos.tsv not found', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        statusText: 'Not Found',
      });

      await expect(dataLoader.loadVideos()).rejects.toThrow(
        'Failed to load videos.tsv: Not Found'
      );
    });
  });

  describe('loadPlaylists', () => {
    test('loads and parses playlists.tsv', async () => {
      const mockTSV = `playlist_id\ttitle\tchannel_id\tchannel_name\tvideo_count\ttotal_duration\tprivacy_status\tcreated_at\tlast_sync
PL123\tTest Playlist\tUC123\tTest Channel\t5\t1500\tpublic\t2024-01-01T00:00:00Z\t2024-01-15T00:00:00Z`;

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        text: async () => mockTSV,
      });

      const playlists = await dataLoader.loadPlaylists();

      expect(fetch).toHaveBeenCalledWith('..//playlists/playlists.tsv');
      expect(playlists).toHaveLength(1);
      expect(playlists[0]).toMatchObject({
        playlist_id: 'PL123',
        title: 'Test Playlist',
        channel_id: 'UC123',
        video_count: 5,
        total_duration: 1500,
        privacy_status: 'public',
      });
    });
  });

  describe('loadVideoMetadata', () => {
    test('loads metadata JSON on demand', async () => {
      const mockMetadata = {
        video_id: 'abc123',
        title: 'Full Video Title',
        description: 'Full description',
        duration: 300,
        tags: ['tag1', 'tag2'],
        captions_available: ['en', 'es'],
        has_auto_captions: true,
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetadata,
      });

      const metadata = await dataLoader.loadVideoMetadata('abc123');

      expect(fetch).toHaveBeenCalledWith(
        '..//videos/abc123/metadata.json'
      );
      expect(metadata).toMatchObject(mockMetadata);
    });

    test('caches metadata after first load', async () => {
      const mockMetadata = { video_id: 'abc123', title: 'Test' };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetadata,
      });

      // First call
      await dataLoader.loadVideoMetadata('abc123');
      expect(fetch).toHaveBeenCalledTimes(1);

      // Second call (should use cache)
      await dataLoader.loadVideoMetadata('abc123');
      expect(fetch).toHaveBeenCalledTimes(1); // Still 1
    });
  });

  describe('loadComments', () => {
    test('loads comments JSON', async () => {
      const mockComments = [
        {
          comment_id: 'c1',
          video_id: 'abc123',
          author: 'User1',
          text: 'Great video!',
          like_count: 5,
        },
      ];

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockComments,
      });

      const comments = await dataLoader.loadComments('abc123');

      expect(fetch).toHaveBeenCalledWith(
        '..//videos/abc123/comments.json'
      );
      expect(comments).toHaveLength(1);
      expect(comments[0].text).toBe('Great video!');
    });

    test('returns empty array if comments not found (404)', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const comments = await dataLoader.loadComments('abc123');

      expect(comments).toEqual([]);
    });

    test('throws error for non-404 failures', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      await expect(dataLoader.loadComments('abc123')).rejects.toThrow(
        'Failed to load comments for abc123: Internal Server Error'
      );
    });
  });

  describe('getCaptionPath', () => {
    test('returns correct caption path', () => {
      const path = dataLoader.getCaptionPath('abc123', 'en');
      expect(path).toBe('..//videos/abc123/caption_en.vtt');
    });
  });

  describe('clearCache', () => {
    test('clears all caches', async () => {
      const mockTSV = `video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\tduration\tview_count\tlike_count\tcomment_count\tthumbnail_url\tdownload_status\tsource_url
abc123\tTest\tUC123\tChannel\t2024-01-01T00:00:00Z\t300\t1000\t50\t10\thttp://example.com/thumb.jpg\ttracked\thttps://youtube.com/watch?v=abc123`;

      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        text: async () => mockTSV,
      });

      // Load videos
      await dataLoader.loadVideos();
      expect(fetch).toHaveBeenCalledTimes(1);

      // Clear cache
      dataLoader.clearCache();

      // Load again (should fetch again, not use cache)
      await dataLoader.loadVideos();
      expect(fetch).toHaveBeenCalledTimes(2);
    });
  });
});
