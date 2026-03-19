/**
 * Tests for browser detection utility
 *
 * @ai_generated
 */

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  isSafari,
  isFirefox,
  getFirefoxVersion,
  isFileProtocol,
  supportsMediaSource,
  getMkvErrorMessage,
} from '../../src/services/browser-detect';

// Helper to mock navigator.userAgent
function mockUserAgent(ua: string) {
  Object.defineProperty(navigator, 'userAgent', {
    value: ua,
    writable: true,
    configurable: true,
  });
}

// Helper to mock window.location.protocol
function mockProtocol(protocol: string) {
  Object.defineProperty(window, 'location', {
    value: { ...window.location, protocol },
    writable: true,
    configurable: true,
  });
}

const UA = {
  chrome:
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  firefox145:
    'Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145',
  firefox120:
    'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120',
  safari:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
  edge:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
  iosSafari:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
};

describe('isSafari', () => {
  it('returns true for desktop Safari', () => {
    mockUserAgent(UA.safari);
    expect(isSafari()).toBe(true);
  });

  it('returns true for iOS Safari', () => {
    mockUserAgent(UA.iosSafari);
    expect(isSafari()).toBe(true);
  });

  it('returns false for Chrome', () => {
    mockUserAgent(UA.chrome);
    expect(isSafari()).toBe(false);
  });

  it('returns false for Edge', () => {
    mockUserAgent(UA.edge);
    expect(isSafari()).toBe(false);
  });

  it('returns false for Firefox', () => {
    mockUserAgent(UA.firefox145);
    expect(isSafari()).toBe(false);
  });
});

describe('isFirefox', () => {
  it('returns true for Firefox', () => {
    mockUserAgent(UA.firefox145);
    expect(isFirefox()).toBe(true);
  });

  it('returns false for Chrome', () => {
    mockUserAgent(UA.chrome);
    expect(isFirefox()).toBe(false);
  });

  it('returns false for Safari', () => {
    mockUserAgent(UA.safari);
    expect(isFirefox()).toBe(false);
  });
});

describe('getFirefoxVersion', () => {
  it('returns 145 for Firefox 145', () => {
    mockUserAgent(UA.firefox145);
    expect(getFirefoxVersion()).toBe(145);
  });

  it('returns 120 for Firefox 120', () => {
    mockUserAgent(UA.firefox120);
    expect(getFirefoxVersion()).toBe(120);
  });

  it('returns null for Chrome', () => {
    mockUserAgent(UA.chrome);
    expect(getFirefoxVersion()).toBeNull();
  });

  it('returns null for Safari', () => {
    mockUserAgent(UA.safari);
    expect(getFirefoxVersion()).toBeNull();
  });
});

describe('isFileProtocol', () => {
  it('returns true for file:// protocol', () => {
    mockProtocol('file:');
    expect(isFileProtocol()).toBe(true);
  });

  it('returns false for http:// protocol', () => {
    mockProtocol('http:');
    expect(isFileProtocol()).toBe(false);
  });

  it('returns false for https:// protocol', () => {
    mockProtocol('https:');
    expect(isFileProtocol()).toBe(false);
  });
});

describe('supportsMediaSource', () => {
  it('returns true when MediaSource is defined', () => {
    // jsdom may not define MediaSource, so stub it
    const original = globalThis.MediaSource;
    // @ts-ignore
    globalThis.MediaSource = class {};
    expect(supportsMediaSource()).toBe(true);
    if (original === undefined) {
      // @ts-ignore
      delete globalThis.MediaSource;
    } else {
      globalThis.MediaSource = original;
    }
  });

  it('returns false when MediaSource is undefined', () => {
    const original = globalThis.MediaSource;
    // @ts-ignore
    delete globalThis.MediaSource;
    expect(supportsMediaSource()).toBe(false);
    if (original !== undefined) {
      globalThis.MediaSource = original;
    }
  });
});

describe('getMkvErrorMessage', () => {
  it('returns update message for Firefox < 145', () => {
    mockUserAgent(UA.firefox120);
    const result = getMkvErrorMessage();
    expect(result).toContain('120');
    expect(result).toContain('145');
  });

  it('returns codec issue message for Firefox >= 145', () => {
    mockUserAgent(UA.firefox145);
    const result = getMkvErrorMessage();
    expect(result).toContain('codec');
  });

  it('returns Safari-specific message', () => {
    mockUserAgent(UA.safari);
    const result = getMkvErrorMessage();
    expect(result).toContain('Safari');
    expect(result).toContain('Chrome or Firefox');
  });

  it('returns generic message for Chrome/other', () => {
    mockUserAgent(UA.chrome);
    const result = getMkvErrorMessage();
    expect(result).toContain('Chrome or Firefox');
  });
});
