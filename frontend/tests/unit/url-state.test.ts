/**
 * URLStateManager Unit Tests
 */

import { describe, test, expect } from '@jest/globals';
import { URLStateManager } from '../../src/services/url-state';

describe('URLStateManager', () => {
  const urlStateManager = new URLStateManager();

  test('parses empty hash', () => {
    const state = urlStateManager.parseHash('');
    expect(state.search).toBeUndefined();
    expect(state.dateFrom).toBeUndefined();
  });

  test('parses search parameter', () => {
    const state = urlStateManager.parseHash('#/?search=test');
    expect(state.search).toBe('test');
  });

  test('parses date range parameters', () => {
    const state = urlStateManager.parseHash('#/?from=2024-01-01&to=2024-12-31');
    expect(state.dateFrom).toBe('2024-01-01');
    expect(state.dateTo).toBe('2024-12-31');
  });

  test('parses array parameters (channels)', () => {
    const state = urlStateManager.parseHash('#/?channels=CH1,CH2,CH3');
    expect(state.channels).toEqual(['CH1', 'CH2', 'CH3']);
  });

  test('parses playlist parameters', () => {
    const state = urlStateManager.parseHash('#/?playlists=PL1,PL2');
    expect(state.playlists).toEqual(['PL1', 'PL2']);
  });

  test('parses sort parameters', () => {
    const state = urlStateManager.parseHash('#/?sort=views&dir=desc');
    expect(state.sortField).toBe('views');
    expect(state.sortDirection).toBe('desc');
  });

  test('parses complex URL with multiple parameters', () => {
    const hash =
      '#/?search=test&from=2024-01-01&channels=CH1,CH2&sort=views&dir=desc';
    const state = urlStateManager.parseHash(hash);
    expect(state.search).toBe('test');
    expect(state.dateFrom).toBe('2024-01-01');
    expect(state.channels).toEqual(['CH1', 'CH2']);
    expect(state.sortField).toBe('views');
    expect(state.sortDirection).toBe('desc');
  });

  test('encodes empty state', () => {
    const hash = urlStateManager.encodeHash({});
    expect(hash).toBe('#/');
  });

  test('encodes search parameter', () => {
    const hash = urlStateManager.encodeHash({ search: 'test' });
    expect(hash).toBe('#/?search=test');
  });

  test('encodes date range parameters', () => {
    const hash = urlStateManager.encodeHash({
      dateFrom: '2024-01-01',
      dateTo: '2024-12-31',
    });
    expect(hash).toContain('from=2024-01-01');
    expect(hash).toContain('to=2024-12-31');
  });

  test('encodes array parameters', () => {
    const hash = urlStateManager.encodeHash({
      channels: ['CH1', 'CH2'],
      playlists: ['PL1', 'PL2'],
    });
    expect(hash).toContain('channels=CH1%2CCH2');
    expect(hash).toContain('playlists=PL1%2CPL2');
  });

  test('encodes and parses are symmetrical', () => {
    const originalState = {
      search: 'test query',
      dateFrom: '2024-01-01',
      dateTo: '2024-12-31',
      channels: ['CH1', 'CH2'],
      playlists: ['PL1'],
      sortField: 'views' as const,
      sortDirection: 'asc' as const,
    };

    const hash = urlStateManager.encodeHash(originalState);
    const parsedState = urlStateManager.parseHash(hash);

    expect(parsedState.search).toBe(originalState.search);
    expect(parsedState.dateFrom).toBe(originalState.dateFrom);
    expect(parsedState.dateTo).toBe(originalState.dateTo);
    expect(parsedState.channels).toEqual(originalState.channels);
    expect(parsedState.playlists).toEqual(originalState.playlists);
    expect(parsedState.sortField).toBe(originalState.sortField);
    expect(parsedState.sortDirection).toBe(originalState.sortDirection);
  });

  test('does not encode default sort field (date)', () => {
    const hash = urlStateManager.encodeHash({ sortField: 'date' });
    expect(hash).toBe('#/');
    expect(hash).not.toContain('sort=');
  });

  test('does not encode default sort direction (desc)', () => {
    const hash = urlStateManager.encodeHash({ sortDirection: 'desc' });
    expect(hash).toBe('#/');
    expect(hash).not.toContain('dir=');
  });

  test('encodes non-default sort field', () => {
    const hash = urlStateManager.encodeHash({ sortField: 'views' });
    expect(hash).toContain('sort=views');
  });

  test('encodes non-default sort direction', () => {
    const hash = urlStateManager.encodeHash({ sortDirection: 'asc' });
    expect(hash).toContain('dir=asc');
  });

  test('encodes non-default sort but omits default direction', () => {
    const hash = urlStateManager.encodeHash({ sortField: 'views', sortDirection: 'desc' });
    expect(hash).toContain('sort=views');
    expect(hash).not.toContain('dir=');
  });

  test('handles URL with hash variations', () => {
    const variations = ['#/?search=test', '#?search=test', '?search=test'];
    variations.forEach((hash) => {
      const state = urlStateManager.parseHash(hash);
      expect(state.search).toBe('test');
    });
  });

  test('filters out empty array values', () => {
    const state = urlStateManager.parseHash('#/?channels=');
    expect(state.channels).toBeUndefined();
  });
});
