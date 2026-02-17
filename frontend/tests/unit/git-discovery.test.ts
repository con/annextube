/**
 * Unit tests for git-discovery service.
 * @ai_generated
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { probeGitUrl } from '../../src/services/git-discovery';

describe('probeGitUrl', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    // Reset fetch mock before each test
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('returns absolute URL when .git/HEAD is accessible', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true });

    const result = await probeGitUrl('http://localhost:8081');
    expect(result).toBe('http://localhost:8081/.git');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://localhost:8081/.git/HEAD',
      { method: 'HEAD' }
    );
  });

  it('returns null when .git/HEAD is not found', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: false });

    const result = await probeGitUrl('http://localhost:8081');
    expect(result).toBeNull();
  });

  it('returns null on network error', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));

    const result = await probeGitUrl('http://localhost:8081');
    expect(result).toBeNull();
  });

  it('probes correct URL for channel subdataset', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true });

    const result = await probeGitUrl('http://localhost:8081/ReproNim');
    expect(result).toBe('http://localhost:8081/ReproNim/.git');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://localhost:8081/ReproNim/.git/HEAD',
      { method: 'HEAD' }
    );
  });

  it('strips trailing slash from result', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true });

    // The URL constructor normalizes, but verify no trailing slash
    const result = await probeGitUrl('http://localhost:8081');
    expect(result).not.toMatch(/\/$/);
  });
});
