<script lang="ts">
  import type { Video } from '@/types/models';

  export let video: Video;
  export let baseUrl: string = '..';

  // Get video file path (look for common video formats)
  // In a real archive, this would be in the video's directory
  function getVideoPath(videoId: string): string {
    // Try common formats - the actual file will be git-annex symlinked
    return `${baseUrl}/videos/${videoId}/${videoId}.mp4`;
  }

  // Get caption tracks
  $: captionTracks = video.captions_available || [];
</script>

<div class="video-player">
  <video controls crossorigin="anonymous">
    <source src={getVideoPath(video.video_id)} type="video/mp4" />

    {#each captionTracks as lang}
      <track
        kind="subtitles"
        src={`${baseUrl}/videos/${video.video_id}/caption_${lang}.vtt`}
        srclang={lang}
        label={lang.toUpperCase()}
      />
    {/each}

    <p class="video-error">
      Your browser doesn't support HTML5 video.
      <a href={getVideoPath(video.video_id)} download>Download the video</a> instead.
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
