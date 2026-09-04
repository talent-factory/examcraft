import { AppError } from '../AppError';
import { apiDetail } from '../apiDetail';
import { translateError, type Translate } from '../translateError';

const axiosError = (detail: unknown) => ({
  response: { data: { detail } },
});

describe('apiDetail', () => {
  it('liefert den Detail-String bei einem axios-förmigen Fehler', () => {
    expect(apiDetail(axiosError('Tag wird noch von Fragen verwendet.'))).toBe(
      'Tag wird noch von Fragen verwendet.',
    );
  });

  it('trimmt umgebende Leerzeichen', () => {
    expect(apiDetail(axiosError('  Tag existiert bereits.  '))).toBe('Tag existiert bereits.');
  });

  it('gibt null zurück, wenn detail fehlt', () => {
    expect(apiDetail({ response: { data: {} } })).toBeNull();
  });

  it('gibt null zurück, wenn detail ein leerer String ist', () => {
    expect(apiDetail(axiosError(''))).toBeNull();
  });

  it('gibt null zurück, wenn detail nur aus Leerzeichen besteht', () => {
    expect(apiDetail(axiosError('   '))).toBeNull();
  });

  it('gibt null zurück, wenn detail kein String ist', () => {
    expect(apiDetail(axiosError({ code: 'tag.inUse' }))).toBeNull();
    expect(apiDetail(axiosError(42))).toBeNull();
    expect(apiDetail(axiosError(null))).toBeNull();
  });

  it('gibt null zurück bei einem gewöhnlichen Error', () => {
    expect(apiDetail(new Error('boom'))).toBeNull();
  });

  it('gibt null zurück bei einem AppError', () => {
    expect(apiDetail(new AppError('rag.contextPreviewFailed', 'raw detail'))).toBeNull();
  });

  it('gibt null zurück bei null, undefined und einem beliebigen Objekt', () => {
    expect(apiDetail(null)).toBeNull();
    expect(apiDetail(undefined)).toBeNull();
    expect(apiDetail({ foo: 'bar' })).toBeNull();
  });
});

describe('apiDetail ?? translateError (Aufrufmuster)', () => {
  const KNOWN: Record<string, string> = {
    'components.tags.deleteFailed': 'Löschen fehlgeschlagen.',
  };
  const t: Translate = (key) => KNOWN[key] ?? key;

  it('bevorzugt den Backend-Text, wenn detail vorhanden ist', () => {
    const err = axiosError('Tag wird noch von Fragen verwendet.');
    const result = apiDetail(err) ?? translateError(err, t, 'components.tags.deleteFailed');
    expect(result).toBe('Tag wird noch von Fragen verwendet.');
  });

  it('fällt auf den übersetzten Schlüssel zurück, wenn detail fehlt', () => {
    const err = { response: { data: {} } };
    const result = apiDetail(err) ?? translateError(err, t, 'components.tags.deleteFailed');
    expect(result).toBe('Löschen fehlgeschlagen.');
  });
});
