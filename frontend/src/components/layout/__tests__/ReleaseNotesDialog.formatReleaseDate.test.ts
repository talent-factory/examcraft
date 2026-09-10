import { formatReleaseDate } from '../ReleaseNotesDialog';

// Review fix: the component-level test suite's global react-i18next mock
// (setupTests.ts) pins i18n.language to 'de', so every DATE_LOCALES branch
// except 'de' — and the `?? 'de-CH'` fallback for an unrecognised language —
// was previously never exercised by any test. formatReleaseDate is exported
// so this can be checked directly, without fighting the i18n mock.

const expectedFor = (locale: string) =>
  new Date('2026-09-09T00:00:00').toLocaleDateString(locale, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

describe('formatReleaseDate', () => {
  it.each([
    ['de', 'de-CH'],
    ['en', 'en-US'],
    ['fr', 'fr-CH'],
    ['it', 'it-CH'],
  ])('formats a %s date using the %s locale', (lang, locale) => {
    expect(formatReleaseDate('2026-09-09', lang)).toBe(expectedFor(locale));
  });

  it('falls back to de-CH for an unsupported/unknown language code', () => {
    expect(formatReleaseDate('2026-09-09', 'xx')).toBe(expectedFor('de-CH'));
  });
});
