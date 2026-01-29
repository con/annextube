/**
 * Filter Service
 *
 * Provides filtering capabilities for videos by various criteria
 */

import type { Video, Playlist } from '@/types/models';

export interface FilterCriteria {
  dateRange?: {
    from: string; // ISO date string (YYYY-MM-DD)
    to: string;
  };
  channels?: string[]; // channel_id list (OR logic)
  tags?: string[]; // tag list (OR logic)
  downloadStatus?: Video['download_status'][]; // status list (OR logic)
  playlists?: string[]; // playlist_id list (OR logic)
}

export class FilterService {
  /**
   * Filter videos by multiple criteria (AND logic between criteria types)
   *
   * @param videos - Videos to filter
   * @param criteria - Filter criteria
   * @param playlists - Optional playlists for playlist filtering
   * @returns Filtered videos
   */
  filter(
    videos: Video[],
    criteria: FilterCriteria,
    playlists?: Playlist[]
  ): Video[] {
    let filtered = videos;

    // Date range filter
    if (criteria.dateRange?.from || criteria.dateRange?.to) {
      filtered = filtered.filter((v) => {
        const published = new Date(v.published_at);
        const from = criteria.dateRange?.from
          ? new Date(criteria.dateRange.from)
          : new Date(0); // epoch
        const to = criteria.dateRange?.to
          ? new Date(criteria.dateRange.to)
          : new Date(); // now

        return published >= from && published <= to;
      });
    }

    // Channel filter (OR logic: any of selected channels)
    if (criteria.channels && criteria.channels.length > 0) {
      filtered = filtered.filter((v) =>
        criteria.channels!.includes(v.channel_id)
      );
    }

    // Tag filter (OR logic: video has any of selected tags)
    if (criteria.tags && criteria.tags.length > 0) {
      filtered = filtered.filter((v) =>
        v.tags.some((tag) => criteria.tags!.includes(tag))
      );
    }

    // Download status filter (OR logic)
    if (criteria.downloadStatus && criteria.downloadStatus.length > 0) {
      filtered = filtered.filter((v) =>
        criteria.downloadStatus!.includes(v.download_status)
      );
    }

    // Playlist filter (OR logic: video is in any of selected playlists)
    if (criteria.playlists && criteria.playlists.length > 0) {
      // If playlist filtering is requested but no playlists provided, return empty
      if (!playlists || playlists.length === 0) {
        return [];
      }

      // Build a set of video IDs that are in selected playlists
      const videoIdsInPlaylists = new Set<string>();
      playlists.forEach((playlist) => {
        if (criteria.playlists!.includes(playlist.playlist_id)) {
          playlist.video_ids.forEach((videoId) =>
            videoIdsInPlaylists.add(videoId)
          );
        }
      });

      // Filter videos that are in the set
      filtered = filtered.filter((v) => videoIdsInPlaylists.has(v.video_id));
    }

    return filtered;
  }

  /**
   * Extract unique channels from videos for filter dropdown
   *
   * @param videos - Videos to extract channels from
   * @returns Array of channel objects sorted by name
   */
  getUniqueChannels(videos: Video[]): Array<{ id: string; name: string }> {
    const channelMap = new Map<string, string>();
    videos.forEach((v) => {
      if (v.channel_id && !channelMap.has(v.channel_id)) {
        channelMap.set(v.channel_id, v.channel_name);
      }
    });
    return Array.from(channelMap.entries())
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  /**
   * Extract unique tags from videos for filter autocomplete
   *
   * @param videos - Videos to extract tags from
   * @returns Array of unique tags sorted alphabetically
   */
  getUniqueTags(videos: Video[]): string[] {
    const tagSet = new Set<string>();
    videos.forEach((v) => {
      if (v.tags && v.tags.length > 0) {
        v.tags.forEach((tag) => tagSet.add(tag));
      }
    });
    return Array.from(tagSet).sort();
  }

  /**
   * Get count of videos in each playlist
   *
   * @param playlists - Playlists to count
   * @param videos - All videos (to verify which ones exist)
   * @returns Map of playlist_id to actual video count
   */
  getPlaylistVideoCounts(
    playlists: Playlist[],
    videos: Video[]
  ): Map<string, number> {
    const videoIdSet = new Set(videos.map((v) => v.video_id));
    const counts = new Map<string, number>();

    playlists.forEach((playlist) => {
      const count = playlist.video_ids.filter((id) => videoIdSet.has(id)).length;
      counts.set(playlist.playlist_id, count);
    });

    return counts;
  }
}

/**
 * Singleton instance for convenience
 */
export const filterService = new FilterService();
