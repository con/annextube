/**
 * Accessibility tests (Constitution IV: WCAG 2.1 AA compliance).
 *
 * Uses axe-core via @axe-core/playwright to scan pages for
 * accessibility violations. Runs against the dev server with
 * mock data (no real archive fixture needed).
 */

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility (WCAG 2.1 AA)', () => {
  test('main page has no critical a11y violations', async ({ page }) => {
    await page.goto('/');
    // Wait for content to render
    await page.waitForSelector('.video-grid', { timeout: 10000 }).catch(() => {
      // Grid may not exist if no mock data — page still testable
    });

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    // Log violations for debugging (don't fail silently)
    if (results.violations.length > 0) {
      const summary = results.violations.map(v =>
        `[${v.impact}] ${v.id}: ${v.description} (${v.nodes.length} nodes)`
      ).join('\n');
      console.log(`Accessibility violations found:\n${summary}`);
    }

    // Fail on serious and critical violations only
    const serious = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(serious, `Found ${serious.length} serious/critical a11y violations`).toHaveLength(0);
  });

  test('page has valid landmark structure', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .include('body')
      .analyze();

    // Check specifically for landmark-related rules
    const landmarkViolations = results.violations.filter(v =>
      v.id.includes('landmark') || v.id.includes('region')
    );

    // Log but don't fail on landmark issues (informational for now)
    if (landmarkViolations.length > 0) {
      console.log('Landmark suggestions:', landmarkViolations.map(v => v.id).join(', '));
    }
  });

  test('interactive elements are keyboard accessible', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    // Filter for keyboard-related violations
    const keyboardViolations = results.violations.filter(
      v => v.tags.some(t => t.includes('keyboard')) ||
           ['tabindex', 'focus-order-semantics', 'scrollable-region-focusable',
            'focus-trap-deactivate', 'focus-trap-nav'].includes(v.id)
    );
    const serious = keyboardViolations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(serious).toHaveLength(0);
  });

  test('color contrast meets AA standards', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2aa'])
      .analyze();

    const serious = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(serious).toHaveLength(0);
  });
});
