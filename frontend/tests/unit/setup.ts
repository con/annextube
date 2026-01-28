/**
 * Jest setup file for unit tests
 *
 * Configure globals and mocks needed for tests
 */

// Make jest available globally for ES modules
import { jest } from '@jest/globals';

// @ts-ignore
globalThis.jest = jest;

// Mock fetch API (not available in Node.js)
if (!globalThis.fetch) {
  // @ts-ignore
  globalThis.fetch = jest.fn();
}
