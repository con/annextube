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
  let selectedStatusFilter: string = 'all'; // Dropdown: 'all', 'downloaded', 'metadata_only'
  let selectedPlaylists: string[] = [];
  let sortField: SortField = 'date';
  let sortDirection: SortDirection = 'desc';

  // Convert dropdown selection to filter array
  $: selectedStatuses = selectedStatusFilter === 'all'
    ? [] // Empty array means no filter (show all)
    : selectedStatusFilter === 'downloaded'
    ? ['downloaded'] // Show only downloaded videos
    : selectedStatusFilter === 'metadata_only'
    ? ['metadata_only'] // Show only metadata-only videos
    : [];

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
    selectedStatusFilter;
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
    selectedStatusFilter = 'all';
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
    selectedStatusFilter !== 'all',
    selectedPlaylists.length > 0,
  ].filter(Boolean).length;

  // Date range presets
  function setDateRange(preset: string) {
    const now = new Date();
    const today = now.toISOString().split('T')[0];

    switch (preset) {
      case 'week':
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        dateFrom = weekAgo.toISOString().split('T')[0];
        dateTo = today;
        break;
      case 'month':
        const monthAgo = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
        dateFrom = monthAgo.toISOString().split('T')[0];
        dateTo = today;
        break;
      case 'year':
        const yearAgo = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
        dateFrom = yearAgo.toISOString().split('T')[0];
        dateTo = today;
        break;
      case 'thisyear':
        dateFrom = `${now.getFullYear()}-01-01`;
        dateTo = today;
        break;
      case 'lastyear':
        dateFrom = `${now.getFullYear() - 1}-01-01`;
        dateTo = `${now.getFullYear() - 1}-12-31`;
        break;
      case 'all':
        dateFrom = '';
        dateTo = '';
        break;
    }
  }
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
      <div class="date-presets">
        <button type="button" class="preset-btn" on:click={() => setDateRange('week')}>Last Week</button>
        <button type="button" class="preset-btn" on:click={() => setDateRange('month')}>Last Month</button>
        <button type="button" class="preset-btn" on:click={() => setDateRange('year')}>Last Year</button>
        <button type="button" class="preset-btn" on:click={() => setDateRange('thisyear')}>This Year</button>
        <button type="button" class="preset-btn" on:click={() => setDateRange('all')}>All Time</button>
      </div>
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
      <label class="filter-label">Video Availability</label>
      <select bind:value={selectedStatusFilter} class="filter-select">
        <option value="all">All Videos</option>
        <option value="downloaded">Backup Available (Local)</option>
        <option value="metadata_only">Metadata Only</option>
      </select>
    </div>

    <!-- Sort -->
    <div class="filter-group">
      <label class="filter-label">Sort By</label>
      <div class="sort-controls">
        <select bind:value={sortField} class="sort-select">
          <option value="date">Date</option>
          <option value="views">Views</option>
          <option value="comments">Comments</option>
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

  .date-presets {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
    flex-wrap: wrap;
  }

  .preset-btn {
    padding: 6px 12px;
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .preset-btn:hover {
    background: #e8f0fe;
    border-color: #4285f4;
    color: #4285f4;
  }

  .preset-btn:active {
    background: #d2e3fc;
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
