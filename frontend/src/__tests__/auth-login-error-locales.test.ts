/**
 * Guard (EXAMCRAFT-137): jeder Login-Fehlercode, den die LoginPage kennt, hat
 * in allen vier Sprachen einen Text unter `auth.loginError.<code>`.
 *
 * Der Schlüssel wird dynamisch aufgelöst (`t(`auth.loginError.${code}`)`), das
 * Skript `check-i18n-keys.ts` kennt nur den Präfix und prüft nicht, ob jeder
 * Code der LoginPage einen Text hat. Ohne diesen Test erschiene bei einem
 * fehlenden Code der Rohschlüssel (bzw. dank `fallbackLng: 'de'` deutscher
 * Text in den anderen Sprachen), und nichts schlüge fehl.
 */
import * as fs from 'fs';
import * as path from 'path';

import deTranslations from '../locales/de/translation.json';
import enTranslations from '../locales/en/translation.json';
import frTranslations from '../locales/fr/translation.json';
import itTranslations from '../locales/it/translation.json';

const loginPageSource = fs.readFileSync(
  path.resolve(__dirname, '../components/auth/LoginPage.tsx'),
  'utf8',
);

const declaredCodes = ((): string[] => {
  const match = /const LOGIN_ERROR_CODES = \[([\s\S]*?)\]/.exec(loginPageSource);
  if (!match) throw new Error('LOGIN_ERROR_CODES in LoginPage.tsx nicht gefunden');
  return [...match[1].matchAll(/'([a-z_]+)'/g)].map((m) => m[1]);
})();

const locales: Record<string, { auth?: { loginError?: Record<string, unknown> } }> = {
  de: deTranslations,
  en: enTranslations,
  fr: frTranslations,
  it: itTranslations,
};

describe('auth.loginError.* in allen Sprachen', () => {
  it('liest die Codes der LoginPage (Schutz gegen ein leeres Ergebnis)', () => {
    expect(declaredCodes.length).toBeGreaterThan(0);
    expect(new Set(declaredCodes).size).toBe(declaredCodes.length);
  });

  describe.each(Object.keys(locales))('%s', (lang) => {
    const block = locales[lang].auth?.loginError ?? {};

    it.each(declaredCodes)('hat einen Text für %s', (code) => {
      const text = block[code];
      expect(typeof text).toBe('string');
      expect((text as string).trim().length).toBeGreaterThan(0);
      // Kein Platzhalter, der auf den Rohschlüssel zurückfällt.
      expect(text).not.toBe(`auth.loginError.${code}`);
    });

    it('enthält keine Texte ohne zugehörigen Code', () => {
      expect(Object.keys(block).sort()).toEqual([...declaredCodes].sort());
    });
  });

  it('übersetzt die Texte wirklich (in keiner Sprache ist ein Text identisch zu Deutsch)', () => {
    const de = locales.de.auth?.loginError ?? {};
    for (const lang of ['en', 'fr', 'it']) {
      const other = locales[lang].auth?.loginError ?? {};
      const untranslated = declaredCodes.filter((code) => other[code] === de[code]);
      expect(untranslated).toEqual([]);
    }
  });
});
