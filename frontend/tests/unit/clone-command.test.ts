/**
 * CloneCommand unit tests.
 *
 * Regression coverage for the clone URL shown on top of the page pointing at
 * the web server root (e.g. `datalad clone https://datasets.datalad.org/.git`)
 * instead of the archive being browsed.
 *
 * @ai_generated
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import CloneCommand from '../../src/components/CloneCommand.svelte';

const PAGE_URL =
  'https://datasets.datalad.org/repronim/ReproTube/web/#/channel/ABCD-ReproNim_Course';

/**
 * Emulate a server that publishes a DataLad collection at
 * /repronim/ReproTube/ with per-channel subdatasets — and, like
 * datasets.datalad.org, is itself a dataset at its root.
 */
function mockServer(paths: string[]) {
  const available = new Set(paths);
  return vi.fn(async (input: string) => {
    const resolved = new URL(input, window.location.href).pathname;
    return { ok: available.has(resolved) } as Response;
  });
}

const COLLECTION_LAYOUT = [
  '/.git/HEAD', // datasets.datalad.org is a dataset at its root, too
  '/repronim/ReproTube/.git/HEAD',
  '/repronim/ReproTube/ABCD-ReproNim_Course/.git/HEAD',
];

function commandTexts(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll('.command-text')).map(
    (el) => el.textContent?.replace(/^\$\s*/, '').trim() ?? ''
  );
}

async function expandPanel(container: HTMLElement) {
  const toggle = container.querySelector('.clone-toggle') as HTMLButtonElement | null;
  expect(toggle).not.toBeNull();
  toggle!.click();
  await waitFor(() => expect(container.querySelector('.clone-panel')).not.toBeNull());
}

describe('CloneCommand', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    // Browsing a channel of the collection published at
    // https://datasets.datalad.org/repronim/ReproTube/
    const location = new URL(PAGE_URL);
    vi.spyOn(window, 'location', 'get').mockReturnValue({
      href: location.href,
      origin: location.origin,
      pathname: location.pathname,
      hash: location.hash,
      protocol: location.protocol,
    } as Location);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = originalFetch;
  });

  test('does not probe before the archive root has been discovered', async () => {
    const fetchMock = mockServer(COLLECTION_LAYOUT);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const { container } = render(CloneCommand, {
      props: {
        // dataLoader.baseUrl is still '' until init() resolves
        baseUrl: '',
        channelDir: 'ABCD-ReproNim_Course',
        videoFilePath: null,
        isMultiChannel: false,
      },
    });

    // Give any probe a chance to fire before asserting that none did
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(fetchMock).not.toHaveBeenCalled();
    // Nothing found means nothing offered — never the server root
    expect(container.querySelector('.clone-toggle')).toBeNull();
  });

  test('offers the channel dataset and the collection when browsing a channel', async () => {
    globalThis.fetch = mockServer(COLLECTION_LAYOUT) as unknown as typeof fetch;

    const { container } = render(CloneCommand, {
      props: {
        baseUrl: '..',
        channelDir: 'ABCD-ReproNim_Course',
        videoFilePath: null,
        isMultiChannel: true,
      },
    });

    await waitFor(() => expect(container.querySelector('.clone-toggle')).not.toBeNull());
    await expandPanel(container);

    expect(commandTexts(container)).toEqual([
      'datalad clone https://datasets.datalad.org/repronim/ReproTube/ABCD-ReproNim_Course/.git',
      'datalad clone https://datasets.datalad.org/repronim/ReproTube/.git',
    ]);

    const labels = Array.from(container.querySelectorAll('.target-label')).map(
      (el) => el.textContent?.trim()
    );
    expect(labels).toEqual(['This channel', 'Whole collection']);
  });

  test('get paths are relative to the repository each command clones', async () => {
    globalThis.fetch = mockServer(COLLECTION_LAYOUT) as unknown as typeof fetch;

    const { container } = render(CloneCommand, {
      props: {
        baseUrl: '..',
        channelDir: 'ABCD-ReproNim_Course',
        videoFilePath: '2024/20240101_intro',
        isMultiChannel: true,
      },
    });

    await waitFor(() => expect(container.querySelector('.clone-toggle')).not.toBeNull());
    await expandPanel(container);

    expect(commandTexts(container)).toEqual([
      'datalad clone https://datasets.datalad.org/repronim/ReproTube/ABCD-ReproNim_Course/.git',
      'cd ABCD-ReproNim_Course && datalad get videos/2024/20240101_intro/',
      'datalad clone https://datasets.datalad.org/repronim/ReproTube/.git',
      'cd ReproTube && datalad get ABCD-ReproNim_Course/videos/2024/20240101_intro/',
    ]);
  });

  test('git tab only fetches from the repository that holds the video', async () => {
    globalThis.fetch = mockServer(COLLECTION_LAYOUT) as unknown as typeof fetch;

    const { container } = render(CloneCommand, {
      props: {
        baseUrl: '..',
        channelDir: 'ABCD-ReproNim_Course',
        videoFilePath: '2024/20240101_intro',
        isMultiChannel: true,
      },
    });

    await waitFor(() => expect(container.querySelector('.clone-toggle')).not.toBeNull());
    await expandPanel(container);

    const gitTab = Array.from(container.querySelectorAll('.tab')).find((el) =>
      /git/i.test(el.textContent ?? '')
    ) as HTMLButtonElement;
    gitTab.click();
    await waitFor(() =>
      expect(commandTexts(container)[0]).toContain('git clone')
    );

    // No `git annex get` under the collection: the video sits in a subdataset
    // there, and `git submodule update` cannot resolve it from a /.git URL
    expect(commandTexts(container)).toEqual([
      'git clone https://datasets.datalad.org/repronim/ReproTube/ABCD-ReproNim_Course/.git',
      'cd ABCD-ReproNim_Course && git annex get videos/2024/20240101_intro/',
      'git clone https://datasets.datalad.org/repronim/ReproTube/.git',
    ]);
  });

  test('single-channel archive shows one unlabelled clone target', async () => {
    globalThis.fetch = mockServer([
      '/.git/HEAD',
      '/repronim/ReproTube/.git/HEAD',
    ]) as unknown as typeof fetch;

    const { container } = render(CloneCommand, {
      props: {
        baseUrl: '..',
        channelDir: null,
        videoFilePath: '2024/20240101_intro',
        isMultiChannel: false,
      },
    });

    await waitFor(() => expect(container.querySelector('.clone-toggle')).not.toBeNull());
    await expandPanel(container);

    expect(commandTexts(container)).toEqual([
      'datalad clone https://datasets.datalad.org/repronim/ReproTube/.git',
      'cd ReproTube && datalad get videos/2024/20240101_intro/',
    ]);
    expect(container.querySelectorAll('.target-label')).toHaveLength(0);
  });

  test('offers only the clone when a video is opened without channel context', async () => {
    // #/video/{id} in a collection: the video is in some channel subdataset,
    // but the route does not say which, so there is no path to hand `get`
    globalThis.fetch = mockServer([
      '/.git/HEAD',
      '/repronim/ReproTube/.git/HEAD',
    ]) as unknown as typeof fetch;

    const { container } = render(CloneCommand, {
      props: {
        baseUrl: '..',
        channelDir: null,
        videoFilePath: '2024/20240101_intro',
        isMultiChannel: true,
      },
    });

    await waitFor(() => expect(container.querySelector('.clone-toggle')).not.toBeNull());
    await expandPanel(container);

    expect(commandTexts(container)).toEqual([
      'datalad clone https://datasets.datalad.org/repronim/ReproTube/.git',
    ]);
  });

  test('quotes command arguments a shell would otherwise split', async () => {
    globalThis.fetch = mockServer([
      '/.git/HEAD',
      '/repronim/ReproTube/.git/HEAD',
    ]) as unknown as typeof fetch;

    const { container } = render(CloneCommand, {
      props: {
        baseUrl: '..',
        channelDir: null,
        videoFilePath: '2024/2024-01-01 Intro talk',
        isMultiChannel: false,
      },
    });

    await waitFor(() => expect(container.querySelector('.clone-toggle')).not.toBeNull());
    await expandPanel(container);

    expect(commandTexts(container)[1]).toBe(
      "cd ReproTube && datalad get 'videos/2024/2024-01-01 Intro talk/'"
    );
  });

  test('falls back to the collection when the channel dataset is not published', async () => {
    globalThis.fetch = mockServer([
      '/.git/HEAD',
      '/repronim/ReproTube/.git/HEAD',
    ]) as unknown as typeof fetch;

    const { container } = render(CloneCommand, {
      props: {
        baseUrl: '..',
        channelDir: 'ABCD-ReproNim_Course',
        videoFilePath: null,
        isMultiChannel: true,
      },
    });

    await waitFor(() => expect(container.querySelector('.clone-toggle')).not.toBeNull());
    await expandPanel(container);

    expect(commandTexts(container)).toEqual([
      'datalad clone https://datasets.datalad.org/repronim/ReproTube/.git',
    ]);
  });
});
