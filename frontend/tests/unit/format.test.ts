/**
 * Tests for formatting utilities (src/utils/format.ts)
 *
 * @ai_generated
 */

import { formatCaptionLang } from '../../src/utils/format';

describe('formatCaptionLang', () => {
  test('simple language codes are uppercased', () => {
    expect(formatCaptionLang('en')).toBe('EN');
    expect(formatCaptionLang('es')).toBe('ES');
    expect(formatCaptionLang('fr')).toBe('FR');
  });

  test('standard BCP 47 codes are uppercased as-is', () => {
    expect(formatCaptionLang('pt-BR')).toBe('PT-BR');
    expect(formatCaptionLang('zh-Hans')).toBe('ZH-HANS');
    expect(formatCaptionLang('sr-Latn')).toBe('SR-LATN');
  });

  test('known yt-dlp variant suffixes get human-readable labels', () => {
    expect(formatCaptionLang('en-cur1')).toBe('EN (curated)');
    expect(formatCaptionLang('en-cur2')).toBe('EN (curated 2)');
    expect(formatCaptionLang('en-cur3')).toBe('EN (curated 3)');
    expect(formatCaptionLang('en-orig')).toBe('EN (original)');
  });

  test('variant labels work with any base language', () => {
    expect(formatCaptionLang('es-cur1')).toBe('ES (curated)');
    expect(formatCaptionLang('fr-orig')).toBe('FR (original)');
    expect(formatCaptionLang('de-cur2')).toBe('DE (curated 2)');
  });

  test('unknown suffixes are uppercased as-is', () => {
    expect(formatCaptionLang('en-xyz')).toBe('EN-XYZ');
    expect(formatCaptionLang('en-custom')).toBe('EN-CUSTOM');
  });

  test('empty string returns empty string', () => {
    expect(formatCaptionLang('')).toBe('');
  });

  test('code with only hyphen prefix returns uppercased', () => {
    // Edge case: leading hyphen (shouldn't happen in practice)
    expect(formatCaptionLang('-cur1')).toBe('-CUR1');
  });
});
