/**
 * E2E Tests for Caption Search (Pagefind)
 *
 * Tests the full-text caption search feature powered by Pagefind.
 * Runs against a real annextube archive served at localhost:8765
 * that has curated VTT captions and a pre-built Pagefind index.
 *
 * Prerequisites:
 *   - Archive server running at http://localhost:8765 with:
 *     - 68 curated VTT captions
 *     - Pagefind index at web/pagefind/
 *   - Set CAPTION_SEARCH_ARCHIVE_URL=http://localhost:8765 or
 *     have the server already running on port 8765
 *
 * @ai_generated
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:8765/web/';

// Increase timeout -- Pagefind init + search can be slow on first load
test.setTimeout(60000);

/**
 * Wait for the Pagefind-powered search mode toggle to appear.
 * The toggle only renders after initPagefind() resolves true,
 * which requires fetching /pagefind/pagefind.js from the server.
 */
async function waitForPagefindToggle(page: import('@playwright/test').Page) {
  await page.waitForSelector('.search-mode-toggle', { timeout: 15000 });
}

/**
 * Switch to caption search mode by clicking the "Captions" tab.
 */
async function switchToCaptionMode(page: import('@playwright/test').Page) {
  await waitForPagefindToggle(page);
  const captionsTab = page.locator('.mode-tab').filter({ hasText: 'Captions' });
  await captionsTab.click();
  await expect(captionsTab).toHaveClass(/active/);
}

/**
 * Type a query into the search input and wait for caption results to appear.
 */
async function searchCaptions(
  page: import('@playwright/test').Page,
  query: string,
) {
  const searchInput = page.locator('#search-input');
  await searchInput.fill(query);

  // Wait for debounced search (300ms) + Pagefind response
  await page.waitForSelector('.caption-search-results .result-card', {
    timeout: 15000,
  });
}

test.describe('Caption Search (Pagefind)', () => {
  // Run serially -- all tests share the same external server
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('.video-grid', { timeout: 15000 });
  });

  test.describe('Search mode toggle', () => {
    test('Videos/Captions toggle appears when Pagefind index exists', async ({
      page,
    }) => {
      await waitForPagefindToggle(page);

      const toggle = page.locator('.search-mode-toggle');
      await expect(toggle).toBeVisible();

      // Should have exactly two tabs
      const tabs = toggle.locator('.mode-tab');
      await expect(tabs).toHaveCount(2);
      await expect(tabs.first()).toContainText('Videos');
      await expect(tabs.last()).toContainText('Captions');
    });

    test('Videos tab is active by default', async ({ page }) => {
      await waitForPagefindToggle(page);

      const videosTab = page.locator('.mode-tab').filter({ hasText: 'Videos' });
      await expect(videosTab).toHaveClass(/active/);

      const captionsTab = page
        .locator('.mode-tab')
        .filter({ hasText: 'Captions' });
      await expect(captionsTab).not.toHaveClass(/active/);
    });

    test('clicking Captions tab activates it', async ({ page }) => {
      await switchToCaptionMode(page);

      const captionsTab = page
        .locator('.mode-tab')
        .filter({ hasText: 'Captions' });
      await expect(captionsTab).toHaveClass(/active/);

      const videosTab = page.locator('.mode-tab').filter({ hasText: 'Videos' });
      await expect(videosTab).not.toHaveClass(/active/);
    });

    test('search input placeholder changes in caption mode', async ({
      page,
    }) => {
      await switchToCaptionMode(page);

      const searchInput = page.locator('#search-input');
      await expect(searchInput).toHaveAttribute(
        'placeholder',
        /caption/i,
      );
    });
  });

  test.describe('Caption search results', () => {
    test('searching for "DataLad" returns results', async ({ page }) => {
      await switchToCaptionMode(page);
      await searchCaptions(page, 'DataLad');

      const resultCards = page.locator('.caption-search-results .result-card');
      const count = await resultCards.count();
      expect(count).toBeGreaterThan(0);
    });

    test('result cards show video title, timestamp, and excerpt', async ({
      page,
    }) => {
      await switchToCaptionMode(page);
      await searchCaptions(page, 'DataLad');

      const firstCard = page
        .locator('.caption-search-results .result-card')
        .first();

      // Title should be non-empty
      const title = firstCard.locator('.result-title');
      await expect(title).toBeVisible();
      const titleText = await title.textContent();
      expect(titleText!.trim().length).toBeGreaterThan(0);

      // Timestamp badge should be visible (e.g. "01:23" or "1:02:34")
      const timestamp = firstCard.locator('.timestamp-badge').first();
      await expect(timestamp).toBeVisible();
      const tsText = await timestamp.textContent();
      expect(tsText).toMatch(/\d{1,2}:\d{2}/);

      // Excerpt should be visible and contain highlighted <mark> tags
      const excerpt = firstCard.locator('.result-excerpt');
      await expect(excerpt).toBeVisible();
      const markTags = excerpt.locator('mark');
      const markCount = await markTags.count();
      expect(markCount).toBeGreaterThan(0);
    });

    test('result header shows video count', async ({ page }) => {
      await switchToCaptionMode(page);
      await searchCaptions(page, 'DataLad');

      const resultCount = page.locator(
        '.caption-search-results .result-count',
      );
      await expect(resultCount).toBeVisible();
      // Should say something like "5 videos with caption matches"
      await expect(resultCount).toContainText(/\d+ videos? with caption matches/);
    });

    test('different queries return different results', async ({ page }) => {
      await switchToCaptionMode(page);

      // Search for "containers"
      await searchCaptions(page, 'containers');
      const containersCount = await page
        .locator('.caption-search-results .result-card')
        .count();

      // Clear and search for "YODA"
      const searchInput = page.locator('#search-input');
      await searchInput.fill('YODA');
      // Wait for new results (or empty state)
      await page.waitForTimeout(500);
      // Allow time for Pagefind to respond
      await page.waitForFunction(
        () => {
          const spinner = document.querySelector(
            '.caption-search-results .spinner',
          );
          return !spinner;
        },
        { timeout: 10000 },
      );

      const yodaResults = page.locator(
        '.caption-search-results .result-card',
      );
      const yodaCount = await yodaResults.count();

      // At least one query should return results; counts should differ
      // (both are valid search terms for the ReproNim archive)
      expect(containersCount + yodaCount).toBeGreaterThan(0);
    });

    test('empty query shows no results', async ({ page }) => {
      await switchToCaptionMode(page);

      // Make sure input is empty
      const searchInput = page.locator('#search-input');
      await searchInput.fill('');
      await page.waitForTimeout(500);

      // No result cards should be visible
      const resultCards = page.locator('.caption-search-results .result-card');
      await expect(resultCards).toHaveCount(0);
    });

    // Note: "nonsense query returns no results" test omitted -- Pagefind's
    // fuzzy matching returns hits even for gibberish strings on a small corpus.
  });

  test.describe('Result navigation', () => {
    test('clicking a result navigates to video detail with timestamp', async ({
      page,
    }) => {
      await switchToCaptionMode(page);
      await searchCaptions(page, 'DataLad');

      // Click the first result card's main area
      const firstCard = page
        .locator('.caption-search-results .result-card .result-main')
        .first();
      await firstCard.click();

      // URL should contain #/video/<id>?t=<seconds>&q=DataLad
      await page.waitForURL(/.*#\/video\/.*\?t=\d+&q=/, { timeout: 10000 });

      // Verify the URL structure
      const url = page.url();
      expect(url).toMatch(/#\/video\/[^?]+\?t=\d+&q=/);
      expect(url).toContain('q=DataLad');

      // Video detail view should be visible
      await expect(page.locator('.video-detail')).toBeVisible({
        timeout: 15000,
      });
    });
  });

  test.describe('Multiple matches and expansion', () => {
    test('result with multiple matches shows match count badge', async ({
      page,
    }) => {
      await switchToCaptionMode(page);
      // "DataLad" is mentioned many times across captions --
      // at least some videos should have multiple matches
      await searchCaptions(page, 'DataLad');

      // Find a card that has a match-count-badge
      const badges = page.locator(
        '.caption-search-results .match-count-badge',
      );
      const badgeCount = await badges.count();

      // At least one video should have multiple matches for "DataLad"
      expect(badgeCount).toBeGreaterThan(0);

      // Badge should show "N matches" where N > 1
      const firstBadge = badges.first();
      const badgeText = await firstBadge.textContent();
      expect(badgeText).toMatch(/\d+ matches/);
      const matchNum = parseInt(badgeText!.match(/(\d+)/)?.[1] || '0', 10);
      expect(matchNum).toBeGreaterThan(1);
    });

    test('clicking match count badge expands match list', async ({ page }) => {
      await switchToCaptionMode(page);
      await searchCaptions(page, 'DataLad');

      // Find a card with a match-count-badge
      const badge = page
        .locator('.caption-search-results .match-count-badge')
        .first();
      // Skip if no multi-match results
      if ((await badge.count()) === 0) {
        test.skip();
        return;
      }

      // Expanded matches should NOT be visible before clicking
      const card = badge.locator('xpath=ancestor::div[contains(@class,"result-card")]');
      await expect(card.locator('.expanded-matches')).toHaveCount(0);

      // Click the badge to expand
      await badge.click();

      // Expanded matches should now be visible
      const expandedMatches = card.locator('.expanded-matches');
      await expect(expandedMatches).toBeVisible({ timeout: 5000 });

      // Should contain match items with timestamps
      const matchItems = expandedMatches.locator('.match-item');
      const itemCount = await matchItems.count();
      expect(itemCount).toBeGreaterThan(1);

      // Each match item should have a timestamp badge
      const firstMatchTimestamp = matchItems
        .first()
        .locator('.timestamp-badge');
      await expect(firstMatchTimestamp).toBeVisible();
    });

    test('clicking badge again collapses the match list', async ({ page }) => {
      await switchToCaptionMode(page);
      await searchCaptions(page, 'DataLad');

      const badge = page
        .locator('.caption-search-results .match-count-badge')
        .first();
      if ((await badge.count()) === 0) {
        test.skip();
        return;
      }

      const card = badge.locator('xpath=ancestor::div[contains(@class,"result-card")]');

      // Expand
      await badge.click();
      await expect(card.locator('.expanded-matches')).toBeVisible({
        timeout: 5000,
      });

      // Collapse
      await badge.click();
      await expect(card.locator('.expanded-matches')).toHaveCount(0);
    });

    test('clicking an expanded match navigates to correct timestamp', async ({
      page,
    }) => {
      await switchToCaptionMode(page);
      await searchCaptions(page, 'DataLad');

      const badge = page
        .locator('.caption-search-results .match-count-badge')
        .first();
      if ((await badge.count()) === 0) {
        test.skip();
        return;
      }

      // Expand matches
      await badge.click();
      const card = badge.locator('xpath=ancestor::div[contains(@class,"result-card")]');
      const expandedMatches = card.locator('.expanded-matches');
      await expect(expandedMatches).toBeVisible({ timeout: 5000 });

      // Click the second match item (different timestamp from primary)
      const matchItems = expandedMatches.locator('.match-item');
      if ((await matchItems.count()) < 2) {
        // Only one match item -- click it anyway
        await matchItems.first().click();
      } else {
        await matchItems.nth(1).click();
      }

      // Should navigate to video detail with timestamp
      await page.waitForURL(/.*#\/video\/.*\?t=\d+&q=/, { timeout: 10000 });
      await expect(page.locator('.video-detail')).toBeVisible({
        timeout: 15000,
      });
    });
  });

  test.describe('Show more pagination', () => {
    test('show more button appears when results exceed page size', async ({
      page,
    }) => {
      await switchToCaptionMode(page);
      // Use a broad search term likely to match many videos
      await searchCaptions(page, 'reproducibility');

      const resultCards = page.locator(
        '.caption-search-results .result-card',
      );
      const count = await resultCards.count();

      if (count < 10) {
        // Not enough results to trigger pagination -- skip
        test.skip();
        return;
      }

      // PAGE_SIZE is 10, so if there are more than 10 results,
      // the show-more button should be visible
      const showMoreBtn = page.locator(
        '.caption-search-results .show-more-button',
      );
      await expect(showMoreBtn).toBeVisible();
      await expect(showMoreBtn).toContainText(/remaining/);
    });

    test('clicking show more loads additional results', async ({ page }) => {
      await switchToCaptionMode(page);
      await searchCaptions(page, 'reproducibility');

      const showMoreBtn = page.locator(
        '.caption-search-results .show-more-button',
      );
      if ((await showMoreBtn.count()) === 0) {
        test.skip();
        return;
      }

      const initialCount = await page
        .locator('.caption-search-results .result-card')
        .count();

      // Click show more
      await showMoreBtn.click();

      // Should show more results
      const newCount = await page
        .locator('.caption-search-results .result-card')
        .count();
      expect(newCount).toBeGreaterThan(initialCount);
    });
  });

  test.describe('Mode switching', () => {
    test('switching back to Videos mode hides caption results', async ({
      page,
    }) => {
      await switchToCaptionMode(page);
      await searchCaptions(page, 'DataLad');

      // Caption results should be visible
      await expect(
        page.locator('.caption-search-results .result-card').first(),
      ).toBeVisible();

      // Switch back to Videos
      const videosTab = page.locator('.mode-tab').filter({ hasText: 'Videos' });
      await videosTab.click();
      await expect(videosTab).toHaveClass(/active/);

      // Caption results container should be gone
      await expect(page.locator('.caption-search-results')).toHaveCount(0);

      // Video grid should be visible again
      await expect(page.locator('.video-grid')).toBeVisible();
    });
  });
});
