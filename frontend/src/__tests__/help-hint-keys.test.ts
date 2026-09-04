/**
 * Guard: every seeded context hint has a text in all four locales.
 *
 * The hint text is resolved with `t(hint.i18n_key)` — a DYNAMIC key. The
 * literal-only scan in `i18n-keys.test.ts` cannot see it, so without this test
 * a hint whose key is missing from translation.json would render its raw key
 * ("help.hints.examsCompose") in the panel, and nothing would fail.
 *
 * All four locales, not just DE+EN: the hints were the last help surface whose
 * language the server decided, and the FR/IT gap in that surface was invisible
 * to every existing test because the text lived in database columns
 * (TF-625/TF-670). Putting the keys under the same guard as everything else is
 * the point of the move.
 *
 * The key list is read from the Python seed rather than duplicated here —
 * seed_help_hints.DEFAULT_HINTS is the single source of truth for which hints
 * exist.
 */

import * as fs from 'fs';
import * as path from 'path';

// Suffixed on purpose: a bare `it` would shadow Jest's `it` and every test in
// this file would fail with "is not a function".
import deTranslations from '../locales/de/translation.json';
import enTranslations from '../locales/en/translation.json';
import frTranslations from '../locales/fr/translation.json';
import itTranslations from '../locales/it/translation.json';

const REPO_ROOT = path.resolve(__dirname, '../../../..');
const SEED_FILE = path.resolve(REPO_ROOT, 'core/backend/utils/seed_help_hints.py');

const LOCALES: Record<string, unknown> = {
  de: deTranslations,
  en: enTranslations,
  fr: frTranslations,
  it: itTranslations,
};

function seededHintKeys(): string[] {
  const source = fs.readFileSync(SEED_FILE, 'utf8');
  const keys = [...source.matchAll(/"i18n_key":\s*"([^"]+)"/g)].map((m) => m[1]);
  return keys;
}

function resolve(tree: unknown, key: string): string | undefined {
  let current: any = tree;
  for (const part of key.split('.')) {
    if (current == null || typeof current !== 'object') return undefined;
    current = current[part];
  }
  return typeof current === 'string' ? current : undefined;
}

describe('seeded context hint i18n keys', () => {
  const keys = seededHintKeys();

  it('finds the seeded hints', () => {
    // Guards the regex above: a refactor of the seed that changes the literal
    // shape would otherwise silently reduce this whole suite to zero checks.
    // Five since the dead "/admin/users" hint was dropped — that path never
    // existed as a route, the user management is a tab under "/admin".
    expect(keys.length).toBeGreaterThanOrEqual(5);
    expect(keys).toContain('help.hints.examsCompose');
  });

  it.each(Object.keys(LOCALES))('resolves every hint key in %s', (locale) => {
    const missing = keys.filter((key) => !resolve(LOCALES[locale], key));
    expect(missing).toEqual([]);
  });

  it('has no orphaned help.hints entries', () => {
    const entries = Object.keys((deTranslations as any).help?.hints ?? {}).map(
      (name) => `help.hints.${name}`
    );
    const orphans = entries.filter((key) => !keys.includes(key));
    expect(orphans).toEqual([]);
  });
});
