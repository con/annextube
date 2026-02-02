<script lang="ts">
  import type { Video } from '@/types/models';

  export let video: Video;
  export let baseUrl: string = '..';

  // Active tab: 'local' or 'youtube'
  let activeTab: 'local' | 'youtube' = video.download_status === 'downloaded' ? 'local' : 'youtube';

  // Check if local video is available
  $: hasLocalVideo = video.download_status === 'downloaded';

  // Error and loading states
  let videoError = false;
  let videoErrorMessage = '';
  let youtubeLoading = true;

  // Get video file path
  function getVideoPath(): string {
    // Use path from videos.tsv (supports hierarchical structure like 2026/01/video_dir)
    // Fall back to video_id for older archives
    const filePath = video.file_path || video.video_id;
    // Video files are named video.mkv (git-annex symlinked to actual content)
    return `${baseUrl}/videos/${filePath}/video.mkv`;
  }

  // Get YouTube embed URL
  function getYouTubeEmbedUrl(): string {
    return `https://www.youtube.com/embed/${video.video_id}`;
  }

  // Get caption tracks
  $: captionTracks = video.captions_available || [];

  // Handle video loading error
  function handleVideoError(event: Event) {
    videoError = true;
    const videoEl = event.target as HTMLVideoElement;
    const error = videoEl.error;

    if (error) {
      switch (error.code) {
        case error.MEDIA_ERR_ABORTED:
          videoErrorMessage = 'Video loading was aborted. Please try again.';
          break;
        case error.MEDIA_ERR_NETWORK:
          videoErrorMessage = 'Network error while loading video. Check your connection.';
          break;
        case error.MEDIA_ERR_DECODE:
          videoErrorMessage = 'Video file is corrupted or in an unsupported format.';
          break;
        case error.MEDIA_ERR_SRC_NOT_SUPPORTED:
          videoErrorMessage = 'Video file could not be loaded. You may need to run `git annex get` to download the file, or your browser may not support MKV format.';
          break;
        default:
          videoErrorMessage = 'An unknown error occurred while loading the video.';
      }
    }
  }

  // Handle iframe load
  function handleIframeLoad() {
    youtubeLoading = false;
  }

  // Reset error state when switching tabs
  function switchTab(tab: 'local' | 'youtube') {
    activeTab = tab;
    if (tab === 'local') {
      videoError = false;
      videoErrorMessage = '';
    } else {
      youtubeLoading = true;
    }
  }
</script>

<div class="video-player">
  <!-- Tab Navigation (hide if only one tab) -->
  {#if hasLocalVideo}
    <div class="tabs" role="tablist">
      <button
        class="tab"
        class:active={activeTab === 'local'}
        role="tab"
        aria-selected={activeTab === 'local'}
        aria-controls="local-player-panel"
        on:click={() => switchTab('local')}
      >
        Play from Archive
      </button>
      <button
        class="tab"
        class:active={activeTab === 'youtube'}
        role="tab"
        aria-selected={activeTab === 'youtube'}
        aria-controls="youtube-player-panel"
        on:click={() => switchTab('youtube')}
      >
        Play from YouTube
      </button>
    </div>
  {/if}

  <!-- Tab Content -->
  <div class="tab-content-wrapper">
    <div
      class="tab-content"
      role="tabpanel"
      id={activeTab === 'local' ? 'local-player-panel' : 'youtube-player-panel'}
      aria-labelledby={activeTab === 'local' ? 'local-tab' : 'youtube-tab'}
    >
      {#if activeTab === 'local' && hasLocalVideo}
        <!-- Local Video Player -->
        {#if videoError}
          <div class="video-error-message">
            <p class="error-title">⚠️ Video Playback Error</p>
            <p class="error-details">{videoErrorMessage}</p>
            <div class="error-actions">
              <button
                class="error-button"
                on:click={() => switchTab('youtube')}
              >
                Watch on YouTube instead
              </button>
            </div>
          </div>
        {:else}
          <video
            controls
            crossorigin="anonymous"
            preload="metadata"
            on:error={handleVideoError}
          >
            <source src={getVideoPath()} type="video/x-matroska" />

            {#each captionTracks as lang}
              <track
                kind="subtitles"
                src={`${baseUrl}/videos/${video.file_path || video.video_id}/video.${lang}.vtt`}
                srclang={lang}
                label={lang.toUpperCase()}
              />
            {/each}

            <p class="video-fallback">
              Your browser doesn't support HTML5 video or the MKV format.
              <button class="fallback-button" on:click={() => switchTab('youtube')}>
                Watch on YouTube
              </button>
            </p>
          </video>
        {/if}
      {:else if activeTab === 'youtube'}
        <!-- YouTube Embed -->
        <div class="youtube-wrapper">
          {#if youtubeLoading}
            <div class="youtube-loading">
              <img
                src={video.thumbnail_url}
                alt={video.title}
                class="thumbnail-placeholder"
              />
              <div class="loading-spinner">Loading...</div>
            </div>
          {/if}
          <iframe
            src={getYouTubeEmbedUrl()}
            title={video.title}
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
            on:load={handleIframeLoad}
            style={youtubeLoading ? 'opacity: 0;' : ''}
          ></iframe>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .video-player {
    width: 100%;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e0e0e0;
  }

  .tabs {
    display: flex;
    background: #f8f9fa;
    border-bottom: 1px solid #e0e0e0;
  }

  .tab {
    flex: 1;
    padding: 12px 20px;
    background: none;
    border: none;
    font-size: 14px;
    font-weight: 500;
    color: #666;
    cursor: pointer;
    transition: all 0.2s;
    border-bottom: 2px solid transparent;
  }

  .tab:hover {
    background: #f0f0f0;
    color: #333;
  }

  .tab:focus-visible {
    outline: 2px solid #1a73e8;
    outline-offset: -2px;
  }

  .tab.active {
    color: #1a73e8;
    border-bottom-color: #1a73e8;
    background: white;
  }

  .tab-content-wrapper {
    background: #000;
    position: relative;
    width: 100%;
  }

  .tab-content {
    background: #000;
    position: relative;
    width: 100%;
    padding-bottom: 56.25%; /* 16:9 aspect ratio */
  }

  video,
  iframe {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: block;
    border: none;
  }

  .youtube-wrapper {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
  }

  .youtube-loading {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #000;
  }

  .thumbnail-placeholder {
    position: absolute;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0.5;
  }

  .loading-spinner {
    position: relative;
    color: white;
    font-size: 16px;
    background: rgba(0, 0, 0, 0.7);
    padding: 12px 24px;
    border-radius: 4px;
    z-index: 1;
  }

  .video-error-message {
    background: #1a1a1a;
    color: #fff;
    padding: 40px 20px;
    text-align: center;
    min-height: 300px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }

  .error-title {
    font-size: 20px;
    font-weight: 600;
    margin-bottom: 12px;
    color: #ff6b6b;
  }

  .error-details {
    font-size: 14px;
    color: #ccc;
    margin-bottom: 24px;
    max-width: 500px;
    line-height: 1.6;
  }

  .error-actions {
    display: flex;
    gap: 12px;
  }

  .error-button,
  .fallback-button {
    background: #1a73e8;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
  }

  .error-button:hover,
  .fallback-button:hover {
    background: #1557b0;
  }

  .video-fallback {
    color: #ccc;
    padding: 40px 20px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }

  @media (max-width: 768px) {
    .tab {
      padding: 10px 12px;
      font-size: 13px;
    }

    .error-title {
      font-size: 18px;
    }

    .error-details {
      font-size: 13px;
    }
  }
</style>
