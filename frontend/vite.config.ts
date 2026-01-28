import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [svelte()],

  // Critical for file:// protocol support
  base: './',  // Relative paths instead of absolute /assets/

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },

  build: {
    outDir: '../web',  // Output to parent web/ directory
    emptyOutDir: true,

    // Optimization
    minify: 'esbuild',  // Use esbuild (faster, built-in)
    sourcemap: false

    // Note: manualChunks will be added later when components exist
  },

  // Configure Vitest
  test: {
    globals: true,
    environment: 'jsdom'
  }
});
