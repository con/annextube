<script lang="ts">
  import type { Video } from '@/types/models';
  import VideoCard from './VideoCard.svelte';

  export let videos: Video[];
  export let totalVideos: number = 0;
  export let onVideoClick: (video: Video) => void = () => {};
  export let loading: boolean = false;
  export let error: string | null = null;

  $: isFiltered = totalVideos > 0 && videos.length !== totalVideos;
</script>

<div class="video-list-container">
  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
      <p>Loading videos...</p>
    </div>
  {:else if error}
    <div class="error">
      <p class="error-title">Error loading videos</p>
      <p class="error-message">{error}</p>
    </div>
  {:else if videos.length === 0}
    <div class="empty">
      {#if isFiltered}
        <p>No videos match the current filters.</p>
        <p class="hint">Try adjusting your search or filter criteria.</p>
      {:else}
        <p>No videos found in this archive.</p>
        <p class="hint">Check that videos.tsv exists in the videos/ directory.</p>
      {/if}
    </div>
  {:else}
    {#if totalVideos > 0}
      <div class="result-header">
        <p class="result-count">
          {#if isFiltered}
            Showing {videos.length} of {totalVideos} videos
          {:else}
            {videos.length} videos
          {/if}
        </p>
      </div>
    {/if}
    <div class="video-grid">
      {#each videos as video (video.video_id)}
        <VideoCard {video} onClick={onVideoClick} />
      {/each}
    </div>
  {/if}
</div>

<style>
  .video-list-container {
    width: 100%;
    min-height: 400px;
  }

  .result-header {
    padding: 12px 0;
    border-bottom: 1px solid #e0e0e0;
    margin-bottom: 16px;
  }

  .result-count {
    margin: 0;
    font-size: 14px;
    color: #606060;
    font-weight: 500;
  }

  .video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
    padding: 20px 0;
  }

  @media (max-width: 768px) {
    .video-grid {
      grid-template-columns: 1fr;
      gap: 16px;
    }
  }

  @media (min-width: 1400px) {
    .video-grid {
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    }
  }

  .loading,
  .error,
  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 400px;
    text-align: center;
    padding: 40px 20px;
  }

  .spinner {
    width: 48px;
    height: 48px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #065fd4;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .loading p {
    color: #606060;
    font-size: 16px;
  }

  .error {
    color: #d32f2f;
  }

  .error-title {
    font-size: 18px;
    font-weight: 500;
    margin: 0 0 8px 0;
  }

  .error-message {
    font-size: 14px;
    color: #666;
    margin: 0;
  }

  .empty {
    color: #606060;
  }

  .empty p {
    margin: 8px 0;
  }

  .hint {
    font-size: 14px;
    color: #999;
  }
</style>
