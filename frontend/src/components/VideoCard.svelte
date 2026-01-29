<script lang="ts">
  import type { Video } from '@/types/models';
  import { formatDuration, formatViews, formatRelativeTime, formatCommentCount } from '@/utils/format';

  export let video: Video;
  export let onClick: (video: Video) => void = () => {};
</script>

<div class="video-card" on:click={() => onClick(video)} on:keypress={(e) => e.key === 'Enter' && onClick(video)} role="button" tabindex="0">
  <div class="thumbnail-container">
    <img src={video.thumbnail_url} alt={video.title} class="thumbnail" loading="lazy" />
    <div class="duration">{formatDuration(video.duration)}</div>
  </div>

  <div class="info">
    <h3 class="title">{video.title}</h3>
    <div class="channel">{video.channel_name}</div>
    <div class="metadata">
      <span class="views">{formatViews(video.view_count)}</span>
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
  }
</style>
