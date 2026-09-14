/**
 * Availability service unit tests.
 *
 * @ai_generated
 */

import { describe, test, expect, beforeEach, vi } from 'vitest';
import {
  checkVideoAvailability,
  clearAvailabilityCache,
  isFileAvailable,
} from '../../src/services/availability';

describe('availability', () => {
  beforeEach(() => {
    clearAvailabilityCache();
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true } as Response);
  });

  test('isFileAvailable issues a HEAD request', async () => {
    expect(await isFileAvailable('/videos/a/video.mkv')).toBe(true);
    expect(globalThis.fetch).toHaveBeenCalledWith('/videos/a/video.mkv', { method: 'HEAD' });
  });

  test('isFileAvailable reports a missing file as unavailable', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false } as Response);
    expect(await isFileAvailable('/videos/a/video.mkv')).toBe(false);
  });

  test('caches a completed check', async () => {
    await checkVideoAvailability('/videos/a/video.mkv');
    await checkVideoAvailability('/videos/a/video.mkv');

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  test('coalesces checks that overlap in flight', async () => {
    // Regression: only completed checks were cached, so callers arriving
    // while a check was still in flight each fired their own HEAD request.
    let resolveFetch: (value: Response) => void = () => {};
    globalThis.fetch = vi.fn().mockImplementation(
      () => new Promise((resolve) => { resolveFetch = resolve; })
    );

    const checks = [
      checkVideoAvailability('/videos/a/video.mkv'),
      checkVideoAvailability('/videos/a/video.mkv'),
      checkVideoAvailability('/videos/a/video.mkv'),
    ];
    resolveFetch({ ok: true } as Response);

    expect(await Promise.all(checks)).toEqual([true, true, true]);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  test('a clear that lands during a check is not undone by it', async () => {
    // Otherwise clearing a known-wrong entry (e.g. a video that turned out
    // not to load) silently restores the very value being thrown away.
    let resolveFetch: (value: Response) => void = () => {};
    globalThis.fetch = vi.fn().mockImplementation(
      () => new Promise((resolve) => { resolveFetch = resolve; })
    );

    const check = checkVideoAvailability('/videos/a/video.mkv');
    clearAvailabilityCache('/videos/a/video.mkv');
    resolveFetch({ ok: true } as Response);
    // The caller that asked still gets its answer...
    expect(await check).toBe(true);

    // ...but the cleared entry was not repopulated behind its back.
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false } as Response);
    expect(await checkVideoAvailability('/videos/a/video.mkv')).toBe(false);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  test('checks each distinct path separately', async () => {
    await Promise.all([
      checkVideoAvailability('/videos/a/video.mkv'),
      checkVideoAvailability('/videos/b/video.mkv'),
    ]);

    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });

  test('forceCheck bypasses the cache', async () => {
    await checkVideoAvailability('/videos/a/video.mkv');
    await checkVideoAvailability('/videos/a/video.mkv', true);

    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });

  test('clearing one path re-checks only that path', async () => {
    await checkVideoAvailability('/videos/a/video.mkv');
    await checkVideoAvailability('/videos/b/video.mkv');

    clearAvailabilityCache('/videos/a/video.mkv');
    await checkVideoAvailability('/videos/a/video.mkv');
    await checkVideoAvailability('/videos/b/video.mkv');

    expect(globalThis.fetch).toHaveBeenCalledTimes(3);
  });

  test('clearing everything re-checks everything', async () => {
    await checkVideoAvailability('/videos/a/video.mkv');

    clearAvailabilityCache();
    await checkVideoAvailability('/videos/a/video.mkv');

    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });
});
