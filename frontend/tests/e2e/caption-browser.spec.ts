/**
 * E2E Tests for Interactive Caption Browser
 *
 * Tests the caption browser panel alongside the video player:
 * language selection, cue display, click-to-seek, search, and auto-scroll.
 *
 * Test data: test-archives/archive-workflow-fixture (@AnnexTubeTesting channel)
 *   - Downloaded videos have synthetic VTT captions (en + es) added by create-e2e-fixture.sh
 *   - Metadata-only videos have no captions
 *
 * @ai_generated
 */

import { test, expect } from '@playwright/test';

// Video IDs loaded dynamically (same pattern as archive-workflow.spec.ts)
let DOWNLOADED_VIDEO_ID = '';
let METADATA_ONLY_VIDEO_ID = '';

const WEB_BASE = '/web/';

async function navigateToVideo(page: import('@playwright/test').Page, videoId: string) {
  await page.goto(`${WEB_BASE}#/video/${videoId}`);
  await page.waitForSelector('.video-detail', { timeout: 15000 });
}

// Increase timeout for archive server tests
test.setTimeout(60000);

test.describe('Caption Browser', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    try {
      const response = await page.goto('/videos/videos.tsv');
      const tsvText = await response!.text();
      const lines = tsvText.trim().split('\n');
      const headers = lines[0].split('\t');
      const idIdx = headers.indexOf('video_id');
      const statusIdx = headers.indexOf('download_status');

      for (const line of lines.slice(1)) {
        const cols = line.split('\t');
        const videoId = cols[idIdx];
        const status = cols[statusIdx];
        if (status === 'downloaded' && !DOWNLOADED_VIDEO_ID) {
          DOWNLOADED_VIDEO_ID = videoId;
        }
        if (status === 'metadata_only' && !METADATA_ONLY_VIDEO_ID) {
          METADATA_ONLY_VIDEO_ID = videoId;
        }
        if (DOWNLOADED_VIDEO_ID && METADATA_ONLY_VIDEO_ID) break;
      }
    } finally {
      await page.close();
    }

    if (!DOWNLOADED_VIDEO_ID) throw new Error('No downloaded video found in videos.tsv');
    if (!METADATA_ONLY_VIDEO_ID) throw new Error('No metadata_only video found in videos.tsv');
  });

  test('caption browser appears for video with captions', async ({ page }) => {
    await navigateToVideo(page, DOWNLOADED_VIDEO_ID);

    // Wait for metadata to load (captions_available populated from metadata.json)
    const captionBrowser = page.locator('.caption-browser');
    await expect(captionBrowser).toBeVisible({ timeout: 10000 });
  });

  test('caption browser absent for metadata-only videos', async ({ page }) => {
    await navigateToVideo(page, METADATA_ONLY_VIDEO_ID);

    // Wait for page to settle
    await page.waitForTimeout(2000);

    // Caption browser should not be present
    const captionBrowser = page.locator('.caption-browser');
    await expect(captionBrowser).toHaveCount(0);
  });

  test('language selector shows available languages', async ({ page }) => {
    await navigateToVideo(page, DOWNLOADED_VIDEO_ID);
    await expect(page.locator('.caption-browser')).toBeVisible({ timeout: 10000 });

    // Should show a language selector with EN and ES options
    const langSelect = page.locator('.caption-browser .lang-select');
    await expect(langSelect).toBeVisible();

    const options = langSelect.locator('option');
    await expect(options).toHaveCount(2);

    const optionTexts = await options.allTextContents();
    expect(optionTexts).toContain('EN');
    expect(optionTexts).toContain('ES');
  });

  test('cues load and display with timestamps', async ({ page }) => {
    await navigateToVideo(page, DOWNLOADED_VIDEO_ID);
    await expect(page.locator('.caption-browser')).toBeVisible({ timeout: 10000 });

    // Wait for cues to load
    const cues = page.locator('.caption-browser .cue');
    await expect(cues.first()).toBeVisible({ timeout: 5000 });

    // Should have 4 cue elements (matching our synthetic VTT)
    await expect(cues).toHaveCount(4);

    // First cue should contain "Welcome" text
    const firstCueText = cues.first().locator('.cue-text');
    await expect(firstCueText).toContainText('Welcome');

    // First cue timestamp should show "0:00"
    const firstCueTime = cues.first().locator('.cue-time');
    await expect(firstCueTime).toContainText('0:00');
  });

  test('click-to-seek works', async ({ page }) => {
    await navigateToVideo(page, DOWNLOADED_VIDEO_ID);
    await expect(page.locator('.caption-browser')).toBeVisible({ timeout: 10000 });

    // Wait for cues to load
    const cues = page.locator('.caption-browser .cue');
    await expect(cues.first()).toBeVisible({ timeout: 5000 });

    // Click the third cue (startTime = 2.0)
    const thirdCue = cues.nth(2);
    await thirdCue.click();

    // Verify video currentTime is approximately 2 seconds
    const videoElement = page.locator('.video-player .tab-content video');
    const currentTime = await videoElement.evaluate((video: HTMLVideoElement) => video.currentTime);
    expect(currentTime).toBeCloseTo(2, 0);
  });

  test('language switching loads different captions', async ({ page }) => {
    await navigateToVideo(page, DOWNLOADED_VIDEO_ID);
    await expect(page.locator('.caption-browser')).toBeVisible({ timeout: 10000 });

    // Wait for English cues to load
    const cues = page.locator('.caption-browser .cue');
    await expect(cues.first()).toBeVisible({ timeout: 5000 });
    await expect(cues.first().locator('.cue-text')).toContainText('Welcome');

    // Switch to Spanish
    const langSelect = page.locator('.caption-browser .lang-select');
    await langSelect.selectOption('es');

    // Wait for Spanish cues to load
    await expect(cues.first().locator('.cue-text')).toContainText('Bienvenidos', { timeout: 5000 });
  });

  test('search filters and shows match count', async ({ page }) => {
    await navigateToVideo(page, DOWNLOADED_VIDEO_ID);
    await expect(page.locator('.caption-browser')).toBeVisible({ timeout: 10000 });

    // Wait for cues
    const cues = page.locator('.caption-browser .cue');
    await expect(cues.first()).toBeVisible({ timeout: 5000 });

    // Type "searchable" in the search input
    const searchInput = page.locator('.caption-browser .search-input');
    await searchInput.fill('searchable');

    // Should show 1 match
    const matchCount = page.locator('.caption-browser .match-count');
    await expect(matchCount).toContainText('1 match');

    // The matching cue should have search-match class
    const matchingCues = page.locator('.caption-browser .cue.search-match');
    await expect(matchingCues).toHaveCount(1);

    // Non-matching cues should be dimmed
    const dimmedCues = page.locator('.caption-browser .cue.dimmed');
    await expect(dimmedCues).toHaveCount(3);
  });

  test('auto-scroll highlights active cue during playback', async ({ page }) => {
    await navigateToVideo(page, DOWNLOADED_VIDEO_ID);
    await expect(page.locator('.caption-browser')).toBeVisible({ timeout: 10000 });

    // Wait for cues
    const cues = page.locator('.caption-browser .cue');
    await expect(cues.first()).toBeVisible({ timeout: 5000 });

    // Play the video
    const videoElement = page.locator('.video-player .tab-content video');
    await videoElement.evaluate((video: HTMLVideoElement) => video.play());

    // Wait for playback and active cue highlighting
    await expect(page.locator('.caption-browser .cue.active')).toBeVisible({ timeout: 6000 });
  });

  test('toggle hides and shows transcript', async ({ page }) => {
    await navigateToVideo(page, DOWNLOADED_VIDEO_ID);
    await expect(page.locator('.caption-browser')).toBeVisible({ timeout: 10000 });

    // Wait for cues
    const cueList = page.locator('.caption-browser .cue-list');
    await expect(cueList).toBeVisible({ timeout: 5000 });

    // Click hide toggle
    const toggleBtn = page.locator('.caption-browser .toggle-btn');
    await toggleBtn.click();

    // Cue list should be hidden
    await expect(cueList).not.toBeVisible();

    // Click show toggle
    await toggleBtn.click();

    // Cue list should be visible again
    await expect(cueList).toBeVisible();
  });
});
