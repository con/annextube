/**
 * Data Loader Service
 *
 * Implements the mykrok on-demand loading pattern:
 * 1. Load TSV files immediately (fast, ~1-2 MB)
 * 2. Fetch JSON details on demand (lazy loading)
 */

import { parseTSV, parseIntField } from '@/utils/tsv-parser';
import type {
  Video,
  Playlist,
  Comment,
  Channel,
  VideoTSVRow,
  PlaylistTSVRow,
  ChannelTSVRow,
} from '@/types/models';

export class DataLoader {
  private baseUrl: string;
  private videosCache: Video[] | null = null;
  private playlistsCache: Playlist[] | null = null;
  private metadataCache: Map<string, Video> = new Map();
  private commentsCache: Map<string, Comment[]> = new Map();

  constructor(baseUrl: string = '..') {
    // Default baseUrl: '../' (frontend is in web/, data is in parent)
    this.baseUrl = baseUrl;
  }

  /**
   * Load all videos from videos.tsv (fast initial load)
   *
   * Following mykrok pattern: Load TSV immediately for list view
   */
  async loadVideos(): Promise<Video[]> {
    if (this.videosCache) {
      return this.videosCache;
    }

    const response = await fetch(`${this.baseUrl}/videos/videos.tsv`);
    if (!response.ok) {
      throw new Error(`Failed to load videos.tsv: ${response.statusText}`);
    }

    const text = await response.text();
    const rows = parseTSV(text) as unknown as VideoTSVRow[];

    // Convert TSV rows to Video objects (with type conversion)
    this.videosCache = rows.map((row) => this.parseTSVVideo(row));

    return this.videosCache;
  }

  /**
   * Load all playlists from playlists.tsv
   */
  async loadPlaylists(): Promise<Playlist[]> {
    if (this.playlistsCache) {
      return this.playlistsCache;
    }

    const response = await fetch(`${this.baseUrl}/playlists/playlists.tsv`);
    if (!response.ok) {
      throw new Error(
        `Failed to load playlists.tsv: ${response.statusText}`
      );
    }

    const text = await response.text();
    const rows = parseTSV(text) as unknown as PlaylistTSVRow[];

    // Convert TSV rows to Playlist objects
    const playlists = rows.map((row) => this.parseTSVPlaylist(row));

    // Load video_ids from playlist.json files
    await Promise.all(
      playlists.map(async (playlist) => {
        try {
          const fullPlaylist = await this.loadPlaylistMetadata(
            playlist.playlist_id,
            playlist.path  // Pass the path from TSV
          );
          playlist.video_ids = fullPlaylist.video_ids;
        } catch (err) {
          // If playlist.json doesn't exist, keep empty array
          console.warn(
            `Could not load video_ids for playlist ${playlist.playlist_id}:`,
            err
          );
        }
      })
    );

    this.playlistsCache = playlists;

    return this.playlistsCache;
  }

  /**
   * Load full video metadata from JSON (on-demand, mykrok pattern)
   *
   * @param videoId - YouTube video ID
   * @returns Full Video object with all metadata
   */
  async loadVideoMetadata(videoId: string): Promise<Video> {
    // Check cache first
    if (this.metadataCache.has(videoId)) {
      return this.metadataCache.get(videoId)!;
    }

    // Get file_path from videos cache (use path if available, otherwise video_id)
    const filePath = this.getVideoPath(videoId);

    // Fetch from JSON file
    const response = await fetch(
      `${this.baseUrl}/videos/${filePath}/metadata.json`
    );
    if (!response.ok) {
      throw new Error(
        `Failed to load metadata for ${videoId}: ${response.statusText}`
      );
    }

    const metadata = (await response.json()) as Video;

    // Preserve fields from TSV that aren't in metadata.json
    // (These are calculated during TSV export)
    if (this.videosCache) {
      const tsvVideo = this.videosCache.find((v) => v.video_id === videoId);
      if (tsvVideo) {
        metadata.file_path = filePath;
        metadata.download_status = tsvVideo.download_status;
      }
    }

    // Cache for future requests
    this.metadataCache.set(videoId, metadata);

    return metadata;
  }

  /**
   * Load comments for a video (on-demand, mykrok pattern)
   *
   * @param videoId - YouTube video ID
   * @returns Array of Comment objects (may include nested replies)
   */
  async loadComments(videoId: string): Promise<Comment[]> {
    // Check cache first
    if (this.commentsCache.has(videoId)) {
      return this.commentsCache.get(videoId)!;
    }

    // Get file_path from videos cache
    const filePath = this.getVideoPath(videoId);

    // Fetch from JSON file
    const response = await fetch(
      `${this.baseUrl}/videos/${filePath}/comments.json`
    );
    if (!response.ok) {
      // Comments may not exist for some videos
      if (response.status === 404) {
        return [];
      }
      throw new Error(
        `Failed to load comments for ${videoId}: ${response.statusText}`
      );
    }

    const comments = (await response.json()) as Comment[];

    // Cache for future requests
    this.commentsCache.set(videoId, comments);

    return comments;
  }

  /**
   * Load full playlist metadata from JSON
   *
   * @param playlistId - YouTube playlist ID
   * @returns Full Playlist object with video_ids
   */
  async loadPlaylistMetadata(playlistId: string, path?: string): Promise<Playlist> {
    // Find playlist path from cached playlists or use provided path
    let playlistPath = path || '';

    if (!playlistPath && this.playlistsCache) {
      const cached = this.playlistsCache.find((p) => p.playlist_id === playlistId);
      if (cached && cached.path) {
        // Use path from TSV (directory name)
        playlistPath = cached.path;
      }
    }

    if (!playlistPath) {
      throw new Error(
        `Cannot load playlist metadata for ${playlistId}: path not found in cache`
      );
    }

    // Fetch playlist.json from the playlist directory
    const response = await fetch(
      `${this.baseUrl}/playlists/${playlistPath}/playlist.json`
    );
    if (!response.ok) {
      throw new Error(
        `Failed to load playlist metadata for ${playlistId}: ${response.statusText}`
      );
    }

    return (await response.json()) as Playlist;
  }

  /**
   * Get caption file path for a video
   *
   * @param videoId - YouTube video ID
   * @param languageCode - ISO 639-1 language code (e.g., 'en', 'es')
   * @returns Path to VTT caption file
   */
  getCaptionPath(videoId: string, languageCode: string): string {
    const filePath = this.getVideoPath(videoId);
    return `${this.baseUrl}/videos/${filePath}/caption_${languageCode}.vtt`;
  }

  /**
   * Get video file path (folder name) for a video
   *
   * @param videoId - YouTube video ID
   * @returns File path (either path from TSV or video_id)
   */
  private getVideoPath(videoId: string): string {
    // Find video in cache and use its file_path
    if (this.videosCache) {
      const video = this.videosCache.find((v) => v.video_id === videoId);
      if (video && video.file_path) {
        return video.file_path;
      }
    }
    // Fallback to video_id if not found in cache
    return videoId;
  }

  /**
   * Check if this is a multi-channel collection (channels.tsv exists)
   */
  async isMultiChannelMode(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/channels.tsv`);
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Load channels from channels.tsv (for multi-channel collections)
   */
  async loadChannels(): Promise<Channel[]> {
    const response = await fetch(`${this.baseUrl}/channels.tsv`);
    if (!response.ok) {
      throw new Error(`Failed to load channels.tsv: ${response.statusText}`);
    }

    const text = await response.text();
    const rows = parseTSV(text) as unknown as ChannelTSVRow[];

    // Convert TSV rows to Channel objects
    return rows.map((row) => this.parseTSVChannel(row));
  }

  /**
   * Load videos for a specific channel directory
   *
   * @param channelDir - Relative path to channel directory (from channels.tsv)
   */
  async loadChannelVideos(channelDir: string): Promise<Video[]> {
    const response = await fetch(
      `${this.baseUrl}/${channelDir}/videos/videos.tsv`
    );
    if (!response.ok) {
      throw new Error(
        `Failed to load videos for channel ${channelDir}: ${response.statusText}`
      );
    }

    const text = await response.text();
    const rows = parseTSV(text) as unknown as VideoTSVRow[];

    // Convert TSV rows to Video objects
    return rows.map((row) => this.parseTSVVideo(row));
  }

  /**
   * Clear all caches (useful for testing or manual refresh)
   */
  clearCache(): void {
    this.videosCache = null;
    this.playlistsCache = null;
    this.metadataCache.clear();
    this.commentsCache.clear();
  }

  /**
   * Convert TSV row to Video object (with type conversion)
   */
  private parseTSVVideo(row: VideoTSVRow): Video {
    return {
      video_id: row.video_id,
      title: row.title,
      channel_id: row.channel_id,
      channel_name: row.channel_name,
      published_at: row.published_at,
      duration: parseIntField(row.duration),
      view_count: parseIntField(row.view_count),
      like_count: parseIntField(row.like_count),
      comment_count: parseIntField(row.comment_count),
      thumbnail_url: row.thumbnail_url,
      download_status: row.download_status as Video['download_status'],
      source_url: row.source_url,
      file_path: row.path || row.video_id, // Use path if available, otherwise video_id
      // These fields are only in full metadata.json
      license: 'standard', // Default, will be in metadata.json
      privacy_status: 'public',
      availability: 'public',
      tags: [],
      categories: [],
      captions_available: [],
      has_auto_captions: false,
      fetched_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  /**
   * Convert TSV row to Playlist object
   */
  private parseTSVPlaylist(row: PlaylistTSVRow): Playlist {
    return {
      playlist_id: row.playlist_id,
      title: row.title,
      channel_id: row.channel_id,
      channel_name: row.channel_name,
      video_count: parseIntField(row.video_count),
      total_duration: parseIntField(row.total_duration),
      privacy_status: row.privacy_status as Playlist['privacy_status'],
      created_at: row.created_at,
      last_sync: row.last_sync,
      path: row.path, // Directory name for loading playlist.json
      // These fields require reading playlist.json
      video_ids: [],
      updated_at: row.last_sync,
      fetched_at: row.last_sync,
    };
  }

  /**
   * Convert TSV row to Channel object
   */
  private parseTSVChannel(row: ChannelTSVRow): Channel {
    return {
      channel_id: row.channel_id,
      name: row.title,
      description: row.description,
      custom_url: row.custom_url,
      subscriber_count: parseIntField(row.subscriber_count),
      video_count: parseIntField(row.video_count),
      avatar_url: '',
      videos: [],
      playlists: [],
      last_sync: row.last_sync,
      created_at: '',
      fetched_at: row.last_sync,
      archive_stats: {
        total_videos_archived: parseIntField(row.total_videos_archived),
        first_video_date: row.first_video_date || undefined,
        last_video_date: row.last_video_date || undefined,
        total_duration_seconds: 0,
        total_size_bytes: 0,
      },
      // Add channel_dir as custom property for navigation
      channel_dir: row.channel_dir,
    };
  }
}

/**
 * Singleton instance for convenience
 */
export const dataLoader = new DataLoader();
