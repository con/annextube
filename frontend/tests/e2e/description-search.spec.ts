/**
 * E2E Test for Description Search (FR-042c/d)
 *
 * Verifies that the Metadata search mode matches terms that appear only in
 * a video's full description, loaded from video_fulldescriptions.json
 * alongside videos.tsv, and that archives without that file degrade to the
 * TSV first-line description column.
 *
 * Uses Playwright route() API to intercept requests and serve mock data
 * (same pattern as multi-channel.spec.ts), so it runs against the plain
 * Vite dev server.
 */

import { test, expect } from '@playwright/test';

const VIDEOS_TSV =
  'video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\tduration\tview_count\tlike_count\tcomment_count\tthumbnail_url\tdownload_status\tsource_url\tpath\tdescription\n' +
  'D001\tAlpha Lecture\tUC001\tTest Channel\t2024-01-01T00:00:00\t300\t1000\t50\t10\thttps://example.com/thumb1.jpg\ttracked\thttps://www.youtube.com/watch?v=D001\talpha-lecture\tAlpha lecture overview\n' +
  'D002\tBeta Talk\tUC001\tTest Channel\t2024-02-01T00:00:00\t600\t5000\t200\t50\thttps://example.com/thumb2.jpg\tdownloaded\thttps://www.youtube.com/watch?v=D002\tbeta-talk\t';

// "Halchenko" appears ONLY here -- not in any title and not in the TSV
// first-line description column
const FULLDESCRIPTIONS_JSON = JSON.stringify({
  D001:
    'Alpha lecture overview\n\n' +
    'Presented by Yaroslav Halchenko (Dartmouth College).\n' +
    'Covers DataLad basics.',
});

/**
 * Intercept archive requests for a single-channel archive.
 *
 * @param fulldescriptions - JSON body for video_fulldescriptions.json,
 *   or null to 404 it (archives exported before FR-042c)
 */
async function setupSingleChannelRoutes(
  page: import('@playwright/test').Page,
  fulldescriptions: string | null,
) {
  await page.route('**/*', async (route) => {
    // Match on exact pathname suffixes -- a loose substring match would
    // also catch app modules like /src/services/pagefind.ts
    const pathname = new URL(route.request().url()).pathname;
    const method = route.request().method();

    // No multi-channel markers -> single-channel mode
    if (pathname.endsWith('/channels.tsv') || pathname.endsWith('/channel.json')) {
      await route.fulfill({ status: 404 });
      return;
    }

    if (pathname.endsWith('/videos/videos.tsv')) {
      if (method === 'HEAD') {
        await route.fulfill({ status: 200 });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'text/tab-separated-values',
        body: VIDEOS_TSV,
      });
      return;
    }

    if (pathname.endsWith('/video_fulldescriptions.json')) {
      if (fulldescriptions === null) {
        await route.fulfill({ status: 404 });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: fulldescriptions,
      });
      return;
    }

    if (
      pathname.endsWith('/playlists.tsv') ||
      pathname.endsWith('/pagefind/pagefind.js')
    ) {
      await route.fulfill({ status: 404 });
      return;
    }

    // App assets etc. -> the dev server
    await route.continue();
  });
}

async function search(page: import('@playwright/test').Page, query: string) {
  await page.fill('input[placeholder*="Search"]', query);
  // Wait for the debounced filter to apply
  await page.waitForTimeout(500);
}

test.describe('Description Search (FR-042d)', () => {
  test('term appearing only in the full description matches', async ({
    page,
  }) => {
    await setupSingleChannelRoutes(page, FULLDESCRIPTIONS_JSON);
    await page.goto('/');
    await page.waitForSelector('.video-grid');

    await search(page, 'Halchenko');

    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(1);
    await expect(page.getByText('Alpha Lecture')).toBeVisible();
  });

  test('term in the TSV first-line description matches without the JSON', async ({
    page,
  }) => {
    await setupSingleChannelRoutes(page, null);
    await page.goto('/');
    await page.waitForSelector('.video-grid');

    await search(page, 'overview');

    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(1);
    await expect(page.getByText('Alpha Lecture')).toBeVisible();
  });

  test('full-description term finds nothing without the JSON (degradation)', async ({
    page,
  }) => {
    await setupSingleChannelRoutes(page, null);
    await page.goto('/');
    await page.waitForSelector('.video-grid');

    await search(page, 'Halchenko');

    await expect(page.locator('.video-card')).toHaveCount(0);
  });

  test('title search still works alongside description search', async ({
    page,
  }) => {
    await setupSingleChannelRoutes(page, FULLDESCRIPTIONS_JSON);
    await page.goto('/');
    await page.waitForSelector('.video-grid');

    await search(page, 'Beta Talk');

    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(1);
    await expect(page.getByText('Beta Talk')).toBeVisible();
  });
});
