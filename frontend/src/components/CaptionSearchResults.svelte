<!--
  CaptionSearchResults Component

  Displays Pagefind caption search results grouped by video.
  Each card shows the video title, channel, timestamp, excerpt with
  highlights, and an expandable list of all matches when there are
  multiple hits in the same video.
-->
<script lang="ts">
  import type { GroupedCaptionResult } from '@/services/pagefind';
  import { formatTimestamp } from '@/services/pagefind';

  export let results: GroupedCaptionResult[] = [];
  export let query: string = '';
  export let loading: boolean = false;

  /** How many results to show initially */
  const PAGE_SIZE = 10;
  let visibleCount = PAGE_SIZE;

  /** Track which result cards have their match list expanded */
  let expandedIds: Set<string> = new Set();

  $: visibleResults = results.slice(0, visibleCount);
  $: hasMore = results.length > visibleCount;

  // Reset visible count and expanded state when results change
  $: if (results) {
    visibleCount = PAGE_SIZE;
    expandedIds = new Set();
  }

  function showMore() {
    visibleCount += PAGE_SIZE;
  }

  function toggleExpanded(videoId: string) {
    // Create a new Set to trigger Svelte reactivity
    const next = new Set(expandedIds);
    if (next.has(videoId)) {
      next.delete(videoId);
    } else {
      next.add(videoId);
    }
    expandedIds = next;
  }

  function navigateToVideo(videoId: string, timestamp: number) {
    const encodedQuery = encodeURIComponent(query);
    window.location.hash = `#/video/${videoId}?t=${Math.floor(timestamp)}&q=${encodedQuery}`;
  }

  function formatDate(dateStr: string): string {
    if (!dateStr) return '';
    // Normalize YYYYMMDD to YYYY-MM-DD
    let normalized = dateStr;
    if (dateStr.length === 8 && !dateStr.includes('-')) {
      normalized = `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
    }
    // Parse date parts directly to avoid timezone shift.
    // Date-only strings like "2024-03-15" are parsed as UTC midnight,
    // but toLocaleDateString uses the local timezone, which can shift
    // the displayed date backwards in negative-offset timezones.
    const match = normalized.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!match) {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return dateStr;
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
    const [, yearStr, monthStr, dayStr] = match;
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthIdx = parseInt(monthStr, 10) - 1;
    if (monthIdx < 0 || monthIdx > 11) return dateStr;
    return `${months[monthIdx]} ${parseInt(dayStr, 10)}, ${yearStr}`;
  }
</script>

<div class="caption-search-results">
  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Searching captions...</p>
    </div>
  {:else if query && results.length === 0}
    <div class="empty-state">
      <p>No caption matches found for '{query}'</p>
    </div>
  {:else}
    {#if results.length > 0}
      <div class="result-header">
        <p class="result-count">
          {results.length} video{results.length !== 1 ? 's' : ''} with caption matches
        </p>
      </div>
    {/if}

    <div class="results-list">
      {#each visibleResults as result (result.videoId)}
        <div class="result-card">
          <div
            class="result-main"
            role="button"
            tabindex="0"
            on:click={() => navigateToVideo(result.videoId, result.primaryTimestamp)}
            on:keydown={(e) => { if (e.key === 'Enter') navigateToVideo(result.videoId, result.primaryTimestamp); }}
          >
            <div class="result-info">
              <h3 class="result-title">{result.title}</h3>
              <div class="result-meta">
                {#if result.channelName}
                  <span class="channel-name">{result.channelName}</span>
                {/if}
                {#if result.channelName && result.uploadDate}
                  <span class="separator">&#8226;</span>
                {/if}
                {#if result.uploadDate}
                  <span class="upload-date">{formatDate(result.uploadDate)}</span>
                {/if}
              </div>
              <div class="result-excerpt-row">
                <span class="timestamp-badge">{formatTimestamp(result.primaryTimestamp)}</span>
                <span class="result-excerpt">{@html result.primaryExcerpt}</span>
              </div>
            </div>
            {#if result.matchCount > 1}
              <button
                class="match-count-badge"
                on:click|stopPropagation={() => toggleExpanded(result.videoId)}
                title="Show all {result.matchCount} matches"
              >
                {result.matchCount} matches
              </button>
            {/if}
          </div>

          {#if result.matchCount > 1 && expandedIds.has(result.videoId)}
            <div class="expanded-matches">
              {#each result.allMatches as match, idx}
                <button
                  class="match-item"
                  on:click={() => navigateToVideo(result.videoId, match.timestamp)}
                >
                  <span class="match-index">{idx + 1}.</span>
                  <span class="timestamp-badge small">{formatTimestamp(match.timestamp)}</span>
                  <span class="match-excerpt">{@html match.excerpt}</span>
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>

    {#if hasMore}
      <div class="show-more">
        <button class="show-more-button" on:click={showMore}>
          Show more ({results.length - visibleCount} remaining)
        </button>
      </div>
    {/if}
  {/if}
</div>

<style>
  .caption-search-results {
    width: 100%;
    min-height: 200px;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    text-align: center;
    padding: 40px 20px;
  }

  .spinner {
    width: 36px;
    height: 36px;
    border: 3px solid #f3f3f3;
    border-top: 3px solid #065fd4;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 12px;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .loading-state p {
    color: #606060;
    font-size: 14px;
    margin: 0;
  }

  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    text-align: center;
    padding: 40px 20px;
    color: #606060;
    font-size: 14px;
  }

  .empty-state p {
    margin: 0;
  }

  .result-header {
    padding: 12px 0;
    border-bottom: 1px solid #e0e0e0;
    margin-bottom: 8px;
  }

  .result-count {
    margin: 0;
    font-size: 14px;
    color: #606060;
    font-weight: 500;
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 0;
  }

  .result-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    overflow: hidden;
    transition: box-shadow 0.2s;
  }

  .result-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .result-main {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 16px;
    cursor: pointer;
    transition: background 0.15s;
  }

  .result-main:hover {
    background: #f8f9fa;
  }

  .result-info {
    flex: 1;
    min-width: 0;
  }

  .result-title {
    margin: 0 0 4px 0;
    font-size: 15px;
    font-weight: 500;
    color: #030303;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .result-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
    font-size: 13px;
    color: #606060;
  }

  .channel-name {
    font-weight: 500;
    color: #030303;
  }

  .separator {
    color: #909090;
  }

  .result-excerpt-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
  }

  .timestamp-badge {
    flex-shrink: 0;
    display: inline-block;
    background: #e8f0fe;
    color: #1a73e8;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 4px;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    margin-top: 1px;
  }

  .timestamp-badge.small {
    font-size: 11px;
    padding: 1px 5px;
  }

  .result-excerpt,
  .match-excerpt {
    font-size: 13px;
    color: #333;
    line-height: 1.5;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .result-excerpt :global(mark),
  .match-excerpt :global(mark) {
    background: #ffeb3b;
    color: inherit;
    padding: 0 1px;
    border-radius: 2px;
  }

  .match-count-badge {
    flex-shrink: 0;
    display: inline-block;
    background: #4285f4;
    color: white;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 12px;
    border: none;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.2s;
    margin-top: 2px;
  }

  .match-count-badge:hover {
    background: #1a73e8;
  }

  .expanded-matches {
    border-top: 1px solid #e0e0e0;
    background: #fafafa;
    padding: 4px 0;
  }

  .match-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 16px;
    width: 100%;
    border: none;
    background: none;
    text-align: left;
    cursor: pointer;
    transition: background 0.15s;
    font-family: inherit;
  }

  .match-item:hover {
    background: #f0f4ff;
  }

  .match-index {
    flex-shrink: 0;
    font-size: 12px;
    color: #909090;
    min-width: 18px;
    margin-top: 2px;
  }

  .show-more {
    display: flex;
    justify-content: center;
    padding: 16px 0;
  }

  .show-more-button {
    padding: 10px 24px;
    background: #f0f0f0;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
    color: #333;
  }

  .show-more-button:hover {
    background: #e0e0e0;
  }

  @media (max-width: 768px) {
    .result-main {
      flex-direction: column;
    }

    .match-count-badge {
      align-self: flex-start;
    }
  }
</style>
