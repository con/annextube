/**
 * E2E Test for Archive Browser
 *
 * Tests the frontend with a minimal test archive to verify:
 * - Video list loading
 * - Search functionality
 * - Filtering (channels, playlists, date range, status)
 * - Sorting
 * - Video detail view
 *
 * Setup: Copy test fixtures to web/../ before running:
 *   cp -r tests/fixtures/test-archive/* ../
 */

import { test, expect } from '@playwright/test';

test.describe('Archive Browser', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the archive browser
    await page.goto('/');
  });

  test('loads and displays video list', async ({ page }) => {
    // Wait for videos to load
    await page.waitForSelector('.video-grid');

    // Should show 3 videos
    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(3);

    // Check video titles are visible
    await expect(page.getByText('Test Video Alpha')).toBeVisible();
    await expect(page.getByText('Test Video Beta')).toBeVisible();
    await expect(page.getByText('Another Channel Video')).toBeVisible();
  });

  test('displays result count', async ({ page }) => {
    await page.waitForSelector('.video-grid');

    // Should show "3 videos" in header or result count
    const resultText = page.locator('.result-count, .subtitle');
    await expect(resultText).toContainText('3 video');
  });

  test('search filters videos', async ({ page }) => {
    await page.waitForSelector('.video-grid');

    // Type in search box
    await page.fill('input[placeholder*="Search"]', 'Alpha');

    // Wait for filter to apply (debounced)
    await page.waitForTimeout(400);

    // Should only show 1 video
    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(1);
    await expect(page.getByText('Test Video Alpha')).toBeVisible();
  });

  test('channel filter works', async ({ page }) => {
    await page.waitForSelector('.video-grid');

    // Select "Another Channel" from channel dropdown
    await page.selectOption('select', { label: /Another Channel/ });

    // Wait for filter to apply
    await page.waitForTimeout(400);

    // Should only show 1 video
    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(1);
    await expect(page.getByText('Another Channel Video')).toBeVisible();
  });

  test('playlist filter shows correct count', async ({ page }) => {
    await page.waitForSelector('.video-grid');

    // Check if playlists are loaded
    const playlistSelect = page.locator('select').filter({ hasText: /Test Playlist/ });

    if (await playlistSelect.count() > 0) {
      // Verify playlist shows (2) videos
      await expect(playlistSelect).toContainText('Test Playlist (2)');

      // Select the playlist
      const playlistOption = playlistSelect.locator('option').filter({ hasText: /Test Playlist/ });
      await playlistOption.click();

      // Wait for filter to apply
      await page.waitForTimeout(400);

      // Should show 2 videos
      const videoCards = page.locator('.video-card');
      await expect(videoCards).toHaveCount(2);
      await expect(page.getByText('Test Video Alpha')).toBeVisible();
      await expect(page.getByText('Test Video Beta')).toBeVisible();
    }
  });

  test('sort by views works', async ({ page }) => {
    await page.waitForSelector('.video-grid');

    // Select "Views" from sort dropdown
    await page.selectOption('select[class*="sort"]', { label: /Views/ });

    // Wait for sort to apply
    await page.waitForTimeout(400);

    // Get all video cards
    const videoCards = page.locator('.video-card');
    const firstCard = videoCards.first();
    const lastCard = videoCards.last();

    // With descending sort (default), highest views should be first
    // "Test Video Beta" has 5000 views (highest)
    await expect(firstCard).toContainText('Test Video Beta');
    // "Another Channel Video" has 500 views (lowest)
    await expect(lastCard).toContainText('Another Channel Video');
  });

  test('clear filters button appears and works', async ({ page }) => {
    await page.waitForSelector('.video-grid');

    // Apply a search filter
    await page.fill('input[placeholder*="Search"]', 'Beta');
    await page.waitForTimeout(400);

    // Clear button should appear
    const clearButton = page.getByRole('button', { name: /Clear.*Filter/i });
    await expect(clearButton).toBeVisible();

    // Click clear button
    await clearButton.click();
    await page.waitForTimeout(400);

    // Should show all 3 videos again
    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(3);
  });

  test('clicking video shows detail view', async ({ page }) => {
    await page.waitForSelector('.video-grid');

    // Click on first video
    const firstVideo = page.locator('.video-card').first();
    await firstVideo.click();

    // Should navigate to video detail view
    // URL should change to #/video/TEST001 or similar
    await page.waitForURL(/.*#\/video\/.*/);

    // Should show video detail component
    await expect(page.locator('.video-detail')).toBeVisible();

    // Back button should be visible
    const backButton = page.getByRole('button', { name: /Back/i });
    await expect(backButton).toBeVisible();
  });

  test('back button returns to list', async ({ page }) => {
    await page.waitForSelector('.video-grid');

    // Click on a video
    await page.locator('.video-card').first().click();
    await page.waitForURL(/.*#\/video\/.*/);

    // Click back button
    const backButton = page.getByRole('button', { name: /Back/i });
    await backButton.click();

    // Should return to list view
    await page.waitForSelector('.video-grid');
    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(3);
  });

  test('clean URL does not get default sort params appended', async ({ page }) => {
    await page.waitForSelector('.video-grid');
    await page.waitForTimeout(800); // Wait for debounced URL updates
    expect(page.url()).not.toContain('sort=');
    expect(page.url()).not.toContain('dir=');
  });

  test('filter selection persists without reset', async ({ page }) => {
    await page.waitForSelector('.video-grid');
    const statusSelect = page.locator('select').filter({
      has: page.locator('option', { hasText: 'Backup Available' })
    });
    await statusSelect.selectOption('downloaded');
    await page.waitForTimeout(800);
    // Selection should still be "downloaded" (not reset to "all")
    await expect(statusSelect).toHaveValue('downloaded');
  });

  test('URL state preserves filters', async ({ page }) => {
    await page.waitForSelector('.video-grid');

    // Apply a search filter
    await page.fill('input[placeholder*="Search"]', 'Alpha');
    await page.waitForTimeout(600); // Wait for URL update debounce

    // URL should contain search parameter
    expect(page.url()).toContain('search=Alpha');

    // Reload page
    await page.reload();
    await page.waitForSelector('.video-grid');

    // Search box should still have "Alpha"
    const searchInput = page.locator('input[placeholder*="Search"]');
    await expect(searchInput).toHaveValue('Alpha');

    // Should still show filtered result
    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(1);
  });
});
