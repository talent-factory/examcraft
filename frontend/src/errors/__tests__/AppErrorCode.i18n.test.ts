import { APP_ERROR_CODES } from '../AppError';
import de from '../../locales/de/translation.json';
import en from '../../locales/en/translation.json';
import fr from '../../locales/fr/translation.json';
// Named itLocale, not `it` — `it` is Jest's global test function, and
// shadowing it with this import silently breaks every it(...) call below
// (TypeError: ... is not a function, since it becomes the JSON object).
import itLocale from '../../locales/it/translation.json';

/**
 * Closes the loop AppError.ts's doc comment promises: `AppErrorCode` makes
 * "the code is a valid, translated key" a compile-time contract for callers,
 * but nothing enforced that every code IN the registry actually resolves to
 * a translation — a code could be added to APP_ERROR_CODES and merged
 * without ever getting a locale entry, and it would only fail at runtime
 * (silently, via translateError's fallback) the first time that error path
 * fired. This test makes that a CI failure instead, in all four locales.
 *
 * Deliberately does not check the reverse direction (an `errors.*` locale
 * key with no matching AppErrorCode) — several existing `errors.*` keys
 * (`generic`, `network`, `oauth.callbackFailed`, `oauth.providerError`) are
 * legitimate translateError() fallback keys or direct t() calls, not
 * AppError codes, and distinguishing those from real orphans needs more than
 * a JSON walk. See TagSettingsPage's apiDetail.boundary.test.ts for the same
 * "forward-only, documented scope" tradeoff.
 */

const ERROR_KEY_PREFIX = 'errors.';

function resolveKey(obj: Record<string, unknown>, key: string): unknown {
  return key.split('.').reduce<unknown>((current, part) => {
    if (current == null || typeof current !== 'object') return undefined;
    return (current as Record<string, unknown>)[part];
  }, obj);
}

const LOCALES: Array<[string, Record<string, unknown>]> = [
  ['de', de],
  ['en', en],
  ['fr', fr],
  ['it', itLocale],
];

for (const [locale, translations] of LOCALES) {
  describe(`AppErrorCode → errors.<code> Übersetzung (${locale})`, () => {
    for (const code of APP_ERROR_CODES) {
      it(`${code} hat einen Übersetzungs-Eintrag`, () => {
        const value = resolveKey(translations, `${ERROR_KEY_PREFIX}${code}`);
        expect(typeof value).toBe('string');
        expect((value as string).length).toBeGreaterThan(0);
      });
    }
  });
}

it('APP_ERROR_CODES ist nicht leer (Sanity-Check gegen einen kaputten Import)', () => {
  expect(APP_ERROR_CODES.length).toBeGreaterThan(0);
});
