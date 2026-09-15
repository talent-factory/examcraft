import { QUOTA_ERROR_CODES } from '../QuotaBanner';
import de from '../../../locales/de/translation.json';
import en from '../../../locales/en/translation.json';
import fr from '../../../locales/fr/translation.json';
// Named itLocale, not `it` — see AppErrorCode.i18n.test.ts for why shadowing
// Jest's `it` with this import silently breaks every it(...) call below.
import itLocale from '../../../locales/it/translation.json';

/**
 * `QuotaBanner`'s `translateQuotaError` reads `auswertungen.tierBanner.<code>`
 * for the pre-ADR-0005 quota envelope, a lookup `AppErrorCode.i18n.test.ts`
 * does not cover (that test only walks `AppErrorCode`, and this envelope is
 * documented in QuotaBanner.tsx as deliberately not part of that family). A
 * quota code added to `QUOTA_ERROR_CODES` without a matching locale entry
 * would otherwise fall back to the generic tier sentence silently, with no
 * CI signal — this test closes that gap the same way the AppError one does.
 */

const KEY_PREFIX = 'auswertungen.tierBanner.';

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
  describe(`QuotaBanner error_code → auswertungen.tierBanner.<code> Übersetzung (${locale})`, () => {
    for (const code of QUOTA_ERROR_CODES) {
      it(`${code} hat einen Übersetzungs-Eintrag`, () => {
        const value = resolveKey(translations, `${KEY_PREFIX}${code}`);
        expect(typeof value).toBe('string');
        expect((value as string).length).toBeGreaterThan(0);
      });
    }
  });
}

it('QUOTA_ERROR_CODES ist nicht leer (Sanity-Check gegen einen kaputten Import)', () => {
  expect(QUOTA_ERROR_CODES.length).toBeGreaterThan(0);
});
