# E2E Tests for Frontend

End-to-end tests using Playwright to verify the frontend works correctly with a real archive.

## Setup

1. **Install Playwright browsers** (one-time):
   ```bash
   npx playwright install
   ```

2. **Setup test archive** (creates symlinks to test fixtures):
   ```bash
   ./tests/e2e/setup-test-archive.sh
   ```

## Running Tests

```bash
npm run test:e2e
```

This will:
- Start the dev server on http://localhost:5173
- Run all E2E tests against the test archive
- Generate an HTML report

## Test Fixtures

The test archive (`tests/fixtures/test-archive/`) contains:
- **3 videos**: TEST001 (Alpha), TEST002 (Beta), TEST003 (Another Channel)
- **1 playlist**: "Test Playlist" with 2 videos (TEST001, TEST002)
- **2 channels**: "Test Channel" and "Another Channel"

This minimal dataset allows for predictable testing of:
- Video list loading
- Search functionality
- Filtering (channels, playlists, date range, status)
- Sorting (views, date, duration, title)
- Video detail view navigation
- URL state preservation

## Test Coverage

The E2E test suite (`archive-browser.spec.ts`) verifies:

1. **Video List Loading**: All videos display correctly
2. **Result Counts**: Shows correct "X videos" count
3. **Search**: Filters videos by search query
4. **Channel Filter**: Filters by selected channel
5. **Playlist Filter**: Shows correct video count in playlist, filters correctly
6. **Sorting**: Orders videos by views (descending)
7. **Clear Filters**: Button appears and resets all filters
8. **Video Detail**: Clicking video navigates to detail view
9. **Back Navigation**: Returning from detail view to list
10. **URL State**: Filters persist in URL and across page reloads

## Adding New Tests

To add new E2E tests:

1. Add test cases to `archive-browser.spec.ts` or create new spec files in `tests/e2e/`
2. If needed, extend the test fixtures in `tests/fixtures/test-archive/`
3. Run `./tests/e2e/setup-test-archive.sh` to update symlinks
4. Run `npm run test:e2e` to verify

## CI Integration

For CI environments, ensure:
1. Playwright browsers are installed: `npx playwright install --with-deps`
2. Test archive is set up before running tests
3. Use headless mode (default in CI)

Example CI workflow:
```yaml
- name: Install dependencies
  run: npm ci
- name: Install Playwright browsers
  run: npx playwright install --with-deps
- name: Build frontend
  run: npm run build
- name: Setup test archive
  run: ./tests/e2e/setup-test-archive.sh
- name: Run E2E tests
  run: npm run test:e2e
```

## Notes

- The setup script creates **symlinks** from `web/videos` and `web/playlists` to the test fixtures
- This allows the dev server to serve test data as if it were a real archive
- Before switching back to development with a real archive, remove the symlinks:
  ```bash
  cd ../web
  rm videos playlists
  ```
- Or run the setup script again with a different archive location

## Debugging

To debug tests with Playwright's UI:
```bash
npx playwright test --ui
```

To run a single test:
```bash
npx playwright test -g "loads and displays video list"
```

To run tests in headed mode (see the browser):
```bash
npx playwright test --headed
```
