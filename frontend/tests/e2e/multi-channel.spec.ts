/**
 * E2E Test for Multi-Channel Navigation
 *
 * Tests multi-channel mode in the web interface:
 * - Channel overview detection and display
 * - Channel drill-down navigation
 * - Breadcrumb navigation
 * - Single-channel fallback
 *
 * Uses Playwright route() API to intercept requests and serve mock data.
 *
 * @ai_generated
 */

import { test, expect } from '@playwright/test';

const CHANNELS_TSV =
  'channel_id\ttitle\tcustom_url\tdescription\tsubscriber_count\tvideo_count\tplaylist_count\ttotal_videos_archived\tfirst_video_date\tlast_video_date\tlast_sync\tchannel_dir\n' +
  'UC001\tAlpha Channel\t@AlphaChannel\tFirst test channel\t50000\t100\t5\t95\t2020-01-01\t2024-06-01\t2024-06-15T00:00:00Z\tch-alphachannel\n' +
  'UC002\tBeta Channel\t@BetaChannel\tSecond test channel\t25000\t50\t2\t48\t2021-03-01\t2024-05-15\t2024-06-15T00:00:00Z\tch-betachannel';

const ALPHA_CHANNEL_JSON = JSON.stringify({
  channel_id: 'UC001',
  name: 'Alpha Channel',
  custom_url: '@AlphaChannel',
  description: 'First test channel',
  subscriber_count: 50000,
  video_count: 100,
  channel_dir: 'ch-alphachannel',
  archive_stats: {
    total_videos_archived: 95,
    first_video_date: '2020-01-01',
    last_video_date: '2024-06-01',
    total_duration_seconds: 360000,
    total_size_bytes: 5368709120,
  },
});

const BETA_CHANNEL_JSON = JSON.stringify({
  channel_id: 'UC002',
  name: 'Beta Channel',
  custom_url: '@BetaChannel',
  description: 'Second test channel',
  subscriber_count: 25000,
  video_count: 50,
  channel_dir: 'ch-betachannel',
  archive_stats: {
    total_videos_archived: 48,
    first_video_date: '2021-03-01',
    last_video_date: '2024-05-15',
    total_duration_seconds: 120000,
    total_size_bytes: 2147483648,
  },
});

const ALPHA_VIDEOS_TSV =
  'video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\tduration\tview_count\tlike_count\tcomment_count\tthumbnail_url\tdownload_status\tsource_url\tpath\n' +
  'V001\tAlpha Video One\tUC001\tAlpha Channel\t2024-01-01T00:00:00\t300\t1000\t50\t10\thttps://example.com/thumb1.jpg\ttracked\thttps://www.youtube.com/watch?v=V001\talpha-video-one\n' +
  'V002\tAlpha Video Two\tUC001\tAlpha Channel\t2024-02-01T00:00:00\t600\t2000\t100\t20\thttps://example.com/thumb2.jpg\tdownloaded\thttps://www.youtube.com/watch?v=V002\talpha-video-two';

const SINGLE_CHANNEL_VIDEOS_TSV =
  'video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\tduration\tview_count\tlike_count\tcomment_count\tthumbnail_url\tdownload_status\tsource_url\tpath\n' +
  'S001\tSingle Channel Video\tUC999\tSolo Channel\t2024-01-01T00:00:00\t300\t500\t25\t5\thttps://example.com/thumb-s.jpg\ttracked\thttps://www.youtube.com/watch?v=S001\tsolo-video';

/**
 * Set up route interception for multi-channel mode.
 */
async function setupMultiChannelRoutes(page: any) {
  await page.route('**/*', async (route: any) => {
    const url = route.request().url();

    // channels.tsv HEAD and GET
    if (url.includes('channels.tsv')) {
      const method = route.request().method();
      if (method === 'HEAD') {
        await route.fulfill({ status: 200 });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'text/tab-separated-values',
          body: CHANNELS_TSV,
        });
      }
      return;
    }

    // channel.json for each channel
    if (url.includes('ch-alphachannel/channel.json')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ALPHA_CHANNEL_JSON,
      });
      return;
    }
    if (url.includes('ch-betachannel/channel.json')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: BETA_CHANNEL_JSON,
      });
      return;
    }

    // Channel avatars - none exist
    if (url.includes('channel_avatar')) {
      await route.fulfill({ status: 404 });
      return;
    }

    // Alpha channel videos
    if (url.includes('ch-alphachannel/videos/videos.tsv')) {
      await route.fulfill({
        status: 200,
        contentType: 'text/tab-separated-values',
        body: ALPHA_VIDEOS_TSV,
      });
      return;
    }

    // Playlists - 404
    if (url.includes('playlists/playlists.tsv')) {
      await route.fulfill({ status: 404 });
      return;
    }

    // Single-channel markers should fail in multi-channel mode
    if (url.includes('videos/videos.tsv') && !url.includes('ch-')) {
      await route.fulfill({ status: 404 });
      return;
    }
    if (url.includes('channel.json') && !url.includes('ch-')) {
      await route.fulfill({ status: 404 });
      return;
    }

    // Let everything else through (HTML, JS, CSS, etc.)
    await route.fallback();
  });
}

test.describe('Multi-Channel Navigation', () => {
  test('displays channel overview in multi-channel mode', async ({ page }) => {
    await setupMultiChannelRoutes(page);
    await page.goto('/');

    // Wait for channels to load
    await page.waitForSelector('.channel-card', { timeout: 10000 });

    // Should show 2 channel cards
    const channelCards = page.locator('.channel-card');
    await expect(channelCards).toHaveCount(2);

    // Channel names visible
    await expect(page.getByText('Alpha Channel')).toBeVisible();
    await expect(page.getByText('Beta Channel')).toBeVisible();
  });

  test('channel cards show handles', async ({ page }) => {
    await setupMultiChannelRoutes(page);
    await page.goto('/');
    await page.waitForSelector('.channel-card', { timeout: 10000 });

    // Handles should be displayed (without @ prefix in the URL display)
    await expect(page.getByText('@AlphaChannel')).toBeVisible();
    await expect(page.getByText('@BetaChannel')).toBeVisible();
  });

  test('channel cards show video stats', async ({ page }) => {
    await setupMultiChannelRoutes(page);
    await page.goto('/');
    await page.waitForSelector('.channel-card', { timeout: 10000 });

    // Stats should be visible
    await expect(page.locator('.stat-value').first()).toBeVisible();
  });

  test('subtitle shows channel count', async ({ page }) => {
    await setupMultiChannelRoutes(page);
    await page.goto('/');
    await page.waitForSelector('.channel-card', { timeout: 10000 });

    // Header should show "2 channels in collection"
    await expect(page.locator('.subtitle')).toContainText('2 channels');
  });

  test('clicking channel shows video list with breadcrumb', async ({ page }) => {
    await setupMultiChannelRoutes(page);
    await page.goto('/');
    await page.waitForSelector('.channel-card', { timeout: 10000 });

    // Click first channel
    await page.locator('.channel-card').first().click();

    // Wait for videos to load
    await page.waitForSelector('.video-card', { timeout: 10000 });

    // Should show breadcrumb
    const breadcrumb = page.locator('.breadcrumb');
    await expect(breadcrumb).toBeVisible();
    await expect(breadcrumb).toContainText('Channels');

    // Should show 2 videos
    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(2);
  });

  test('breadcrumb navigates back to channels', async ({ page }) => {
    await setupMultiChannelRoutes(page);
    await page.goto('/');
    await page.waitForSelector('.channel-card', { timeout: 10000 });

    // Navigate to channel
    await page.locator('.channel-card').first().click();
    await page.waitForSelector('.video-card', { timeout: 10000 });

    // Click "Channels" breadcrumb
    await page.locator('.breadcrumb button').first().click();

    // Should be back to channel overview
    await page.waitForSelector('.channel-card', { timeout: 10000 });
    const channelCards = page.locator('.channel-card');
    await expect(channelCards).toHaveCount(2);
  });
});

test.describe('Single-Channel Fallback', () => {
  test('shows video list when channels.tsv absent', async ({ page }) => {
    // Set up single-channel routes
    await page.route('**/*', async (route) => {
      const url = route.request().url();

      // channels.tsv should not exist
      if (url.includes('channels.tsv')) {
        await route.fulfill({ status: 404 });
        return;
      }

      // Single-channel videos.tsv HEAD and GET
      if (url.includes('videos/videos.tsv')) {
        const method = route.request().method();
        if (method === 'HEAD') {
          await route.fulfill({ status: 200 });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'text/tab-separated-values',
            body: SINGLE_CHANNEL_VIDEOS_TSV,
          });
        }
        return;
      }

      // channel.json marker for single-channel detection
      if (url.includes('channel.json')) {
        await route.fulfill({ status: 404 });
        return;
      }

      // playlists
      if (url.includes('playlists/playlists.tsv')) {
        await route.fulfill({ status: 404 });
        return;
      }

      await route.fallback();
    });

    await page.goto('/');

    // Should show video list directly (no channel overview)
    await page.waitForSelector('.video-card', { timeout: 10000 });

    const videoCards = page.locator('.video-card');
    await expect(videoCards).toHaveCount(1);
    await expect(page.getByText('Single Channel Video')).toBeVisible();

    // No breadcrumb in single-channel mode
    await expect(page.locator('.breadcrumb')).toHaveCount(0);
  });
});
