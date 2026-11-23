import type { Preview } from '@storybook/html-vite';
import '../src/app.css';

// The components print ages ("11 months ago") relative to now, so the clock is pinned, or every
// story with a date would change on its own as time passes. Only "now" is fixed: a Date built
// from arguments, and the timers, behave as usual.
const FIXED_NOW = Date.parse('2025-01-01T00:00:00Z');
const RealDate = Date;
class FixedDate extends RealDate {
  constructor(...args: unknown[]) {
    if (args.length === 0) super(FIXED_NOW);
    else super(...(args as ConstructorParameters<typeof Date>));
  }
  static now(): number {
    return FIXED_NOW;
  }
}
globalThis.Date = FixedDate as DateConstructor;

const preview: Preview = {
  parameters: {
    // The app paints its own page background (below), so Storybook's background layer is disabled
    // rather than painted over it.
    backgrounds: { disable: true },
  },
  decorators: [
    // The page background App.svelte sets through :global(body), which the stories do not load.
    // The app has one theme, so there are no Chromatic modes to declare.
    (story) => {
      document.body.style.background = '#f9f9f9';
      return story();
    },
  ],
};

export default preview;
