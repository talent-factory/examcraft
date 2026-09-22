/**
 * TF-775 (Teil A): The help-text options insert `{{ competencies }}` as the
 * value of the i18next variable of the same name. The inserted value must not
 * be scanned again — with `skipOnVariables: false` i18next restarts the scan
 * after every replacement and would re-substitute the value up to
 * `maxReplaces` (1000) times.
 *
 * The rendered text cannot show that: `{{ competencies }}` → `{{ competencies }}`
 * is a fixed point. `alwaysFormat` routes every substitution through `format`,
 * so counting its calls counts the substitutions.
 */
import i18next from 'i18next';
import {
  COMPETENCIES_HELPER_I18N_OPTIONS,
  COMPETENCIES_TEMPLATE_VARIABLE,
} from '../competenciesTemplateVariable';

describe('COMPETENCIES_HELPER_I18N_OPTIONS', () => {
  it('zeigt die Jinja2-Schreibweise des Backends', () => {
    expect(COMPETENCIES_TEMPLATE_VARIABLE).toBe('{{ competencies }}');
  });

  it('setzt den Platzhalter genau einmal ein, auch mit skipOnVariables: false', async () => {
    const format = jest.fn((value: unknown) => value);
    const instance = i18next.createInstance();
    await instance.init({
      resources: { de: { translation: { helper: 'als {{ competencies }} übernommen' } } },
      lng: 'de',
      interpolation: { escapeValue: false, skipOnVariables: false, alwaysFormat: true, format },
    });

    const text = instance.t('helper', COMPETENCIES_HELPER_I18N_OPTIONS);

    expect({ text, substitutions: format.mock.calls.length }).toEqual({
      text: 'als {{ competencies }} übernommen',
      substitutions: 1,
    });
  });
});
