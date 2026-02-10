<script lang="ts">
  import { onMount } from 'svelte';
  import type { Video } from '@/types/models';

  export let video: Video;
  export let channelDir: string | undefined = undefined; // Channel directory for multi-channel mode

  // Check if local video is available (metadata says downloaded)
  $: metadataHasLocalVideo = video.download_status === 'downloaded';

  // Actually available after checking file existence
  let hasLocalVideo = metadataHasLocalVideo;
  let localVideoCheckComplete = false;

  // Active tab: 'local' or 'youtube'
  let activeTab: 'local' | 'youtube' = metadataHasLocalVideo ? 'local' : 'youtube';

  // Error and loading states
  let videoError = false;
  let videoErrorMessage = '';
  let youtubeLoading = true;

  // Get video file path (absolute path from server root)
  function getVideoPath(): string {
    // Use path from videos.tsv (supports hierarchical structure like 2026/01/video_dir)
    // Fall back to video_id for older archives
    const filePath = video.file_path || video.video_id;

    // Video files are named video.mkv (git-annex symlinked to actual content)
    // Use absolute path from server root to avoid relative path issues with hash routing
    // In multi-channel mode, include channel directory prefix
    const path = channelDir
      ? `/${channelDir}/videos/${filePath}/video.mkv`
      : `/videos/${filePath}/video.mkv`;

    console.log('[VideoPlayer] Video path:', path, 'channelDir:', channelDir, 'download_status:', video.download_status);
    return path;
  }

  // Get local thumbnail path (use local file instead of YouTube CDN to avoid CORS issues)
  function getThumbnailPath(): string {
    const filePath = video.file_path || video.video_id;
    // Use absolute path from server root, include channel directory in multi-channel mode
    return channelDir
      ? `/${channelDir}/videos/${filePath}/thumbnail.jpg`
      : `/videos/${filePath}/thumbnail.jpg`;
  }

  // Get YouTube embed URL
  function getYouTubeEmbedUrl(): string {
    return `https://www.youtube.com/embed/${video.video_id}`;
  }

  // Get caption tracks
  $: captionTracks = video.captions_available || [];

  // Get caption file path for a language
  function getCaptionPath(lang: string): string {
    const filePath = video.file_path || video.video_id;
    return channelDir
      ? `/${channelDir}/videos/${filePath}/video.${lang}.vtt`
      : `/videos/${filePath}/video.${lang}.vtt`;
  }

  // Handle video loading error
  function handleVideoError(event: Event) {
    videoError = true;
    const videoEl = event.target as HTMLVideoElement;
    const error = videoEl.error;

    console.error('[VideoPlayer] Video error event:', {
      error: error ? {
        code: error.code,
        message: error.message,
      } : 'no error object',
      src: videoEl.src,
      networkState: videoEl.networkState,
      readyState: videoEl.readyState,
    });

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

  // Add debug logging for video events
  function handleVideoLoadStart() {
    console.log('[VideoPlayer] Video load started');
  }

  function handleVideoLoadedMetadata() {
    console.log('[VideoPlayer] Video metadata loaded');
  }

  function handleVideoCanPlay() {
    console.log('[VideoPlayer] Video can play');
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

  // Check if video file actually exists on mount
  onMount(async () => {
    if (metadataHasLocalVideo) {
      const videoPath = getVideoPath();
      try {
        // Use HEAD request to check file existence without downloading
        const response = await fetch(videoPath, { method: 'HEAD' });

        if (!response.ok) {
          // File doesn't exist or is not accessible
          console.warn('[VideoPlayer] Local video not available:', videoPath, 'status:', response.status);
          hasLocalVideo = false;
          activeTab = 'youtube';
          videoError = true;
          videoErrorMessage = 'Video file not found in archive. The file may not have been downloaded yet (git-annex symlink without content).';
        } else {
          console.log('[VideoPlayer] Local video available:', videoPath);
        }
      } catch (error) {
        // Network error or CORS issue
        console.warn('[VideoPlayer] Failed to check video availability:', error);
        // Assume video is available and let the video element handle errors
      }
      localVideoCheckComplete = true;
    } else {
      localVideoCheckComplete = true;
    }
  });
</script>

<div class="video-player">
  <!-- Tab Navigation (show if metadata says video is downloaded) -->
  {#if metadataHasLocalVideo}
    <div class="tabs" role="tablist">
      <button
        class="tab"
        class:active={activeTab === 'local'}
        class:warning={!hasLocalVideo}
        role="tab"
        aria-selected={activeTab === 'local'}
        aria-controls="local-player-panel"
        on:click={() => switchTab('local')}
        title={hasLocalVideo ? '' : 'Video file not available'}
      >
        Play from Archive{#if !hasLocalVideo && localVideoCheckComplete} ⚠️{/if}
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
      {#if activeTab === 'local' && metadataHasLocalVideo}
        <!-- Local Video Player -->
        {#if !hasLocalVideo || videoError}
          <div class="video-error-message">
            <p class="error-title">⚠️ {hasLocalVideo ? 'Video Playback Error' : 'Video File Not Available'}</p>
            <p class="error-details">{videoErrorMessage}</p>
            {#if !hasLocalVideo}
              <p class="error-hint">
                The video metadata indicates this file should be downloaded, but the actual file is not available.
                This usually means the git-annex symlink exists but the content hasn't been retrieved with <code>git annex get</code>.
              </p>
            {/if}
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
            poster={getThumbnailPath()}
            on:error={handleVideoError}
            on:loadstart={handleVideoLoadStart}
            on:loadedmetadata={handleVideoLoadedMetadata}
            on:canplay={handleVideoCanPlay}
          >
            <!--
              NOTE: No type attribute specified - let browser auto-detect format.
              Specifying type="video/x-matroska" causes some browsers to reject the video
              before even trying to load it (networkState: NETWORK_NO_SOURCE).
              Without the type attribute, browsers will load the file and detect format.
            -->
            <source src={getVideoPath()} />

            {#each captionTracks as lang}
              <track
                kind="subtitles"
                src={getCaptionPath(lang)}
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
                src={getThumbnailPath()}
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

  .tab.warning {
    color: #ff6b00;
  }

  .tab.warning.active {
    border-bottom-color: #ff6b00;
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

  .error-hint {
    font-size: 13px;
    color: #aaa;
    margin-bottom: 24px;
    max-width: 600px;
    line-height: 1.5;
    background: rgba(255, 255, 255, 0.05);
    padding: 12px 16px;
    border-radius: 4px;
  }

  .error-hint code {
    background: rgba(255, 255, 255, 0.1);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: monospace;
    font-size: 12px;
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
