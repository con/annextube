import { test, expect } from '@playwright/test';

test('video seeking functionality', async ({ page }) => {
  console.log('Navigating to video page...');
  await page.goto('http://0.0.0.0:8080/web/#/video/26S5SKx4NmI');

  // Wait for video to load
  console.log('Waiting for video element...');
  const video = page.locator('video');
  await video.waitFor({ timeout: 10000 });

  // Wait a bit for video to be ready
  await page.waitForTimeout(2000);

  // Check video properties
  const videoInfo = await page.evaluate(() => {
    const vid = document.querySelector('video');
    if (!vid) return null;
    return {
      paused: vid.paused,
      duration: vid.duration,
      currentTime: vid.currentTime,
      readyState: vid.readyState,
      networkState: vid.networkState,
      src: vid.currentSrc,
      controls: vid.controls,
      width: vid.clientWidth,
      height: vid.clientHeight,
      seekable: vid.seekable.length > 0 ? {
        ranges: vid.seekable.length,
        start: vid.seekable.start(0),
        end: vid.seekable.end(0)
      } : null,
      buffered: vid.buffered.length > 0 ? {
        ranges: vid.buffered.length,
        start: vid.buffered.start(0),
        end: vid.buffered.end(0)
      } : null
    };
  });

  console.log('Video info:', JSON.stringify(videoInfo, null, 2));

  // Try programmatic seeking
  console.log('\nTrying programmatic seek to 30 seconds...');
  const seekResult = await page.evaluate(() => {
    const vid = document.querySelector('video');
    if (!vid) return { success: false, error: 'No video element' };

    const initialTime = vid.currentTime;
    try {
      vid.currentTime = 30;
      return {
        success: true,
        initialTime,
        requestedTime: 30,
        actualTime: vid.currentTime,
        seekable: vid.seekable.length > 0
      };
    } catch (err) {
      return { success: false, error: (err as Error).message };
    }
  });

  console.log('Seek result:', JSON.stringify(seekResult, null, 2));

  // Wait and check if seek actually happened
  await page.waitForTimeout(2000);

  const finalInfo = await page.evaluate(() => {
    const vid = document.querySelector('video');
    if (!vid) return null;
    return {
      currentTime: vid.currentTime,
      duration: vid.duration,
      seekable: vid.seekable.length > 0 ? {
        start: vid.seekable.start(0),
        end: vid.seekable.end(0)
      } : null
    };
  });

  console.log('\nFinal state:', JSON.stringify(finalInfo, null, 2));

  // Take a screenshot for debugging
  await page.screenshot({ path: '/tmp/video-seeking-test.png', fullPage: true });
  console.log('Screenshot saved to /tmp/video-seeking-test.png');
});
