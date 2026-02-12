/**
 * Simple hash-based router for file:// protocol compatibility
 *
 * Routes:
 * - #/ or empty → Home (video list or multi-channel overview)
 * - #/channel/{channel_dir} → Channel view in multi-channel mode
 * - #/channel/{channel_dir}/video/{video_id} → Video detail with channel context
 * - #/video/{video_id} → Video detail (backward compatibility, no channel context)
 */

export interface Route {
  name: 'home' | 'channel' | 'video';
  params: Record<string, string>;
}

export class Router {
  private listeners: ((route: Route) => void)[] = [];
  private currentRoute: Route = { name: 'home', params: {} };

  constructor() {
    // Listen for hash changes
    window.addEventListener('hashchange', () => this.handleHashChange());
    // Parse initial hash
    this.handleHashChange();
  }

  /**
   * Subscribe to route changes
   */
  subscribe(listener: (route: Route) => void): () => void {
    this.listeners.push(listener);
    // Immediately call with current route
    listener(this.currentRoute);

    // Return unsubscribe function
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  /**
   * Navigate to a route
   */
  navigate(name: 'home' | 'channel' | 'video', params: Record<string, string> = {}): void {
    if (name === 'home') {
      window.location.hash = '#/';
    } else if (name === 'channel') {
      window.location.hash = `#/channel/${params.channel_dir}`;
    } else if (name === 'video') {
      // If channel_dir is provided, use nested route format
      if (params.channel_dir) {
        window.location.hash = `#/channel/${params.channel_dir}/video/${params.video_id}`;
      } else {
        // Backward compatibility: video without channel context
        window.location.hash = `#/video/${params.video_id}`;
      }
    }
  }

  /**
   * Get current route
   */
  getCurrentRoute(): Route {
    return this.currentRoute;
  }

  /**
   * Parse hash and notify listeners (only on actual route changes)
   */
  private handleHashChange(): void {
    const hash = window.location.hash.slice(1); // Remove leading #
    const route = this.parseHash(hash);

    // Only notify if route actually changed (ignore query parameter changes)
    if (this.isSameRoute(this.currentRoute, route)) {
      return;
    }

    this.currentRoute = route;
    this.notifyListeners(route);
  }

  /**
   * Compare two routes for equality (name and params only, ignores query params)
   */
  private isSameRoute(a: Route, b: Route): boolean {
    if (a.name !== b.name) return false;

    const aKeys = Object.keys(a.params);
    const bKeys = Object.keys(b.params);

    if (aKeys.length !== bKeys.length) return false;

    return aKeys.every((key) => a.params[key] === b.params[key]);
  }

  /**
   * Parse hash string into route
   */
  private parseHash(hash: string): Route {
    // Remove leading slash
    const path = hash.startsWith('/') ? hash.slice(1) : hash;

    // Split on '?' to handle query params separately
    const questionIndex = path.indexOf('?');
    const cleanPath = questionIndex === -1 ? path : path.substring(0, questionIndex);

    // Empty or just "/" → home
    if (!cleanPath || cleanPath === '/') {
      return { name: 'home', params: {} };
    }

    // /channel/{channel_dir}/video/{video_id} (nested route with channel context)
    const nestedVideoMatch = cleanPath.match(/^channel\/([^/]+)\/video\/([^/]+)$/);
    if (nestedVideoMatch) {
      return {
        name: 'video',
        params: {
          channel_dir: nestedVideoMatch[1],
          video_id: nestedVideoMatch[2],
        },
      };
    }

    // /channel/{channel_dir} (channel view)
    const channelMatch = cleanPath.match(/^channel\/([^/]+)$/);
    if (channelMatch) {
      return {
        name: 'channel',
        params: { channel_dir: channelMatch[1] },
      };
    }

    // /video/{video_id} (backward compatibility: video without channel context)
    const videoMatch = cleanPath.match(/^video\/([^/]+)$/);
    if (videoMatch) {
      return {
        name: 'video',
        params: { video_id: videoMatch[1] },
      };
    }

    // Unknown route → fallback to home
    return { name: 'home', params: {} };
  }

  /**
   * Notify all listeners of route change
   */
  private notifyListeners(route: Route): void {
    this.listeners.forEach((listener) => listener(route));
  }
}

/**
 * Singleton instance
 */
export const router = new Router();
