<script lang="ts">
  import type { Video } from '@/types/models';

  export let video: Video;
  export let baseUrl: string = '..';

  // Get video file path
  function getVideoPath(): string {
    // Use path from videos.tsv (supports hierarchical structure like 2026/01/video_dir)
    // Fall back to video_id for older archives
    const filePath = video.file_path || video.video_id;
    // Video files are named video.mkv (git-annex symlinked to actual content)
    return `${baseUrl}/videos/${filePath}/video.mkv`;
  }

  // Get caption tracks
  $: captionTracks = video.captions_available || [];
</script>

<div class="video-player">
  <video controls crossorigin="anonymous">
    <source src={getVideoPath()} type="video/mp4" />

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
</div>

<style>
  .video-player {
    width: 100%;
    background: #000;
    border-radius: 8px;
    overflow: hidden;
  }

  video {
    width: 100%;
    height: auto;
    display: block;
    max-height: 70vh;
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
