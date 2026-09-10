/**
 * App-level regression test for the clone URL in the header.
 *
 * The archive root is discovered asynchronously by DataLoader.init(); App must
 * hand the discovered value to CloneCommand rather than the empty string it
 * starts out with, otherwise the probe resolves against the web server root
 * (`https://datasets.datalad.org/.git`) instead of the archive.
 *
 * @ai_generated
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import App from '../../src/App.svelte';

const CHANNELS_TSV = [
  'channel_id\ttitle\tcustom_url\tdescription\tsubscriber_count\tvideo_count\tplaylist_count\ttotal_videos_archived\tfirst_video_date\tlast_video_date\tlast_sync\tchannel_dir',
  'UC001\tABCD-ReproNim Course\t@abcd\tCourse videos\t232\t71\t0\t71\t2020-10-05\t2025-12-16\t2026-02-11T08:28:26\tABCD-ReproNim_Course',
].join('\n');

/**
 * A server hosting the collection under /repronim/ReproTube/ which — like
 * datasets.datalad.org — is also a git repository at its own root.
 */
function mockServer() {
  const files: Record<string, string> = {
    '/repronim/ReproTube/channels.tsv': CHANNELS_TSV,
    '/repronim/ReproTube/.git/HEAD': 'ref: refs/heads/main\n',
    '/.git/HEAD': 'ref: refs/heads/main\n',
  };
  return vi.fn(async (input: string) => {
    const path = new URL(input, window.location.href).pathname;
    const body = files[path];
    return {
      ok: body !== undefined,
      status: body === undefined ? 404 : 200,
      text: async () => body ?? '',
      json: async () => JSON.parse(body ?? '{}'),
    } as Response;
  });
}

describe('App clone command', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    // The web UI lives one level below the archive root
    window.history.replaceState({}, '', '/repronim/ReproTube/web/#/');
    globalThis.fetch = mockServer() as unknown as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test('clones the archive, not the web server root', async () => {
    const { container } = render(App);

    await waitFor(() => expect(container.querySelector('.clone-toggle')).not.toBeNull());
    (container.querySelector('.clone-toggle') as HTMLButtonElement).click();

    await waitFor(() => expect(container.querySelector('.command-text')).not.toBeNull());
    const commands = Array.from(container.querySelectorAll('.command-text')).map(
      (el) => el.textContent?.replace(/^\$\s*/, '').trim()
    );

    expect(commands).toEqual([
      `datalad clone ${window.location.origin}/repronim/ReproTube/.git`,
    ]);
  });
});
