/**
 * Tests for DataLoader multi-channel functionality
 *
 * Tests loadChannels, loadChannelVideos, and multi-channel
 * methods of the DataLoader service.
 *
 * @ai_generated
 */

import { vi, type Mock } from 'vitest';
import { DataLoader } from '../../src/services/data-loader';

// Mock fetch globally
const mockFetch = vi.fn() as Mock;
vi.stubGlobal('fetch', mockFetch);

const CHANNELS_TSV_HEADER =
  'channel_id\ttitle\tcustom_url\tdescription\tsubscriber_count\tvideo_count\tplaylist_count\ttotal_videos_archived\tfirst_video_date\tlast_video_date\tlast_sync\tchannel_dir';

const CHANNELS_TSV_ROW1 =
  'UC001\tAlpha Channel\t@AlphaChannel\tFirst test channel\t50000\t100\t5\t95\t2020-01-01\t2024-06-01\t2024-06-15T00:00:00Z\tch-alphachannel';

const CHANNELS_TSV_ROW2 =
  'UC002\tBeta Channel\t@BetaChannel\tSecond test channel\t25000\t50\t2\t48\t2021-03-01\t2024-05-15\t2024-06-15T00:00:00Z\tch-betachannel';

const MOCK_CHANNELS_TSV = [CHANNELS_TSV_HEADER, CHANNELS_TSV_ROW1, CHANNELS_TSV_ROW2].join('\n');

const VIDEOS_TSV_HEADER =
  'video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\tduration\tview_count\tlike_count\tcomment_count\tthumbnail_url\tdownload_status\tsource_url';

const VIDEOS_TSV_ROW =
  'V001\tAlpha Video One\tUC001\tAlpha Channel\t2024-01-01T00:00:00\t300\t1000\t50\t10\thttps://example.com/thumb1.jpg\ttracked\thttps://www.youtube.com/watch?v=V001';

const MOCK_VIDEOS_TSV = [VIDEOS_TSV_HEADER, VIDEOS_TSV_ROW].join('\n');

describe('DataLoader multi-channel', () => {
  let dataLoader: DataLoader;

  beforeEach(() => {
    dataLoader = new DataLoader('../');
    mockFetch.mockClear();
  });

  describe('loadChannels', () => {
    test('loads and parses channels.tsv without full metadata', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => MOCK_CHANNELS_TSV,
      });

      const channels = await dataLoader.loadChannels(false);

      expect(fetch).toHaveBeenCalledWith('..//channels.tsv');
      expect(channels).toHaveLength(2);
      expect(channels[0]).toMatchObject({
        channel_id: 'UC001',
        name: 'Alpha Channel',
        custom_url: '@AlphaChannel',
        subscriber_count: 50000,
        video_count: 100,
        channel_dir: 'ch-alphachannel',
      });
      expect(channels[0].archive_stats).toMatchObject({
        total_videos_archived: 95,
      });
      expect(channels[1]).toMatchObject({
        channel_id: 'UC002',
        name: 'Beta Channel',
        channel_dir: 'ch-betachannel',
      });
    });

    test('loads channels with full metadata from channel.json', async () => {
      // First: channels.tsv
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => MOCK_CHANNELS_TSV,
      });

      const alphaJson = {
        channel_id: 'UC001',
        name: 'Alpha Channel Full',
        description: 'Full description from JSON',
        channel_dir: 'ch-alphachannel',
        archive_stats: {
          total_videos_archived: 95,
          total_duration_seconds: 360000,
          total_size_bytes: 5368709120,
        },
      };

      const betaJson = {
        channel_id: 'UC002',
        name: 'Beta Channel Full',
        channel_dir: 'ch-betachannel',
      };

      // Mock fetch for channel.json + avatar probes
      mockFetch.mockImplementation(async (url: string) => {
        if (url.includes('ch-alphachannel/channel.json')) {
          return { ok: true, json: async () => alphaJson };
        }
        if (url.includes('ch-betachannel/channel.json')) {
          return { ok: true, json: async () => betaJson };
        }
        // Avatar probes - all return 404
        return { ok: false, status: 404 };
      });

      const channels = await dataLoader.loadChannels(true);

      expect(channels).toHaveLength(2);
      expect(channels[0].name).toBe('Alpha Channel Full');
    });

    test('gracefully handles failed channel.json fetch', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => MOCK_CHANNELS_TSV,
      });

      // All subsequent fetches fail
      mockFetch.mockImplementation(async () => ({
        ok: false,
        status: 500,
        statusText: 'Server Error',
      }));

      const channels = await dataLoader.loadChannels(true);

      // Should still return TSV data
      expect(channels).toHaveLength(2);
      expect(channels[0].channel_id).toBe('UC001');
    });

    test('throws error when channels.tsv not found', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Not Found',
      });

      await expect(dataLoader.loadChannels()).rejects.toThrow(
        'Failed to load channels.tsv: Not Found'
      );
    });
  });

  describe('loadChannelVideos', () => {
    test('loads videos for a specific channel directory', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => MOCK_VIDEOS_TSV,
      });

      const videos = await dataLoader.loadChannelVideos('ch-alphachannel');

      expect(fetch).toHaveBeenCalledWith('..//ch-alphachannel/videos/videos.tsv');
      expect(videos).toHaveLength(1);
      expect(videos[0]).toMatchObject({
        video_id: 'V001',
        title: 'Alpha Video One',
        duration: 300,
      });
    });

    test('throws error when channel videos not found', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Not Found',
      });

      await expect(
        dataLoader.loadChannelVideos('ch-missing')
      ).rejects.toThrow('Failed to load videos for channel ch-missing');
    });
  });

  describe('loadVideoMetadata with channel context', () => {
    test('includes channel prefix in metadata URL', async () => {
      const mockMetadata = {
        video_id: 'V001',
        title: 'Alpha Video One',
        description: 'Full description',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetadata,
      });

      const video = {
        video_id: 'V001',
        file_path: 'alpha-video-one',
      };

      await dataLoader.loadVideoMetadata(video as any, 'ch-alphachannel');

      expect(fetch).toHaveBeenCalledWith(
        '..//ch-alphachannel/videos/alpha-video-one/metadata.json'
      );
    });
  });

  describe('loadComments with channel context', () => {
    test('includes channel prefix in comments URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      const video = {
        video_id: 'V001',
        file_path: 'alpha-video-one',
      };

      await dataLoader.loadComments(video as any, 'ch-alphachannel');

      expect(fetch).toHaveBeenCalledWith(
        '..//ch-alphachannel/videos/alpha-video-one/comments.json'
      );
    });
  });

  describe('loadAllChannelVideos', () => {
    test('loads videos from all channels in parallel', async () => {
      const channels = [
        { channel_id: 'UC001', channel_dir: 'ch-alpha' },
        { channel_id: 'UC002', channel_dir: 'ch-beta' },
      ] as any[];

      mockFetch.mockImplementation(async (url: string) => {
        if (url.includes('ch-alpha')) {
          return {
            ok: true,
            text: async () =>
              'video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\tduration\tview_count\tlike_count\tcomment_count\tthumbnail_url\tdownload_status\tsource_url\n' +
              'A1\tAlpha Vid\tUC001\tAlpha\t2024-01-01\t300\t100\t10\t5\thttp://x/a.jpg\ttracked\thttp://yt/A1',
          };
        }
        if (url.includes('ch-beta')) {
          return {
            ok: true,
            text: async () =>
              'video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\tduration\tview_count\tlike_count\tcomment_count\tthumbnail_url\tdownload_status\tsource_url\n' +
              'B1\tBeta Vid\tUC002\tBeta\t2024-02-01\t600\t200\t20\t10\thttp://x/b.jpg\tdownloaded\thttp://yt/B1',
          };
        }
        return { ok: false, statusText: 'Not Found' };
      });

      const allVideos = await dataLoader.loadAllChannelVideos(channels);

      expect(allVideos).toHaveLength(2);
      expect(allVideos[0].channel_dir).toBe('ch-alpha');
      expect(allVideos[1].channel_dir).toBe('ch-beta');
    });

    test('handles failure for one channel gracefully', async () => {
      const channels = [
        { channel_id: 'UC001', channel_dir: 'ch-alpha' },
        { channel_id: 'UC002', channel_dir: 'ch-broken' },
      ] as any[];

      mockFetch.mockImplementation(async (url: string) => {
        if (url.includes('ch-alpha')) {
          return {
            ok: true,
            text: async () =>
              'video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\tduration\tview_count\tlike_count\tcomment_count\tthumbnail_url\tdownload_status\tsource_url\n' +
              'A1\tAlpha Vid\tUC001\tAlpha\t2024-01-01\t300\t100\t10\t5\thttp://x/a.jpg\ttracked\thttp://yt/A1',
          };
        }
        return { ok: false, statusText: 'Not Found' };
      });

      const allVideos = await dataLoader.loadAllChannelVideos(channels);

      expect(allVideos).toHaveLength(1);
      expect(allVideos[0].video_id).toBe('A1');
    });
  });
});
