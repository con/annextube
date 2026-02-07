import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

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

      // Manual chunks for better caching
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['svelte']
          }
        }
      }
    },

    // Configure Vitest
    test: {
      globals: true,
      environment: 'jsdom'
    }
  };
});
