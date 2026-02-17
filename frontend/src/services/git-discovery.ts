/**
 * Git repository discovery for clone commands.
 *
 * Probes for a .git directory accessible over HTTP so the web UI
 * can offer ready-to-copy clone commands.
 */

/**
 * Probe for a .git directory at the given base path.
 * Returns the absolute clone URL or null if not found.
 *
 * @param relativeBase - Relative path to the repository root (e.g. '..' or '../channel-dir')
 * @returns Absolute URL to the .git directory, or null if not accessible
 */
export async function probeGitUrl(relativeBase: string): Promise<string | null> {
  const probe = `${relativeBase}/.git/HEAD`;
  try {
    const resp = await fetch(probe, { method: 'HEAD' });
    if (resp.ok) {
      // Resolve to absolute URL and strip any trailing slash
      return new URL(`${relativeBase}/.git`, window.location.href).href.replace(/\/$/, '');
    }
  } catch {
    // Network error or file:// — not available
  }
  return null;
}
