<script lang="ts">
  import { onMount } from 'svelte';
  import type { Video, Comment } from '@/types/models';
  import { dataLoader } from '@/services/data-loader';
  import { formatViews, formatRelativeTime } from '@/utils/format';
  import VideoPlayer from './VideoPlayer.svelte';
  import CommentView from './CommentView.svelte';

  export let video: Video;
  export let onBack: () => void;

  let fullMetadata: Video = video;
  let comments: Comment[] = [];
  let loadingMetadata = false;
  let loadingComments = false;
  let showDescription = false;

  onMount(async () => {
    // Load full metadata (with tags, description, etc.)
    try {
      loadingMetadata = true;
      fullMetadata = await dataLoader.loadVideoMetadata(video.video_id);
    } catch (err) {
      console.warn('Could not load full metadata, using TSV data:', err);
      fullMetadata = video;
    } finally {
      loadingMetadata = false;
    }

    // Load comments
    try {
      loadingComments = true;
      comments = await dataLoader.loadComments(video.video_id);
    } catch (err) {
      console.warn('Could not load comments:', err);
      comments = [];
    } finally {
      loadingComments = false;
    }
  });

  function formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${minutes}:${String(secs).padStart(2, '0')}`;
  }
</script>

<div class="video-detail">
  <button class="back-button" on:click={onBack}>
    ← Back to list
  </button>

  <div class="player-container">
    <VideoPlayer video={fullMetadata} />
  </div>

  <div class="video-info">
    <h1 class="title">{fullMetadata.title}</h1>

    <div class="metadata-row">
      <div class="metadata-left">
        <span class="channel-name">{fullMetadata.channel_name}</span>
        <span class="separator">•</span>
        <span class="views">{formatViews(fullMetadata.view_count)}</span>
        <span class="separator">•</span>
        <span class="date">{formatRelativeTime(fullMetadata.published_at)}</span>
      </div>
      <div class="metadata-right">
        <a
          href={fullMetadata.source_url}
          target="_blank"
          rel="noopener noreferrer"
          class="youtube-link"
        >
          View on YouTube ↗
        </a>
        <div class="stat">
          <span class="stat-value">{fullMetadata.like_count.toLocaleString()}</span>
          <span class="stat-label">likes</span>
        </div>
      </div>
    </div>

    <div class="details-section">
      <button
        class="details-toggle"
        on:click={() => showDescription = !showDescription}
      >
        {showDescription ? '▼' : '▶'} Video Details
      </button>
      {#if showDescription}
        <div class="details-content">
          <div class="details-meta">
            <div><strong>Published:</strong> {new Date(fullMetadata.published_at).toLocaleDateString()}</div>
            <div><strong>Duration:</strong> {formatDuration(fullMetadata.duration)}</div>
            <div><strong>Download Status:</strong> {fullMetadata.download_status}</div>
            {#if fullMetadata.tags && fullMetadata.tags.length > 0}
              <div><strong>Tags:</strong> {fullMetadata.tags.join(', ')}</div>
            {/if}
            {#if fullMetadata.categories && fullMetadata.categories.length > 0}
              <div><strong>Categories:</strong> {fullMetadata.categories.join(', ')}</div>
            {/if}
            {#if fullMetadata.captions_available.length > 0}
              <div><strong>Captions:</strong> {fullMetadata.captions_available.join(', ')}</div>
            {/if}
            {#if fullMetadata.description}
              <div class="description-text">
                <strong>Description:</strong>
                <p>{fullMetadata.description}</p>
              </div>
            {/if}
          </div>
        </div>
      {/if}
    </div>
  </div>

  <CommentView {comments} commentCount={fullMetadata.comment_count} loading={loadingComments} />
</div>

<style>
  .video-detail {
    max-width: 1280px;
    margin: 0 auto;
    padding: 24px 0;
  }

  .back-button {
    background: #f0f0f0;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    margin-bottom: 16px;
    transition: background 0.2s;
  }

  .back-button:hover {
    background: #e0e0e0;
  }

  .player-container {
    margin-bottom: 16px;
  }

  .video-info {
    padding: 0 12px;
  }

  .title {
    font-size: 20px;
    font-weight: 500;
    line-height: 1.4;
    margin: 0 0 8px 0;
    color: #030303;
  }

  .metadata-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 0;
    border-bottom: 1px solid #e0e0e0;
    margin-bottom: 16px;
  }

  .metadata-left {
    font-size: 14px;
    color: #606060;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .separator {
    color: #909090;
  }

  .metadata-right {
    display: flex;
    gap: 16px;
  }

  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .stat-value {
    font-size: 14px;
    font-weight: 500;
    color: #030303;
  }

  .stat-label {
    font-size: 12px;
    color: #606060;
  }

  .channel-name {
    font-weight: 500;
    color: #030303;
  }

  .youtube-link {
    color: #065fd4;
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    padding: 6px 12px;
    border: 1px solid #065fd4;
    border-radius: 4px;
    transition: all 0.2s;
  }

  .youtube-link:hover {
    background: #065fd4;
    color: white;
  }

  .details-section {
    margin-top: 16px;
    padding: 16px 0;
    border-top: 1px solid #e0e0e0;
  }

  .details-toggle {
    background: none;
    border: none;
    padding: 8px 0;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: #030303;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .details-toggle:hover {
    color: #065fd4;
  }

  .details-content {
    margin-top: 12px;
    padding: 16px;
    background: #f9f9f9;
    border-radius: 8px;
    font-size: 14px;
    line-height: 1.6;
  }

  .details-meta {
    display: flex;
    flex-direction: column;
    gap: 8px;
    color: #030303;
  }

  .details-meta strong {
    font-weight: 500;
  }

  .description-text {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #e0e0e0;
  }

  .description-text p {
    margin: 8px 0 0 0;
    white-space: pre-wrap;
  }

  @media (max-width: 768px) {
    .video-detail {
      padding: 16px 0;
    }

    .back-button {
      position: sticky;
      top: 0;
      z-index: 10;
      margin-bottom: 12px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .title {
      font-size: 18px;
    }

    .metadata-row {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }

    .youtube-link {
      align-self: flex-start;
    }
  }
</style>
