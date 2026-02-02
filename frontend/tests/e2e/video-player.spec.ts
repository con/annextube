/**
 * E2E Tests for Video Player Tabs
 *
 * Verifies the video player tab behavior:
 * - Downloaded videos show both "Local Player" and "Watch on YouTube" tabs
 * - Metadata-only videos show only "Watch on YouTube" tab
 * - Correct default tab selection based on download status
 * - Tab switching between local and YouTube player
 * - Correct player elements rendered per tab
 *
 * Test data: apopyk-archive from test-archives/fake-home-hierarchical-test
 *   - Downloaded video: x2vBnbAvAg4 (download_status: downloaded)
 *   - Metadata-only video: YOZ6rFQhv1U (download_status: metadata_only)
 */

import { test, expect } from '@playwright/test';

// Video IDs from the test archive
const DOWNLOADED_VIDEO_ID = 'x2vBnbAvAg4';
const METADATA_ONLY_VIDEO_ID = 'YOZ6rFQhv1U';

/**
 * Navigate to a video detail page by clicking the video card from the list.
 * This ensures the data loader has the TSV cache populated (needed for
 * download_status to propagate to the VideoPlayer component).
 */
async function navigateToVideo(page: import('@playwright/test').Page, videoId: string) {
  await page.goto('/');
  await page.waitForSelector('.video-grid');

  // Click the video card that links to this video
  // The card click navigates to #/video/{video_id}
  const videoCard = page.locator(`.video-card`).filter({
    has: page.locator(`a[href*="${videoId}"], [data-video-id="${videoId}"]`),
  });

  // If direct card targeting does not work, navigate via URL hash
  if ((await videoCard.count()) === 0) {
    await page.goto(`/#/video/${videoId}`);
  } else {
    await videoCard.first().click();
  }

  await page.waitForURL(new RegExp(`#/video/${videoId}`));
  await page.waitForSelector('.video-detail');
}

test.describe('Video Player Tabs', () => {
  test.describe('Downloaded video', () => {
    test.beforeEach(async ({ page }) => {
      await navigateToVideo(page, DOWNLOADED_VIDEO_ID);
    });

    test('shows both "Local Player" and "Watch on YouTube" tabs', async ({ page }) => {
      const tabs = page.locator('.video-player .tab');
      await expect(tabs).toHaveCount(2);

      await expect(tabs.nth(0)).toContainText('Local Player');
      await expect(tabs.nth(1)).toContainText('Watch on YouTube');
    });

    test('"Local Player" tab is selected by default', async ({ page }) => {
      const localTab = page.locator('.video-player .tab').filter({ hasText: 'Local Player' });
      await expect(localTab).toHaveClass(/active/);

      const youtubeTab = page.locator('.video-player .tab').filter({ hasText: 'Watch on YouTube' });
      await expect(youtubeTab).not.toHaveClass(/active/);
    });

    test('Local Player tab shows <video> element', async ({ page }) => {
      const videoElement = page.locator('.video-player .tab-content video');
      await expect(videoElement).toBeVisible();
    });

    test('clicking "Watch on YouTube" tab switches to YouTube player', async ({ page }) => {
      // Click the YouTube tab
      const youtubeTab = page.locator('.video-player .tab').filter({ hasText: 'Watch on YouTube' });
      await youtubeTab.click();

      // YouTube tab should now be active
      await expect(youtubeTab).toHaveClass(/active/);

      // Local Player tab should no longer be active
      const localTab = page.locator('.video-player .tab').filter({ hasText: 'Local Player' });
      await expect(localTab).not.toHaveClass(/active/);

      // Should show iframe instead of video
      const iframe = page.locator('.video-player .tab-content iframe');
      await expect(iframe).toBeVisible();

      const videoElement = page.locator('.video-player .tab-content video');
      await expect(videoElement).toHaveCount(0);
    });

    test('clicking back to "Local Player" tab restores local player', async ({ page }) => {
      // Switch to YouTube first
      const youtubeTab = page.locator('.video-player .tab').filter({ hasText: 'Watch on YouTube' });
      await youtubeTab.click();
      await expect(youtubeTab).toHaveClass(/active/);

      // Switch back to Local Player
      const localTab = page.locator('.video-player .tab').filter({ hasText: 'Local Player' });
      await localTab.click();

      await expect(localTab).toHaveClass(/active/);
      await expect(youtubeTab).not.toHaveClass(/active/);

      const videoElement = page.locator('.video-player .tab-content video');
      await expect(videoElement).toBeVisible();

      const iframe = page.locator('.video-player .tab-content iframe');
      await expect(iframe).toHaveCount(0);
    });
  });

  test.describe('Metadata-only video', () => {
    test.beforeEach(async ({ page }) => {
      await navigateToVideo(page, METADATA_ONLY_VIDEO_ID);
    });

    test('shows only "Watch on YouTube" tab', async ({ page }) => {
      const tabs = page.locator('.video-player .tab');
      await expect(tabs).toHaveCount(1);

      await expect(tabs.first()).toContainText('Watch on YouTube');
    });

    test('"Watch on YouTube" tab is selected by default', async ({ page }) => {
      const youtubeTab = page.locator('.video-player .tab').filter({ hasText: 'Watch on YouTube' });
      await expect(youtubeTab).toHaveClass(/active/);
    });

    test('YouTube tab shows <iframe> element', async ({ page }) => {
      const iframe = page.locator('.video-player .tab-content iframe');
      await expect(iframe).toBeVisible();

      // Verify the iframe src points to YouTube embed
      await expect(iframe).toHaveAttribute(
        'src',
        `https://www.youtube.com/embed/${METADATA_ONLY_VIDEO_ID}`
      );
    });

    test('does not show "Local Player" tab', async ({ page }) => {
      const localTab = page.locator('.video-player .tab').filter({ hasText: 'Local Player' });
      await expect(localTab).toHaveCount(0);
    });

    test('does not show <video> element', async ({ page }) => {
      const videoElement = page.locator('.video-player .tab-content video');
      await expect(videoElement).toHaveCount(0);
    });
  });
});
