import { defineConfig, devices } from '@playwright/test';

const PORT = 4173;
const baseURL = `http://localhost:${PORT}`;

// The Chromatic snapshot suite (tests/chromatic/). It shares playwright.config.ts's retries,
// reporter kind and trace setting, so a page renders the same under both; the test directory, the
// projects and the web server are its own.
export default defineConfig({
  testDir: './tests/chromatic',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report-chromatic', open: 'never' }],
  ],
  // outputDir is left alone on purpose: it defaults to test-results/, which is where the Chromatic
  // fixture writes its archives and where build-archive-storybook looks for them.
  use: { baseURL, trace: 'on-first-retry' },
  // One Desktop Chrome project, deliberately. Chromatic names a Playwright archive by the test's
  // file, describe and title, never its project, so several projects write over one story file.
  // Viewports are set per test instead (tests/chromatic/viewports.ts), never as projects.
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    // Builds the web UI and serves it inside the fixture archives, laid out as a deployed archive
    // is; the script says why this is not `vite preview`.
    command: `bash scripts/serve-chromatic-fixtures.sh ${PORT}`,
    url: `${baseURL}/archive/web/`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
