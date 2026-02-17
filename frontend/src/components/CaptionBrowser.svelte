<script lang="ts">
  import { onMount, afterUpdate } from 'svelte';
  import type { Video } from '@/types/models';
  import { parseVtt, type VttCue } from '@/utils/vtt-parser';
  import { formatDuration, formatCaptionLang } from '@/utils/format';
  import { dataLoader } from '@/services/data-loader';

  export let video: Video;
  export let channelDir: string | undefined = undefined;
  export let currentTime: number = 0;
  export let onSeek: (time: number) => void = () => {};
  export let onHide: () => void = () => {};
  export let initialLang: string | undefined = undefined;
  export let onLangChange: ((lang: string) => void) | undefined = undefined;
  export let initialSearchQuery: string | undefined = undefined;
  export let initialCaseSensitive: boolean = false;
  export let initialUseRegex: boolean = false;
  export let initialFilterMode: boolean = false;
  export let initialMatchPos: number | undefined = undefined;
  export let onSearchStateChange: ((state: { query: string; caseSensitive: boolean; useRegex: boolean; filterMode: boolean; matchPos: number }) => void) | undefined = undefined;

  // Internal state
  let selectedLang: string = '';
  let cues: VttCue[] = [];
  let loading = false;
  let error = '';
  let searchQuery = initialSearchQuery || '';
  let autoScroll = true;
  let activeCueIndex = -1;
  let caseSensitive = initialCaseSensitive;
  let useRegex = initialUseRegex;
  let filterMode = initialFilterMode; // true = hide non-matching cues; false = dim them

  function notifySearchStateChange() {
    onSearchStateChange?.({ query: searchQuery, caseSensitive, useRegex, filterMode, matchPos: currentMatchPos });
  }

  function toggleFilterMode() {
    filterMode = !filterMode;
    // When exiting filter mode, scroll to the current match in the full list
    // (the scroll position from the short filtered list is meaningless)
    if (!filterMode && matchCount > 0) {
      scrollToMatch(currentMatchPos);
    }
    notifySearchStateChange();
  }

  // DOM refs
  let cueListEl: HTMLDivElement;
  let autoScrollTimer: ReturnType<typeof setTimeout> | null = null;

  // Available languages
  $: languages = video.captions_available || [];

  // Auto-select language when video changes (prefer initialLang, then 'en', then first)
  $: if (languages.length > 0 && !selectedLang) {
    const pref = initialLang || 'en';
    selectedLang = languages.includes(pref) ? pref : languages[0];
  }

  // Reset when video changes (track previous ID so we don't depend on selectedLang,
  // which would cause this block to revert user language picks)
  let prevVideoId = video.video_id;
  $: {
    const vid = video.video_id;
    if (vid && vid !== prevVideoId) {
      prevVideoId = vid;
      const pref = initialLang || 'en';
      selectedLang = languages.includes(pref) ? pref : (languages[0] || '');
    }
  }

  // Load captions when language changes
  $: if (selectedLang) {
    loadCaptions(selectedLang);
  }

  // Track active cue based on currentTime
  $: {
    if (cues.length > 0) {
      activeCueIndex = findActiveCue(currentTime);
    }
  }

  // Search: filter and highlight
  $: searchRegex = buildSearchRegex(searchQuery, caseSensitive, useRegex);
  $: matchingIndices = searchRegex
    ? cues.reduce((acc: number[], cue, idx) => {
        if (searchRegex!.test(cue.text)) acc.push(idx);
        return acc;
      }, [])
    : [];
  $: matchCount = matchingIndices.length;

  function buildSearchRegex(query: string, cs: boolean, re: boolean): RegExp | null {
    if (!query) return null;
    try {
      // No 'g' flag — .test() with 'g' is stateful (advances lastIndex),
      // which breaks when called in a loop across different strings.
      // highlightText() creates its own regex with 'g' for .replace().
      const flags = cs ? '' : 'i';
      const pattern = re ? query : escapeRegex(query);
      return new RegExp(pattern, flags);
    } catch {
      // Invalid regex — treat as literal
      return new RegExp(escapeRegex(query), cs ? '' : 'i');
    }
  }

  // Current search match navigation
  let currentMatchPos = 0;
  let searchInitialized = false;
  $: if (matchingIndices.length > 0) {
    if (!searchInitialized && initialMatchPos != null && initialMatchPos >= 0 && initialMatchPos < matchingIndices.length) {
      // First match computation with a restored position from URL
      currentMatchPos = initialMatchPos;
      scrollToMatch(initialMatchPos);
      searchInitialized = true;
    } else {
      // Normal behavior: reset to first match
      currentMatchPos = 0;
      scrollToMatch(0);
      searchInitialized = true;
    }
  } else {
    currentMatchPos = 0;
  }

  function scrollToMatch(pos: number) {
    // Run after DOM updates
    setTimeout(() => {
      const targetIdx = matchingIndices[pos];
      if (targetIdx == null) return;
      const el = cueListEl?.querySelector(`[data-cue-index="${targetIdx}"]`);
      if (el) {
        autoScroll = false;
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 0);
  }

  function getCaptionUrl(lang: string): string {
    const filePath = video.file_path || video.video_id;
    const base = dataLoader.baseUrl;
    return channelDir
      ? `${base}/${channelDir}/videos/${filePath}/video.${lang}.vtt`
      : `${base}/videos/${filePath}/video.${lang}.vtt`;
  }

  async function loadCaptions(lang: string) {
    if (!lang) return;
    loading = true;
    error = '';
    cues = [];
    activeCueIndex = -1;

    try {
      const response = await fetch(getCaptionUrl(lang));
      if (!response.ok) {
        throw new Error(`Failed to load captions: ${response.statusText}`);
      }
      const text = await response.text();
      cues = parseVtt(text);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load captions';
      cues = [];
    } finally {
      loading = false;
    }
  }

  /** Binary search for active cue at given time */
  function findActiveCue(time: number): number {
    let lo = 0;
    let hi = cues.length - 1;
    let result = -1;

    while (lo <= hi) {
      const mid = (lo + hi) >>> 1;
      if (cues[mid].startTime <= time) {
        if (time < cues[mid].endTime) {
          return mid;
        }
        result = mid;
        lo = mid + 1;
      } else {
        hi = mid - 1;
      }
    }

    // If no exact match, return the most recent cue that started before current time
    if (result >= 0 && time >= cues[result].startTime) {
      return result;
    }
    return -1;
  }

  // Auto-scroll to active cue
  afterUpdate(() => {
    if (!autoScroll || activeCueIndex < 0) return;
    const activeEl = cueListEl?.querySelector('.cue.active');
    if (activeEl) {
      activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });

  function handleCueClick(cue: VttCue) {
    // Set activeCueIndex immediately so afterUpdate scrolls to the clicked
    // cue, not the old active cue (seek is async — currentTime updates later)
    activeCueIndex = cue.index;
    onSeek(cue.startTime);
    autoScroll = true;
  }

  function handleCueListScroll() {
    // User scrolled manually — disable auto-scroll
    autoScroll = false;
    // Re-enable after 5s idle
    if (autoScrollTimer) clearTimeout(autoScrollTimer);
    autoScrollTimer = setTimeout(() => {
      autoScroll = true;
    }, 5000);
  }

  function resumeAutoScroll() {
    autoScroll = true;
    if (autoScrollTimer) clearTimeout(autoScrollTimer);
  }

  function navigateMatch(direction: 1 | -1) {
    if (matchCount === 0) return;
    currentMatchPos = (currentMatchPos + direction + matchCount) % matchCount;
    scrollToMatch(currentMatchPos);
    notifySearchStateChange();
  }

  function handleSearchKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      event.preventDefault();
      navigateMatch(event.shiftKey ? -1 : 1);
    }
  }

  function formatCueTime(seconds: number): string {
    return formatDuration(Math.floor(seconds));
  }

  /** Highlight search matches in text with <mark> elements */
  function highlightText(text: string, query: string): string {
    if (!query) return escapeHtml(text);
    const escaped = escapeHtml(text);
    try {
      const flags = caseSensitive ? 'g' : 'gi';
      const pattern = useRegex ? query : escapeRegex(escapeHtml(query));
      const regex = new RegExp(`(${pattern})`, flags);
      return escaped.replace(regex, '<mark>$1</mark>');
    } catch {
      return escaped;
    }
  }

  function escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function escapeRegex(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function handleLanguageChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    selectedLang = select.value;
    onLangChange?.(selectedLang);
  }

  onMount(() => {
    return () => {
      if (autoScrollTimer) clearTimeout(autoScrollTimer);
    };
  });
</script>

<div class="caption-browser">
  <div class="caption-header">
    <div class="header-left">
      <span class="header-title">Transcript</span>
      {#if languages.length > 1}
        <select
          class="lang-select"
          value={selectedLang}
          on:change={handleLanguageChange}
        >
          {#each languages as lang}
            <option value={lang}>{formatCaptionLang(lang)}</option>
          {/each}
        </select>
      {:else if languages.length === 1}
        <span class="lang-badge">{formatCaptionLang(languages[0])}</span>
      {/if}
    </div>
    <div class="header-right">
      {#if selectedLang}
        <a
          class="download-btn"
          href={getCaptionUrl(selectedLang)}
          download="video.{selectedLang}.vtt"
          title="Download VTT caption file"
        >
          Download
        </a>
      {/if}
      <button
        class="toggle-btn"
        on:click={onHide}
        title="Hide transcript"
      >
        Hide
      </button>
    </div>
  </div>

  <div class="search-bar">
    <div class="search-row">
      <input
        type="text"
        class="search-input"
        placeholder="Search (Enter/Shift+Enter to navigate)"
        bind:value={searchQuery}
        on:input={notifySearchStateChange}
        on:keydown={handleSearchKeydown}
      />
      <button
        class="option-btn"
        class:active={caseSensitive}
        on:click={() => { caseSensitive = !caseSensitive; notifySearchStateChange(); }}
        title="Case sensitive"
        aria-pressed={caseSensitive}
      >C</button>
      <button
        class="option-btn"
        class:active={useRegex}
        on:click={() => { useRegex = !useRegex; notifySearchStateChange(); }}
        title="Regular expression"
        aria-pressed={useRegex}
      >.*</button>
    </div>
    {#if searchQuery}
      <div class="nav-row">
        <button
          class="option-btn"
          class:active={filterMode}
          on:click={toggleFilterMode}
          title="Filter: hide non-matching cues"
          aria-pressed={filterMode}
        >Filter</button>
        <div class="nav-group">
          <span class="match-count" role="status" aria-live="polite">{matchCount > 0 ? `${currentMatchPos + 1}/${matchCount}` : '0/0'}</span>
          <button
            class="nav-btn"
            on:click={() => navigateMatch(-1)}
            title="Previous match (Shift+Enter)"
            aria-label="Previous match"
            disabled={matchCount === 0}
          >&lsaquo; Prev</button>
          <button
            class="nav-btn"
            on:click={() => navigateMatch(1)}
            title="Next match (Enter)"
            aria-label="Next match"
            disabled={matchCount === 0}
          >Next &rsaquo;</button>
        </div>
      </div>
    {/if}
  </div>

  <div
    class="cue-list"
    bind:this={cueListEl}
    on:scroll={handleCueListScroll}
  >
    {#if loading}
      <div class="cue-loading">Loading captions...</div>
    {:else if error}
      <div class="cue-error">{error}</div>
    {:else if cues.length === 0}
      <div class="cue-empty">No captions available</div>
    {:else}
      {#each cues as cue (cue.index)}
        {@const isActive = cue.index === activeCueIndex}
        {@const isMatch = searchRegex ? searchRegex.test(cue.text) : false}
        {@const isDimmed = searchQuery && !isMatch}
        {#if !(filterMode && isDimmed)}
          <button
            class="cue"
            class:active={isActive}
            class:search-match={isMatch}
            class:dimmed={isDimmed}
            data-cue-index={cue.index}
            on:click={() => handleCueClick(cue)}
          >
            <span class="cue-time">{formatCueTime(cue.startTime)}</span>
            <span class="cue-text">
              {#if searchQuery && isMatch}
                {@html highlightText(cue.text, searchQuery)}
              {:else}
                {cue.text}
              {/if}
            </span>
          </button>
        {/if}
      {/each}
    {/if}
  </div>

  {#if !autoScroll && cues.length > 0 && activeCueIndex >= 0}
    <button class="autoscroll-btn" on:click={resumeAutoScroll}>
      Resume auto-scroll
    </button>
  {/if}
</div>

<style>
  .caption-browser {
    display: flex;
    flex-direction: column;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background: #fff;
    overflow: hidden;
  }

  .caption-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    background: #f8f9fa;
    border-bottom: 1px solid #e0e0e0;
    flex-shrink: 0;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .header-title {
    font-size: 14px;
    font-weight: 600;
    color: #030303;
  }

  .lang-select {
    padding: 3px 6px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 12px;
    background: #fff;
    cursor: pointer;
  }

  .lang-badge {
    font-size: 11px;
    font-weight: 500;
    color: #606060;
    background: #e8e8e8;
    padding: 2px 6px;
    border-radius: 3px;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .download-btn {
    background: none;
    border: 1px solid #ccc;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    color: #606060;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.2s;
  }

  .download-btn:hover {
    background: #e8e8e8;
    color: #030303;
  }

  .toggle-btn {
    background: none;
    border: 1px solid #ccc;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    color: #606060;
    cursor: pointer;
    transition: all 0.2s;
  }

  .toggle-btn:hover {
    background: #e8e8e8;
    color: #030303;
  }

  .search-bar {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 12px;
    border-bottom: 1px solid #e0e0e0;
    flex-shrink: 0;
  }

  .search-row {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .search-input {
    flex: 1;
    min-width: 0;
    padding: 6px 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;
  }

  .search-input:focus {
    border-color: #1a73e8;
  }

  .option-btn {
    flex: none;
    background: #f0f0f0;
    border: 1px solid #ccc;
    border-radius: 3px;
    padding: 4px 7px;
    font-size: 11px;
    font-weight: 600;
    font-family: monospace;
    cursor: pointer;
    color: #666;
    line-height: 1;
    transition: all 0.15s;
  }

  .option-btn:hover {
    background: #e0e0e0;
  }

  .option-btn.active {
    background: #1a73e8;
    border-color: #1a73e8;
    color: white;
  }

  .nav-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
  }

  .nav-group {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-left: auto;
  }

  .match-count {
    font-size: 12px;
    color: #606060;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  .nav-btn {
    background: #f0f0f0;
    border: 1px solid #ccc;
    border-radius: 3px;
    padding: 4px 8px;
    font-size: 12px;
    cursor: pointer;
    color: #606060;
    line-height: 1;
    transition: all 0.15s;
  }

  .nav-btn:hover:not(:disabled) {
    background: #e0e0e0;
  }

  .nav-btn:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .cue-list {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }

  .cue {
    display: flex;
    gap: 10px;
    padding: 8px 12px;
    border: none;
    background: none;
    width: 100%;
    text-align: left;
    cursor: pointer;
    transition: background 0.15s;
    font-size: 13px;
    line-height: 1.5;
    border-bottom: 1px solid #f0f0f0;
  }

  .cue:hover {
    background: #f0f4ff;
  }

  .cue.active {
    background: #e8f0fe;
    border-left: 3px solid #1a73e8;
    padding-left: 9px;
  }

  .cue.dimmed {
    opacity: 0.35;
  }

  .cue.search-match {
    opacity: 1;
    background: #fff8e1;
  }

  .cue.search-match.active {
    background: #e8f0fe;
  }

  .cue-time {
    flex-shrink: 0;
    font-size: 12px;
    color: #1a73e8;
    font-variant-numeric: tabular-nums;
    min-width: 36px;
    padding-top: 1px;
  }

  .cue-text {
    color: #030303;
    word-break: break-word;
  }

  .cue-text :global(mark) {
    background: #ffeb3b;
    color: inherit;
    padding: 0 1px;
    border-radius: 2px;
  }

  .cue-loading,
  .cue-error,
  .cue-empty {
    padding: 24px 12px;
    text-align: center;
    font-size: 13px;
    color: #606060;
  }

  .cue-error {
    color: #d32f2f;
  }

  .autoscroll-btn {
    display: block;
    width: 100%;
    padding: 8px;
    background: #f0f4ff;
    border: none;
    border-top: 1px solid #e0e0e0;
    font-size: 12px;
    color: #1a73e8;
    cursor: pointer;
    text-align: center;
    flex-shrink: 0;
  }

  .autoscroll-btn:hover {
    background: #e0ecff;
  }

  @media (max-width: 1023px) {
    .cue-list {
      max-height: 350px;
    }
  }
</style>
