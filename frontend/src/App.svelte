<script lang="ts">
  import { onMount } from 'svelte';
  import type { Video } from '@/types/models';
  import { dataLoader } from '@/services/data-loader';
  import { router } from '@/services/router';
  import VideoList from '@/components/VideoList.svelte';
  import VideoDetail from '@/components/VideoDetail.svelte';

  let videos: Video[] = [];
  let loading = true;
  let error: string | null = null;
  let currentRoute = router.getCurrentRoute();
  let selectedVideo: Video | null = null;

  onMount(async () => {
    // Load all videos for list view
    try {
      videos = await dataLoader.loadVideos();
      loading = false;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unknown error loading archive';
      loading = false;
    }

    // Subscribe to route changes
    router.subscribe((route) => {
      currentRoute = route;
      if (route.name === 'video') {
        // Find video by ID and set as selected
        const videoId = route.params.video_id;
        selectedVideo = videos.find((v) => v.video_id === videoId) || null;
      } else {
        selectedVideo = null;
      }
    });
  });

  function handleVideoClick(video: Video) {
    router.navigate('video', { video_id: video.video_id });
  }

  function handleBackToList() {
    router.navigate('home');
  }
</script>

<main>
  <header>
    <div class="header-content">
      <h1>📹 YouTube Archive Browser</h1>
      <p class="subtitle">
        {#if !loading && !error}
          {videos.length} videos archived
        {/if}
      </p>
    </div>
  </header>

  <div class="container">
    {#if selectedVideo}
      <VideoDetail video={selectedVideo} onBack={handleBackToList} />
    {:else}
      <VideoList
        {videos}
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
