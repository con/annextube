import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';
import { readFileSync } from 'fs';

// Read version from package.json
const pkg = JSON.parse(readFileSync('./package.json', 'utf-8'));

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [svelte()],

  // Inject version at build time
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },

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
