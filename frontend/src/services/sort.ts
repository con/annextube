/**
 * Sort Service
 *
 * Provides sorting capabilities for videos by various criteria
 */

import type { Video } from '@/types/models';

export type SortField = 'views' | 'date' | 'duration' | 'title' | 'relevance';
export type SortDirection = 'asc' | 'desc';

export interface SortCriteria {
  field: SortField;
  direction: SortDirection;
}

export class SortService {
  /**
   * Sort videos by criteria
   *
   * @param videos - Videos to sort
   * @param criteria - Sort criteria
   * @returns Sorted videos (new array, does not mutate original)
   */
  sort(videos: Video[], criteria: SortCriteria): Video[] {
    const sorted = [...videos]; // Don't mutate original array

    sorted.sort((a, b) => {
      let comparison = 0;

      switch (criteria.field) {
        case 'views':
          comparison = a.view_count - b.view_count;
          break;
        case 'date':
          comparison =
            new Date(a.published_at).getTime() -
            new Date(b.published_at).getTime();
          break;
        case 'duration':
          comparison = a.duration - b.duration;
          break;
        case 'title':
          comparison = a.title.localeCompare(b.title);
          break;
        case 'relevance':
          // Relevance sorting is handled by SearchService
          // Assume videos are already sorted by relevance
          return 0;
      }

      return criteria.direction === 'asc' ? comparison : -comparison;
    });

    return sorted;
  }
}

/**
 * Singleton instance for convenience
 */
export const sortService = new SortService();
