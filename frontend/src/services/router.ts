/**
 * Simple hash-based router for file:// protocol compatibility
 *
 * Routes:
 * - #/ or empty → Home (video list or multi-channel overview)
 * - #/channel/{channel_dir} → Channel view in multi-channel mode
 * - #/video/{video_id} → Video detail
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
      window.location.hash = `#/video/${params.video_id}`;
    }
  }

  /**
   * Get current route
   */
  getCurrentRoute(): Route {
    return this.currentRoute;
  }

  /**
   * Parse hash and notify listeners
   */
  private handleHashChange(): void {
    const hash = window.location.hash.slice(1); // Remove leading #
    const route = this.parseHash(hash);

    this.currentRoute = route;
    this.notifyListeners(route);
  }

  /**
   * Parse hash string into route
   */
  private parseHash(hash: string): Route {
    // Remove leading slash
    const path = hash.startsWith('/') ? hash.slice(1) : hash;

    // Empty or just "/" → home
    if (!path || path === '/') {
      return { name: 'home', params: {} };
    }

    // /channel/{channel_dir}
    const channelMatch = path.match(/^channel\/([^/?]+)/);
    if (channelMatch) {
      return {
        name: 'channel',
        params: { channel_dir: channelMatch[1] },
      };
    }

    // /video/{video_id}
    const videoMatch = path.match(/^video\/([^/?]+)/);
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
