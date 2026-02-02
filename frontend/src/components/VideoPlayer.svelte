<script lang="ts">
  import type { Video } from '@/types/models';

  export let video: Video;
  export let baseUrl: string = '..';

  // Active tab: 'local' or 'youtube'
  let activeTab: 'local' | 'youtube' = video.download_status === 'downloaded' ? 'local' : 'youtube';

  // Check if local video is available
  $: hasLocalVideo = video.download_status === 'downloaded';

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
</script>

<div class="video-player">
  <!-- Tab Navigation -->
  <div class="tabs">
    {#if hasLocalVideo}
      <button
        class="tab"
        class:active={activeTab === 'local'}
        on:click={() => (activeTab = 'local')}
      >
        Local Player
      </button>
    {/if}
    <button
      class="tab"
      class:active={activeTab === 'youtube'}
      on:click={() => (activeTab = 'youtube')}
    >
      Watch on YouTube
    </button>
  </div>

  <!-- Tab Content -->
  <div class="tab-content">
    {#if activeTab === 'local' && hasLocalVideo}
      <!-- Local Video Player -->
      <video controls crossorigin="anonymous" preload="metadata">
        <source src={getVideoPath()} />

        {#each captionTracks as lang}
          <track
            kind="subtitles"
            src={`${baseUrl}/videos/${video.file_path || video.video_id}/video.${lang}.vtt`}
            srclang={lang}
            label={lang.toUpperCase()}
          />
        {/each}

        <p class="video-error">
          Your browser doesn't support HTML5 video.
          <a href={getVideoPath()} download>Download the video</a> instead.
        </p>
      </video>
    {:else if activeTab === 'youtube'}
      <!-- YouTube Embed -->
      <iframe
        src={getYouTubeEmbedUrl()}
        title={video.title}
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
      ></iframe>
    {/if}
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

  .tab.active {
    color: #1a73e8;
    border-bottom-color: #1a73e8;
    background: white;
  }

  .tab-content {
    background: #000;
  }

  video,
  iframe {
    width: 100%;
    height: auto;
    display: block;
    max-height: 70vh;
    aspect-ratio: 16 / 9;
  }

  .video-error {
    color: #ccc;
    padding: 20px;
    text-align: center;
  }

  .video-error a {
    color: #3ea6ff;
    text-decoration: none;
  }

  .video-error a:hover {
    text-decoration: underline;
  }
</style>
