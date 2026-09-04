import { AppError, isAppError, translateError } from '../index';
import type { AppErrorCode } from '../index';

// The real i18next and the react-i18next mock in setupTests.ts agree on one
// thing: a missing key resolves to the key itself. This fake reproduces that.
const KNOWN: Record<string, string> = {
  'errors.rag.contextPreviewFailed': 'Der Kontext konnte nicht analysiert werden.',
  'premium.ragExamCreator.errorContextPreview': 'Vorschau fehlgeschlagen.',
};
const t = (key: string): string => KNOWN[key] ?? key;

describe('AppError', () => {
  it('behält Code, Detail und Status', () => {
    const err = new AppError('rag.contextPreviewFailed', 'HTTP 500 boom', 500);
    expect(err.code).toBe('rag.contextPreviewFailed');
    expect(err.detail).toBe('HTTP 500 boom');
    expect(err.status).toBe(500);
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe('AppError');
  });

  it('erkennt AppError, aber nicht gewöhnliche Errors', () => {
    expect(isAppError(new AppError('rag.contextPreviewFailed'))).toBe(true);
    expect(isAppError(new Error('x'))).toBe(false);
    expect(isAppError('x')).toBe(false);
    expect(isAppError(null)).toBe(false);
  });
});

describe('translateError', () => {
  let warn: jest.SpyInstance;
  beforeEach(() => {
    warn = jest.spyOn(console, 'warn').mockImplementation(() => undefined);
  });
  afterEach(() => warn.mockRestore());

  it('übersetzt einen AppError über errors.<code>', () => {
    const result = translateError(
      new AppError('rag.contextPreviewFailed', 'Context preview failed: boom'),
      t,
      'premium.ragExamCreator.errorContextPreview',
    );
    expect(result).toBe('Der Kontext konnte nicht analysiert werden.');
  });

  it('nimmt den Fallback-Schlüssel, wenn der Code keinen Schlüssel hat', () => {
    // Deliberately outside the AppErrorCode registry: exercises the runtime
    // fallback for a code without a translation (e.g. a stale cached value),
    // a state the closed union prevents at new call sites but not at runtime.
    const result = translateError(
      new AppError('rag.somethingNobodyTranslated' as AppErrorCode, 'raw detail'),
      t,
      'premium.ragExamCreator.errorContextPreview',
    );
    expect(result).toBe('Vorschau fehlgeschlagen.');
  });

  it('nimmt den Fallback-Schlüssel bei einem gewöhnlichen Error', () => {
    const result = translateError(
      new Error('Context preview failed: boom'),
      t,
      'premium.ragExamCreator.errorContextPreview',
    );
    expect(result).toBe('Vorschau fehlgeschlagen.');
  });

  it('nimmt den Fallback-Schlüssel bei einem Nicht-Error', () => {
    expect(translateError('kaputt', t, 'premium.ragExamCreator.errorContextPreview'))
      .toBe('Vorschau fehlgeschlagen.');
    expect(translateError(undefined, t, 'premium.ragExamCreator.errorContextPreview'))
      .toBe('Vorschau fehlgeschlagen.');
  });

  // This is the invariant the whole ticket rests on.
  it('gibt niemals den rohen Text zurück', () => {
    const raw = 'Context preview failed: ECONNREFUSED';
    for (const err of [
      new Error(raw),
      // Deliberately outside the AppErrorCode registry — see the fallback-key test above.
      new AppError('unknown.code' as AppErrorCode, raw),
      { message: raw },
    ]) {
      expect(translateError(err, t, 'premium.ragExamCreator.errorContextPreview'))
        .not.toContain('ECONNREFUSED');
    }
  });

  it('protokolliert den rohen Text, statt ihn anzuzeigen', () => {
    translateError(new Error('ECONNREFUSED'), t, 'premium.ragExamCreator.errorContextPreview');
    expect(warn).toHaveBeenCalled();
    expect(JSON.stringify(warn.mock.calls)).toContain('ECONNREFUSED');
  });
});
