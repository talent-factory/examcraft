import { importRowErrorMessage } from '../importRowErrorMessage';

// A real lookup, not an echoing mock: translateError detects a missing key by
// `t(key) === key`, so a mock that echoes every key would make each assertion
// below pass for the wrong reason.
const TEXTS: Record<string, string> = {
  'errors.submissions_import_database_error': 'Datenbankfehler (übersetzt)',
  'errors.submissions_import_moodle_server_error': 'Moodle-Serverfehler (HTTP {{status}})',
  'errors.submissions_import_internal_error': 'Interner Fehler (übersetzt)',
};
const t = (key: string, params?: Record<string, string | number>) => {
  let value = TEXTS[key] ?? key;
  Object.entries(params ?? {}).forEach(([k, v]) => {
    value = value.replace(`{{${k}}}`, String(v));
  });
  return value;
};

describe('importRowErrorMessage', () => {
  afterEach(() => jest.restoreAllMocks());

  it('übersetzt einen registrierten Code und zeigt den reason nicht', () => {
    jest.spyOn(console, 'debug').mockImplementation(() => {});
    expect(
      importRowErrorMessage(
        {
          row_index: 0,
          reason: 'The import failed because of a database error.',
          error_code: 'submissions_import_database_error',
        },
        t,
      ),
    ).toBe('Datenbankfehler (übersetzt)');
  });

  it('interpoliert error_params', () => {
    jest.spyOn(console, 'debug').mockImplementation(() => {});
    expect(
      importRowErrorMessage(
        {
          row_index: 0,
          reason: 'x',
          error_code: 'submissions_import_moodle_server_error',
          error_params: { status: 503, nested: { no: 1 } },
        },
        t,
      ),
    ).toBe('Moodle-Serverfehler (HTTP 503)');
  });

  it('zeigt bei einem unbekannten Code den reason des Backends und protokolliert', () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    expect(
      importRowErrorMessage(
        { row_index: 0, reason: 'Vom Backend übersetzt', error_code: 'submissions_import_future' },
        t,
      ),
    ).toBe('Vom Backend übersetzt');
    expect(warn).toHaveBeenCalledWith(
      '[i18n] Unknown import row error_code, using reason:',
      'submissions_import_future',
    );
  });

  it('reicht eine Treiber-Zeile ohne Code unverändert durch', () => {
    expect(importRowErrorMessage({ row_index: 3, reason: 'Leere external_id' }, t)).toBe(
      'Leere external_id',
    );
  });
});
