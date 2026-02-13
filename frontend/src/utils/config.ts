/**
 * Configuration for GitHub Pages and local deployment support.
 */

/**
 * Base path for the application.
 * Set via VITE_BASE_PATH environment variable during build.
 * - Local: './' (relative paths for file:// protocol)
 * - GitHub Pages: '/repo-name/' (absolute paths with repo prefix)
 */
export const BASE_PATH = import.meta.env.BASE_URL;

/**
 * Resolve path to data files (videos.tsv, playlists.tsv, etc.)
 * Handles both local file:// protocol and GitHub Pages https:// deployment.
 *
 * @param relativePath - Relative path from repository root (e.g., 'videos/videos.tsv')
 * @returns Resolved absolute or relative path
 *
 * @example
 * // Local file:// - returns '../videos/videos.tsv'
 * resolveDataPath('videos/videos.tsv')
 *
 * // GitHub Pages - returns '/annextubetesting/videos/videos.tsv'
 * resolveDataPath('videos/videos.tsv')
 */
export function resolveDataPath(relativePath: string): string {
  // Remove leading slash if present
  const cleanPath = relativePath.startsWith('/') ? relativePath.slice(1) : relativePath;

  if (window.location.protocol === 'file:') {
    // Local development/deployment: data is in parent directory
    // Frontend is in web/ or dist/, data is in repository root
    return `../${cleanPath}`;
  } else {
    // GitHub Pages or web server: data is served alongside frontend
    // BASE_PATH already includes trailing slash for gh-pages mode
    return `${BASE_PATH}${cleanPath}`;
  }
}

/**
 * Resolve path to video files or other media assets.
 * Same logic as resolveDataPath but more semantic for media.
 *
 * @param relativePath - Relative path from repository root
 * @returns Resolved path
 */
export function resolveMediaPath(relativePath: string): string {
  return resolveDataPath(relativePath);
}

/**
 * Check if running on GitHub Pages (or any web server).
 */
export function isWebDeployment(): boolean {
  return window.location.protocol !== 'file:';
}

/**
 * Check if running locally via file:// protocol.
 */
export function isLocalDeployment(): boolean {
  return window.location.protocol === 'file:';
}

/**
 * Get the deployment mode for debugging/display.
 */
export function getDeploymentMode(): 'local' | 'github-pages' | 'web-server' {
  if (isLocalDeployment()) {
    return 'local';
  }

  // Check if on GitHub Pages by hostname
  if (window.location.hostname.includes('github.io')) {
    return 'github-pages';
  }

  return 'web-server';
}
