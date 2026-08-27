/**
 * Guard against missing i18n translations.
 *
 * Why: a `t('foo.bar')` call where `foo.bar` does not exist in a translation
 * file silently renders the raw key in the UI (see TF-331 / Dokument-ChatBot
 * regression where `premium.chatInterface.documentCount` leaked into the
 * header chip). Component tests do not catch this because the mock in
 * `setupTests.ts` returns the key string when a translation is missing.
 *
 * What this test enforces:
 *   1. Every static `t('...')` / `i18n.t('...')` key referenced anywhere in
 *      core/frontend/src or premium/frontend/src resolves to a DE string.
 *   2. Every such key also resolves to an EN string (DE+EN are the actively
 *      maintained primary locales; missing keys would yield mixed-language UI
 *      via the DE fallback).
 *   3. DE and EN have full logical-key parity (no extras on either side).
 *
 * Out of scope: FR/IT parity. Both currently lag DE by ~70 keys (`help.*`).
 * Closing that gap is tracked separately; this test relies on the i18next
 * fallback to DE for those locales until then.
 *
 * Limitations: only literal string arguments are scanned. Dynamic keys such
 * as `` t(`pages.dashboard.activityTypes.${type}`) `` are skipped — there is
 * no static way to enumerate them.
 */

import * as fs from 'fs';
import * as path from 'path';

import deTranslations from '../locales/de/translation.json';
import enTranslations from '../locales/en/translation.json';

const REPO_ROOT = path.resolve(__dirname, '../../../..');
const SCAN_ROOTS = [
  path.resolve(__dirname, '..'),
  path.resolve(REPO_ROOT, 'premium/frontend/src'),
  path.resolve(REPO_ROOT, 'enterprise/frontend/src'),
];

const SOURCE_EXT = /\.(ts|tsx|js|jsx)$/;
const SKIP_DIRS = new Set([
  'node_modules',
  '__tests__',
  '__mocks__',
  'build',
  'dist',
  'coverage',
  'locales',
]);
const SKIP_FILE = /\.(test|spec)\.(ts|tsx|js|jsx)$|\.d\.ts$/;

// Matches t('a.b'), t("a.b"), i18n.t('a.b'), i18next.t('a.b').
// Lookbehind rules out identifiers ending in `t` like getByText, setCommentText.
const T_CALL = /(?<![a-zA-Z0-9_$])t\(\s*(['"])([a-zA-Z0-9_.]+)\1/g;

const PLURAL_SUFFIX = /_(zero|one|two|few|many|other)$/;
const PLURAL_VARIANTS = ['_zero', '_one', '_two', '_few', '_many', '_other'];

interface Callsite {
  key: string;
  file: string;
  line: number;
}

function walk(dir: string, out: string[] = []): string[] {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, out);
    } else if (SOURCE_EXT.test(entry.name) && !SKIP_FILE.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

function collectCallsites(): Callsite[] {
  const calls: Callsite[] = [];
  for (const root of SCAN_ROOTS) {
    for (const file of walk(root)) {
      const lines = fs.readFileSync(file, 'utf8').split('\n');
      const rel = path.relative(REPO_ROOT, file);
      lines.forEach((line, i) => {
        line.replace(T_CALL, (_match, _quote, key: string) => {
          calls.push({ key, file: rel, line: i + 1 });
          return _match;
        });
      });
    }
  }
  return calls;
}

function flattenKeys(obj: unknown, prefix = '', out: Set<string> = new Set()): Set<string> {
  if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      const next = prefix ? `${prefix}.${k}` : k;
      // Arrays are a valid leaf translation value (used with
      // t(key, { returnObjects: true }), e.g. legal.privacy.subprocessors.items)
      // — treat them like strings instead of recursing into them, which
      // would otherwise silently drop the key from the resolved set.
      if (typeof v === 'string' || Array.isArray(v)) out.add(next);
      else flattenKeys(v, next, out);
    }
  }
  return out;
}

function resolves(allKeys: Set<string>, key: string): boolean {
  if (allKeys.has(key)) return true;
  for (const suffix of PLURAL_VARIANTS) {
    if (allKeys.has(`${key}${suffix}`)) return true;
  }
  return false;
}

function formatMissing(missing: Callsite[]): string {
  const head = missing
    .slice(0, 50)
    .map((m) => `  ${m.key}  →  ${m.file}:${m.line}`)
    .join('\n');
  const tail = missing.length > 50 ? `\n  ... (+${missing.length - 50} more)` : '';
  return `${head}${tail}`;
}

describe('i18n key coverage', () => {
  const callsites = collectCallsites();
  const deKeys = flattenKeys(deTranslations);
  const enKeys = flattenKeys(enTranslations);

  it('finds at least one t() call (sanity check)', () => {
    expect(callsites.length).toBeGreaterThan(100);
  });

  it('every t() key referenced in source resolves to a DE translation', () => {
    const missing = callsites.filter((c) => !resolves(deKeys, c.key));
    if (missing.length > 0) {
      throw new Error(
        `Missing DE translations for ${missing.length} key(s):\n${formatMissing(missing)}`,
      );
    }
  });

  it('every t() key referenced in source resolves to an EN translation', () => {
    const missing = callsites.filter((c) => !resolves(enKeys, c.key));
    if (missing.length > 0) {
      throw new Error(
        `Missing EN translations for ${missing.length} key(s):\n${formatMissing(missing)}`,
      );
    }
  });

  it('DE and EN have full logical-key parity', () => {
    const stripPlural = (k: string): string => k.replace(PLURAL_SUFFIX, '');
    const logical = (s: Set<string>): Set<string> =>
      new Set(Array.from(s, stripPlural));
    const deLog = logical(deKeys);
    const enLog = logical(enKeys);
    const missingInEn = Array.from(deLog).filter((k) => !enLog.has(k)).sort();
    const extraInEn = Array.from(enLog).filter((k) => !deLog.has(k)).sort();
    const issues: string[] = [];
    if (missingInEn.length > 0) {
      issues.push(`EN missing ${missingInEn.length} key(s) present in DE: ${missingInEn.join(', ')}`);
    }
    if (extraInEn.length > 0) {
      issues.push(`EN has ${extraInEn.length} key(s) not in DE: ${extraInEn.join(', ')}`);
    }
    if (issues.length > 0) {
      throw new Error(issues.join('\n'));
    }
  });
});
