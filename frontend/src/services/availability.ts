/**
 * Video availability checking utilities.
 *
 * Provides functions to check if git-annex managed files are available
 * via HEAD requests. This is the browser-side equivalent of
 * os.path.exists() in Python.
 */

/**
 * Check if a file is available via HEAD request.
 *
 * For git-annex symlinks served via HTTP:
 * - 200 OK = content is available (symlink target exists)
 * - 404 = symlink exists but content not present, or file doesn't exist
 *
 * @param url - URL to the file
 * @returns Promise<boolean> - true if file is available
 */
export async function isFileAvailable(url: string): Promise<boolean> {
  try {
    const response = await fetch(url, { method: 'HEAD' });
    return response.ok;
  } catch (error) {
    // Network error - can't determine availability
    console.warn('[availability] Failed to check:', url, error);
    return false;
  }
}

/**
 * Cache for availability checks to avoid repeated HEAD requests.
 */
const availabilityCache = new Map<string, boolean>();

/**
 * Check video availability with caching.
 *
 * Caches results for the session to avoid repeated HEAD requests
 * for the same video.
 *
 * @param videoPath - Path to the video file
 * @param forceCheck - If true, bypass cache and check again
 * @returns Promise<boolean> - true if video is available
 */
export async function checkVideoAvailability(
  videoPath: string,
  forceCheck = false
): Promise<boolean> {
  if (!forceCheck && availabilityCache.has(videoPath)) {
    return availabilityCache.get(videoPath)!;
  }

  const available = await isFileAvailable(videoPath);
  availabilityCache.set(videoPath, available);
  return available;
}

/**
 * Clear cached availability for a path.
 *
 * Call this after git annex get to refresh availability.
 *
 * @param videoPath - Specific path to clear, or undefined to clear all
 */
export function clearAvailabilityCache(videoPath?: string): void {
  if (videoPath) {
    availabilityCache.delete(videoPath);
  } else {
    availabilityCache.clear();
  }
}
