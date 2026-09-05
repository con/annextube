<script lang="ts">
  import { onMount } from 'svelte';
  import type { Video, Playlist, Channel } from '@/types/models';
  import { dataLoader } from '@/services/data-loader';
  import { router } from '@/services/router';
  import { searchService } from '@/services/search';
  import VideoList from '@/components/VideoList.svelte';
  import VideoDetail from '@/components/VideoDetail.svelte';
  import FilterPanel from '@/components/FilterPanel.svelte';
  import ChannelList from '@/components/ChannelList.svelte';
  import CloneCommand from '@/components/CloneCommand.svelte';

  const appVersion: string = __APP_VERSION__;

  let isMultiChannel = false;
  let channels: Channel[] = [];
  let selectedChannel: Channel | null = null;
  let allVideos: Video[] = [];
  let filteredVideos: Video[] = [];
  let fuzzyStartIndex: number = Infinity;
  let playlists: Playlist[] = [];
  let loading = true;
  let error: string | null = null;
  let currentRoute = router.getCurrentRoute();
  let selectedVideo: Video | null = null;

  onMount(async () => {
    try {
      // Check if this is a multi-channel collection
      isMultiChannel = await dataLoader.isMultiChannelMode();

      if (isMultiChannel) {
        // Load channels list
        channels = await dataLoader.loadChannels();
        loading = false;
      } else {
        // Single-channel mode: load videos directly
        allVideos = await dataLoader.loadVideos();
        filteredVideos = allVideos;

        // Initialize search service with all videos
        searchService.initialize(allVideos);

        // Load playlists (non-blocking, failure is OK)
        try {
          playlists = await dataLoader.loadPlaylists();
        } catch (err) {
          console.warn('Could not load playlists:', err);
          playlists = [];
        }

        loading = false;
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unknown error loading archive';
      loading = false;
    }

    // Subscribe to route changes
    router.subscribe(async (route) => {
      currentRoute = route;
      if (route.name === 'video') {
        const videoId = route.params.video_id;
        const channelDir = route.params.channel_dir;

        // If channel context is provided, load channel first
        if (channelDir && isMultiChannel) {
          const channel = channels.find((c) => c.channel_dir === channelDir);
          if (channel && channel.channel_dir !== selectedChannel?.channel_dir) {
            await loadChannelData(channel);
          }
        }

        // Find video by ID in loaded videos
        selectedVideo = allVideos.find((v) => v.video_id === videoId) || null;

        // If video not found in current context, try loading metadata directly
        if (!selectedVideo) {
          try {
            selectedVideo = await dataLoader.loadVideoMetadata(videoId);
          } catch (err) {
            console.warn('Could not load video metadata:', err);
            selectedVideo = null;
          }
        }
      } else if (route.name === 'channel' && isMultiChannel) {
        // Load channel videos from URL
        const channelDir = route.params.channel_dir;
        const channel = channels.find((c) => c.channel_dir === channelDir);
        if (channel) {
          await loadChannelData(channel);
        }
        selectedVideo = null;
      } else {
        // Home route
        selectedVideo = null;
      }
    });
  });

  async function loadChannelData(channel: Channel) {
    // Load videos and playlists for this channel
    loading = true;
    selectedChannel = channel;
    try {
      allVideos = await dataLoader.loadChannelVideos(channel.channel_dir!);
      filteredVideos = allVideos;
      searchService.initialize(allVideos);

      // Load playlists for this channel (non-blocking, failure is OK)
      try {
        playlists = await dataLoader.loadChannelPlaylists(channel.channel_dir!);
      } catch (err) {
        console.warn('Could not load playlists for channel:', err);
        playlists = [];
      }

      loading = false;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unknown error loading channel';
      loading = false;
    }
  }

  function handleChannelClick(channel: Channel) {
    // Navigate to channel URL (router will handle loading)
    router.navigate('channel', { channel_dir: channel.channel_dir! });
  }

  function handleBackToChannels() {
    // Navigate back to home (router will handle state reset)
    router.navigate('home');
    selectedChannel = null;
    allVideos = [];
    filteredVideos = [];
    playlists = [];
    error = null;
  }

  function handleVideoClick(video: Video) {
    // Include channel context in video URL if available
    if (selectedChannel) {
      router.navigate('video', {
        video_id: video.video_id,
        channel_dir: selectedChannel.channel_dir!,
      });
    } else {
      router.navigate('video', { video_id: video.video_id });
    }
  }

  function handleBackToList() {
    // Return to channel view if in channel context, otherwise home
    if (selectedChannel) {
      router.navigate('channel', { channel_dir: selectedChannel.channel_dir! });
    } else {
      router.navigate('home');
    }
  }

  let captionSearchActive = false;
  let channelSearchQuery = '';

  $: filteredChannels = channelSearchQuery.trim()
    ? channels.filter((ch) => {
        const q = channelSearchQuery.toLowerCase();
        return (
          (ch.name || '').toLowerCase().includes(q) ||
          (ch.custom_url || '').toLowerCase().includes(q) ||
          (ch.description || '').toLowerCase().includes(q)
        );
      })
    : channels;

  function handleFilterChange(filtered: Video[]) {
    filteredVideos = filtered;
  }

  function handleCaptionSearchActive(active: boolean) {
    captionSearchActive = active;
  }
</script>

<main>
  <header>
    <div class="header-content">
      {#if isMultiChannel && (selectedChannel || selectedVideo)}
        <nav class="breadcrumb" aria-label="Breadcrumb">
          <button on:click={handleBackToChannels}>Channels</button>
          {#if selectedChannel}
            <span class="separator">/</span>
            {#if selectedVideo}
              <button on:click={handleBackToList}>{selectedChannel.title}</button>
              <span class="separator">/</span>
              <span class="current">{selectedVideo.title}</span>
            {:else}
              <span class="current">{selectedChannel.title}</span>
            {/if}
          {/if}
        </nav>
      {/if}
      <div class="title-row">
        <h1><a href="https://github.com/con/annextube" target="_blank" rel="noopener noreferrer" class="app-link">AnnexTube</a> <span class="version">v{appVersion}</span></h1>
        <a
          href="https://github.com/con/annextube"
          target="_blank"
          rel="noopener noreferrer"
          class="github-link"
          aria-label="AnnexTube on GitHub"
          title="AnnexTube on GitHub"
        >
          <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
              0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13
              -.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07
              -1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82
              .64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12
              .51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48
              0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
          </svg>
        </a>
        <CloneCommand
          baseUrl={dataLoader.baseUrl}
          channelDir={selectedChannel?.channel_dir ?? currentRoute.params.channel_dir ?? null}
          videoFilePath={selectedVideo?.file_path ?? null}
          {isMultiChannel}
        />
      </div>
      <p class="subtitle">
        {#if isMultiChannel && !selectedChannel}
          {channels.length} channel{channels.length !== 1 ? 's' : ''} in collection
        {:else if !loading && !error}
          {allVideos.length} video{allVideos.length !== 1 ? 's' : ''} archived
        {/if}
      </p>
    </div>
  </header>

  <div class="container">
    {#if selectedVideo}
      <VideoDetail video={selectedVideo} onBack={handleBackToList} channelDir={selectedChannel?.channel_dir} />
    {:else if isMultiChannel && !selectedChannel}
      <!-- Multi-channel mode: show channels overview -->
      {#if channels.length > 1}
        <div class="channel-filter">
          <input
            type="text"
            placeholder="Filter channels..."
            bind:value={channelSearchQuery}
            class="channel-search-input"
          />
          {#if channelSearchQuery && filteredChannels.length !== channels.length}
            <span class="channel-filter-count">
              {filteredChannels.length} of {channels.length} channels
            </span>
          {/if}
        </div>
      {/if}
      <ChannelList
        channels={filteredChannels}
        {loading}
        {error}
        onChannelClick={handleChannelClick}
      />
    {:else}
      <!-- Single-channel mode or channel selected: show videos -->
      {#if !loading && !error}
        <FilterPanel
          videos={allVideos}
          {playlists}
          onFilterChange={handleFilterChange}
          onCaptionSearchActive={handleCaptionSearchActive}
          bind:fuzzyStartIndex
        />
      {/if}
      {#if !captionSearchActive}
      <VideoList
        videos={filteredVideos}
        totalVideos={allVideos.length}
        {loading}
        {error}
        onVideoClick={handleVideoClick}
        {fuzzyStartIndex}
      />
      {/if}
    {/if}
  </div>
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu,
                 Cantarell, 'Helvetica Neue', sans-serif;
    background: #f9f9f9;
  }

  main {
    min-height: 100vh;
  }

  header {
    background: white;
    border-bottom: 1px solid #e0e0e0;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    position: sticky;
    top: 0;
    z-index: 100;
  }

  .header-content {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px 32px;
  }

  .breadcrumb {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 14px;
    margin-bottom: 8px;
    flex-wrap: wrap;
  }

  .breadcrumb button {
    background: none;
    border: none;
    color: #065fd4;
    cursor: pointer;
    padding: 0;
    font-size: inherit;
  }

  .breadcrumb button:hover {
    text-decoration: underline;
  }

  .breadcrumb .separator {
    color: #909090;
  }

  .breadcrumb .current {
    color: #606060;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 400px;
  }

  .title-row {
    display: flex;
    align-items: baseline;
    gap: 1rem;
    position: relative;
  }

  h1 {
    margin: 0;
    color: #030303;
    font-size: 24px;
    font-weight: 500;
  }

  .app-link {
    color: inherit;
    text-decoration: none;
  }

  .app-link:hover {
    text-decoration: underline;
  }

  .github-link {
    display: inline-flex;
    align-items: center;
    align-self: center;
    color: #606060;
  }

  .github-link:hover {
    color: #030303;
  }

  .version {
    font-size: 12px;
    font-weight: 400;
    color: #767676;
    vertical-align: middle;
  }

  .subtitle {
    margin: 8px 0 0 0;
    color: #606060;
    font-size: 14px;
  }

  .container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 32px 40px 32px;
  }

  .channel-filter {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 0;
  }

  .channel-search-input {
    flex: 1;
    max-width: 400px;
    padding: 8px 12px;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    font-size: 14px;
    outline: none;
  }

  .channel-search-input:focus {
    border-color: #065fd4;
    box-shadow: 0 0 0 2px rgba(6, 95, 212, 0.1);
  }

  .channel-filter-count {
    font-size: 13px;
    color: #606060;
  }

  @media (max-width: 768px) {
    .header-content,
    .container {
      padding-left: 16px;
      padding-right: 16px;
    }

    h1 {
      font-size: 20px;
    }
  }
</style>
