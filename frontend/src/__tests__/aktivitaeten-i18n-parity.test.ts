/**
 * Activity-page i18n parity guard.
 *
 * The existing i18n-keys.test.ts checks DE+EN parity globally; FR/IT
 * are allowed to lag and rely on i18next DE fallback. The activity
 * page was shipped with full DE+EN+FR+IT translations, so missing a
 * key in fr/it would only surface as fallback-German text on the
 * French/Italian UI without any test failure. This test pins the
 * shape of the activity-related keys in all four locales.
 */

import deTranslations from '../locales/de/translation.json';
import enTranslations from '../locales/en/translation.json';
import frTranslations from '../locales/fr/translation.json';
import itTranslations from '../locales/it/translation.json';

function flatten(
  obj: unknown,
  prefix = '',
  out: Set<string> = new Set(),
): Set<string> {
  if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      const next = prefix ? `${prefix}.${k}` : k;
      if (typeof v === 'string') out.add(next);
      else flatten(v, next, out);
    }
  }
  return out;
}

function aktivitaetenKeys(translations: unknown): Set<string> {
  const all = flatten(translations);
  return new Set(
    Array.from(all).filter(
      (k) =>
        k.startsWith('aktivitaeten.') ||
        k === 'pages.dashboard.viewAllActivities' ||
        k === 'nav.sidebar.aktivitaeten',
    ),
  );
}

describe('aktivitaeten i18n parity (DE+EN+FR+IT)', () => {
  const de = aktivitaetenKeys(deTranslations);
  const en = aktivitaetenKeys(enTranslations);
  const fr = aktivitaetenKeys(frTranslations);
  const itLocale = aktivitaetenKeys(itTranslations);

  it('every locale has at least the core activity-page keys', () => {
    // Sanity check: a regression that wipes the namespace fails here.
    expect(de.size).toBeGreaterThan(5);
    expect(en.size).toBeGreaterThan(5);
    expect(fr.size).toBeGreaterThan(5);
    expect(itLocale.size).toBeGreaterThan(5);
  });

  it.each([
    ['EN', en],
    ['FR', fr],
    ['IT', itLocale],
  ])('%s has every aktivitaeten.* key present in DE', (_label, locale) => {
    const missing = Array.from(de).filter((k) => !locale.has(k));
    if (missing.length > 0) {
      throw new Error(
        `Locale missing ${missing.length} aktivitaeten key(s) present in DE:\n` +
          missing.map((k) => `  ${k}`).join('\n'),
      );
    }
  });

  it.each([
    ['EN', en],
    ['FR', fr],
    ['IT', itLocale],
  ])('%s has no extra aktivitaeten.* keys not in DE', (_label, locale) => {
    const extras = Array.from(locale).filter((k) => !de.has(k));
    if (extras.length > 0) {
      throw new Error(
        `Locale has ${extras.length} extra aktivitaeten key(s) not in DE:\n` +
          extras.map((k) => `  ${k}`).join('\n'),
      );
    }
  });
});
