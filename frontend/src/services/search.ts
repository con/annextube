/**
 * Search Service
 *
 * Provides fuzzy search across video titles, descriptions, channels, and tags using fuse.js
 */

import Fuse from 'fuse.js';
import type { Video } from '@/types/models';

export interface SearchOptions {
  threshold?: number;  // 0.0 (exact) to 1.0 (anything) - default 0.3
  keys?: string[];     // Fields to search - default ['title', 'channel_name', 'tags']
  limit?: number;      // Max results - default unlimited
}

export interface SearchResult {
  video: Video;
  score: number;       // Relevance score from fuse.js (lower = better)
  matches: string[];   // Which fields matched
}

export class SearchService {
  private fuse: Fuse<Video> | null = null;
  private videos: Video[] = [];

  /**
   * Initialize search index with videos
   */
  initialize(videos: Video[]): void {
    this.videos = videos;
    this.fuse = new Fuse(videos, {
      keys: [
        { name: 'title', weight: 0.4 },
        { name: 'channel_name', weight: 0.2 },
        { name: 'tags', weight: 0.3 },
        { name: 'description', weight: 0.1 },
      ],
      threshold: 0.3,
      includeScore: true,
      includeMatches: true,
      ignoreLocation: true,  // Search entire string, not just beginning
      minMatchCharLength: 2,  // Require at least 2 characters to match
    });
  }

  /**
   * Search videos by query string
   *
   * @param query - Search query
   * @param options - Search options
   * @returns Array of search results with scores and matched fields
   */
  search(query: string, options?: SearchOptions): SearchResult[] {
    // If no search index or empty query, return all videos
    if (!this.fuse || !query.trim()) {
      return this.videos.map((v) => ({ video: v, score: 0, matches: [] }));
    }

    const results = this.fuse.search(query);

    const mapped = results.map((r) => ({
      video: r.item,
      score: r.score || 0,
      matches: r.matches?.map((m) => m.key || '') || [],
    }));

    // Apply limit if specified
    if (options?.limit && options.limit > 0) {
      return mapped.slice(0, options.limit);
    }

    return mapped;
  }

  /**
   * Clear search index
   */
  clear(): void {
    this.fuse = null;
    this.videos = [];
  }

  /**
   * Get total indexed videos count
   */
  getIndexedCount(): number {
    return this.videos.length;
  }
}

/**
 * Singleton instance for convenience
 */
export const searchService = new SearchService();
