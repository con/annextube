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
import VideoCard from '../../src/components/VideoCard.svelte';
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

describe('VideoCard hover preview', () => {
  let playSpy: ReturnType<typeof vi.fn>;
  let pauseSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    clearAvailabilityCache();

    // Local video is available via a HEAD request.
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true } as Response);

    // jsdom doesn't implement HTMLMediaElement playback; stub it.
    playSpy = vi.fn().mockResolvedValue(undefined);
    pauseSpy = vi.fn();
    HTMLMediaElement.prototype.play = playSpy;
    HTMLMediaElement.prototype.pause = pauseSpy;
  });

  test('does not render a preview video before hovering', () => {
    const { container } = render(VideoCard, { props: { video: makeVideo() } });
    expect(container.querySelector('.preview-video')).toBeNull();
  });

  test('plays the video inline within the thumbnail on hover', async () => {
    const { container } = render(VideoCard, { props: { video: makeVideo() } });

    const thumbnail = container.querySelector('.thumbnail-container') as HTMLElement;
    await fireEvent.mouseEnter(thumbnail);

    await waitFor(() => {
      expect(container.querySelector('.preview-video')).not.toBeNull();
    });

    const previewVideo = container.querySelector('.preview-video') as HTMLVideoElement;
    // Muted is mandatory so autoplay isn't blocked and isn't intrusive.
    expect(previewVideo.muted).toBe(true);

    previewVideo.dispatchEvent(new Event('canplay'));
    expect(playSpy).toHaveBeenCalledTimes(1);
  });

  test('reverts to the static thumbnail and stops playback on mouseleave', async () => {
    const { container } = render(VideoCard, { props: { video: makeVideo() } });

    const thumbnail = container.querySelector('.thumbnail-container') as HTMLElement;
    await fireEvent.mouseEnter(thumbnail);
    await waitFor(() => {
      expect(container.querySelector('.preview-video')).not.toBeNull();
    });
    container.querySelector('.preview-video')!.dispatchEvent(new Event('canplay'));

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
    await fireEvent.mouseLeave(thumbnail);

    // The HEAD request finally resolves after the mouse already left.
    resolveFetch({ ok: true } as Response);
    await Promise.resolve();
    await Promise.resolve();

    expect(container.querySelector('.preview-video')).toBeNull();
  });

  test('does not leak a playing video when the card unmounts while hovered', async () => {
    const { container, unmount } = render(VideoCard, { props: { video: makeVideo() } });

    const thumbnail = container.querySelector('.thumbnail-container') as HTMLElement;
    await fireEvent.mouseEnter(thumbnail);
    await waitFor(() => {
      expect(container.querySelector('.preview-video')).not.toBeNull();
    });
    container.querySelector('.preview-video')!.dispatchEvent(new Event('canplay'));

    unmount();

    expect(pauseSpy).toHaveBeenCalled();
  });
});
