/**
 * Regression guard for the i18n CI gate itself (TF-670, TF-772). Runs as the
 * first half of `bun run i18n:check` (`bun test ./scripts`) — these exercise
 * the pure detection functions against fixtures, not the real locale files
 * (that's the gate's job), so a future refactor of the detection logic can't
 * silently stop catching the exact defect classes it was built for.
 */
import { describe, expect, it } from 'bun:test';
import {
  absentScanRoots,
  analyzeLocaleDirs,
  collectI18nKeys,
  compareWithBaseline,
  coveredBy,
  diffLocale,
  effectivePrefixes,
  emptyValues,
  findUndocumentedDynamicCalls,
  findUnreferencedKeys,
  flatten,
  partCMode,
  placeholders,
  resolves,
  scanReferences,
  widePrefixes,
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

describe('scanReferences — liveness inputs for unreferenced keys (TF-775 B)', () => {
  it('collects key-shaped literals outside t(): constants, option tables, props, <Trans>', () => {
    const src = [
      "const KEY = 'a.constant';",
      "const OPTS = [{ labelKey: 'a.option' }];",
      '<X featureNameKey="a.prop" />',
      '<Trans i18nKey="a.trans" />',
      'const tpl = `a.template`;',
    ].join('\n');
    const keys = scanReferences(src, 'f.tsx').keyLiterals.map((r) => r.key);
    expect(keys).toEqual(['a.constant', 'a.option', 'a.prop', 'a.trans', 'a.template']);
  });

  it('does not read a single-segment string or a template with a placeholder as a key', () => {
    const src = `const a = 'plain'; const b = \`x.\${y}\`; const c = 'has space.x';`;
    expect(scanReferences(src, 'f.ts').keyLiterals).toEqual([]);
  });

  it('ignores a key literal left behind in a comment', () => {
    const src = "// const OLD = 'a.dead';\n/* 'b.dead' */\nconst x = 1;";
    expect(scanReferences(src, 'f.ts').keyLiterals).toEqual([]);
  });

  it("finds a key inside a template's placeholder, which is not a prefix of its own", () => {
    const src = `const a = \`\${cond ? 'a.lit' : 'a.other'}\`; t(\`b.outer.\${c ? 'b.lit' : x}\`);`;
    const keys = scanReferences(src, 'f.tsx').keyLiterals.map((r) => r.key);
    expect(keys).toEqual(['a.lit', 'a.other', 'b.lit']);
  });

  it('is not thrown off by a stray apostrophe earlier on the same line', () => {
    const src = [
      "<p>Don't <Trans i18nKey='a.jsx' /></p>",
      "s.replace(/'/g, ''); const k = 'a.regex';",
    ].join('\n');
    const keys = scanReferences(src, 'f.tsx').keyLiterals.map((r) => r.key);
    expect(keys).toEqual(['a.jsx', 'a.regex']);
  });

  it('takes the static head of a template literal as a prefix, even mid-segment', () => {
    const src = `t(\`pages.dashboard.activityTypes.\${item.type}\`); t(\`admin.orgUnits.unitType_\${type}\`);`;
    const prefixes = scanReferences(src, 'f.tsx').dynamicPrefixes.map((r) => r.key);
    expect(prefixes).toEqual(['pages.dashboard.activityTypes.', 'admin.orgUnits.unitType_']);
  });

  it("takes a 'prefix.' + expr concatenation as a prefix", () => {
    const src = "const k = 'components.documentLibrary.errorMessages.' + code;";
    const prefixes = scanReferences(src, 'f.ts').dynamicPrefixes.map((r) => r.key);
    expect(prefixes).toEqual(['components.documentLibrary.errorMessages.']);
  });

  it('takes a concatenation head that ends mid-segment as a prefix, like a template head', () => {
    const src = `const k = 'admin.orgUnits.unitType_' + type; const j = "h.pref" + code;`;
    const prefixes = scanReferences(src, 'f.ts').dynamicPrefixes.map((r) => r.key);
    expect(prefixes).toEqual(['admin.orgUnits.unitType_', 'h.pref']);
  });

  it('takes the head of a template opened on its own line', () => {
    const src = `t(\`\n  pages.x.\${y}\`);`;
    const prefixes = scanReferences(src, 'f.tsx').dynamicPrefixes.map((r) => r.key);
    expect(prefixes).toEqual(['pages.x.']);
  });

  it('ignores template heads that name no namespace: no dot, or no letter', () => {
    const src = `t(\`\${step.i18n_key}.title\`); fetch(\`/api/v1/exams/\${id}\`); t(\`plain\${x}\`);`;
    expect(scanReferences(src, 'f.tsx').dynamicPrefixes).toEqual([]);
  });
});

describe('effectivePrefixes — errors.* comes from the registry, not a prefix (TF-775 B)', () => {
  it('drops a dynamic errors. prefix and anything under it, keeps the rest, de-duplicates', () => {
    expect(effectivePrefixes(['errors.', 'errors.rag.', 'a.b.', 'a.b.'])).toEqual(['a.b.']);
  });
});

describe('coveredBy / findUnreferencedKeys — which locale keys are live (TF-775 B)', () => {
  const live = { exact: new Set(['a.exact', 'a.plural', 'a.parent']), prefixes: ['a.dyn.'] };

  it('covers a key exactly, as plural base, as ancestor, and by prefix', () => {
    expect(coveredBy('a.exact', live)).toBe('a.exact');
    expect(coveredBy('a.plural_one', live)).toBe('a.plural');
    expect(coveredBy('a.plural_other', live)).toBe('a.plural');
    expect(coveredBy('a.plural_zero', live)).toBe('a.plural');
    expect(coveredBy('a.plural_few', live)).toBe('a.plural');
    expect(coveredBy('a.plural_many', live)).toBe('a.plural');
    expect(coveredBy('a.parent.items.0', live)).toBe('a.parent');
    expect(coveredBy('a.dyn.anything', live)).toBe('a.dyn.*');
  });

  it('does not treat a key as the ancestor of a sibling with a longer name', () => {
    // `a.exact` must not cover `a.exactly` — ancestors split on dots, not characters.
    expect(coveredBy('a.exactly', live)).toBeNull();
  });

  it('lets only the registry decide inside errors.: no prefix, no ancestor literal', () => {
    const errorsLive = {
      exact: new Set(['errors.rag.known', 'errors.rag']),
      prefixes: effectivePrefixes(['errors.', 'errors.rag.']),
    };
    expect(coveredBy('errors.rag.known', errorsLive)).toBe('errors.rag.known');
    expect(findUnreferencedKeys(['errors.rag.known', 'errors.rag.unregistered'], errorsLive)).toEqual([
      'errors.rag.unregistered',
    ]);
  });

  it('reports what nothing covers, and only that', () => {
    const keys = ['a.exact', 'a.plural_one', 'a.dead', 'a.dyn.x', 'b.dead_one'];
    expect(findUnreferencedKeys(keys, live)).toEqual(['a.dead', 'b.dead_one']);
  });
});

describe('compareWithBaseline — the unreferenced-key ratchet only shrinks (TF-775 B)', () => {
  it('passes when current and baseline agree', () => {
    expect(compareWithBaseline(['a', 'b'], ['a', 'b'])).toEqual({ added: [], stale: [] });
  });

  it('reports a newly unreferenced key', () => {
    expect(compareWithBaseline(['a', 'new'], ['a'])).toEqual({ added: ['new'], stale: [] });
  });

  it('reports a baseline entry that is referenced again or was deleted', () => {
    expect(compareWithBaseline(['a'], ['a', 'gone'])).toEqual({ added: [], stale: ['gone'] });
  });
});

describe('collectI18nKeys — i18n_key values in a data file (TF-775 B)', () => {
  it('finds i18n_key at any depth, in objects and arrays, and nothing else', () => {
    const data = {
      teacher: { core: [{ step: 0, i18n_key: 'help.tour.a' }], tracks: [{ i18n_key: 'help.tour.b', label: 'x.y' }] },
      i18n_key: 42,
    };
    expect(collectI18nKeys(data)).toEqual(['help.tour.a', 'help.tour.b']);
  });
});

describe('absentScanRoots — part C only runs with every tier present (TF-775 B)', () => {
  const roots = [
    { dir: '/r/core/frontend/src', prefix: 'core/frontend/src' },
    { dir: '/r/premium/frontend/src', prefix: 'premium/frontend/src' },
    { dir: '/r/enterprise/frontend/src', prefix: 'enterprise/frontend/src' },
  ];

  it('reports nothing when every root exists (the private repo)', () => {
    expect(absentScanRoots(roots, () => true)).toEqual([]);
  });

  it('reports the tiers the public mirror lacks', () => {
    const mirror = (dir: string) => dir.includes('/core/');
    expect(absentScanRoots(roots, mirror)).toEqual(['premium/frontend/src', 'enterprise/frontend/src']);
  });
});

describe('partCMode — only a mirror may skip part C, and never where every tier is required (TF-775 B)', () => {
  const roots = [
    { prefix: 'core/frontend/src' },
    { prefix: 'premium/frontend/src' },
    { prefix: 'enterprise/frontend/src' },
  ];
  const tiers = ['premium/frontend/src', 'enterprise/frontend/src'];

  it('runs when nothing is absent, whether or not every tier is required', () => {
    expect(partCMode([], roots, false)).toEqual({ mode: 'run' });
    expect(partCMode([], roots, true)).toEqual({ mode: 'run' });
  });

  it('skips in the public mirror, where every tier outside core/ is absent', () => {
    expect(partCMode(tiers, roots, false)).toEqual({ mode: 'skip' });
  });

  it('fails when only one tier is absent — a renamed or removed tier, not a mirror', () => {
    expect(partCMode(['enterprise/frontend/src'], roots, false).mode).toBe('fail');
    expect(partCMode(['premium/frontend/src'], roots, false).mode).toBe('fail');
  });

  it('fails instead of skipping when every tier is required (the private CI)', () => {
    expect(partCMode(tiers, roots, true).mode).toBe('fail');
  });
});

describe('widePrefixes — broad prefixes are listed, widest first (TF-775 B)', () => {
  it('counts the keys under each prefix and keeps those at or above the floor', () => {
    const keys = ['a.x.1', 'a.x.2', 'a.x.3', 'b.y.1', 'b.y.2', 'c.z.1'];
    expect(widePrefixes(['b.y.', 'a.x.', 'c.z.'], keys, 2)).toEqual([
      { prefix: 'a.x.', covers: 3 },
      { prefix: 'b.y.', covers: 2 },
    ]);
  });
});
