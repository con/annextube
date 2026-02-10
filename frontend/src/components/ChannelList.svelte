<script lang="ts">
  import type { Channel } from '@/types/models';

  export let channels: Channel[] = [];
  export let loading = false;
  export let error: string | null = null;
  export let onChannelClick: (channel: Channel) => void = () => {};

  function formatNumber(num: number): string {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  }

  function formatDuration(seconds: number): string {
    if (seconds === 0) return '0s';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    if (minutes > 0) {
      return `${minutes}m`;
    }
    return `${seconds}s`;
  }

  function formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));
    const size = bytes / Math.pow(1024, index);
    return `${size.toFixed(1)} ${units[index]}`;
  }

  function formatDate(dateString: string | undefined): string {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return dateString;
    }
  }
</script>

<div class="channel-list">
  {#if loading}
    <div class="loading">Loading channels...</div>
  {:else if error}
    <div class="error">
      <p>❌ Error loading channels</p>
      <p class="error-message">{error}</p>
    </div>
  {:else if channels.length === 0}
    <div class="empty">
      <p>📁 No channels found</p>
      <p class="empty-hint">Add channel archives to this collection</p>
    </div>
  {:else}
    <div class="channels-grid">
      {#each channels as channel (channel.channel_id)}
        <div
          class="channel-card"
          on:click={() => onChannelClick(channel)}
          on:keydown={(e) => e.key === 'Enter' && onChannelClick(channel)}
          tabindex="0"
          role="button"
          title={channel.description || channel.name}
        >
          <div class="channel-header">
            {#if channel.avatar_url}
              <img
                src={channel.avatar_url}
                alt="{channel.name} avatar"
                class="channel-avatar"
                onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
              />
              <div class="channel-icon-fallback" style="display: none;">📺</div>
            {:else}
              <div class="channel-icon">📺</div>
            {/if}
            <div class="channel-info">
              <h3 class="channel-name">{channel.name || channel.channel_id}</h3>
              {#if channel.custom_url}
                <p class="channel-url">@{channel.custom_url}</p>
              {/if}
            </div>
          </div>

          {#if channel.description}
            <p class="channel-description">{channel.description}</p>
          {/if}

          <div class="channel-stats">
            {#if channel.archive_stats}
              <div class="stat">
                <span class="stat-value">
                  {formatNumber(channel.archive_stats.total_videos_archived)}
                </span>
                <span class="stat-label">videos</span>
              </div>

              {#if channel.archive_stats.total_duration_seconds > 0}
                <div class="stat">
                  <span class="stat-value">
                    {formatDuration(channel.archive_stats.total_duration_seconds)}
                  </span>
                  <span class="stat-label">duration</span>
                </div>
              {/if}

              {#if channel.archive_stats.total_size_bytes > 0}
                <div class="stat">
                  <span class="stat-value">
                    {formatSize(channel.archive_stats.total_size_bytes)}
                  </span>
                  <span class="stat-label">size</span>
                </div>
              {/if}
            {/if}

            {#if channel.subscriber_count > 0}
              <div class="stat">
                <span class="stat-value">
                  {formatNumber(channel.subscriber_count)}
                </span>
                <span class="stat-label">subscribers</span>
              </div>
            {/if}
          </div>

          {#if channel.archive_stats?.first_video_date || channel.archive_stats?.last_video_date}
            <div class="channel-date-range">
              {formatDate(channel.archive_stats.first_video_date)} — {formatDate(channel.archive_stats.last_video_date)}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .channel-list {
    padding: 24px 0;
  }

  .loading,
  .error,
  .empty {
    text-align: center;
    padding: 60px 20px;
    color: #606060;
  }

  .error {
    color: #d32f2f;
  }

  .error-message {
    font-size: 14px;
    margin-top: 8px;
    font-family: monospace;
    background: #ffebee;
    padding: 12px;
    border-radius: 4px;
    display: inline-block;
  }

  .empty-hint {
    font-size: 14px;
    margin-top: 8px;
    color: #909090;
  }

  .channels-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 20px;
  }

  .channel-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 20px;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .channel-card:hover {
    border-color: #065fd4;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  .channel-card:focus {
    outline: 2px solid #065fd4;
    outline-offset: 2px;
  }

  .channel-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }

  .channel-avatar {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
  }

  .channel-icon,
  .channel-icon-fallback {
    font-size: 48px;
    width: 64px;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .channel-info {
    flex: 1;
    min-width: 0;
  }

  .channel-name {
    margin: 0 0 4px 0;
    font-size: 18px;
    font-weight: 500;
    color: #030303;
  }

  .channel-url {
    margin: 0 0 8px 0;
    font-size: 14px;
    color: #606060;
  }

  .channel-description {
    margin: 0;
    font-size: 14px;
    color: #606060;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .channel-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
    gap: 16px;
    padding-top: 16px;
    border-top: 1px solid #f0f0f0;
  }

  .stat {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .stat-value {
    font-size: 16px;
    font-weight: 500;
    color: #030303;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .stat-label {
    font-size: 11px;
    color: #606060;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .channel-date-range {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #f0f0f0;
    font-size: 12px;
    color: #606060;
    text-align: center;
  }

  @media (max-width: 768px) {
    .channels-grid {
      grid-template-columns: 1fr;
    }

    .channel-card {
      padding: 16px;
    }

    .channel-stats {
      gap: 16px;
    }
  }
</style>
