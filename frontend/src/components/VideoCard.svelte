<script lang="ts">
  import type { Video } from '@/types/models';
  import { formatDuration, formatViews, formatRelativeTime, formatCommentCount } from '@/utils/format';

  export let video: Video;
  export let onClick: (video: Video) => void = () => {};

  let thumbnailError = false;

  function handleThumbnailError() {
    thumbnailError = true;
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick(video);
    }
  }
</script>

<div
  class="video-card"
  on:click={() => onClick(video)}
  on:keydown={handleKeyDown}
  role="button"
  tabindex="0"
>
  <div class="thumbnail-container">
    {#if thumbnailError}
      <div class="thumbnail-placeholder">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        <span class="placeholder-text">No thumbnail</span>
      </div>
    {:else}
      <img
        src={video.thumbnail_url}
        alt={video.title}
        class="thumbnail"
        loading="lazy"
        on:error={handleThumbnailError}
      />
    {/if}

    <!-- Download status badge -->
    {#if video.download_status === 'downloaded'}
      <div class="status-badge downloaded" title="Video available locally">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
      </div>
    {:else if video.download_status === 'metadata_only'}
      <div class="status-badge metadata-only" title="Metadata only (no video file)">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
          <polyline points="15 3 21 3 21 9"></polyline>
          <line x1="10" y1="14" x2="21" y2="3"></line>
        </svg>
      </div>
    {/if}

    <div class="duration">{formatDuration(video.duration)}</div>
  </div>

  <div class="info">
    <h3 class="title">{video.title}</h3>
    <div class="channel">{video.channel_name}</div>
    <div class="metadata">
      <span class="views" title="View count from YouTube">{formatViews(video.view_count)}</span>
      {#if video.comment_count > 0}
        <span class="separator">•</span>
        <span class="comments">{formatCommentCount(video.comment_count)}</span>
      {/if}
      <span class="separator">•</span>
      <span class="date">{formatRelativeTime(video.published_at)}</span>
    </div>
  </div>
</div>

<style>
  .video-card {
    cursor: pointer;
    border-radius: 8px;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    background: white;
  }

  .video-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .video-card:focus {
    outline: 2px solid #065fd4;
    outline-offset: 2px;
  }

  .thumbnail-container {
    position: relative;
    aspect-ratio: 16 / 9;
    background: #f0f0f0;
  }

  .thumbnail {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .thumbnail-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #e0e0e0;
    color: #909090;
  }

  .placeholder-text {
    margin-top: 8px;
    font-size: 13px;
  }

  .status-badge {
    position: absolute;
    top: 8px;
    left: 8px;
    padding: 4px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(4px);
  }

  .status-badge.downloaded {
    background: rgba(46, 125, 50, 0.9);
    color: white;
  }

  .status-badge.metadata-only {
    background: rgba(97, 97, 97, 0.9);
    color: white;
  }

  .duration {
    position: absolute;
    bottom: 8px;
    right: 8px;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
  }

  .info {
    padding: 12px;
  }

  .title {
    margin: 0 0 8px 0;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.4;
    color: #030303;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .channel {
    font-size: 13px;
    color: #606060;
    margin-bottom: 4px;
  }

  .metadata {
    font-size: 13px;
    color: #606060;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .separator {
    font-size: 10px;
  }

  @media (max-width: 768px) {
    .title {
      font-size: 13px;
    }

    .channel,
    .metadata {
      font-size: 12px;
    }

    .status-badge {
      top: 6px;
      left: 6px;
      padding: 3px;
    }

    .status-badge svg {
      width: 14px;
      height: 14px;
    }
  }
</style>
