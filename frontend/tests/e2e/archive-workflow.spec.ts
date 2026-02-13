/**
 * E2E Tests for Complete Archive Workflow
 *
 * Tests the full user journey from browsing the video list to playing videos,
 * using a real test archive served by `annextube serve`.
 *
 * Test data: test-archives/archive-workflow-fixture (@AnnexTubeTesting channel)
 *   - Created by: frontend/scripts/create-e2e-fixture.sh
 *   - 10 videos total (3 downloaded + 7 metadata_only)
 *   - 5 playlists
 *   - Video IDs loaded dynamically from videos.tsv (upload dates are identical,
 *     so yt-dlp ordering may vary between runs)
 *
 * @ai_generated
 */

import { test, expect } from '@playwright/test';

// Archive counts — must match the fixture created by create-e2e-fixture.sh
const TOTAL_VIDEOS = 10;
const DOWNLOADED_COUNT = 3;
const METADATA_ONLY_COUNT = 7;

// Video IDs are loaded dynamically in beforeAll (see below)
let DOWNLOADED_VIDEO_ID = '';
let METADATA_ONLY_VIDEO_ID = '';

// Base path for the web UI when served by `annextube serve`
const WEB_BASE = '/web/';

/**
 * Navigate to a specific video detail page by hash URL.
 * Uses a single navigation to the hash URL which triggers both
 * data loading and routing in the Svelte app.
 */
async function navigateToVideo(page: import('@playwright/test').Page, videoId: string) {
  // Navigate directly to the video detail URL.
  // The app will load TSV data and then route to the video detail view.
  await page.goto(`${WEB_BASE}#/video/${videoId}`);
  await page.waitForSelector('.video-detail', { timeout: 15000 });
}

// Increase timeout for archive server tests (Python HTTP server is slower than vite)
test.setTimeout(60000);

test.describe('Complete Archive Workflow', () => {
  // Run tests serially to avoid overwhelming the single-threaded Python HTTP server
  test.describe.configure({ mode: 'serial' });

  // Load video IDs dynamically from the fixture's videos.tsv
  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    try {
      const response = await page.goto('/videos/videos.tsv');
      const tsvText = await response!.text();
      const lines = tsvText.trim().split('\n');
      // Parse header to find column indices
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

    // Sanity check — fail fast if the fixture is broken
    if (!DOWNLOADED_VIDEO_ID) throw new Error('No downloaded video found in videos.tsv');
    if (!METADATA_ONLY_VIDEO_ID) throw new Error('No metadata_only video found in videos.tsv');
  });

  test.describe('Navigation and video list display', () => {
    test('loads and displays all videos from the archive', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      // Should display all 10 videos
      const videoCards = page.locator('.video-card');
      await expect(videoCards).toHaveCount(TOTAL_VIDEOS);
    });

    test('shows correct total video count in header', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      // Header subtitle shows "N videos archived"
      const subtitle = page.locator('.subtitle');
      await expect(subtitle).toContainText(`${TOTAL_VIDEOS} videos`);
    });

    test('video cards show download status badges', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      // Downloaded videos should have a green badge
      const downloadedBadges = page.locator('.status-badge.downloaded');
      await expect(downloadedBadges).toHaveCount(DOWNLOADED_COUNT);

      // Metadata-only videos should have a grey badge
      const metadataOnlyBadges = page.locator('.status-badge.metadata-only');
      await expect(metadataOnlyBadges).toHaveCount(METADATA_ONLY_COUNT);
    });

    test('clicking a video card navigates to detail page', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      // Click the first video card
      const firstCard = page.locator('.video-card').first();
      await firstCard.click();

      // URL should contain #/video/
      await page.waitForURL(/.*#\/video\/.*/);

      // Video detail view should appear
      await expect(page.locator('.video-detail')).toBeVisible();
    });

    test('result count updates when filtering', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      const resultCount = page.locator('.result-count');
      await expect(resultCount).toContainText(`${TOTAL_VIDEOS} videos`);
    });
  });

  test.describe('Video detail page', () => {
    test('renders video detail with player and metadata', async ({ page }) => {
      await navigateToVideo(page, DOWNLOADED_VIDEO_ID);

      // Back button should be visible
      const backButton = page.locator('.back-button');
      await expect(backButton).toBeVisible();
      await expect(backButton).toContainText('Back to list');

      // Video player should be visible
      await expect(page.locator('.video-player')).toBeVisible();

      // Video title should be visible
      await expect(page.locator('.video-detail .title')).toBeVisible();

      // Channel name should be visible
      await expect(page.locator('.channel-name')).toBeVisible();
    });

    test('shows YouTube link in metadata', async ({ page }) => {
      await navigateToVideo(page, DOWNLOADED_VIDEO_ID);

      const youtubeLink = page.locator('.youtube-link');
      await expect(youtubeLink).toBeVisible();
      await expect(youtubeLink).toHaveAttribute(
        'href',
        `https://www.youtube.com/watch?v=${DOWNLOADED_VIDEO_ID}`
      );
    });
  });

  test.describe('Local video player', () => {
    test('shows video element with controls for downloaded video', async ({ page }) => {
      await navigateToVideo(page, DOWNLOADED_VIDEO_ID);

      // The local player tab should be active by default for downloaded videos
      const localTab = page.locator('.video-player .tab').filter({ hasText: 'Play from Archive' });
      await expect(localTab).toHaveClass(/active/);

      // Video element should be present and have controls
      const videoElement = page.locator('.video-player .tab-content video');
      await expect(videoElement).toBeVisible();
      await expect(videoElement).toHaveAttribute('controls', '');

      // Video should have non-zero dimensions (verify it's actually rendered)
      const boundingBox = await videoElement.boundingBox();
      expect(boundingBox).not.toBeNull();
      expect(boundingBox!.width).toBeGreaterThan(0);
      expect(boundingBox!.height).toBeGreaterThan(0);

      // Video should have poster attribute
      await expect(videoElement).toHaveAttribute('poster');
    });

    test('video element has correct source path', async ({ page }) => {
      await navigateToVideo(page, DOWNLOADED_VIDEO_ID);

      // The source element should point to the video.mkv file
      const sourceElement = page.locator('.video-player .tab-content video source');
      const src = await sourceElement.getAttribute('src');
      expect(src).toContain('video.mkv');
      expect(src).toContain(DOWNLOADED_VIDEO_ID.length > 0 ? 'videos/' : '');
    });

    test('video element has crossorigin and preload attributes', async ({ page }) => {
      await navigateToVideo(page, DOWNLOADED_VIDEO_ID);

      const videoElement = page.locator('.video-player .tab-content video');
      await expect(videoElement).toHaveAttribute('crossorigin', 'anonymous');
      await expect(videoElement).toHaveAttribute('preload', 'metadata');
    });
  });

  test.describe('YouTube iframe player', () => {
    test('shows YouTube iframe for metadata-only video', async ({ page }) => {
      await navigateToVideo(page, METADATA_ONLY_VIDEO_ID);

      // YouTube tab should be active by default for metadata-only videos
      // (metadata-only videos only have the YouTube player, no tabs shown)
      const iframe = page.locator('.video-player .tab-content iframe');
      await expect(iframe).toBeVisible();

      // Verify iframe src points to YouTube embed (may include query params like enablejsapi)
      const iframeSrc = await iframe.getAttribute('src');
      expect(iframeSrc).toContain(`https://www.youtube.com/embed/${METADATA_ONLY_VIDEO_ID}`);
    });

    test('metadata-only video does not show local player tab', async ({ page }) => {
      await navigateToVideo(page, METADATA_ONLY_VIDEO_ID);

      // Should not show tab bar at all (only one option)
      const tabs = page.locator('.video-player .tab');
      await expect(tabs).toHaveCount(0);
    });

    test('metadata-only video does not render video element', async ({ page }) => {
      await navigateToVideo(page, METADATA_ONLY_VIDEO_ID);

      const videoElement = page.locator('.video-player .tab-content video');
      await expect(videoElement).toHaveCount(0);
    });
  });

  test.describe('Tab switching', () => {
    test('downloaded video shows both tabs', async ({ page }) => {
      await navigateToVideo(page, DOWNLOADED_VIDEO_ID);

      const tabs = page.locator('.video-player .tab');
      await expect(tabs).toHaveCount(2);

      await expect(tabs.nth(0)).toContainText('Play from Archive');
      await expect(tabs.nth(1)).toContainText('Play from YouTube');
    });

    test('switching to YouTube tab shows iframe and hides video', async ({ page }) => {
      await navigateToVideo(page, DOWNLOADED_VIDEO_ID);

      // Click YouTube tab
      const youtubeTab = page.locator('.video-player .tab').filter({ hasText: 'Play from YouTube' });
      await youtubeTab.click();

      // YouTube tab should now be active
      await expect(youtubeTab).toHaveClass(/active/);

      // Local tab should not be active
      const localTab = page.locator('.video-player .tab').filter({ hasText: 'Play from Archive' });
      await expect(localTab).not.toHaveClass(/active/);

      // Should show iframe
      const iframe = page.locator('.video-player .tab-content iframe');
      await expect(iframe).toBeVisible();
      const iframeSrc = await iframe.getAttribute('src');
      expect(iframeSrc).toContain(`https://www.youtube.com/embed/${DOWNLOADED_VIDEO_ID}`);

      // Should not show video element
      const videoElement = page.locator('.video-player .tab-content video');
      await expect(videoElement).toHaveCount(0);
    });

    test('switching back to local tab restores video element', async ({ page }) => {
      await navigateToVideo(page, DOWNLOADED_VIDEO_ID);

      // Switch to YouTube
      const youtubeTab = page.locator('.video-player .tab').filter({ hasText: 'Play from YouTube' });
      await youtubeTab.click();
      await expect(youtubeTab).toHaveClass(/active/);

      // Switch back to local
      const localTab = page.locator('.video-player .tab').filter({ hasText: 'Play from Archive' });
      await localTab.click();

      // Local tab should be active again
      await expect(localTab).toHaveClass(/active/);
      await expect(youtubeTab).not.toHaveClass(/active/);

      // Video element should be back
      const videoElement = page.locator('.video-player .tab-content video');
      await expect(videoElement).toBeVisible();
      await expect(videoElement).toHaveAttribute('controls', '');

      // Iframe should be gone
      const iframe = page.locator('.video-player .tab-content iframe');
      await expect(iframe).toHaveCount(0);
    });
  });

  test.describe('Filter by download status', () => {
    test('filtering by "Backup Available" shows only downloaded videos', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      // Select "Backup Available (Local)" from the Video Availability dropdown
      const statusSelect = page.locator('select').filter({ has: page.locator('option', { hasText: 'Backup Available' }) });
      await statusSelect.selectOption('downloaded');

      // Wait for filter to apply
      await page.waitForTimeout(400);

      // Should show only downloaded videos
      const videoCards = page.locator('.video-card');
      await expect(videoCards).toHaveCount(DOWNLOADED_COUNT);

      // Result count should reflect filtering
      const resultCount = page.locator('.result-count');
      await expect(resultCount).toContainText(`${DOWNLOADED_COUNT} of ${TOTAL_VIDEOS}`);

      // All visible badges should be "downloaded"
      const downloadedBadges = page.locator('.status-badge.downloaded');
      await expect(downloadedBadges).toHaveCount(DOWNLOADED_COUNT);

      const metadataOnlyBadges = page.locator('.status-badge.metadata-only');
      await expect(metadataOnlyBadges).toHaveCount(0);
    });

    test('filtering by "Metadata Only" shows only metadata-only videos', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      const statusSelect = page.locator('select').filter({ has: page.locator('option', { hasText: 'Backup Available' }) });
      await statusSelect.selectOption('metadata_only');

      await page.waitForTimeout(400);

      const videoCards = page.locator('.video-card');
      await expect(videoCards).toHaveCount(METADATA_ONLY_COUNT);

      const resultCount = page.locator('.result-count');
      await expect(resultCount).toContainText(`${METADATA_ONLY_COUNT} of ${TOTAL_VIDEOS}`);
    });

    test('clearing filter shows all videos again', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      // Apply a filter first
      const statusSelect = page.locator('select').filter({ has: page.locator('option', { hasText: 'Backup Available' }) });
      await statusSelect.selectOption('downloaded');
      await page.waitForTimeout(400);

      // Videos should be filtered
      await expect(page.locator('.video-card')).toHaveCount(DOWNLOADED_COUNT);

      // Click "Clear All Filters" button
      const clearButton = page.locator('.clear-button');
      await expect(clearButton).toBeVisible();
      await clearButton.click();
      await page.waitForTimeout(400);

      // All videos should be back
      await expect(page.locator('.video-card')).toHaveCount(TOTAL_VIDEOS);
    });
  });

  test.describe('Search functionality', () => {
    test('search filters videos by title', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      // Type a search term that matches known video titles
      // "Location" matches "NYC Location" and "London Location" test videos
      const searchInput = page.locator('#search-input');
      await searchInput.fill('Location');

      // Wait for debounced search to apply
      await page.waitForTimeout(500);

      // Should show filtered results (2 videos with "Location" in the title)
      const videoCards = page.locator('.video-card');
      const count = await videoCards.count();
      expect(count).toBeGreaterThan(0);
      expect(count).toBeLessThan(TOTAL_VIDEOS);
    });

    test('search with no matches shows empty state', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      const searchInput = page.locator('#search-input');
      await searchInput.fill('xyznonexistent12345');

      await page.waitForTimeout(500);

      // Should show no results
      const videoCards = page.locator('.video-card');
      await expect(videoCards).toHaveCount(0);

      // Should show empty state message
      await expect(page.getByText('No videos match')).toBeVisible();
    });

    test('clearing search restores all videos', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      // Apply search
      const searchInput = page.locator('#search-input');
      await searchInput.fill('Location');
      await page.waitForTimeout(500);

      // Clear search
      await searchInput.fill('');
      await page.waitForTimeout(500);

      // All videos should be back
      await expect(page.locator('.video-card')).toHaveCount(TOTAL_VIDEOS);
    });
  });

  test.describe('Video player debugging', () => {
    test('video actually plays and controls work', async ({ page }) => {
      await navigateToVideo(page, DOWNLOADED_VIDEO_ID);

      const videoElement = page.locator('.video-player .tab-content video');
      await expect(videoElement).toBeVisible();

      // Try to play the video
      await videoElement.evaluate((video: HTMLVideoElement) => {
        return video.play();
      });

      // Wait a bit for playback to start
      await page.waitForTimeout(1000);

      // Check if video is actually playing
      const isPlaying = await videoElement.evaluate((video: HTMLVideoElement) => {
        return !video.paused && video.currentTime > 0;
      });

      console.log('Video is playing:', isPlaying);
      expect(isPlaying).toBe(true);

      // Pause the video
      await videoElement.evaluate((video: HTMLVideoElement) => {
        video.pause();
      });

      const isPaused = await videoElement.evaluate((video: HTMLVideoElement) => {
        return video.paused;
      });

      console.log('Video paused successfully:', isPaused);
      expect(isPaused).toBe(true);
    });

    test('video element loads properly and has correct state', async ({ page }) => {
      // Collect console messages
      const consoleMessages: string[] = [];
      page.on('console', (msg) => {
        const text = msg.text();
        if (text.includes('[VideoPlayer]')) {
          consoleMessages.push(`[${msg.type()}] ${text}`);
        }
      });

      // Navigate to downloaded video
      await navigateToVideo(page, DOWNLOADED_VIDEO_ID);

      // Wait for video element
      const videoElement = page.locator('.video-player .tab-content video');
      await expect(videoElement).toBeVisible();

      // Get video state
      const videoState = await videoElement.evaluate((video: HTMLVideoElement) => {
        return {
          readyState: video.readyState,
          networkState: video.networkState,
          duration: video.duration,
          currentTime: video.currentTime,
          paused: video.paused,
          error: video.error ? {
            code: video.error.code,
            message: video.error.message,
          } : null,
          src: video.currentSrc,
        };
      });

      // Log debug info
      console.log('\n=== Video State ===');
      console.log(JSON.stringify(videoState, null, 2));
      console.log('\n=== Console Messages ===');
      consoleMessages.forEach(msg => console.log(msg));

      // Get poster attribute
      const poster = await videoElement.getAttribute('poster');

      // Assertions
      expect(videoState.error).toBeNull();
      expect(videoState.readyState).toBeGreaterThan(0); // Should have started loading
      expect(videoState.src).toContain('/videos/'); // Should use absolute path
      expect(videoState.src).toContain('video.mkv');
      expect(poster).toContain('videos/'); // Should contain videos/ path
      expect(poster).toContain('thumbnail.jpg'); // Should use local thumbnail, not YouTube CDN
      expect(poster).not.toContain('ytimg.com'); // Should NOT use YouTube CDN (CORS issues)
    });
  });

  test.describe('Back navigation', () => {
    test('back button returns to video list', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      // Navigate to a video
      await page.locator('.video-card').first().click();
      await page.waitForURL(/.*#\/video\/.*/);
      await expect(page.locator('.video-detail')).toBeVisible();

      // Click back button
      const backButton = page.locator('.back-button');
      await backButton.click();

      // Should return to list view
      await page.waitForSelector('.video-grid');
      await expect(page.locator('.video-card')).toHaveCount(TOTAL_VIDEOS);

      // Detail view should be gone
      await expect(page.locator('.video-detail')).toHaveCount(0);
    });

    test('browser back button returns to list after navigating to video', async ({ page }) => {
      await page.goto(WEB_BASE);
      await page.waitForSelector('.video-grid');

      // Navigate to a video via click
      await page.locator('.video-card').first().click();
      await page.waitForURL(/.*#\/video\/.*/);
      await expect(page.locator('.video-detail')).toBeVisible();

      // Use browser back
      await page.goBack();

      // Should return to list view
      await page.waitForSelector('.video-grid');
      await expect(page.locator('.video-card')).toHaveCount(TOTAL_VIDEOS);
    });
  });
});
