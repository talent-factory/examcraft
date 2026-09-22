/**
 * TF-775 (Teil A): The help text under "Kompetenzen-Volltext" shows the
 * prompt-template variable `{{ competencies }}` literally. i18next would read
 * those braces as its own placeholder, so the text has to be rendered by the
 * real i18next — the global react-i18next mock in setupTests.ts does its own
 * regex replacement and cannot show what i18next does.
 *
 * Two configurations:
 * - the app's own instance (src/i18n.ts), as shipped;
 * - a strict clone with `skipOnVariables: false` and `debug: true`. Under the
 *   shipped default (`skipOnVariables: true`) i18next leaves an unresolved
 *   placeholder untouched, so the text looked right by accident. The strict
 *   clone is where a missing value blanks the placeholder and logs
 *   "missed to pass in variable" — the case this test guards against.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { I18nextProvider } from 'react-i18next';
import i18next, { type i18n as I18n } from 'i18next';
import appI18n from '../../../i18n';
import CompetencyFrameworkForm from '../CompetencyFrameworkForm';
import deLocale from '../../../locales/de/translation.json';
import enLocale from '../../../locales/en/translation.json';
import frLocale from '../../../locales/fr/translation.json';
import itLocale from '../../../locales/it/translation.json';

// Hoisted above the imports by babel-plugin-jest-hoist (see LegalPages.test.tsx).
jest.unmock('react-i18next');

// The form loads org-unit memberships on mount; left pending, so no state
// update lands outside act() — the help text does not depend on it.
jest.mock('../../../services/orgUnitsService', () => ({
  OrgUnitsService: { mine: jest.fn(() => new Promise(() => {})) },
}));

const EXPECTED: Record<string, string> = {
  de: 'Wird wörtlich als {{ competencies }} in die Generierung übernommen.',
  en: 'Injected verbatim as {{ competencies }} into generation.',
  fr: 'Intégré littéralement en tant que {{ competencies }} dans la génération.',
  it: 'Inserito letteralmente come {{ competencies }} nella generazione.',
};

// i18next logs interpolation warnings only with `debug: true`, and through its
// global logger — a cloned instance keeps the logger of the app instance. A
// separate instance with its own logger plugin collects them instead.
const i18nWarnings: string[] = [];
const strictI18n = i18next.createInstance();
strictI18n
  .use({
    type: 'logger',
    log: () => {},
    warn: (args: unknown[]) => i18nWarnings.push(args.map(String).join(' ')),
    error: () => {},
  })
  .init({
    resources: {
      de: { translation: deLocale },
      en: { translation: enLocale },
      fr: { translation: frLocale },
      it: { translation: itLocale },
    },
    lng: 'de',
    debug: true,
    interpolation: { escapeValue: false, skipOnVariables: false },
  });

const configs: Array<[string, I18n]> = [
  ['App-Konfiguration', appI18n],
  ['skipOnVariables: false', strictI18n],
];

describe('competencyFrameworks.form.renderedTextHelper', () => {
  beforeEach(() => {
    i18nWarnings.length = 0;
  });

  it('die erwarteten Texte entsprechen den Locale-Dateien', () => {
    const locales: Record<string, any> = { de: deLocale, en: enLocale, fr: frLocale, it: itLocale };
    for (const lng of Object.keys(EXPECTED)) {
      expect(locales[lng].competencyFrameworks.form.renderedTextHelper).toBe(EXPECTED[lng]);
    }
  });

  describe.each(configs)('%s', (_label, instance) => {
    it.each(Object.keys(EXPECTED))('rendert in %s den Platzhalter wörtlich', async (lng) => {
      await instance.changeLanguage(lng);
      render(
        <I18nextProvider i18n={instance}>
          <CompetencyFrameworkForm mode="create" onSubmit={jest.fn()} onCancel={jest.fn()} />
        </I18nextProvider>
      );

      // Located by the sentence start, so a blanked placeholder still finds
      // the element and the diff shows text and warnings side by side.
      const leadIn = EXPECTED[lng].split('{{')[0].trim();
      const helper = screen.getByText((content) => content.startsWith(leadIn));
      const interpolationWarnings = i18nWarnings.filter((w) => /missed to pass in variable/.test(w));
      expect({ text: helper.textContent, interpolationWarnings }).toEqual({
        text: EXPECTED[lng],
        interpolationWarnings: [],
      });
    });
  });
});
