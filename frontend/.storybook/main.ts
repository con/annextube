import type { StorybookConfig } from '@storybook/html-vite';

const config: StorybookConfig = {
  // Stories live beside the app rather than in src/, so a story is never mistaken for shipped code.
  stories: ['../stories/**/*.stories.@(js|ts)'],
  // No addons: the stories exist to be snapshotted and looked at, nothing more.
  addons: [],
  // The HTML framework, not the Svelte one: @storybook/svelte-vite needs Svelte 5 and the app is on
  // Svelte 4, so stories mount the real components by hand (stories/utils.ts). The Vite builder
  // also loads the app's own vite.config.ts from the parent of this directory, so its Svelte
  // plugin, its `@` alias and its define (__APP_VERSION__) apply to the stories as is.
  framework: { name: '@storybook/html-vite', options: {} },
  // No usage reports from a developer's machine or from CI.
  core: { disableTelemetry: true },
  // The snapshot suite's fixture thumbnails, served at the path the story data names; a story
  // must not fetch an image from the network.
  staticDirs: [
    { from: '../tests/chromatic/fixtures/archive/videos', to: '/videos' },
  ],
};

export default config;
