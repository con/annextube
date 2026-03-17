/**
 * Browser and protocol detection utilities for MKV playback support.
 *
 * Used by VideoPlayer.svelte to generate context-aware error messages
 * when MKV playback fails in browsers without native support.
 */

/** Check if the current browser is Safari (including iOS Safari). */
export function isSafari(): boolean {
  const ua = navigator.userAgent;
  return /Safari/.test(ua) && !/Chrome|Chromium|Edg/.test(ua);
}

/** Check if the current browser is Firefox. */
export function isFirefox(): boolean {
  return /Firefox\//.test(navigator.userAgent);
}

/**
 * Get the major Firefox version number, or null if not Firefox.
 *
 * Parses "Firefox/145" from the user agent string.
 */
export function getFirefoxVersion(): number | null {
  const match = navigator.userAgent.match(/Firefox\/(\d+)/);
  return match ? parseInt(match[1], 10) : null;
}

/** Check if the page is served via file:// protocol. */
export function isFileProtocol(): boolean {
  return window.location.protocol === 'file:';
}

/** Check if the browser supports MediaSource Extensions. */
export function supportsMediaSource(): boolean {
  return typeof MediaSource !== 'undefined';
}

/**
 * Generate a context-aware error message for MKV playback failure.
 *
 * Returns a user-facing message with actionable guidance based on the
 * detected browser and version.
 */
export function getMkvErrorMessage(): string {
  if (isFirefox()) {
    const version = getFirefoxVersion();
    if (version !== null && version < 145) {
      return `Your Firefox version (${version}) doesn't support MKV playback. Update to Firefox 145 or later, use Chrome, or watch on YouTube.`;
    }
    // Firefox 145+ should play MKV natively — this is likely a codec issue
    return 'Firefox could not play this MKV file. The video may use an unsupported codec. Try Chrome, or watch on YouTube.';
  }

  if (isSafari()) {
    return 'Safari doesn\'t support MKV format. Use Chrome or Firefox 145+, or watch on YouTube.';
  }

  // Generic (Edge, Chrome, other)
  return 'Your browser doesn\'t support this MKV file. Try Chrome or Firefox 145+, or watch on YouTube.';
}
