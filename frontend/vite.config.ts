import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';
// Version placeholder — replaced at deploy time by `annextube generate-web`
// with the real annextube version.  Do NOT hardcode a real version here.
const VERSION_PLACEHOLDER = '0.0.0-unknown';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Determine base path based on build mode
  // - default/local: './' for file:// protocol support
  // - gh-pages: use VITE_BASE_PATH env var (e.g., '/annextubetesting/')
  const isGitHubPages = mode === 'gh-pages';
  const basePath = isGitHubPages
    ? (process.env.VITE_BASE_PATH || '/')
    : './';

  console.log(`Building for ${mode} mode with base path: ${basePath}`);

  return {
    plugins: [svelte()],

    // Inject version at build time
    define: {
      __APP_VERSION__: JSON.stringify(VERSION_PLACEHOLDER),
    },

    // Critical for file:// protocol support (local) or GitHub Pages (deployed)
    base: basePath,

    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },

    build: {
      outDir: isGitHubPages ? 'dist' : '../web',  // dist for gh-pages, web for local
      emptyOutDir: true,

      // Optimization
      minify: 'esbuild',  // Use esbuild (faster, built-in)
      sourcemap: false,

      // Clean asset filenames (no content hashes)
      rollupOptions: {
        output: {
          entryFileNames: 'assets/[name].js',
          chunkFileNames: 'assets/[name].js',
          assetFileNames: 'assets/[name][extname]',
        },
      },
    },

    // Configure Vitest
    test: {
      globals: true,
      environment: 'jsdom'
    }
  };
});
