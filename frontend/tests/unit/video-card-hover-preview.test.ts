/**
 * VideoCard hover-to-preview unit tests (issue #11: auto-play a snippet on
 * hover). Per the issue discussion, the intended behavior is to play the
 * real local video file, muted and inline, within the thumbnail area on
 * hover -- and revert to the static thumbnail on mouseleave. No snippet
 * extraction/caching pipeline.
 *
 * @ai_generated
 */

import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
import VideoCard, { HOVER_DELAY_MS, PREVIEW_START_TIMEOUT_MS } from '../../src/components/VideoCard.svelte';
import { clearAvailabilityCache } from '../../src/services/availability';
import type { Video } from '../../src/types/models';

function makeVideo(overrides: Partial<Video> = {}): Video {
  return {
    video_id: 'abc123',
    title: 'Test Video',
    channel_id: 'chan1',
    channel_name: 'Test Channel',
    published_at: '2024-01-01T00:00:00Z',
    duration: 120,
    view_count: 0,
    like_count: 0,
    comment_count: 0,
    thumbnail_url: 'https://example.com/thumb.jpg',
    license: 'standard',
    privacy_status: 'public',
    availability: 'public',
    tags: [],
    categories: [],
    captions_available: [],
    has_auto_captions: false,
    file_path: 'abc123',
    download_status: 'downloaded',
    source_url: 'https://www.youtube.com/watch?v=abc123',
    fetched_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

/** Wait past the hover delay, i.e. long enough for a preview to start. */
function afterHoverDelay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, HOVER_DELAY_MS + 50));
}

/** Hover a card and wait for its preview element to be mounted. */
async function hover(container: HTMLElement): Promise<HTMLVideoElement> {
  await fireEvent.mouseEnter(container.querySelector('.thumbnail-container') as HTMLElement);
  await waitFor(() => {
    expect(container.querySelector('.preview-video')).not.toBeNull();
  });
  return container.querySelector('.preview-video') as HTMLVideoElement;
}

describe('VideoCard hover preview', () => {
  let playSpy: ReturnType<typeof vi.fn>;
  let pauseSpy: ReturnType<typeof vi.fn>;
  let loadSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    clearAvailabilityCache();

    // Local video is available via a HEAD request.
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true } as Response);

    // jsdom doesn't implement HTMLMediaElement playback; stub it.
    playSpy = vi.fn().mockResolvedValue(undefined);
    pauseSpy = vi.fn();
    loadSpy = vi.fn();
    HTMLMediaElement.prototype.play = playSpy;
    HTMLMediaElement.prototype.pause = pauseSpy;
    HTMLMediaElement.prototype.load = loadSpy;
  });

  test('does not render a preview video before hovering', () => {
    const { container } = render(VideoCard, { props: { video: makeVideo() } });
    expect(container.querySelector('.preview-video')).toBeNull();
  });

  test('plays the video inline within the thumbnail on hover', async () => {
    const { container } = render(VideoCard, { props: { video: makeVideo() } });

    const previewVideo = await hover(container);
    // Muted is mandatory so autoplay isn't blocked and isn't intrusive.
    expect(previewVideo.muted).toBe(true);

    previewVideo.dispatchEvent(new Event('canplay'));
    expect(playSpy).toHaveBeenCalledTimes(1);
  });

  test('reverts to the static thumbnail and stops playback on mouseleave', async () => {
    const { container } = render(VideoCard, { props: { video: makeVideo() } });

    const thumbnail = container.querySelector('.thumbnail-container') as HTMLElement;
    const previewVideo = await hover(container);
    previewVideo.dispatchEvent(new Event('canplay'));

    await fireEvent.mouseLeave(thumbnail);

    expect(pauseSpy).toHaveBeenCalled();
    await waitFor(() => {
      expect(container.querySelector('.preview-video')).toBeNull();
    });
    // Static thumbnail image is back.
    expect(container.querySelector('img.thumbnail')).not.toBeNull();
  });

  test('does not show a preview for videos without a local copy', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false } as Response);

    const { container } = render(VideoCard, {
      props: { video: makeVideo({ video_id: 'noLocal', file_path: 'noLocal', download_status: 'metadata_only' }) },
    });

    const thumbnail = container.querySelector('.thumbnail-container') as HTMLElement;
    await fireEvent.mouseEnter(thumbnail);
    await afterHoverDelay();

    // No fetch/probe should even happen for a video known not to be local.
    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(container.querySelector('.preview-video')).toBeNull();
  });

  test('ignores a slow availability check that resolves after the pointer already left', async () => {
    let resolveFetch: (value: Response) => void = () => {};
    globalThis.fetch = vi.fn().mockImplementation(
      () => new Promise((resolve) => { resolveFetch = resolve; })
    );

    const { container } = render(VideoCard, { props: { video: makeVideo() } });
    const thumbnail = container.querySelector('.thumbnail-container') as HTMLElement;

    await fireEvent.mouseEnter(thumbnail);
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    });
    await fireEvent.mouseLeave(thumbnail);

    // The HEAD request finally resolves after the mouse already left.
    resolveFetch({ ok: true } as Response);
    await Promise.resolve();
    await Promise.resolve();

    expect(container.querySelector('.preview-video')).toBeNull();
  });

  test('does not leak a playing video when the card unmounts while hovered', async () => {
    const { container, unmount } = render(VideoCard, { props: { video: makeVideo() } });

    const previewVideo = await hover(container);
    previewVideo.dispatchEvent(new Event('canplay'));

    unmount();

    expect(pauseSpy).toHaveBeenCalled();
  });

  test('aborts the download when the file fails to load, not just the element', async () => {
    // Unmounting the <video> is not enough: a detached element with its src
    // still set goes on streaming the file nobody can see.
    const { container } = render(VideoCard, { props: { video: makeVideo() } });

    const previewVideo = await hover(container);
    await fireEvent(previewVideo, new Event('error'));

    expect(previewVideo.getAttribute('src')).toBeNull();
    expect(loadSpy).toHaveBeenCalled();
  });

  test('gives up on a preview that never starts playing', async () => {
    // Otherwise an autoplay-blocked or stalled preview stays invisible --
    // and goes on downloading the whole file from behind the thumbnail.
    playSpy.mockRejectedValue(new DOMException('blocked', 'NotAllowedError'));

    const { container } = render(VideoCard, { props: { video: makeVideo() } });
    const previewVideo = await hover(container);

    previewVideo.dispatchEvent(new Event('canplay'));
    await waitFor(() => {
      expect(container.querySelector('.preview-video')).toBeNull();
    });
    expect(previewVideo.getAttribute('src')).toBeNull();
    expect(container.querySelector('img.thumbnail')).not.toBeNull();
  });

  test('gives up on a preview that never even reaches canplay', async () => {
    vi.useFakeTimers();
    try {
      const { container } = render(VideoCard, { props: { video: makeVideo() } });
      await fireEvent.mouseEnter(container.querySelector('.thumbnail-container') as HTMLElement);
      await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS);
      const previewVideo = container.querySelector('.preview-video') as HTMLVideoElement;
      expect(previewVideo).not.toBeNull();

      // No canplay, no timeupdate -- the file never starts.
      await vi.advanceTimersByTimeAsync(PREVIEW_START_TIMEOUT_MS);

      expect(container.querySelector('.preview-video')).toBeNull();
      expect(previewVideo.getAttribute('src')).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  test('a probe from an abandoned hover does not skip the next hover delay', async () => {
    let resolveFetch: (value: Response) => void = () => {};
    globalThis.fetch = vi.fn().mockImplementation(
      () => new Promise((resolve) => { resolveFetch = resolve; })
    );

    const { container } = render(VideoCard, { props: { video: makeVideo() } });
    const thumbnail = container.querySelector('.thumbnail-container') as HTMLElement;

    await fireEvent.mouseEnter(thumbnail);
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    });
    await fireEvent.mouseLeave(thumbnail);
    await fireEvent.mouseEnter(thumbnail);

    // The first hover's probe lands during the second hover's delay: it must
    // not mount a preview the new hover has not waited for yet.
    resolveFetch({ ok: true } as Response);
    await Promise.resolve();
    await Promise.resolve();

    expect(container.querySelector('.preview-video')).toBeNull();
  });

  test('falls back to the thumbnail and drops the stale cache entry when the file fails to load', async () => {
    // The availability check said the file was there (e.g. a stale cache
    // entry from before the content was dropped from the annex), but
    // actually loading it fails.
    const { container } = render(VideoCard, { props: { video: makeVideo() } });
    const thumbnail = container.querySelector('.thumbnail-container') as HTMLElement;

    const previewVideo = await hover(container);
    previewVideo.dispatchEvent(new Event('error'));

    // No permanently-broken black overlay: the preview is torn down and the
    // static thumbnail is shown again, even though the mouse never left.
    await waitFor(() => {
      expect(container.querySelector('.preview-video')).toBeNull();
    });
    expect(container.querySelector('img.thumbnail')).not.toBeNull();

    // The stale cache entry must not be trusted again: re-hovering issues a
    // fresh HEAD check instead of reusing the (wrong) cached "available".
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    await fireEvent.mouseLeave(thumbnail);
    await fireEvent.mouseEnter(thumbnail);
    await afterHoverDelay();
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });

  test('keeps the thumbnail visible until the preview actually renders frames', async () => {
    // Regression: the overlay used to be opaque from the moment it was
    // created, so a preview that was slow to load (or never loaded) showed
    // as a black rectangle covering the thumbnail.
    const { container } = render(VideoCard, { props: { video: makeVideo() } });

    const previewVideo = await hover(container);
    expect(previewVideo.classList.contains('playing')).toBe(false);

    // Even "can play" isn't enough -- frames have to be flowing.
    previewVideo.dispatchEvent(new Event('canplay'));
    expect(previewVideo.classList.contains('playing')).toBe(false);

    Object.defineProperty(previewVideo, 'currentTime', { value: 0.4, configurable: true });
    await fireEvent(previewVideo, new Event('timeupdate'));
    expect(previewVideo.classList.contains('playing')).toBe(true);
  });

  test('does not load anything for a card the pointer merely sweeps across', async () => {
    // Regression: hovering was enough to start fetching the real (often
    // multi-hundred-MB) file, so dragging the pointer over a grid queued up
    // a download per card and starved the ones actually being looked at.
    const { container } = render(VideoCard, { props: { video: makeVideo() } });
    const thumbnail = container.querySelector('.thumbnail-container') as HTMLElement;

    await fireEvent.mouseEnter(thumbnail);
    await fireEvent.mouseLeave(thumbnail);
    await afterHoverDelay();

    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(container.querySelector('.preview-video')).toBeNull();
  });

  test('re-hovering a card still waits out the hover delay', async () => {
    const { container } = render(VideoCard, { props: { video: makeVideo() } });
    const thumbnail = container.querySelector('.thumbnail-container') as HTMLElement;

    await hover(container);
    await fireEvent.mouseLeave(thumbnail);

    // The availability result is cached now, but a card that was previewed
    // once must not re-mount its preview instantly on the next sweep past.
    await fireEvent.mouseEnter(thumbnail);
    expect(container.querySelector('.preview-video')).toBeNull();
    await fireEvent.mouseLeave(thumbnail);
    await afterHoverDelay();
    expect(container.querySelector('.preview-video')).toBeNull();
  });

  test('aborts the in-flight download when the pointer leaves', async () => {
    // Removing the element is not enough: until the source is dropped the
    // browser keeps pulling the rest of the file for a card nobody is
    // looking at any more.
    const { container } = render(VideoCard, { props: { video: makeVideo() } });
    const thumbnail = container.querySelector('.thumbnail-container') as HTMLElement;

    const previewVideo = await hover(container);
    expect(previewVideo.getAttribute('src')).not.toBeNull();

    await fireEvent.mouseLeave(thumbnail);

    expect(previewVideo.getAttribute('src')).toBeNull();
    expect(loadSpy).toHaveBeenCalled();
  });
});
