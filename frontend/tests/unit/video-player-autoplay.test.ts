/**
 * VideoPlayer autoplay unit tests (issue #14: video should play as soon as
 * the page is entered, without an explicit click — with or without a
 * starting time point).
 *
 * @ai_generated
 */

import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import VideoPlayer from '../../src/components/VideoPlayer.svelte';
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

describe('VideoPlayer autoplay', () => {
  let playSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // The local video is treated as available via a HEAD request.
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true } as Response);

    // jsdom doesn't implement HTMLMediaElement.play(); stub it so we can
    // assert it was (or wasn't) called.
    playSpy = vi.fn().mockResolvedValue(undefined);
    HTMLMediaElement.prototype.play = playSpy;
    HTMLMediaElement.prototype.pause = vi.fn();
  });

  test('auto-plays the local video on canplay even without a start time', async () => {
    const { container } = render(VideoPlayer, {
      props: {
        video: makeVideo(),
        initialAutoplay: true,
      },
    });

    await waitFor(() => {
      expect(container.querySelector('video')).not.toBeNull();
    });

    const videoEl = container.querySelector('video') as HTMLVideoElement;
    videoEl.dispatchEvent(new Event('canplay'));

    expect(playSpy).toHaveBeenCalledTimes(1);
  });

  test('auto-plays the local video on canplay when a start time is given', async () => {
    const { container } = render(VideoPlayer, {
      props: {
        video: makeVideo(),
        initialAutoplay: true,
        initialTime: 9,
      },
    });

    await waitFor(() => {
      expect(container.querySelector('video')).not.toBeNull();
    });

    const videoEl = container.querySelector('video') as HTMLVideoElement;
    videoEl.dispatchEvent(new Event('canplay'));

    expect(playSpy).toHaveBeenCalledTimes(1);
  });

  test('does not auto-play when initialAutoplay is false', async () => {
    const { container } = render(VideoPlayer, {
      props: {
        video: makeVideo(),
        initialAutoplay: false,
      },
    });

    await waitFor(() => {
      expect(container.querySelector('video')).not.toBeNull();
    });

    const videoEl = container.querySelector('video') as HTMLVideoElement;
    videoEl.dispatchEvent(new Event('canplay'));

    expect(playSpy).not.toHaveBeenCalled();
  });

  test('sets autoplay=1 on the YouTube embed URL when initialAutoplay is true', async () => {
    // Simulate no local file available, so the player falls back to YouTube.
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false } as Response);

    const { container } = render(VideoPlayer, {
      props: {
        // Distinct video_id so the availability cache from earlier tests
        // (keyed by file path) doesn't leak into this one.
        video: makeVideo({ video_id: 'noLocal1', file_path: 'noLocal1', download_status: 'metadata_only' }),
        initialAutoplay: true,
      },
    });

    await waitFor(() => {
      expect(container.querySelector('iframe')).not.toBeNull();
    });

    const iframe = container.querySelector('iframe') as HTMLIFrameElement;
    expect(iframe.src).toContain('autoplay=1');
  });
});
