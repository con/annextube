/**
 * Pagefind Service
 *
 * Provides full-text search across closed captions using Pagefind.
 * Lazily loads the Pagefind library and groups results by video.
 */

/** Shape of a single result returned by the Pagefind JS API */
export interface PagefindResult {
  id: string;
  data: () => Promise<PagefindResultData>;
}

/** Per-word match score entry from Pagefind's weighted_locations */
export interface PagefindWordLocation {
  weight: number;
  balanced_score: number;
  /** Word index into the whitespace-split content */
  location: number;
}

/** Full data for a single Pagefind result (loaded via result.data()) */
export interface PagefindResultData {
  url: string;
  content: string;
  excerpt: string;
  meta: Record<string, string>;
  filters: Record<string, string[]>;
  /** Per-word match scores (present in pagefind 1.x) */
  weighted_locations?: PagefindWordLocation[];
}

/** A single caption match within a grouped result */
export interface CaptionMatch {
  excerpt: string;
  timestamp: number;
  url: string;
}

/** Results grouped by video -- one entry per video regardless of how many chunks matched */
export interface GroupedCaptionResult {
  videoId: string;
  title: string;
  channelName: string;
  uploadDate: string;
  thumbnailUrl: string;
  matchCount: number;
  /** First (earliest timestamp) match */
  primaryExcerpt: string;
  primaryTimestamp: number;
  primaryUrl: string;
  /** All matches for expansion, sorted by timestamp ascending */
  allMatches: CaptionMatch[];
  /**
   * True when none of this video's matched chunks actually contain the
   * query -- Pagefind only matched a shorter indexed word (e.g. query
   * "reprostim" matching just "repro"). Absent/false means genuine.
   */
  approximate?: boolean;
}

/** The Pagefind JS API shape (subset we use) */
export interface PagefindInstance {
  search: (
    query: string,
    options?: { filters?: Record<string, string[]> },
  ) => Promise<{ results: PagefindResult[] }>;
}

let pagefindInstance: PagefindInstance | null = null;
let initAttempted = false;
let initResult = false;

/**
 * Lazily load the Pagefind JS bundle from /pagefind/pagefind.js.
 * Returns true if the index is available, false if 404 or load error.
 *
 * Safe to call multiple times -- only the first call actually loads the script.
 */
export async function initPagefind(): Promise<boolean> {
  if (initAttempted) return initResult;
  initAttempted = true;

  try {
    // Pagefind is loaded relative to the current page.
    // The frontend lives at /web/ and pagefind index at /web/pagefind/.
    // We construct an absolute URL from the page's location so the browser
    // can resolve it as a proper module specifier (bare specifiers like
    // "pagefind/pagefind.js" fail).  The array join prevents Vite from
    // seeing a static string and attempting build-time resolution.
    const base = window.location.href.replace(/#.*$/, '').replace(/[^/]*$/, '');
    const pagefindUrl = base + ['pagefind', 'pagefind.js'].join('/');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const pf = await (Function('url', 'return import(url)') as (url: string) => Promise<any>)(pagefindUrl);
    pagefindInstance = pf as PagefindInstance;
    initResult = true;
  } catch {
    // 404 or network error -- Pagefind index is not present
    initResult = false;
  }

  return initResult;
}

/**
 * Parse a timestamp from a Pagefind result URL.
 *
 * Expected URL patterns:
 *   /videos/<video_id>/video.en.vtt#t=123
 *   /channel_dir/videos/<video_id>/video.en.vtt#t=123
 *
 * Falls back to 0 if the fragment is missing or malformed.
 */
function parseTimestamp(url: string): number {
  const hashIdx = url.indexOf('#');
  if (hashIdx === -1) return 0;
  const fragment = url.slice(hashIdx + 1);
  const match = fragment.match(/t=(\d+(?:\.\d+)?)/);
  return match ? parseFloat(match[1]) : 0;
}

/**
 * Minimum per-word balanced_score for a match to count as genuine.
 *
 * Pagefind never returns zero results for a query it half-knows: for
 * "reprostim" it returns every chunk containing "repro", because the
 * indexed word is a truncation of the query. Observed balanced_score
 * tiers (pagefind 1.x, default word weight as our index uses):
 *   ~512  whole-word or stemmed match       ("pizzas" -> "pizza")
 *   ~389  query is a prefix of the word     ("datala" -> "datalad")
 *   ~221  word is a truncation of the query ("reprostim" -> "repro")
 * The first two are genuine matches; the last is the misleading
 * fallback we flag as approximate. 300 separates the tiers with
 * comfortable margin on both sides.
 */
const GENUINE_MATCH_MIN_SCORE = 300;

/**
 * True when a result chunk contains no genuine match for the query,
 * i.e. Pagefind only matched via its truncated-word fallback.
 * Chunks without score data (older index) are treated as genuine.
 */
function isApproximateMatch(data: PagefindResultData): boolean {
  const locations = data.weighted_locations;
  if (!locations || locations.length === 0) return false;
  return locations.every((loc) => loc.balanced_score < GENUINE_MATCH_MIN_SCORE);
}

/**
 * Search captions via Pagefind, group results by video, and return
 * sorted GroupedCaptionResult[].
 *
 * Groups are ordered by best match relevance (Pagefind's native ordering
 * determines which video appears first).  Within each group, matches are
 * sorted by timestamp ascending so the earliest match is the "primary"
 * one shown in the collapsed view.
 */
export async function searchCaptions(
  query: string,
  filters?: Record<string, string[]>,
): Promise<GroupedCaptionResult[]> {
  if (!pagefindInstance) {
    const ready = await initPagefind();
    if (!ready) return [];
  }

  if (!query.trim()) return [];

  const searchOptions = filters ? { filters } : undefined;
  const { results } = await pagefindInstance!.search(query, searchOptions);

  // Load all result data in parallel
  const dataPromises = results.map((r) => r.data());
  const allData = await Promise.all(dataPromises);

  // Group by video_id (from meta)
  // We preserve Pagefind's result ordering to determine group relevance:
  // the first occurrence of a video_id sets that group's position.
  const groupMap = new Map<string, GroupedCaptionResult>();
  const groupOrder: string[] = [];

  for (const data of allData) {
    const videoId = data.meta?.video_id;
    if (!videoId) continue;

    const timestamp = parseTimestamp(data.url);
    const match: CaptionMatch = {
      excerpt: data.excerpt,
      timestamp,
      url: data.url,
    };
    const approximate = isApproximateMatch(data);

    const existing = groupMap.get(videoId);
    if (existing) {
      existing.matchCount += 1;
      existing.allMatches.push(match);
      // A single genuine chunk makes the whole video genuine
      existing.approximate = existing.approximate && approximate;
    } else {
      groupOrder.push(videoId);
      groupMap.set(videoId, {
        videoId,
        title: data.meta?.title || videoId,
        channelName: data.meta?.channel_name || '',
        uploadDate: data.meta?.upload_date || '',
        thumbnailUrl: data.meta?.thumbnail_url || '',
        matchCount: 1,
        approximate,
        // Placeholders -- will be finalized after sorting matches
        primaryExcerpt: match.excerpt,
        primaryTimestamp: match.timestamp,
        primaryUrl: match.url,
        allMatches: [match],
      });
    }
  }

  // Sort matches within each group by timestamp and set primary to earliest
  const grouped: GroupedCaptionResult[] = [];
  for (const videoId of groupOrder) {
    const group = groupMap.get(videoId)!;
    group.allMatches.sort((a, b) => a.timestamp - b.timestamp);
    group.primaryExcerpt = group.allMatches[0].excerpt;
    group.primaryTimestamp = group.allMatches[0].timestamp;
    group.primaryUrl = group.allMatches[0].url;
    grouped.push(group);
  }

  return grouped;
}

/**
 * Format a timestamp in seconds to a human-readable string.
 *
 * - < 3600 seconds: "MM:SS"
 * - >= 3600 seconds: "H:MM:SS"
 */
export function formatTimestamp(seconds: number): string {
  const totalSecs = Math.floor(seconds);
  const h = Math.floor(totalSecs / 3600);
  const m = Math.floor((totalSecs % 3600) / 60);
  const s = totalSecs % 60;

  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

/**
 * Reset internal state (useful for testing).
 * Optionally inject a mock Pagefind instance.
 */
export function _resetForTesting(mockInstance?: PagefindInstance | null): void {
  pagefindInstance = mockInstance ?? null;
  initAttempted = !!mockInstance;
  initResult = !!mockInstance;
}
