import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Test archive path for E2E workflow tests.
// Requires an archive with both downloaded and metadata-only videos.
// See tests/e2e/archive-workflow.spec.ts for expected fixture layout.
const TEST_ARCHIVE_DIR = path.resolve(
  __dirname,
  '../test-archives/archive-workflow-fixture'
);
const ARCHIVE_SERVER_PORT = 8090;

// Check if archive exists (needed for archive-workflow tests)
const archiveExists = fs.existsSync(path.join(TEST_ARCHIVE_DIR, '.annextube', 'config.toml'));

// Archive server projects — only included when the test archive fixture exists
const archiveProjects = archiveExists ? [
  {
    name: 'archive-chromium',
    use: {
      ...devices['Desktop Chrome'],
      baseURL: `http://localhost:${ARCHIVE_SERVER_PORT}`,
    },
    testMatch: '**/archive-workflow*',
  },
  {
    name: 'archive-firefox',
    use: {
      ...devices['Desktop Firefox'],
      baseURL: `http://localhost:${ARCHIVE_SERVER_PORT}`,
    },
    testMatch: '**/archive-workflow*',
  },
] : [];

// Archive web server — only started when the test archive fixture exists
const archiveWebServer = archiveExists ? [
  {
    command: `${path.resolve(__dirname, '../.venv/bin/annextube')} serve --output-dir "${TEST_ARCHIVE_DIR}" --port ${ARCHIVE_SERVER_PORT} --no-watch`,
    url: `http://localhost:${ARCHIVE_SERVER_PORT}/web/`,
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
] : [];

export default defineConfig({
  testDir: './tests/e2e',

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  reporter: 'html',

  use: {
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
  },

  // Configure projects for major browsers
  projects: [
    // Dev server projects (existing mock-data tests)
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:5173',
      },
      testIgnore: '**/archive-workflow*',
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        baseURL: 'http://localhost:5173',
      },
      testIgnore: '**/archive-workflow*',
    },
    // Archive server projects (real archive E2E tests — requires test fixture)
    ...archiveProjects,
  ],

  // Run servers before starting the tests
  webServer: [
    // Vite dev server for mock-data tests
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
    },
    // annextube serve for real archive E2E tests (when fixture exists)
    ...archiveWebServer,
  ],
});
