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
 * Checks currently in flight, keyed by path.
 *
 * The result cache only helps once a check has finished. Without this,
 * callers asking about the same file while a check is still in flight
 * (e.g. several hover events landing on one card in quick succession) each
 * fire their own HEAD request for it.
 */
const inFlightChecks = new Map<string, Promise<boolean>>();

/**
 * Bumped by every cache clear.
 *
 * A check that started before a clear describes a state the caller has
 * already declared stale, so its result must not be written back into the
 * cache afterwards -- otherwise clearing an entry during a check silently
 * restores the very value that was being thrown away.
 */
let cacheGeneration = 0;

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
  if (!forceCheck) {
    if (availabilityCache.has(videoPath)) {
      return availabilityCache.get(videoPath)!;
    }
    const inFlight = inFlightChecks.get(videoPath);
    if (inFlight) {
      return inFlight;
    }
  }

  const startedAt = cacheGeneration;
  const check = isFileAvailable(videoPath)
    .then((available) => {
      if (cacheGeneration === startedAt) {
        availabilityCache.set(videoPath, available);
      }
      return available;
    })
    .finally(() => {
      if (inFlightChecks.get(videoPath) === check) {
        inFlightChecks.delete(videoPath);
      }
    });

  inFlightChecks.set(videoPath, check);
  return check;
}

/**
 * Clear cached availability for a path.
 *
 * Call this after git annex get to refresh availability.
 *
 * @param videoPath - Specific path to clear, or undefined to clear all
 */
export function clearAvailabilityCache(videoPath?: string): void {
  cacheGeneration++;
  if (videoPath) {
    availabilityCache.delete(videoPath);
    inFlightChecks.delete(videoPath);
  } else {
    availabilityCache.clear();
    inFlightChecks.clear();
  }
}
