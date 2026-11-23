import { expect, type Page, type TestInfo } from '@playwright/test';

export interface Viewport {
  name: string;
  width: number;
  height: number;
}

/** Two device classes in both orientations, plus the desktop width the suite runs under. */
export const VIEWPORTS: readonly Viewport[] = [
  { name: 'desktop', width: 1280, height: 720 },
  { name: 'tablet portrait', width: 768, height: 1024 },
  { name: 'tablet landscape', width: 1024, height: 768 },
  { name: 'mobile portrait', width: 390, height: 844 },
  { name: 'mobile landscape', width: 844, height: 390 },
];

type Registrar = (
  title: string,
  body: (args: { page: Page }, testInfo: TestInfo) => Promise<void>,
) => void;

/**
 * Registers `title` once per viewport, named in the title and with the page already sized to it.
 * Chromatic snapshots the page after each test body and names the capture by the test's file,
 * describe and title (never its Playwright project), so the viewport in the title is what keeps
 * the captures apart. `testInfo` is passed through for `takeSnapshot(page, name, testInfo)`.
 */
export function forEachViewport(
  test: Registrar,
  title: string,
  body: (
    args: { page: Page },
    viewport: Viewport,
    testInfo: TestInfo,
  ) => Promise<void>,
  viewports: readonly Viewport[] = VIEWPORTS,
): void {
  for (const viewport of viewports) {
    test(`${title} [${viewport.name}]`, async ({ page }, testInfo) => {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await body({ page }, viewport, testInfo);
    });
  }
}

/**
 * Fails naming the elements that reach past the right edge of the viewport. A narrow screen's
 * first failure is a row of controls that cannot wrap, and a named element is far easier to act
 * on than a pixel diff in a snapshot.
 */
export async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const { scrollWidth, clientWidth, offenders } = await page.evaluate(() => {
    const root = document.documentElement;
    const offenders: string[] = [];
    document.querySelectorAll('body *').forEach((el) => {
      // Shapes inside an inline <svg> are measured in its own coordinate space; the <svg> is checked.
      if ((el as SVGElement).ownerSVGElement) return;
      const { width, right } = el.getBoundingClientRect();
      if (width > 0 && right > root.clientWidth + 1) {
        const id = el.id ? `#${el.id}` : '';
        const names =
          typeof el.className === 'string'
            ? el.className.trim().split(/\s+/).filter(Boolean)
            : [];
        const classes = names.length ? `.${names.join('.')}` : '';
        offenders.push(
          `${el.tagName.toLowerCase()}${id}${classes} (${Math.round(width)}px wide, ends at ${Math.round(right)}px)`,
        );
      }
    });
    return {
      scrollWidth: root.scrollWidth,
      clientWidth: root.clientWidth,
      offenders,
    };
  });
  expect(
    offenders,
    `Elements past the right edge of the ${clientWidth}px viewport`,
  ).toEqual([]);
  expect(
    scrollWidth,
    `Page scrolls sideways at ${clientWidth}px`,
  ).toBeLessThanOrEqual(clientWidth + 1);
}
