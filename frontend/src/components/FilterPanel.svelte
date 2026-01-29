<!--
  FilterPanel Component

  Provides search, filtering, sorting, and playlist selection for videos.
  Updates URL hash to preserve filter state (mykrok pattern).
-->
<script lang="ts">
  import type { Video, Playlist } from '@/types/models';
  import { searchService } from '@/services/search';
  import { filterService } from '@/services/filter';
  import { sortService, type SortField, type SortDirection } from '@/services/sort';
  import { urlStateManager } from '@/services/url-state';

  export let videos: Video[];
  export let playlists: Playlist[] = [];
  export let onFilterChange: (filtered: Video[]) => void;

  // Filter state
  let searchQuery = '';
  let dateFrom = '';
  let dateTo = '';
  let selectedChannels: string[] = [];
  let selectedTags: string[] = [];
  let selectedStatuses: string[] = [];
  let selectedPlaylists: string[] = [];
  let sortField: SortField = 'date';
  let sortDirection: SortDirection = 'desc';

  // Derived values for dropdowns
  $: availableChannels = filterService.getUniqueChannels(videos);
  $: availableTags = filterService.getUniqueTags(videos);
  $: playlistCounts = filterService.getPlaylistVideoCounts(playlists, videos);

  // Apply filters with debounce
  let debounceTimer: number;
  $: {
    // Trigger when any filter value changes
    searchQuery;
    dateFrom;
    dateTo;
    selectedChannels;
    selectedTags;
    selectedStatuses;
    selectedPlaylists;
    sortField;
    sortDirection;

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      applyFilters();
    }, 300);
  }

  function applyFilters() {
    let filtered = videos;

    // 1. Search (if query provided)
    if (searchQuery.trim()) {
      const results = searchService.search(searchQuery);
      filtered = results.map((r) => r.video);
    }

    // 2. Filter by criteria
    filtered = filterService.filter(
      filtered,
      {
        dateRange:
          dateFrom || dateTo
            ? { from: dateFrom || '1970-01-01', to: dateTo || new Date().toISOString().split('T')[0] }
            : undefined,
        channels: selectedChannels.length > 0 ? selectedChannels : undefined,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
        downloadStatus: selectedStatuses.length > 0 ? selectedStatuses : undefined,
        playlists: selectedPlaylists.length > 0 ? selectedPlaylists : undefined,
      },
      playlists
    );

    // 3. Sort
    filtered = sortService.sort(filtered, { field: sortField, direction: sortDirection });

    // 4. Update URL hash (debounced separately to avoid history pollution)
    updateURL();

    // 5. Notify parent
    onFilterChange(filtered);
  }

  let urlDebounceTimer: number;
  function updateURL() {
    clearTimeout(urlDebounceTimer);
    urlDebounceTimer = setTimeout(() => {
      urlStateManager.updateHash({
        search: searchQuery || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        channels: selectedChannels.length > 0 ? selectedChannels : undefined,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
        downloadStatus: selectedStatuses.length > 0 ? selectedStatuses : undefined,
        playlists: selectedPlaylists.length > 0 ? selectedPlaylists : undefined,
        sortField,
        sortDirection,
      });
    }, 500);
  }

  function clearFilters() {
    searchQuery = '';
    dateFrom = '';
    dateTo = '';
    selectedChannels = [];
    selectedTags = [];
    selectedStatuses = [];
    selectedPlaylists = [];
    sortField = 'date';
    sortDirection = 'desc';
  }

  // Count active filters for badge
  $: activeFilterCount = [
    searchQuery.length > 0,
    dateFrom.length > 0 || dateTo.length > 0,
    selectedChannels.length > 0,
    selectedTags.length > 0,
    selectedStatuses.length > 0,
    selectedPlaylists.length > 0,
  ].filter(Boolean).length;
</script>

<div class="filter-panel">
  <div class="search-section">
    <input
      type="text"
      bind:value={searchQuery}
      placeholder="Search videos, channels, tags..."
      class="search-input"
    />
  </div>

  <div class="filters-grid">
    <!-- Date Range -->
    <div class="filter-group">
      <label class="filter-label">Date Range</label>
      <div class="date-inputs">
        <input type="date" bind:value={dateFrom} class="date-input" title="From date" />
        <span class="date-separator">to</span>
        <input type="date" bind:value={dateTo} class="date-input" title="To date" />
      </div>
    </div>

    <!-- Channels -->
    <div class="filter-group">
      <label class="filter-label">
        Channels
        {#if selectedChannels.length > 0}
          <span class="count-badge">{selectedChannels.length}</span>
        {/if}
      </label>
      <select multiple bind:value={selectedChannels} class="multi-select" size="3">
        {#each availableChannels as channel}
          <option value={channel.id}>{channel.name}</option>
        {/each}
      </select>
    </div>

    <!-- Playlists -->
    {#if playlists.length > 0}
      <div class="filter-group">
        <label class="filter-label">
          Playlists
          {#if selectedPlaylists.length > 0}
            <span class="count-badge">{selectedPlaylists.length}</span>
          {/if}
        </label>
        <select multiple bind:value={selectedPlaylists} class="multi-select" size="3">
          {#each playlists as playlist}
            <option value={playlist.playlist_id}>
              {playlist.title} ({playlistCounts.get(playlist.playlist_id) || 0})
            </option>
          {/each}
        </select>
      </div>
    {/if}

    <!-- Tags -->
    {#if availableTags.length > 0}
      <div class="filter-group">
        <label class="filter-label">
          Tags
          {#if selectedTags.length > 0}
            <span class="count-badge">{selectedTags.length}</span>
          {/if}
        </label>
        <select multiple bind:value={selectedTags} class="multi-select" size="3">
          {#each availableTags as tag}
            <option value={tag}>{tag}</option>
          {/each}
        </select>
      </div>
    {/if}

    <!-- Download Status -->
    <div class="filter-group">
      <label class="filter-label">Download Status</label>
      <div class="checkbox-group">
        <label class="checkbox-label">
          <input type="checkbox" value="downloaded" bind:group={selectedStatuses} />
          Downloaded
        </label>
        <label class="checkbox-label">
          <input type="checkbox" value="tracked" bind:group={selectedStatuses} />
          Tracked
        </label>
        <label class="checkbox-label">
          <input type="checkbox" value="not_downloaded" bind:group={selectedStatuses} />
          Not Downloaded
        </label>
      </div>
    </div>

    <!-- Sort -->
    <div class="filter-group">
      <label class="filter-label">Sort By</label>
      <div class="sort-controls">
        <select bind:value={sortField} class="sort-select">
          <option value="date">Date</option>
          <option value="views">Views</option>
          <option value="duration">Duration</option>
          <option value="title">Title</option>
          {#if searchQuery.trim()}
            <option value="relevance">Relevance</option>
          {/if}
        </select>
        <select bind:value={sortDirection} class="sort-select">
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </div>
    </div>
  </div>

  {#if activeFilterCount > 0}
    <div class="footer">
      <button class="clear-button" on:click={clearFilters}>
        Clear All Filters ({activeFilterCount})
      </button>
    </div>
  {/if}
</div>

<style>
  .filter-panel {
    background: white;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .search-section {
    margin-bottom: 20px;
  }

  .search-input {
    width: 100%;
    padding: 12px 16px;
    font-size: 16px;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    box-sizing: border-box;
  }

  .search-input:focus {
    outline: none;
    border-color: #4285f4;
    box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.1);
  }

  .filters-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
  }

  .filter-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .filter-label {
    font-size: 14px;
    font-weight: 500;
    color: #333;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .count-badge {
    display: inline-block;
    background: #4285f4;
    color: white;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 10px;
    font-weight: 600;
  }

  .date-inputs {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .date-input {
    flex: 1;
    padding: 8px;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    font-size: 14px;
  }

  .date-separator {
    color: #666;
    font-size: 13px;
  }

  .multi-select {
    padding: 8px;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    font-size: 14px;
    background: white;
  }

  .multi-select:focus {
    outline: none;
    border-color: #4285f4;
  }

  .checkbox-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    cursor: pointer;
  }

  .checkbox-label input[type='checkbox'] {
    cursor: pointer;
  }

  .sort-controls {
    display: flex;
    gap: 8px;
  }

  .sort-select {
    flex: 1;
    padding: 8px;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    font-size: 14px;
    background: white;
  }

  .footer {
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid #e0e0e0;
  }

  .clear-button {
    padding: 10px 20px;
    background: #f0f0f0;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
  }

  .clear-button:hover {
    background: #e0e0e0;
  }

  @media (max-width: 768px) {
    .filters-grid {
      grid-template-columns: 1fr;
    }

    .date-inputs {
      flex-direction: column;
      align-items: stretch;
    }

    .date-separator {
      text-align: center;
    }
  }
</style>
