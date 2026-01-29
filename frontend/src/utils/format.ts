/**
 * Formatting utilities for display
 */

/**
 * Format duration in seconds to human-readable string
 *
 * @param seconds - Duration in seconds
 * @returns Formatted string (e.g., "3:45", "1:23:45")
 */
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }
  return `${minutes}:${String(secs).padStart(2, '0')}`;
}

/**
 * Format number with thousand separators
 *
 * @param num - Number to format
 * @returns Formatted string (e.g., "1,234,567")
 */
export function formatNumber(num: number): string {
  return num.toLocaleString();
}

/**
 * Format view count with K/M/B suffixes
 *
 * @param views - View count
 * @returns Formatted string (e.g., "1.2M views")
 */
export function formatViews(views: number): string {
  if (views >= 1_000_000_000) {
    return `${(views / 1_000_000_000).toFixed(1)}B views`;
  }
  if (views >= 1_000_000) {
    return `${(views / 1_000_000).toFixed(1)}M views`;
  }
  if (views >= 1_000) {
    return `${(views / 1_000).toFixed(1)}K views`;
  }
  return `${views} views`;
}

/**
 * Format ISO 8601 date to relative time (e.g., "2 days ago")
 *
 * @param isoDate - ISO 8601 date string
 * @returns Relative time string
 */
export function formatRelativeTime(dateInput: string | number): string {
  // Handle both ISO date strings and Unix timestamps (in seconds)
  let date: Date;
  if (typeof dateInput === 'number') {
    // Unix timestamp in seconds - convert to milliseconds for Date()
    date = new Date(dateInput * 1000);
  } else {
    // ISO date string
    date = new Date(dateInput);
  }

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffMonths = Math.floor(diffDays / 30);
  const diffYears = Math.floor(diffDays / 365);

  if (diffYears > 0) {
    return `${diffYears} year${diffYears > 1 ? 's' : ''} ago`;
  }
  if (diffMonths > 0) {
    return `${diffMonths} month${diffMonths > 1 ? 's' : ''} ago`;
  }
  if (diffDays > 0) {
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  }
  if (diffHours > 0) {
    return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  }
  if (diffMins > 0) {
    return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  }
  return 'Just now';
}

/**
 * Format ISO 8601 date to short date string
 *
 * @param isoDate - ISO 8601 date string
 * @returns Short date string (e.g., "Jan 15, 2024")
 */
export function formatShortDate(isoDate: string): string {
  const date = new Date(isoDate);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format comment count with K suffix for thousands
 *
 * @param count - Comment count
 * @returns Formatted string (e.g., "5.2K comments", "142 comments", "1 comment") or empty string if zero
 */
export function formatCommentCount(count: number): string {
  if (count === 0) return '';  // Don't show if no comments
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K comments`;
  }
  return `${count} comment${count !== 1 ? 's' : ''}`;
}
