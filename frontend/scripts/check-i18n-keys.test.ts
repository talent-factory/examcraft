/**
 * Regression guard for the i18n CI gate itself (TF-670). Run with
 * `bun test scripts/` — these exercise the pure comparison functions against
 * fixtures, not the real locale files (that's `bun run i18n:check`'s job),
 * so a future refactor of the detection logic can't silently stop catching
 * the exact defect classes it was built for.
 */
import { describe, expect, it } from 'bun:test';
import { diffLocale, flatten, placeholders } from './check-i18n-keys';

describe('flatten', () => {
  it('descends into nested objects, joining keys with a dot', () => {
    const flat = flatten({ a: { b: 'x', c: 'y' } });
    expect(flat.get('a.b')).toBe('x');
    expect(flat.get('a.c')).toBe('y');
  });

  it('descends into arrays by index — a dropped/reordered entry must be visible', () => {
    // PrivacyPage.tsx reads legal.privacy.subprocessors.items with
    // returnObjects: true; a locale shortening that array must fail the
    // gate exactly like a missing string key would.
    const flat = flatten({ a: ['x', 'y', 'z'] });
    expect([...flat.keys()]).toEqual(['a.0', 'a.1', 'a.2']);
    expect(flat.get('a.1')).toBe('y');
  });

  it('records an empty object as a leaf instead of dropping it', () => {
    const flat = flatten({ a: {} });
    expect(flat.has('a')).toBe(true);
  });

  it('records an empty array as a leaf instead of dropping it', () => {
    const flat = flatten({ a: [] });
    expect(flat.has('a')).toBe(true);
  });
});

describe('placeholders', () => {
  it('extracts {{name}} placeholders in a stable, sorted order', () => {
    expect(placeholders('Hallo {{name}}, du hast {{count}} Nachrichten')).toEqual([
      'count',
      'name',
    ]);
  });

  it('tolerates the {{ name }} spacing variant', () => {
    expect(placeholders('{{ name }}')).toEqual(['name']);
  });

  it('returns an empty array for non-string values', () => {
    expect(placeholders(42)).toEqual([]);
    expect(placeholders(null)).toEqual([]);
  });
});

describe('diffLocale — the three defect classes TF-670 exists to catch', () => {
  it('reports a key present in the reference but missing from the target', () => {
    const reference = flatten({ greeting: 'Hallo', farewell: 'Tschüss' });
    const target = flatten({ greeting: 'Bonjour' });
    const { missing, extra, brokenPlaceholders } = diffLocale(reference, target);
    expect(missing).toEqual(['farewell']);
    expect(extra).toEqual([]);
    expect(brokenPlaceholders).toEqual([]);
  });

  it('reports a key present in the target but not the reference', () => {
    const reference = flatten({ greeting: 'Hallo' });
    const target = flatten({ greeting: 'Bonjour', leftover: 'Ancien texte' });
    const { missing, extra, brokenPlaceholders } = diffLocale(reference, target);
    expect(missing).toEqual([]);
    expect(extra).toEqual(['leftover']);
    expect(brokenPlaceholders).toEqual([]);
  });

  it('reports a lost or renamed interpolation placeholder', () => {
    const reference = flatten({ msg: 'Hallo {{name}}, {{count}} neu' });
    const target = flatten({ msg: 'Bonjour {{name}}' }); // {{count}} dropped
    const { missing, extra, brokenPlaceholders } = diffLocale(reference, target);
    expect(missing).toEqual([]);
    expect(extra).toEqual([]);
    expect(brokenPlaceholders).toEqual(['msg']);
  });

  it('reports a shortened array as missing, per the array-descends-by-index strategy', () => {
    // The concrete case that motivated array traversal: a locale list with
    // fewer entries than the reference must fail, not silently pass because
    // "the key exists".
    const reference = flatten({ items: ['a', 'b', 'c'] });
    const target = flatten({ items: ['a', 'b'] });
    const { missing } = diffLocale(reference, target);
    expect(missing).toEqual(['items.2']);
  });

  it('passes clean when target matches the reference exactly', () => {
    const reference = flatten({ a: 'x', b: { c: 'y' } });
    const target = flatten({ a: 'x', b: { c: 'z' } }); // different text, same keys/placeholders
    const { missing, extra, brokenPlaceholders } = diffLocale(reference, target);
    expect(missing).toEqual([]);
    expect(extra).toEqual([]);
    expect(brokenPlaceholders).toEqual([]);
  });
});
