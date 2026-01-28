/**
 * Data Loader Service
 *
 * Implements the mykrok on-demand loading pattern:
 * 1. Load TSV files immediately (fast, ~1-2 MB)
 * 2. Fetch JSON details on demand (lazy loading)
 */

import { parseTSV, parseIntField, parseBooleanField } from '@/utils/tsv-parser';
import type {
  Video,
  Playlist,
  Comment,
  VideoTSVRow,
  PlaylistTSVRow,
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
    this.playlistsCache = rows.map((row) => this.parseTSVPlaylist(row));

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

    // Fetch from JSON file
    const response = await fetch(
      `${this.baseUrl}/videos/${videoId}/metadata.json`
    );
    if (!response.ok) {
      throw new Error(
        `Failed to load metadata for ${videoId}: ${response.statusText}`
      );
    }

    const metadata = (await response.json()) as Video;

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

    // Fetch from JSON file
    const response = await fetch(
      `${this.baseUrl}/videos/${videoId}/comments.json`
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
   * Get caption file path for a video
   *
   * @param videoId - YouTube video ID
   * @param languageCode - ISO 639-1 language code (e.g., 'en', 'es')
   * @returns Path to VTT caption file
   */
  getCaptionPath(videoId: string, languageCode: string): string {
    return `${this.baseUrl}/videos/${videoId}/caption_${languageCode}.vtt`;
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
      // These fields require reading playlist.json
      video_ids: [],
      updated_at: row.last_sync,
      fetched_at: row.last_sync,
    };
  }
}

/**
 * Singleton instance for convenience
 */
export const dataLoader = new DataLoader();
