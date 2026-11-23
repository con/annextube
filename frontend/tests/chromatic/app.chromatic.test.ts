import { test, expect } from '@chromatic-com/playwright';
import { expectNoHorizontalOverflow, forEachViewport } from './viewports';

// One forEachViewport call per page state. The Chromatic fixture archives the page after each
// test body; the assertions are there so a capture of the wrong state fails here, by name, rather
// than turning up as a diff.
//
// Each state is a fixture archive under tests/chromatic/fixtures/, served with the built web UI
// in its web/ folder (scripts/serve-chromatic-fixtures.sh), so what renders is the real boot
// path reading real files, with no stubbed route and no test-only code in the app.

// The UI prints ages relative to now ("11 months ago"); with the clock pinned they stay put.
test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date('2025-01-01T00:00:00Z'));
});

forEachViewport(test, 'Archive - video list', async ({ page }) => {
  await page.goto('/archive/web/');
  await expect(page.locator('.video-card')).toHaveCount(4);
  await expect(page.locator('.subtitle')).toContainText('4 videos archived');
  await expectNoHorizontalOverflow(page);
});

forEachViewport(test, 'Archive - video detail', async ({ page }) => {
  // The one fixture video with a local file, so the page shows the local player and never
  // embeds YouTube, which a snapshot cannot depend on.
  await page.goto('/archive/web/#/video/FIXTURE0001');
  await expect(page.locator('.video-detail video')).toBeVisible();
  await expect(page.locator('.comments-section h3')).toContainText(
    '3 Comments',
  );
  await expectNoHorizontalOverflow(page);
});

forEachViewport(test, 'Archive - load error', async ({ page }) => {
  // A web UI with no archive around it.
  await page.goto('/empty/web/');
  await expect(page.getByText('Error loading videos')).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

forEachViewport(test, 'Collection - channels overview', async ({ page }) => {
  await page.goto('/collection/web/');
  await expect(page.locator('.channel-card')).toHaveCount(2);
  await expect(page.locator('.subtitle')).toContainText(
    '2 channels in collection',
  );
  await expectNoHorizontalOverflow(page);
});
