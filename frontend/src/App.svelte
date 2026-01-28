<script lang="ts">
  import { onMount } from 'svelte';
  import type { Video } from '@/types/models';
  import { dataLoader } from '@/services/data-loader';
  import VideoList from '@/components/VideoList.svelte';

  let videos: Video[] = [];
  let loading = true;
  let error: string | null = null;
  let selectedVideo: Video | null = null;

  onMount(async () => {
    try {
      videos = await dataLoader.loadVideos();
      loading = false;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unknown error loading archive';
      loading = false;
    }
  });

  function handleVideoClick(video: Video) {
    selectedVideo = video;
    // TODO: Navigate to video detail view (Phase 5)
    console.log('Selected video:', video.video_id, video.title);
  }

  function handleBackToList() {
    selectedVideo = null;
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
      <!-- Video detail view -->
      <div class="video-detail">
        <button class="back-button" on:click={handleBackToList}>
          ← Back to list
        </button>
        <h2>{selectedVideo.title}</h2>
        <p class="channel-name">By {selectedVideo.channel_name}</p>
        <div class="video-info">
          <p><strong>Video ID:</strong> {selectedVideo.video_id}</p>
          <p><strong>Duration:</strong> {selectedVideo.duration}s</p>
          <p><strong>Views:</strong> {selectedVideo.view_count.toLocaleString()}</p>
          <p><strong>Likes:</strong> {selectedVideo.like_count.toLocaleString()}</p>
          <p><strong>Comments:</strong> {selectedVideo.comment_count.toLocaleString()}</p>
          <p><strong>Status:</strong> {selectedVideo.download_status}</p>
        </div>
        <p class="note">
          Video player component will be added in next phase.
        </p>
      </div>
    {:else}
      <!-- Video list view -->
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

  .video-detail {
    background: white;
    border-radius: 8px;
    padding: 32px;
    margin-top: 24px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .back-button {
    background: #f0f0f0;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    margin-bottom: 24px;
    transition: background 0.2s;
  }

  .back-button:hover {
    background: #e0e0e0;
  }

  .video-detail h2 {
    margin: 0 0 8px 0;
    font-size: 22px;
    color: #030303;
  }

  .channel-name {
    color: #606060;
    font-size: 14px;
    margin: 0 0 24px 0;
  }

  .video-info {
    background: #f9f9f9;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 24px;
  }

  .video-info p {
    margin: 8px 0;
    font-size: 14px;
    color: #030303;
  }

  .note {
    color: #999;
    font-size: 14px;
    font-style: italic;
    text-align: center;
    padding: 20px;
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

    .video-detail {
      padding: 20px;
    }
  }
</style>
