/**
 * ExamCraft AI — the frontend i18n key gate (TF-670, consolidated in TF-772)
 *
 * The single gate for the frontend locale files. It answers two questions:
 *
 *   A. Are the four locales complete and in sync?
 *      1. Every expected language has its translation.json — a deleted file OR a
 *         deleted directory fails, it is not silently skipped.
 *      2. No locale loses keys against the reference (de) or carries extra ones.
 *         A locale's own valid CLDR plural set (French `_one`/`_many`/`_other`
 *         next to German `_one`/`_other`) is not an extra/missing key.
 *      3. No interpolation placeholder is dropped or renamed.
 *      4. No value is empty: '', whitespace only, `{}` or `[]` — in any locale,
 *         the reference included.
 *
 *   B. Does every key the source spends statically actually exist?
 *      5. Every literal `t('…')` / `i18n.t('…')` key in core, premium and
 *         enterprise resolves to a non-empty value in all four locales.
 *      6. Every `translateError(err, t, '…')` fallback key and every
 *         `fallbackKey: '…'` property does the same (no plural leniency: those
 *         calls pass no count). A translateError call whose third argument is
 *         not a literal must be listed in DOCUMENTED_DYNAMIC_CALLS.
 *
 * Why this exists: i18n.ts sets `fallbackLng: 'de'`, so a missing key does not
 * surface as an empty string or a raw key name — it silently renders German
 * text to a French or Italian user. TF-670 found 410 such keys in fr and it
 * that had accumulated unnoticed since the initial extraction (TF-295).
 *
 * What it replaced (TF-772 PR 6): four overlapping guards —
 * `src/__tests__/i18n-keys.test.ts` (B5, but DE/EN only),
 * `src/__tests__/i18n-fallback-keys.test.ts` (B6),
 * `src/__tests__/aktivitaeten-i18n-parity.test.ts` (A2 for one namespace) and
 * the `releaseNotes translation completeness` block in
 * ReleaseNotesDialog.test.tsx (A2 for another). None of them saw everything;
 * this script alone missed empty values, `{}`, a deleted locale directory and
 * every source-side reference. The perturbation matrix in the PR shows which
 * guard caught what before and that this one catches the union.
 *
 * Not replaced, on purpose: guards whose input is a registry this scan cannot
 * see — `AppErrorCode.i18n.test.ts` (APP_ERROR_CODES), `QuotaBanner.i18n.test.ts`
 * (QUOTA_ERROR_CODES), `help-hint-keys.test.ts` (the Python seed),
 * `onboardingStepsI18n.test.ts` (help-onboarding-steps.json) and
 * `releaseNotes.test.ts` (RELEASE_NOTES). They check dynamic keys
 * (`t(`errors.${code}`)`), which a literal scan cannot enumerate.
 *
 * Frontend locales only. The backend's `core/backend/locales/t.<lang>.json`
 * are gated by `core/backend/tests/test_locale_parity.py` (TF-773 Part C).
 *
 * Usage:
 *   bun run i18n:check        (runs the self-test below first, then the gate)
 *
 * The pure logic is exported and covered by check-i18n-keys.test.ts against
 * fixtures — the gate itself needs a regression guard, not just the locale
 * files it checks.
 */

import * as fs from 'fs';
import * as path from 'path';

import { SCAN_ROOTS, stripComments } from './i18n-hardcoded-strings-scan';

/** i18next default interpolation. Tolerates the `{{ name }}` spacing variant. */
const PLACEHOLDER = /\{\{\s*([A-Za-z0-9_]+)\s*\}\}/g;

/** How many offending keys to print per finding before truncating. */
const SAMPLE_SIZE = 15;

/**
 * The languages i18n.ts loads. Fixed rather than read from the directory: a
 * language that disappears from disk must fail here, not drop out of the
 * comparison (it did — a deleted `fr/` directory used to pass).
 */
export const LANGUAGES = ['de', 'en', 'fr', 'it'] as const;
export const REFERENCE = 'de';

export type Flat = Map<string, unknown>;

/**
 * Arrays are descended into by index (`…items.0.name`), not treated as opaque
 * leaves: PrivacyPage.tsx reads `legal.privacy.subprocessors.items` with
 * `returnObjects: true` and maps over it, so a translation that drops or
 * reorders an entry breaks the page just as a missing string key would.
 *
 * An empty object/array (`{}`/`[]`) has no entries to descend into and would
 * otherwise vanish from the flattened map on both sides of the comparison.
 * The prefix itself is recorded as a key so it stays visible — and
 * `emptyValues` then reports it: an empty container is never a valid
 * translation, whether or not the other locales agree on the key.
 */
export function flatten(node: unknown, prefix = '', out: Flat = new Map()): Flat {
  if (node !== null && typeof node === 'object') {
    const entries = Object.entries(node);
    if (entries.length === 0 && prefix) {
      out.set(prefix, node);
      return out;
    }
    for (const [key, value] of entries) {
      flatten(value, prefix ? `${prefix}.${key}` : key, out);
    }
  } else {
    out.set(prefix, node);
  }
  return out;
}

export function placeholders(value: unknown): string[] {
  if (typeof value !== 'string') return [];
  return [...value.matchAll(PLACEHOLDER)].map((m) => m[1]).sort();
}

export interface LocaleDiff {
  missing: string[];
  extra: string[];
  brokenPlaceholders: string[];
}

const PLURAL_SUFFIX_RE = /_(zero|one|two|few|many|other)$/;

/**
 * Strips a trailing CLDR plural suffix. Used only to decide whether a key's
 * *namespace* is present on both sides — French's three-way `_one`/`_many`/
 * `_other` next to German's two-way `_one`/`_other` is a valid difference per
 * language, not a missing/extra key, the same leniency `resolves()` already
 * grants source references below.
 */
const pluralBase = (key: string): string => key.replace(PLURAL_SUFFIX_RE, '');

/**
 * `_other` is CLDR's mandatory catch-all: every language's plural set
 * includes it. So "does the other side have a valid plural set for this
 * base" is answered by "does it have `<base>_other`" — not merely "does it
 * have *any* suffix under this base". The looser check (any suffix present)
 * would also forgive a locale that dropped `_other` entirely while keeping
 * `_one`, which is exactly the TF-670 defect class (German fallback for
 * every count ≠ 1) this gate exists to catch.
 */
const hasValidPluralSet = (flat: Flat, base: string): boolean => flat.has(`${base}_other`);

/** Pure comparison of one target locale against the reference — no I/O. */
export function diffLocale(reference: Flat, target: Flat): LocaleDiff {
  const referenceKeys = [...reference.keys()];
  const targetKeys = [...target.keys()];

  const missing = referenceKeys.filter((key) => {
    if (target.has(key)) return false;
    if (!PLURAL_SUFFIX_RE.test(key)) return true;
    return !hasValidPluralSet(target, pluralBase(key));
  });
  const extra = targetKeys.filter((key) => {
    if (reference.has(key)) return false;
    if (!PLURAL_SUFFIX_RE.test(key)) return true;
    return !hasValidPluralSet(reference, pluralBase(key));
  });
  const brokenPlaceholders = referenceKeys
    .filter((key) => target.has(key))
    .filter((key) => {
      const want = placeholders(reference.get(key));
      const got = placeholders(target.get(key));
      return want.join('|') !== got.join('|');
    });
  return { missing, extra, brokenPlaceholders };
}

/**
 * Keys whose value renders nothing: an empty or whitespace-only string, an
 * empty object/array, or a non-string scalar (`null`, a number). Before
 * TF-772 PR 6 no gate caught `''` unless the reference text happened to carry
 * a placeholder, and `{}` in fr passed as "key present".
 */
export function emptyValues(flat: Flat): string[] {
  return [...flat.entries()]
    .filter(([, value]) => {
      if (typeof value === 'string') return value.trim() === '';
      if (value !== null && typeof value === 'object') return Object.keys(value).length === 0;
      return true;
    })
    .map(([key]) => key);
}

// ---------------------------------------------------------------------------
// Source references
// ---------------------------------------------------------------------------

/**
 * Matches t('a.b'), t("a.b"), i18n.t('a.b'), i18next.t('a.b'). The lookbehind
 * rules out identifiers ending in `t` like getByText. The charset includes
 * `-` for the handful of keys under a hyphenated segment
 * (`help.tour.teacher.tracks.exam-composer`) — those are only reached
 * dynamically today, but a future literal reference to one must not go
 * unverified because the pattern silently failed to match. No `:` — nothing
 * in this codebase uses i18next's `ns:key` namespace syntax.
 */
export const T_CALL = /(?<![a-zA-Z0-9_$])t\(\s*(['"])([a-zA-Z0-9_.-]+)\1/g;

/** A quoted string literal, either quote style. Captures the contents in group 2. */
const STRING_LITERAL = /^(['"])([^'"]*)\1$/;

/**
 * `translateError(err, t, thirdArg)`. Captures `thirdArg` verbatim — a quoted
 * literal or an arbitrary expression — and leaves classifying it to
 * `scanReferences`, so both quote styles resolve the same key exactly like
 * `T_CALL` does. The first argument may itself be one call deep,
 * `translateError(appErrorFromApiError(err, 'code'), t, 'some.key')`
 * (TF-772 PR 7); without the nested group every such call would read as
 * dynamic. The optional comma before `)` is Prettier's trailing comma once
 * the call spans several lines.
 */
export const TRANSLATE_ERROR_CALL =
  /translateError\(\s*((?:[^,()]|\([^()]*\))+),\s*([^,()]+),\s*([^,()]+?)\s*,?\s*\)/g;

/**
 * Any translateError call at all — the sanity net for a call whose formatting
 * `TRANSLATE_ERROR_CALL` cannot parse (e.g. more than one nesting level in the
 * first argument). Such a call still counts as dynamic below; it just cannot
 * contribute its argument text to the `DOCUMENTED_DYNAMIC_CALLS` content
 * check, only to the count.
 *
 * Known gap: `translateError<T>(...)` — a generic call — is invisible to this
 * pattern too, since `<T>` sits between the name and `(`. `translateError` is
 * not generic anywhere today; narrowing this is speculative until it is.
 */
const TRANSLATE_ERROR_ANY = /translateError\(/g;

/**
 * `fallbackKey: 'some.key'` — the deferred shape. ReviewQueue stores the key
 * with the error and spends it at render time, so the literal never appears
 * inside a translateError call. Either quote style, same reasoning as above.
 */
export const FALLBACK_KEY_PROPERTY = /\bfallbackKey:\s*(['"])([^'"]+)\1/g;

/**
 * translateError call sites whose third argument is an expression rather than
 * a literal. The list exists so the gate cannot go quiet: a new dynamic call
 * site fails until its author either passes a literal or documents it here.
 * `calls` pins both *how many* dynamic calls the file has AND *which*
 * expressions they pass — swapping one documented dynamic call for a
 * different, undocumented one leaves the count unchanged but changes the
 * expression, so it still fails. The literals those expressions resolve to at
 * runtime are reachable through `fallbackKey:` properties, checked above.
 */
export const DOCUMENTED_DYNAMIC_CALLS: Array<{ file: string; calls: string[]; why: string }> = [
  {
    file: 'core/frontend/src/components/ReviewQueue.tsx',
    calls: ['failure.fallbackKey', 'deleteFailure.fallbackKey'],
    why: 'Failure = { error, fallbackKey } for the queue and for the delete dialog: the key is chosen in the catch and spent at render, so the literals sit in `fallbackKey:` properties.',
  },
  {
    file: 'core/frontend/src/errors/translateError.ts',
    calls: ['fallbackKey: string'],
    why: 'The declaration itself — `export function translateError(err: unknown, t: Translate, fallbackKey: string): string`. The captured "call" is really the third parameter, its type annotation included; listed rather than special-cased, so the gate keeps failing if the signature is ever reused elsewhere in that file.',
  },
];

export interface Reference {
  key: string;
  file: string;
  line: number;
}

export interface DynamicCall {
  expr: string;
  file: string;
  line: number;
}

export interface SourceReferences {
  /** Literal t() keys. Plural-lenient: `t('x', { count })` reads `x_one`/`x_other`. */
  tKeys: Reference[];
  /** translateError / fallbackKey literals. Exact: those calls pass no count. */
  fallbackKeys: Reference[];
  /** translateError calls without a literal third argument — count used for the per-file DOCUMENTED_DYNAMIC_CALLS match. */
  dynamicCalls: number;
  /** The parseable ones among `dynamicCalls`, with their raw argument expression. */
  dynamicCallExprs: DynamicCall[];
}

const lineAt = (src: string, index: number): number => src.slice(0, index).split('\n').length;

/**
 * Pure scan of one source file, against the comment-stripped text throughout
 * — a `t('dead.key')` left behind in a `//` comment must not read as a live
 * reference and fail the gate for a key nobody calls, the same reason
 * translateError is read from stripped text. Line numbers therefore refer to
 * the stripped text and are approximate across a removed block comment.
 *
 * Two known, currently-inert gaps inherited from `stripComments`: it strips
 * `/^\s*\/\/.*$/gm`, so a `//` comment trailing on the same line as live code
 * is not stripped (`t('live'); // t('dead')` still finds both); and it is not
 * string-literal-aware, so a block-comment opener/closer pair sitting inside
 * a string could in principle eat real code up to the next closer. Neither
 * has ever fired here — a full-tree raw-vs-stripped diff finds 0 key drift —
 * narrowing them would need `stripComments` itself to track string context.
 */
export function scanReferences(src: string, file: string): SourceReferences {
  const code = stripComments(src);

  const tKeys = [...code.matchAll(T_CALL)].map((m) => ({
    key: m[2],
    file,
    line: lineAt(code, m.index ?? 0),
  }));

  const fallbackKeys: Reference[] = [];
  const dynamicCallExprs: DynamicCall[] = [];
  let literalCallCount = 0;

  for (const m of code.matchAll(TRANSLATE_ERROR_CALL)) {
    const line = lineAt(code, m.index ?? 0);
    const literal = m[3].match(STRING_LITERAL);
    if (literal) {
      fallbackKeys.push({ key: literal[2], file, line });
      literalCallCount++;
    } else {
      dynamicCallExprs.push({ expr: m[3].trim(), file, line });
    }
  }
  for (const m of code.matchAll(FALLBACK_KEY_PROPERTY)) {
    fallbackKeys.push({ key: m[2], file, line: lineAt(code, m.index ?? 0) });
  }

  // A call whose shape TRANSLATE_ERROR_CALL cannot parse at all (e.g. more
  // than one nesting level in the first argument) still shows up here, via
  // the gap between the raw `translateError(` count and what actually parsed
  // — and still counts as dynamic, conservatively, rather than vanishing.
  const totalCalls = [...code.matchAll(TRANSLATE_ERROR_ANY)].length;
  const parsedCalls = literalCallCount + dynamicCallExprs.length;
  const dynamicCalls = dynamicCallExprs.length + Math.max(0, totalCalls - parsedCalls);

  return { tKeys, fallbackKeys, dynamicCalls, dynamicCallExprs };
}

/**
 * Which files disagree with `DOCUMENTED_DYNAMIC_CALLS` — either a different
 * number of dynamic `translateError` calls, or (only once every call in the
 * file actually parsed) a different set of argument expressions. Pure and
 * exported so the defect class this whole mechanism exists to catch —
 * swapping one documented dynamic call for a different, undocumented one
 * without changing the count — is pinned by a fixture in
 * check-i18n-keys.test.ts, not only exercised incidentally by the real
 * ReviewQueue.tsx/translateError.ts on every CI run.
 */
export function findUndocumentedDynamicCalls(
  dynamicByFile: ReadonlyMap<string, number>,
  dynamicExprsByFile: ReadonlyMap<string, readonly string[]>,
  documentedCalls: ReadonlyMap<string, readonly string[]>
): string[] {
  const files = new Set([...documentedCalls.keys(), ...dynamicByFile.keys()]);
  return [...files].filter((file) => {
    const expectedCalls = documentedCalls.get(file) ?? [];
    const actualCount = dynamicByFile.get(file) ?? 0;
    if (actualCount !== expectedCalls.length) return true;
    const actualExprs = [...(dynamicExprsByFile.get(file) ?? [])].sort();
    // A call whose shape TRANSLATE_ERROR_CALL cannot parse contributes to
    // actualCount but not to actualExprs — fail rather than silently trust
    // the count alone: an unparseable call is exactly the shape a swapped,
    // undocumented dynamic call could take.
    if (actualExprs.length !== actualCount) return true;
    return JSON.stringify(actualExprs) !== JSON.stringify([...expectedCalls].sort());
  });
}

const SOURCE_EXT = /\.(ts|tsx|js|jsx)$/;
const SKIP_DIRS = new Set(['node_modules', '__tests__', '__mocks__', 'build', 'dist', 'coverage', 'locales']);
const SKIP_FILE = /\.(test|spec)\.(ts|tsx|js|jsx)$|\.d\.ts$/;

/**
 * The union of what the two former guards walked: .js/.jsx and `types/` from
 * i18n-keys.test.ts, the mirror-safe fixed path prefixes (SCAN_ROOTS) from the
 * hardcoded-strings scan. A tier absent from the checkout (public mirror) is
 * skipped, not an error.
 */
function sourceFiles(dir: string, out: string[] = []): string[] {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) sourceFiles(full, out);
    else if (SOURCE_EXT.test(entry.name) && !SKIP_FILE.test(entry.name)) out.push(full);
  }
  return out;
}

/** Walks a locale tree by dotted key; arrays count as leaves (`returnObjects`). */
export function lookup(bundle: unknown, key: string): unknown {
  return key.split('.').reduce<unknown>((node, part) => {
    if (node === null || typeof node !== 'object' || Array.isArray(node)) return undefined;
    return (node as Record<string, unknown>)[part];
  }, bundle);
}

const PLURAL_SUFFIXES = ['_zero', '_one', '_two', '_few', '_many', '_other'];

const renders = (value: unknown): boolean =>
  (typeof value === 'string' && value.trim() !== '') || (Array.isArray(value) && value.length > 0);

/** True when `key` renders text in `bundle`; with `plural`, a `_one`/`_other` form suffices. */
export function resolves(bundle: unknown, key: string, plural: boolean): boolean {
  if (renders(lookup(bundle, key))) return true;
  return plural && PLURAL_SUFFIXES.some((suffix) => renders(lookup(bundle, `${key}${suffix}`)));
}

// ---------------------------------------------------------------------------
// Reporting
// ---------------------------------------------------------------------------

function sample(keys: string[]): string {
  const shown = keys.slice(0, SAMPLE_SIZE).map((k) => `      ${k}`);
  if (keys.length > SAMPLE_SIZE) {
    shown.push(`      … and ${keys.length - SAMPLE_SIZE} more`);
  }
  return shown.join('\n');
}

const LOCALE_DIR = path.resolve(import.meta.dir, '../src/locales');
const localeFile = (lang: string): string => path.join(LOCALE_DIR, lang, 'translation.json');

/**
 * Which expected locale files are missing, and which on-disk directories
 * aren't among `LANGUAGES` — pure, so "a deleted directory fails" and "an
 * unexpected directory fails" (header, point A1) are pinned by a fixture in
 * check-i18n-keys.test.ts, not only exercised incidentally by whatever
 * src/locales/ happens to contain on a given CI run.
 */
export function analyzeLocaleDirs(
  existingFiles: ReadonlySet<string>,
  dirEntries: readonly string[]
): { missingFiles: string[]; unexpectedDirs: string[] } {
  return {
    missingFiles: LANGUAGES.filter((lang) => !existingFiles.has(lang)),
    unexpectedDirs: dirEntries.filter((name) => !(LANGUAGES as readonly string[]).includes(name)),
  };
}

/** Part A: presence, parity, placeholders, empty values. Returns failures + the loaded bundles. */
function checkLocales(): { failures: string[]; bundles: Map<string, unknown> } {
  const failures: string[] = [];
  const bundles = new Map<string, unknown>();

  if (!fs.existsSync(LOCALE_DIR)) {
    failures.push(`src/locales/ is missing entirely`);
    return { failures, bundles };
  }

  const existingFiles = new Set(LANGUAGES.filter((lang) => fs.existsSync(localeFile(lang))));
  for (const lang of existingFiles) {
    bundles.set(lang, JSON.parse(fs.readFileSync(localeFile(lang), 'utf-8')));
  }
  const dirEntries = fs
    .readdirSync(LOCALE_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name);
  const { missingFiles, unexpectedDirs } = analyzeLocaleDirs(existingFiles, dirEntries);

  for (const lang of missingFiles) {
    failures.push(`${lang}: src/locales/${lang}/translation.json is missing`);
  }
  if (unexpectedDirs.length) {
    failures.push(`unexpected locale directory: ${unexpectedDirs.join(', ')} (add it to LANGUAGES and i18n.ts)`);
  }

  if (!bundles.has(REFERENCE)) return { failures, bundles };

  const reference = flatten(bundles.get(REFERENCE));
  console.log(`\ni18n locale parity — reference "${REFERENCE}" (${reference.size} keys)\n`);

  for (const lang of LANGUAGES) {
    if (!bundles.has(lang)) {
      console.log(`  ✗ ${lang} — file missing`);
      continue;
    }
    const target = lang === REFERENCE ? reference : flatten(bundles.get(lang));
    const { missing, extra, brokenPlaceholders } =
      lang === REFERENCE ? { missing: [], extra: [], brokenPlaceholders: [] } : diffLocale(reference, target);
    const empty = emptyValues(target);
    const ok = !missing.length && !extra.length && !brokenPlaceholders.length && !empty.length;
    console.log(`  ${ok ? '✓' : '✗'} ${lang} — ${target.size} keys`);

    if (missing.length) {
      failures.push(`${lang}: ${missing.length} key(s) missing against ${REFERENCE}`);
      console.log(`    missing (${missing.length}):\n${sample(missing)}`);
    }
    if (extra.length) {
      failures.push(`${lang}: ${extra.length} key(s) not present in ${REFERENCE}`);
      console.log(`    unknown to ${REFERENCE} (${extra.length}):\n${sample(extra)}`);
    }
    if (brokenPlaceholders.length) {
      failures.push(`${lang}: ${brokenPlaceholders.length} placeholder mismatch(es)`);
      const detail = brokenPlaceholders.slice(0, SAMPLE_SIZE).map((key) => {
        const want = placeholders(reference.get(key)).join(', ') || '—';
        const got = placeholders(target.get(key)).join(', ') || '—';
        return `      ${key}: ${REFERENCE}={${want}} ${lang}={${got}}`;
      });
      if (brokenPlaceholders.length > SAMPLE_SIZE) {
        detail.push(`      … and ${brokenPlaceholders.length - SAMPLE_SIZE} more`);
      }
      console.log(`    placeholder mismatch (${brokenPlaceholders.length}):\n${detail.join('\n')}`);
    }
    if (empty.length) {
      failures.push(`${lang}: ${empty.length} empty value(s)`);
      console.log(`    empty ('' / {} / []) (${empty.length}):\n${sample(empty)}`);
    }
  }

  return { failures, bundles };
}

/** Part B: every statically visible key the source spends resolves in every loaded locale. */
function checkReferences(bundles: Map<string, unknown>): string[] {
  const failures: string[] = [];
  const tKeys: Reference[] = [];
  const fallbackKeys: Reference[] = [];
  const dynamicByFile = new Map<string, number>();
  const dynamicExprsByFile = new Map<string, string[]>();

  for (const { dir, prefix } of SCAN_ROOTS) {
    for (const file of sourceFiles(dir)) {
      const rel = `${prefix}/${file.slice(dir.length + 1).split(/[\\/]/).join('/')}`;
      const found = scanReferences(fs.readFileSync(file, 'utf8'), rel);
      tKeys.push(...found.tKeys);
      fallbackKeys.push(...found.fallbackKeys);
      if (found.dynamicCalls > 0) dynamicByFile.set(rel, found.dynamicCalls);
      if (found.dynamicCallExprs.length) {
        dynamicExprsByFile.set(rel, found.dynamicCallExprs.map((d) => d.expr));
      }
    }
  }

  console.log(
    `\ni18n source references — ${tKeys.length} t() call(s), ${fallbackKeys.length} fallback key(s)\n`
  );

  // Sanity floors: a scan pattern that stops matching must not turn the gate
  // green by checking nothing at all.
  if (tKeys.length <= 100) failures.push(`only ${tKeys.length} t() call(s) found — scan pattern broken?`);
  if (fallbackKeys.length <= 20) {
    failures.push(`only ${fallbackKeys.length} fallback key(s) found — scan pattern broken?`);
  }

  for (const [kind, refs, plural] of [
    ['t()', tKeys, true],
    ['fallback', fallbackKeys, false],
  ] as const) {
    for (const [lang, bundle] of bundles) {
      const unresolved = refs.filter((ref) => !resolves(bundle, ref.key, plural));
      if (!unresolved.length) continue;
      failures.push(`${lang}: ${unresolved.length} ${kind} key(s) referenced in source do not resolve`);
      console.log(
        `  ✗ ${lang} — unresolved ${kind} key(s) (${unresolved.length}):\n` +
          sample(unresolved.map((r) => `${r.key}  →  ${r.file}:${r.line}`))
      );
    }
  }

  const documented = new Map(DOCUMENTED_DYNAMIC_CALLS.map((d) => [d.file, d.calls]));
  const mismatched = findUndocumentedDynamicCalls(dynamicByFile, dynamicExprsByFile, documented);
  if (mismatched.length) {
    failures.push(`${mismatched.length} file(s) with undocumented non-literal translateError calls`);
    console.log(
      `  ✗ translateError without a literal fallback key — pass a literal, flatten a first ` +
        `argument nested more than one call deep (e.g. wrap(inner(err, 'x'))), or update ` +
        `DOCUMENTED_DYNAMIC_CALLS with the exact expression(s):\n` +
        sample(
          mismatched.map((f) => {
            const actual = dynamicExprsByFile.get(f)?.join(', ') || String(dynamicByFile.get(f) ?? 0);
            const expected = documented.get(f)?.join(', ') || 'none';
            return `${f}: found [${actual}], documented [${expected}]`;
          })
        )
    );
  }

  return failures;
}

if (import.meta.main) {
  const { failures, bundles } = checkLocales();
  failures.push(...checkReferences(bundles));

  if (failures.length) {
    console.error('\nFAIL — frontend i18n is out of sync:');
    for (const failure of failures) console.error(`  - ${failure}`);
    console.error(
      `\nAdd the missing translations to the locale file(s) named above.\n` +
        `A missing key falls back to the reference language at runtime, so users\n` +
        `see the wrong language rather than a visible error — that is why this\n` +
        `check is a hard gate.`
    );
    process.exit(1);
  }

  console.log('\nOK — all four locales complete and in sync, every static source reference resolves.');
}
