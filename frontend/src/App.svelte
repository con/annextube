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

  let isMultiChannel = false;
  let channels: Channel[] = [];
  let selectedChannel: Channel | null = null;
  let allVideos: Video[] = [];
  let filteredVideos: Video[] = [];
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

  function handleFilterChange(filtered: Video[]) {
    filteredVideos = filtered;
  }
</script>

<main>
  <header>
    <div class="header-content">
      {#if selectedChannel}
        <button class="back-button" on:click={handleBackToChannels}>
          ← Back to channels
        </button>
      {/if}
      <h1>📹 YouTube Archive Browser</h1>
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
      <ChannelList
        {channels}
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
        />
      {/if}
      <VideoList
        videos={filteredVideos}
        totalVideos={allVideos.length}
        {loading}
        {error}
        onVideoClick={handleVideoClick}
      />
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

  .back-button {
    background: none;
    border: none;
    color: #065fd4;
    font-size: 14px;
    cursor: pointer;
    padding: 4px 0;
    margin-bottom: 8px;
    display: inline-block;
  }

  .back-button:hover {
    text-decoration: underline;
  }

  h1 {
    margin: 0;
    color: #030303;
    font-size: 24px;
    font-weight: 500;
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
