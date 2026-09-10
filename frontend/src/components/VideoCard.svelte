<script context="module" lang="ts">
  /**
   * How long the pointer has to rest on a card before its video starts
   * loading. Sweeping across a grid must not kick off a download per card:
   * these are the real, often multi-hundred-MB, archived files.
   */
  export const HOVER_DELAY_MS = 200;

  /**
   * How long one attempt at a preview may take to start playing before it
   * is abandoned. A preview that never plays is never revealed (the
   * thumbnail stays put), so without this it would go on quietly
   * downloading the whole file from behind the thumbnail.
   */
  export const PREVIEW_START_TIMEOUT_MS = 4000;

  /**
   * How far into a video a preview starts.
   *
   * Recordings routinely open on black or a title card, so previewing from
   * the very beginning shows a black rectangle even when everything is
   * working. Starting a little way in is more representative.
   */
  export const PREVIEW_START_SECONDS = 30;

  /**
   * Videos shorter than this are previewed from the start instead: seeking
   * 30s into a 40s clip lands in its tail (and into a 20s one, past the
   * end). Derived from the offset so the two cannot drift apart.
   */
  export const PREVIEW_SEEK_MIN_DURATION_S = PREVIEW_START_SECONDS * 3;
</script>

<script lang="ts">
  import { onDestroy } from 'svelte';
  import type { Video } from '@/types/models';
  import { formatDuration, formatViews, formatRelativeTime, formatCommentCount } from '@/utils/format';
  import { checkVideoAvailability, clearAvailabilityCache } from '@/services/availability';
  import { dataLoader } from '@/services/data-loader';

  export let video: Video;
  export let onClick: (video: Video) => void = () => {};
  export let channelDir: string | undefined = undefined; // Channel directory for multi-channel mode

  let thumbnailError = false;

  // Hover-to-preview (issue #11): play the actual video, muted, inline,
  // within the thumbnail area, reverting to the static image on
  // mouseleave. No snippet extraction/caching -- just the real file.
  // Whether the <video> overlay is mounted at all. Only ever set by
  // startPreview(), so re-hovering an already-probed card still waits out
  // the hover delay rather than re-mounting instantly.
  let previewActive = false;
  // Whether the preview is actually rendering frames. Until it is, the
  // <video> stays transparent so the thumbnail underneath remains visible.
  let previewPlaying = false;
  let previewVideoElement: HTMLVideoElement | null = null;
  let hoverTimer: ReturnType<typeof setTimeout> | null = null;
  let startTimer: ReturnType<typeof setTimeout> | null = null;
  // Bumped on every enter and leave, so an async availability probe can
  // tell whether the hover it belongs to is still the current one.
  let hoverGeneration = 0;
  // Set after a seeked preview fails to play: not every Matroska file has
  // the cues needed to seek, and a preview from the start beats none.
  let previewFromStart = false;

  $: previewUrl = dataLoader.getVideoFileUrl(video, channelDir);
  $: previewOffset =
    !previewFromStart && video.duration > PREVIEW_SEEK_MIN_DURATION_S ? PREVIEW_START_SECONDS : 0;
  // Media fragment, so the browser seeks on load rather than after it.
  $: previewSrc = previewOffset > 0 ? `${previewUrl}#t=${previewOffset}` : previewUrl;

  function handleThumbnailError() {
    thumbnailError = true;
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick(video);
    }
  }

  function handleMouseEnter() {
    hoverGeneration++;
    clearTimers();
    hoverTimer = setTimeout(startPreview, HOVER_DELAY_MS);
  }

  function handleMouseLeave() {
    stopPreview();
  }

  async function startPreview() {
    hoverTimer = null;
    // Only bother probing when the archive actually has a local copy;
    // checkVideoAvailability caches the HEAD request so re-hovering is free.
    if (video.download_status !== 'downloaded' && video.download_status !== 'tracked') {
      return;
    }

    const generation = hoverGeneration;
    const url = previewUrl;
    const available = await checkVideoAvailability(url);
    // The probe is async: this hover may be over by the time it lands, or a
    // later hover may have started -- and that one has its own delay to sit
    // out rather than inheriting this result.
    if (generation !== hoverGeneration || url !== previewUrl) return;

    previewActive = available;
    if (available) startTimer = setTimeout(giveUpOnPreview, PREVIEW_START_TIMEOUT_MS);
  }

  function giveUpOnPreview() {
    startTimer = null;
    if (previewPlaying) return;
    // Never played, so it was never shown. Retry without the seek if that
    // is what failed; otherwise drop it rather than leave it downloading
    // invisibly behind the thumbnail.
    if (previewOffset > 0) retryFromStart();
    else stopPreview();
  }

  function retryFromStart() {
    // previewSrc is reactive, so dropping the offset re-points the existing
    // element -- which aborts the seeked load along the way.
    previewFromStart = true;
    previewPlaying = false;
    startTimer = setTimeout(giveUpOnPreview, PREVIEW_START_TIMEOUT_MS);
  }

  function stopPreview() {
    hoverGeneration++;
    previewActive = false;
    previewPlaying = false;
    previewFromStart = false;
    clearTimers();
    teardownPreviewElement();
  }

  function clearTimers() {
    if (hoverTimer !== null) {
      clearTimeout(hoverTimer);
      hoverTimer = null;
    }
    if (startTimer !== null) {
      clearTimeout(startTimer);
      startTimer = null;
    }
  }

  function teardownPreviewElement() {
    const element = previewVideoElement;
    if (!element) return;
    previewVideoElement = null;
    // Pause explicitly rather than relying on the {#if} removing the
    // element -- a detached but still-referenced <video> can keep playing.
    element.pause();
    // Dropping the source and re-running resource selection aborts the
    // in-flight range request right away. Without it the browser happily
    // keeps pulling (and the server keeps streaming) the rest of a large
    // file for a card the pointer has already left.
    element.removeAttribute('src');
    element.load();
  }

  function handlePreviewCanPlay() {
    previewVideoElement?.play().catch(() => {
      // Autoplay refused (e.g. a browser-level media block). It would stay
      // invisible and keep downloading, so give it up; the static
      // thumbnail underneath is the fallback.
      stopPreview();
    });
  }

  function handlePreviewTimeUpdate() {
    // Reveal the preview only once frames are actually coming through.
    // Showing the <video> as soon as it is created paints an opaque black
    // rectangle over the thumbnail for as long as the file takes to start
    // playing -- which is forever if it never does. Compare against the
    // seek target, not zero: a seeked element reports the offset as its
    // position before it has played anything.
    if (previewVideoElement && previewVideoElement.currentTime > previewOffset) {
      previewPlaying = true;
    }
  }

  function handlePreviewError(event: Event) {
    // An error from an element we already tore down is ours, not the
    // file's -- only the live preview's failure says anything about it.
    if (!previewVideoElement || event.currentTarget !== previewVideoElement) return;
    // A seeked load can fail on the seek rather than on the file itself.
    if (previewOffset > 0) {
      clearTimers();
      retryFromStart();
      return;
    }
    // The availability cache said this file was there, but loading it
    // failed anyway (e.g. content dropped from the annex mid-session).
    // Fall back to the static thumbnail and stop trusting the stale cache
    // entry so the next hover re-checks for real, instead of leaving an
    // opaque, permanently-broken overlay over the thumbnail.
    clearAvailabilityCache(previewUrl);
    stopPreview();
  }

  // Belt-and-braces: if the card is torn down (e.g. list re-render while
  // the pointer is still over it) without a mouseleave ever firing.
  onDestroy(stopPreview);
</script>

<div
  class="video-card"
  on:click={() => onClick(video)}
  on:keydown={handleKeyDown}
  role="button"
  tabindex="0"
>
  <div
    class="thumbnail-container"
    on:mouseenter={handleMouseEnter}
    on:mouseleave={handleMouseLeave}
  >
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

    {#if previewActive}
      <!-- Decorative hover preview -- the accessible experience is the
           thumbnail img (with its alt text) plus the card's click/Enter
           handling; this overlay adds nothing for keyboard/AT users. -->
      <!-- svelte-ignore a11y-media-has-caption -->
      <video
        bind:this={previewVideoElement}
        class="preview-video"
        class:playing={previewPlaying}
        src={previewSrc}
        muted
        loop
        playsinline
        preload="auto"
        tabindex="-1"
        aria-hidden="true"
        on:canplay={handlePreviewCanPlay}
        on:timeupdate={handlePreviewTimeUpdate}
        on:error={handlePreviewError}
      ></video>
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

  .preview-video {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    background: #000;
    pointer-events: none;
    /* Transparent until the first frames render, so a preview that is slow
       to load -- or never loads -- leaves the thumbnail on screen instead
       of covering it with a black rectangle. */
    opacity: 0;
    transition: opacity 0.15s ease-in;
  }

  .preview-video.playing {
    opacity: 1;
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
