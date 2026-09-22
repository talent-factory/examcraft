/**
 * Regression guard for the i18n CI gate itself (TF-670, TF-772). Runs as the
 * first half of `bun run i18n:check` (`bun test ./scripts`) — these exercise
 * the pure detection functions against fixtures, not the real locale files
 * (that's the gate's job), so a future refactor of the detection logic can't
 * silently stop catching the exact defect classes it was built for.
 */
import { describe, expect, it } from 'bun:test';
import {
  analyzeLocaleDirs,
  diffLocale,
  emptyValues,
  findUndocumentedDynamicCalls,
  flatten,
  placeholders,
  resolves,
  scanReferences,
} from './check-i18n-keys';

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

  it('tolerates an extra plural suffix a target locale defines beyond the reference (TF-772)', () => {
    // German: two forms. French: three (one/many/other). _many in fr is not
    // an extra key — resolves()/the runtime picks the right suffix per
    // language. Same leniency as resolves() below.
    const reference = flatten({ n_one: 'x {{count}}', n_other: 'y {{count}}' });
    const target = flatten({ n_one: 'a {{count}}', n_many: 'b {{count}}', n_other: 'c {{count}}' });
    const { extra } = diffLocale(reference, target);
    expect(extra).toEqual([]);
  });

  it('tolerates a target that answers a plural base under different suffixes than the reference', () => {
    // Isolates the missing-side of the same leniency: target has no literal
    // `n_one`, only `n_many`/`n_other` — still not missing, base `n` has a
    // valid CLDR set (it has `_other`).
    const reference = flatten({ n_one: 'x {{count}}', n_other: 'y {{count}}' });
    const target = flatten({ n_many: 'b {{count}}', n_other: 'c {{count}}' });
    const { missing } = diffLocale(reference, target);
    expect(missing).toEqual([]);
  });

  it('still reports a dropped `_other` as missing — plural leniency must not forgive the TF-670 defect itself', () => {
    // `_other` is CLDR's mandatory catch-all; a target that kept `_one` but
    // lost `_other` falls back to German for every count != 1. Tolerating
    // "any suffix present" (rather than "a valid _other-anchored set
    // present") would silently pass this.
    const reference = flatten({ n_one: 'x {{count}}', n_other: 'y {{count}}' });
    const target = flatten({ n_one: 'a {{count}}' });
    const { missing } = diffLocale(reference, target);
    expect(missing).toEqual(['n_other']);
  });

  it('reports a plain reference key answered only with a plural set as both missing and extra', () => {
    const reference = flatten({ foo: 'plain' });
    const target = flatten({ foo_other: 'pluralized' });
    const { missing, extra } = diffLocale(reference, target);
    expect(missing).toEqual(['foo']);
    expect(extra).toEqual(['foo_other']);
  });

  it('reports a pluralized reference key answered only with a plain value as both missing and extra', () => {
    const reference = flatten({ n_one: 'x {{count}}', n_other: 'y {{count}}' });
    const target = flatten({ n: 'not pluralized' });
    const { missing, extra } = diffLocale(reference, target);
    expect(missing).toEqual(['n_one', 'n_other']);
    expect(extra).toEqual(['n']);
  });

  it('still reports a plural namespace missing entirely, not just a suffix', () => {
    const reference = flatten({ n_one: 'x {{count}}', n_other: 'y {{count}}' });
    const target = flatten({ other_key: 'z' }); // no `n` namespace at all
    const { missing } = diffLocale(reference, target);
    expect(missing).toEqual(['n_one', 'n_other']);
  });
});

describe('emptyValues — values that render nothing (TF-772)', () => {
  it('reports an empty and a whitespace-only string', () => {
    expect(emptyValues(flatten({ a: '', b: '  ', c: 'x' }))).toEqual(['a', 'b']);
  });

  it('reports an empty object and an empty array, which flatten keeps as leaves', () => {
    // The case the old gate let through: `{}` in fr where de has a string was
    // "key present" for diffLocale.
    expect(emptyValues(flatten({ a: {}, b: [], c: { d: 'x' } }))).toEqual(['a', 'b']);
  });

  it('reports null and non-string scalars', () => {
    expect(emptyValues(flatten({ a: null, b: 42 }))).toEqual(['a', 'b']);
  });
});

describe('scanReferences — keys the source spends', () => {
  it('finds t(), i18n.t() and double-quoted keys, but not getByText()', () => {
    const src = [
      "t('a.b');",
      'i18n.t("c.d");',
      "screen.getByText('not.a.key');",
    ].join('\n');
    const { tKeys } = scanReferences(src, 'f.tsx');
    expect(tKeys.map((r) => [r.key, r.line])).toEqual([
      ['a.b', 1],
      ['c.d', 2],
    ]);
  });

  it('finds t() keys with a hyphenated segment', () => {
    // help.tour.*.tracks.exam-composer etc. are only reached dynamically
    // today; a future literal reference to one must still resolve.
    const { tKeys } = scanReferences("t('help.tour.teacher.tracks.exam-composer');", 'f.tsx');
    expect(tKeys.map((r) => r.key)).toEqual(['help.tour.teacher.tracks.exam-composer']);
  });

  it('ignores a t() call left behind in a comment (TF-772)', () => {
    const src = "// t('dead.key') left over\n/* t('doc.key') */\nt('live.key');";
    const { tKeys } = scanReferences(src, 'f.tsx');
    expect(tKeys.map((r) => r.key)).toEqual(['live.key']);
  });

  it('finds translateError fallback keys, also one call deep and with a trailing comma', () => {
    const src = [
      "translateError(err, t, 'x.one');",
      "translateError(appErrorFromApiError(err, 'code'), t, 'x.two');",
      "translateError(\n  err,\n  t,\n  'x.three',\n);",
    ].join('\n');
    const { fallbackKeys, dynamicCalls } = scanReferences(src, 'f.tsx');
    expect(fallbackKeys.map((r) => r.key)).toEqual(['x.one', 'x.two', 'x.three']);
    expect(dynamicCalls).toBe(0);
  });

  it('finds translateError fallback keys with double-quoted literals too', () => {
    const src = 'translateError(err, t, "x.dq");';
    const { fallbackKeys, dynamicCalls } = scanReferences(src, 'f.tsx');
    expect(fallbackKeys.map((r) => r.key)).toEqual(['x.dq']);
    expect(dynamicCalls).toBe(0);
  });

  it('finds deferred fallbackKey properties (single or double quotes) and counts non-literal calls with their expression', () => {
    const src = [
      "setFailure({ error, fallbackKey: 'q.failed' });",
      'setOther({ error, fallbackKey: "q.other" });',
      'translateError(e, t, failure.fallbackKey);',
    ].join('\n');
    const { fallbackKeys, dynamicCalls, dynamicCallExprs } = scanReferences(src, 'f.tsx');
    expect(fallbackKeys.map((r) => r.key).sort()).toEqual(['q.failed', 'q.other']);
    expect(dynamicCalls).toBe(1);
    expect(dynamicCallExprs.map((d) => d.expr)).toEqual(['failure.fallbackKey']);
  });

  it('ignores translateError inside comments', () => {
    const src = "/** translateError(err, t, 'doc.only') */\n// translateError(err, t, x)";
    const { fallbackKeys, dynamicCalls } = scanReferences(src, 'f.tsx');
    expect(fallbackKeys).toEqual([]);
    expect(dynamicCalls).toBe(0);
  });
});

describe('findUndocumentedDynamicCalls — DOCUMENTED_DYNAMIC_CALLS cannot go quiet (TF-772)', () => {
  it('passes when count and expressions both match', () => {
    const mismatched = findUndocumentedDynamicCalls(
      new Map([['f.tsx', 2]]),
      new Map([['f.tsx', ['a.b', 'c.d']]]),
      new Map([['f.tsx', ['c.d', 'a.b']]]) // order-independent
    );
    expect(mismatched).toEqual([]);
  });

  it('catches a new, undocumented dynamic call in an unlisted file', () => {
    const mismatched = findUndocumentedDynamicCalls(
      new Map([['f.tsx', 1]]),
      new Map([['f.tsx', ['x.y']]]),
      new Map()
    );
    expect(mismatched).toEqual(['f.tsx']);
  });

  it('catches a documented call that disappeared (count drops to 0)', () => {
    const mismatched = findUndocumentedDynamicCalls(
      new Map(),
      new Map(),
      new Map([['f.tsx', ['a.b']]])
    );
    expect(mismatched).toEqual(['f.tsx']);
  });

  it('catches a swap — same count, different expression, the defect this mechanism exists for', () => {
    // One documented dynamic call replaced by a different one; the file's
    // total dynamic-call count is unchanged, only the expression differs.
    const mismatched = findUndocumentedDynamicCalls(
      new Map([['f.tsx', 1]]),
      new Map([['f.tsx', ['other.key']]]),
      new Map([['f.tsx', ['failure.fallbackKey']]])
    );
    expect(mismatched).toEqual(['f.tsx']);
  });

  it('fails when a call could not be parsed into an expression, even if the count matches', () => {
    // dynamicByFile says 2 (matches documented), but only 1 expression was
    // captured — an unparseable call is exactly the shape a swapped,
    // undocumented dynamic call could take, so this must not pass silently.
    const mismatched = findUndocumentedDynamicCalls(
      new Map([['f.tsx', 2]]),
      new Map([['f.tsx', ['a.b']]]),
      new Map([['f.tsx', ['a.b', 'c.d']]])
    );
    expect(mismatched).toEqual(['f.tsx']);
  });
});

describe('analyzeLocaleDirs — presence/parity of the locale directory itself (TF-772)', () => {
  it('reports no gaps when all four languages are present and nothing else is', () => {
    const { missingFiles, unexpectedDirs } = analyzeLocaleDirs(
      new Set(['de', 'en', 'fr', 'it']),
      ['de', 'en', 'fr', 'it']
    );
    expect(missingFiles).toEqual([]);
    expect(unexpectedDirs).toEqual([]);
  });

  it('reports a missing translation.json even when its directory still exists', () => {
    // existingFiles is file-presence, dirEntries is directory-presence — an
    // empty fr/ directory (file deleted, dir left behind) must still fail.
    const { missingFiles } = analyzeLocaleDirs(new Set(['de', 'en', 'it']), ['de', 'en', 'fr', 'it']);
    expect(missingFiles).toEqual(['fr']);
  });

  it('reports a deleted locale directory as a missing file, not silently', () => {
    const { missingFiles } = analyzeLocaleDirs(new Set(['de', 'en', 'it']), ['de', 'en', 'it']);
    expect(missingFiles).toEqual(['fr']);
  });

  it('reports a directory not among LANGUAGES as unexpected', () => {
    const { unexpectedDirs } = analyzeLocaleDirs(
      new Set(['de', 'en', 'fr', 'it']),
      ['de', 'en', 'fr', 'it', 'xx']
    );
    expect(unexpectedDirs).toEqual(['xx']);
  });
});

describe('resolves — does a referenced key render text?', () => {
  const bundle = { a: { b: 'x', empty: '', obj: {}, list: ['1'] }, n_one: 'eins', n_other: 'viele' };

  it('accepts a non-empty string and a non-empty array (returnObjects)', () => {
    expect(resolves(bundle, 'a.b', false)).toBe(true);
    expect(resolves(bundle, 'a.list', false)).toBe(true);
  });

  it('rejects a missing key, an empty string and an empty object', () => {
    expect(resolves(bundle, 'a.missing', true)).toBe(false);
    expect(resolves(bundle, 'a.empty', true)).toBe(false);
    expect(resolves(bundle, 'a.obj', true)).toBe(false);
  });

  it('accepts plural forms only when asked to — translateError passes no count', () => {
    expect(resolves(bundle, 'n', true)).toBe(true);
    expect(resolves(bundle, 'n', false)).toBe(false);
  });
});
