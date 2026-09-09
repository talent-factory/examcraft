/**
 * Guard for the fallback keys handed to `translateError` (TF-772).
 *
 * Why this is not covered by `i18n-keys.test.ts`: that guard scans for literal
 * `t('...')` / `i18n.t('...')` call sites. TF-772 moves keys *out* of that
 * shape — `t('admin.userList.failedLoad')` becomes
 * `translateError(err, t, 'admin.userList.failedLoad')`, and in ReviewQueue the
 * key is parked in state as `fallbackKey: '...'` and only spent at render. The
 * keys are just as live as before, but no longer visible to the scanner, which
 * has two consequences:
 *
 *   1. A missing FR/IT entry would no longer be caught anywhere, and the
 *      fallback branch is the one that actually fires today — the backend does
 *      not send `error_code` until TF-773 merges.
 *   2. An orphan-key sweep (TF-775 owns that question) would read these keys as
 *      unreferenced and could delete them. Deleting one turns a translated
 *      error message into a raw `admin.userList.failedLoad` on screen.
 *
 * So this guard re-establishes the reference from the other end: every fallback
 * key, in every tier, must resolve in all four locales.
 *
 * It deliberately checks all four languages, not just DE+EN like
 * `i18n-keys.test.ts`. That guard can leave FR/IT to
 * `scripts/check-i18n-keys.ts` because it only asserts key *parity* against DE;
 * here the keys are reached through a code path that has no DE fallback of its
 * own — `translateError` returns whatever `t(fallbackKey)` gives it.
 */
import * as fs from 'fs';

import {
  SCAN_ROOTS,
  stripComments,
  walk,
} from '../../scripts/i18n-hardcoded-strings-scan';
import de from '../locales/de/translation.json';
import en from '../locales/en/translation.json';
import fr from '../locales/fr/translation.json';
// Named itLocale: `it` is Jest's test function, and shadowing it here would
// break every it(...) below (same trap as AppErrorCode.i18n.test.ts).
import itLocale from '../locales/it/translation.json';

const LOCALES: Array<[string, Record<string, unknown>]> = [
  ['de', de],
  ['en', en],
  ['fr', fr],
  ['it', itLocale],
];

/** `translateError(err, t, 'some.key')` — the direct shape. */
const TRANSLATE_ERROR_LITERAL = /translateError\(\s*[^,()]+,\s*[^,()]+,\s*'([^']+)'\s*\)/g;

/** Any translateError call, literal third argument or not. */
const TRANSLATE_ERROR_ANY = /translateError\(/g;

/**
 * `fallbackKey: 'some.key'` — the deferred shape. ReviewQueue stores the key
 * with the error and spends it at render time, so the literal never appears
 * inside a translateError call.
 */
const FALLBACK_KEY_PROPERTY = /\bfallbackKey:\s*'([^']+)'/g;

/**
 * Call sites whose third argument is an expression rather than a literal.
 *
 * The list exists so the guard cannot go quiet: a new dynamic call site is a
 * failure telling its author to either pass a literal or document it here,
 * rather than a key that silently stops being checked. Each entry needs the
 * literals it can resolve to reachable through one of the patterns above —
 * ReviewQueue's are `fallbackKey:` properties, which is why that pattern is
 * scanned too.
 */
const DOCUMENTED_DYNAMIC_CALLS: Array<{ file: string; count: number; why: string }> = [
  {
    file: 'core/frontend/src/components/ReviewQueue.tsx',
    count: 2,
    why: 'Failure = { error, fallbackKey } for the queue and for the delete dialog: the key is chosen in the catch and spent at render, so the literals sit in `fallbackKey:` properties.',
  },
  {
    file: 'core/frontend/src/errors/translateError.ts',
    count: 1,
    why: 'The declaration itself — `export function translateError(err, t, fallbackKey)`. Listed rather than special-cased, so the guard keeps failing if the signature is ever reused elsewhere in that file.',
  },
];

interface Found {
  key: string;
  file: string;
}

function collect(): { keys: Found[]; dynamicByFile: Map<string, number> } {
  const keys: Found[] = [];
  const dynamicByFile = new Map<string, number>();

  for (const { dir, prefix } of SCAN_ROOTS) {
    for (const file of walk(dir)) {
      const rel = `${prefix}/${file.slice(dir.length + 1).split(/[\\/]/).join('/')}`;
      const src = stripComments(fs.readFileSync(file, 'utf8'));

      let literals = 0;
      for (const m of src.matchAll(TRANSLATE_ERROR_LITERAL)) {
        keys.push({ key: m[1], file: rel });
        literals++;
      }
      for (const m of src.matchAll(FALLBACK_KEY_PROPERTY)) {
        keys.push({ key: m[1], file: rel });
      }

      const total = Array.from(src.matchAll(TRANSLATE_ERROR_ANY)).length;
      if (total > literals) dynamicByFile.set(rel, total - literals);
    }
  }
  return { keys, dynamicByFile };
}

function resolve(bundle: Record<string, unknown>, key: string): unknown {
  return key.split('.').reduce<unknown>((current, part) => {
    if (current == null || typeof current !== 'object') return undefined;
    return (current as Record<string, unknown>)[part];
  }, bundle);
}

const { keys, dynamicByFile } = collect();
const unique = Array.from(new Map(keys.map((k) => [k.key, k])).values()).sort((a, b) =>
  a.key.localeCompare(b.key),
);

describe('translateError-Fallbackschlüssel', () => {
  it('findet überhaupt Aufrufstellen (Sanity-Check gegen ein kaputtes Muster)', () => {
    // Without this, a regex that stops matching would turn the whole suite
    // green by checking nothing at all.
    expect(unique.length).toBeGreaterThan(20);
  });

  for (const [locale, bundle] of LOCALES) {
    describe(`Locale ${locale}`, () => {
      for (const { key, file } of unique) {
        it(`${key} löst auf (${file})`, () => {
          const value = resolve(bundle, key);
          expect(typeof value).toBe('string');
          expect((value as string).length).toBeGreaterThan(0);
        });
      }
    });
  }

  it('kennt jede Aufrufstelle mit nicht-literalem Schlüssel', () => {
    const documented = new Map(DOCUMENTED_DYNAMIC_CALLS.map((d) => [d.file, d.count]));
    const undocumented = Array.from(dynamicByFile.entries()).filter(
      ([file, count]) => documented.get(file) !== count,
    );

    // Failing here means someone wrote translateError(err, t, someExpression).
    // Either pass a literal — so this guard can check it — or add the call to
    // DOCUMENTED_DYNAMIC_CALLS with the reason and make sure the keys it can
    // produce are reachable through `fallbackKey:` literals.
    expect(undocumented).toEqual([]);
  });
});
