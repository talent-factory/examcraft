/**
 * ExamCraft AI — i18n key parity check (TF-670)
 *
 * Compares every locale under src/locales/ against the reference language.
 * Fails when a language loses keys against the reference, carries keys the
 * reference doesn't have, or drops an interpolation placeholder.
 *
 * Why this exists: i18n.ts sets `fallbackLng: 'de'`, so a missing key does not
 * surface as an empty string or a raw key name — it silently renders German
 * text to a French or Italian user. TF-670 found 410 such keys in fr and it
 * that had accumulated unnoticed since the initial extraction (TF-295).
 *
 * Usage:
 *   bun run i18n:check
 *
 * The comparison logic below is exported and covered by
 * check-i18n-keys.test.ts (`bun test scripts/`) against fixture objects — the
 * gate itself needs a regression guard, not just the locale files it checks.
 */

import * as fs from 'fs';
import * as path from 'path';

/** i18next default interpolation. Tolerates the `{{ name }}` spacing variant. */
const PLACEHOLDER = /\{\{\s*([A-Za-z0-9_]+)\s*\}\}/g;

/** How many offending keys to print per finding before truncating. */
const SAMPLE_SIZE = 15;

export type Flat = Map<string, unknown>;

/**
 * Arrays are descended into by index (`…items.0.name`), not treated as opaque
 * leaves: PrivacyPage.tsx reads `legal.privacy.subprocessors.items` with
 * `returnObjects: true` and maps over it, so a translation that drops or
 * reorders an entry breaks the page just as a missing string key would.
 *
 * An empty object/array (`{}`/`[]`) has no entries to descend into and would
 * otherwise vanish from the flattened map on both sides of the comparison —
 * silently swallowing a locale value that renders nothing at all. The
 * prefix itself is recorded as a key in that case so it participates in the
 * missing/extra comparison like any leaf.
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

/** Pure comparison of one target locale against the reference — no I/O. */
export function diffLocale(reference: Flat, target: Flat): LocaleDiff {
  const referenceKeys = [...reference.keys()];
  const missing = referenceKeys.filter((key) => !target.has(key));
  const extra = [...target.keys()].filter((key) => !reference.has(key));
  const brokenPlaceholders = referenceKeys
    .filter((key) => target.has(key))
    .filter((key) => {
      const want = placeholders(reference.get(key));
      const got = placeholders(target.get(key));
      return want.join('|') !== got.join('|');
    });
  return { missing, extra, brokenPlaceholders };
}

export interface LocaleSet {
  /** Label used in log output, e.g. "frontend" or "backend". */
  label: string;
  /** Directory containing one subdirectory/file per language. */
  dir: string;
  /** Reference language code (must be present in `dir`). */
  reference: string;
  /** Given a language code, resolve the JSON file to load. */
  resolveFile: (dir: string, lang: string) => string;
  /** Given `dir`, list the language codes to check (reference included). */
  listLanguages: (dir: string) => string[];
  /**
   * Applied to the parsed file before flattening. The frontend's
   * translation.json is already the flat root object; the backend's
   * `t.<lang>.json` wraps it one level deeper under the language code itself
   * (`{"de": {...}}`), so every file needs unwrapping to compare like with
   * like regardless of which language it is.
   */
  unwrap?: (parsed: unknown, lang: string) => unknown;
}

function sample(keys: string[]): string {
  const shown = keys.slice(0, SAMPLE_SIZE).map((k) => `      ${k}`);
  if (keys.length > SAMPLE_SIZE) {
    shown.push(`      … and ${keys.length - SAMPLE_SIZE} more`);
  }
  return shown.join('\n');
}

/** Runs one locale set end-to-end (I/O + reporting). Returns failure messages. */
function checkLocaleSet(set: LocaleSet): string[] {
  const languages = set.listLanguages(set.dir);
  const failures: string[] = [];

  if (!languages.includes(set.reference)) {
    console.error(`Reference locale "${set.reference}" not found in ${set.dir}`);
    return [`${set.label}: reference locale "${set.reference}" not found`];
  }

  const load = (lang: string): Flat => {
    const parsed = JSON.parse(fs.readFileSync(set.resolveFile(set.dir, lang), 'utf-8'));
    return flatten(set.unwrap ? set.unwrap(parsed, lang) : parsed);
  };

  const reference = load(set.reference);
  console.log(
    `\ni18n key parity (${set.label}) — reference "${set.reference}" (${reference.size} keys)\n`
  );

  for (const lang of languages.sort()) {
    if (lang === set.reference) continue;

    const target = load(lang);
    const { missing, extra, brokenPlaceholders } = diffLocale(reference, target);
    const ok = !missing.length && !extra.length && !brokenPlaceholders.length;
    console.log(`  ${ok ? '✓' : '✗'} ${lang} — ${target.size} keys`);

    if (missing.length) {
      failures.push(`${set.label}/${lang}: ${missing.length} key(s) missing against ${set.reference}`);
      console.log(`    missing (${missing.length}):\n${sample(missing)}`);
    }
    if (extra.length) {
      failures.push(`${set.label}/${lang}: ${extra.length} key(s) not present in ${set.reference}`);
      console.log(`    unknown to ${set.reference} (${extra.length}):\n${sample(extra)}`);
    }
    if (brokenPlaceholders.length) {
      failures.push(`${set.label}/${lang}: ${brokenPlaceholders.length} placeholder mismatch(es)`);
      const detail = brokenPlaceholders.slice(0, SAMPLE_SIZE).map((key) => {
        const want = placeholders(reference.get(key)).join(', ') || '—';
        const got = placeholders(target.get(key)).join(', ') || '—';
        return `      ${key}: ${set.reference}={${want}} ${lang}={${got}}`;
      });
      if (brokenPlaceholders.length > SAMPLE_SIZE) {
        detail.push(`      … and ${brokenPlaceholders.length - SAMPLE_SIZE} more`);
      }
      console.log(`    placeholder mismatch (${brokenPlaceholders.length}):\n${detail.join('\n')}`);
    }
  }

  return failures;
}

const listSubdirs = (dir: string): string[] =>
  fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name);

const listTFiles = (dir: string): string[] =>
  fs
    .readdirSync(dir)
    .filter((name) => /^t\.[a-z]+\.json$/.test(name))
    .map((name) => name.slice('t.'.length, -'.json'.length));

const FRONTEND: LocaleSet = {
  label: 'frontend',
  dir: path.resolve(import.meta.dir, '../src/locales'),
  reference: 'de',
  listLanguages: listSubdirs,
  resolveFile: (dir, lang) => path.join(dir, lang, 'translation.json'),
};

/**
 * The backend's own `t.<lang>.json` files (help-hint fallback text, server-
 * rendered notification copy) are a separate translation surface with a
 * different on-disk shape — not gated by the frontend check above, and
 * silently divergent otherwise. 216 keys × 4 languages as of TF-670; verified
 * by hand at the time, now enforced.
 */
const BACKEND: LocaleSet = {
  label: 'backend',
  dir: path.resolve(import.meta.dir, '../../backend/locales'),
  reference: 'de',
  listLanguages: listTFiles,
  resolveFile: (dir, lang) => path.join(dir, `t.${lang}.json`),
  unwrap: (parsed, lang) => (parsed as Record<string, unknown>)[lang],
};

if (import.meta.main) {
  const failures = [...checkLocaleSet(FRONTEND), ...checkLocaleSet(BACKEND)];

  if (failures.length) {
    console.error('\nFAIL — locale files are out of sync:');
    for (const failure of failures) console.error(`  - ${failure}`);
    console.error(
      `\nAdd the missing translations to the locale file(s) named above.\n` +
        `A missing key falls back to the reference language at runtime, so users\n` +
        `see the wrong language rather than a visible error — that is why this\n` +
        `check is a hard gate.`
    );
    process.exit(1);
  }

  console.log('\nOK — all locales key-identical to their reference, placeholders intact.');
}
