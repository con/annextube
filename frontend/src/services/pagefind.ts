/**
 * Pagefind Service
 *
 * Provides full-text search across video metadata (title, description, tags)
 * and closed captions using Pagefind ("Full" search mode). Records carry a
 * record_type of 'metadata' or 'caption' (FR-042f); records without one come
 * from pre-FR-042f indexes and are treated as captions.
 * Lazily loads the Pagefind library, groups results by video, and flags
 * videos whose only matches are Pagefind's truncated-word fallback.
 * Excerpts are sanitized here, at the boundary where untrusted YouTube
 * content enters the app, so every consumer can render them with {@html}.
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
  /** Sanitized by sanitizeExcerpt(): safe to render with {@html} */
  excerpt: string;
  timestamp: number;
  url: string;
}

/** Results grouped by video -- one entry per video regardless of how many records matched */
export interface GroupedSearchResult {
  videoId: string;
  title: string;
  channelName: string;
  uploadDate: string;
  thumbnailUrl: string;
  /** Caption matches + 1 if the metadata record (description) matched */
  matchCount: number;
  /**
   * Earliest-timestamp caption match; falls back to the description match
   * when no captions matched (then primaryTimestamp is -1).
   * Sanitized by sanitizeExcerpt(): safe to render with {@html}
   */
  primaryExcerpt: string;
  primaryTimestamp: number;
  primaryUrl: string;
  /** Caption matches for expansion, sorted by timestamp ascending */
  allMatches: CaptionMatch[];
  /**
   * Match on the video's metadata record (title/description/tags), if any.
   * The excerpt is sanitized by sanitizeExcerpt(): safe to render with {@html}
   */
  descriptionMatch?: { excerpt: string };
  /**
   * True when none of this video's matched records actually contain the
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
 * True when a result record contains no genuine match for the query,
 * i.e. Pagefind only matched via its truncated-word fallback.
 *
 * The two "no scores" cases differ and must not be conflated:
 *   - field absent  -> index predates per-word scores; assume genuine
 *   - empty array   -> the record matched with no word-level evidence at
 *     all (e.g. a metadata record hit only through a tag). That is never
 *     a genuine content match, and treating it as one would rank an
 *     unrelated video above the near-misses.
 */
function isApproximateMatch(data: PagefindResultData): boolean {
  const locations = data.weighted_locations;
  if (!locations) return false;
  if (locations.length === 0) return true;
  return locations.every((loc) => loc.balanced_score < GENUINE_MATCH_MIN_SCORE);
}

/**
 * Neutralize any markup in a Pagefind excerpt except its own <mark> highlights.
 *
 * Excerpts come from video descriptions and captions -- YouTube content we
 * do not control -- and are rendered with {@html}.  Pagefind 1.x escapes
 * `<` and `>` in the excerpt itself (its `content` field keeps them raw), so
 * a description holding `<img src=x onerror=...>` currently reaches the DOM
 * as text.  This does not depend on that: it escapes any remaining raw tag
 * delimiter and restores only the exact <mark>/</mark> pair, so no
 * attacker-supplied markup can become an element even if a future Pagefind
 * stops escaping -- an allowlist by construction, mirroring what
 * CaptionBrowser's highlightText() does for VTT cues.
 *
 * `&` is deliberately left alone: escaping it would double-escape
 * Pagefind's own entities and show `&lt;img&gt;` to the reader instead of
 * the `<img>` they typed.  Entities can never create an element, so
 * leaving them is safe.  Highlight markup carrying attributes (Pagefind
 * emits none) renders escaped rather than as an element: degraded
 * highlighting, never injection.
 */
export function sanitizeExcerpt(excerpt: string): string {
  return excerpt
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/&lt;mark&gt;/g, '<mark>')
    .replace(/&lt;\/mark&gt;/g, '</mark>');
}

/**
 * Search metadata + captions via Pagefind ("Full" mode), group results by
 * video, and return sorted GroupedSearchResult[].
 *
 * Groups are ordered by best match relevance (Pagefind's native ordering
 * determines which video appears first).  Within each group, caption matches
 * are sorted by timestamp ascending so the earliest match is the "primary"
 * one shown in the collapsed view; a match on the video's metadata record
 * (description) is kept separately in descriptionMatch.
 */
export async function searchFull(
  query: string,
  filters?: Record<string, string[]>,
): Promise<GroupedSearchResult[]> {
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
  const groupMap = new Map<string, GroupedSearchResult>();
  const groupOrder: string[] = [];

  for (const data of allData) {
    const videoId = data.meta?.video_id;
    if (!videoId) continue;

    let group = groupMap.get(videoId);
    if (!group) {
      groupOrder.push(videoId);
      group = {
        videoId,
        title: data.meta?.title || videoId,
        channelName: data.meta?.channel_name || '',
        uploadDate: data.meta?.upload_date || '',
        thumbnailUrl: data.meta?.thumbnail_url || '',
        matchCount: 0,
        // AND-ed over every matched record below: one genuine record
        // makes the whole video genuine
        approximate: true,
        // Placeholders -- finalized below once all matches are collected
        primaryExcerpt: '',
        primaryTimestamp: -1,
        primaryUrl: `#/video/${videoId}`,
        allMatches: [],
      };
      groupMap.set(videoId, group);
    }

    group.approximate = group.approximate && isApproximateMatch(data);

    if (data.meta?.record_type === 'metadata') {
      // At most one metadata record per video
      if (!group.descriptionMatch) {
        group.descriptionMatch = { excerpt: sanitizeExcerpt(data.excerpt) };
        group.matchCount += 1;
      }
    } else {
      // 'caption' or absent (pre-FR-042f index)
      group.allMatches.push({
        excerpt: sanitizeExcerpt(data.excerpt),
        timestamp: parseTimestamp(data.url),
        url: data.url,
      });
      group.matchCount += 1;
    }
  }

  // Sort caption matches by timestamp; primary is the earliest caption
  // match, or the description match (timestamp -1) when no captions matched
  const grouped: GroupedSearchResult[] = [];
  for (const videoId of groupOrder) {
    const group = groupMap.get(videoId)!;
    group.allMatches.sort((a, b) => a.timestamp - b.timestamp);
    if (group.allMatches.length > 0) {
      group.primaryExcerpt = group.allMatches[0].excerpt;
      group.primaryTimestamp = group.allMatches[0].timestamp;
      group.primaryUrl = group.allMatches[0].url;
    } else if (group.descriptionMatch) {
      group.primaryExcerpt = group.descriptionMatch.excerpt;
    }
    grouped.push(group);
  }

  // Genuine matches first; approximate fallbacks keep their relative order after
  return [
    ...grouped.filter((g) => !g.approximate),
    ...grouped.filter((g) => g.approximate),
  ];
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
