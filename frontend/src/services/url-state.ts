/**
 * URL State Manager
 *
 * Encodes and decodes filter/search state to/from URL hash for shareable URLs
 * Follows the mykrok pattern for preserving application state in URLs
 */

import type { SortField, SortDirection } from './sort';

export interface URLState {
  search?: string;
  dateFrom?: string;
  dateTo?: string;
  channels?: string[];
  tags?: string[];
  downloadStatus?: string[];
  playlists?: string[];
  sortField?: SortField;
  sortDirection?: SortDirection;
}

export class URLStateManager {
  /**
   * Parse URL hash to state object
   *
   * @param hash - URL hash (e.g., "#/?search=test&from=2024-01-01")
   * @returns Parsed state object
   */
  parseHash(hash: string): URLState {
    // Remove leading # and /? variations
    const cleanHash = hash.replace(/^#\/?(\?)?/, '');
    const params = new URLSearchParams(cleanHash);

    // Helper to parse array parameters and return undefined for empty arrays
    const parseArray = (value: string | null): string[] | undefined => {
      const arr = value?.split(',').filter(Boolean);
      return arr?.length ? arr : undefined;
    };

    return {
      search: params.get('search') || undefined,
      dateFrom: params.get('from') || undefined,
      dateTo: params.get('to') || undefined,
      channels: parseArray(params.get('channels')),
      tags: parseArray(params.get('tags')),
      downloadStatus: parseArray(params.get('status')),
      playlists: parseArray(params.get('playlists')),
      sortField: (params.get('sort') as SortField) || undefined,
      sortDirection: (params.get('dir') as SortDirection) || undefined,
    };
  }

  /**
   * Encode state object to URL hash
   *
   * @param state - State object to encode
   * @returns URL hash string (e.g., "#/?search=test&from=2024-01-01")
   */
  encodeHash(state: URLState): string {
    const params = new URLSearchParams();

    if (state.search) params.set('search', state.search);
    if (state.dateFrom) params.set('from', state.dateFrom);
    if (state.dateTo) params.set('to', state.dateTo);
    if (state.channels?.length) params.set('channels', state.channels.join(','));
    if (state.tags?.length) params.set('tags', state.tags.join(','));
    if (state.downloadStatus?.length)
      params.set('status', state.downloadStatus.join(','));
    if (state.playlists?.length)
      params.set('playlists', state.playlists.join(','));
    if (state.sortField) params.set('sort', state.sortField);
    if (state.sortDirection) params.set('dir', state.sortDirection);

    const queryString = params.toString();
    return queryString ? `#/?${queryString}` : '#/';
  }

  /**
   * Update URL hash without page reload
   *
   * @param state - State object to encode and set
   */
  updateHash(state: URLState): void {
    window.location.hash = this.encodeHash(state);
  }

  /**
   * Get current URL state
   *
   * @returns Current state from URL hash
   */
  getCurrentState(): URLState {
    return this.parseHash(window.location.hash);
  }
}

/**
 * Singleton instance for convenience
 */
export const urlStateManager = new URLStateManager();
