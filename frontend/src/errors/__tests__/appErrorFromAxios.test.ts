import { appErrorFromAxios } from '../appErrorFromAxios';
import { AppError } from '../AppError';

/**
 * Companion to `appErrorFromResponse.test.ts`, for the axios half of the
 * conversion (TF-772 PR 4). The cases mirror that file — an unknown code, a
 * body that is not the promised shape, non-scalar params — plus the two axios
 * shapes `fetch` has no equivalent for: a rejection with no `response` at all
 * (network/CORS/timeout), and an `AppError` that has already been constructed
 * further down the stack.
 */

function axiosError(data: unknown, status = 500): unknown {
  return { isAxiosError: true, message: 'Request failed', response: { status, data } };
}

describe('appErrorFromAxios', () => {
  let warn: jest.SpyInstance;

  beforeEach(() => {
    warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    warn.mockRestore();
  });

  it('übernimmt einen registrierten error_code aus der Antwort', () => {
    const err = appErrorFromAxios(
      axiosError({ detail: 'Prompt nicht gefunden', error_code: 'documents_not_found' }, 404),
      'documents_load_failed',
    );

    expect(err).toBeInstanceOf(AppError);
    expect(err.code).toBe('documents_not_found');
    expect(err.status).toBe(404);
    expect(err.detail).toBe('Prompt nicht gefunden');
    expect(warn).not.toHaveBeenCalled();
  });

  it('reicht error_params für die Interpolation durch', () => {
    const err = appErrorFromAxios(
      axiosError({ error_code: 'documents_not_found', error_params: { name: 'Mathematik' } }, 404),
      'documents_load_failed',
    );

    expect(err.params).toEqual({ name: 'Mathematik' });
  });

  it('verwirft einen unbekannten error_code und warnt', () => {
    const err = appErrorFromAxios(
      axiosError({ error_code: 'aus_einem_neueren_backend' }, 409),
      'documents_load_failed',
    );

    expect(err.code).toBe('documents_load_failed');
    expect(warn).toHaveBeenCalled();
  });

  it('fällt auf den Fallback zurück, wenn der Body kein error_code trägt', () => {
    const err = appErrorFromAxios(axiosError({ detail: 'Internal Server Error' }), 'documents_load_failed');

    expect(err.code).toBe('documents_load_failed');
    expect(err.detail).toBe('Internal Server Error');
    expect(warn).not.toHaveBeenCalled();
  });

  it('verträgt einen Body, der kein Objekt ist (HTML-Fehlerseite eines Proxys)', () => {
    const err = appErrorFromAxios(axiosError('<html>502 Bad Gateway</html>', 502), 'documents_load_failed');

    expect(err.code).toBe('documents_load_failed');
    expect(err.status).toBe(502);
    // Der HTML-Text ist kein `detail` — er darf nicht als solches durchgereicht
    // werden, sonst steht er in der Log-Zeile, wo ein Backend-Satz erwartet wird.
    expect(err.detail).toBeUndefined();
  });

  it('nimmt nur skalare error_params', () => {
    const err = appErrorFromAxios(
      axiosError({
        error_code: 'documents_not_found',
        error_params: { name: 'Mathematik', count: 3, nested: { a: 1 }, list: [1, 2] },
      }),
      'documents_load_failed',
    );

    expect(err.params).toEqual({ name: 'Mathematik', count: 3 });
  });

  it('behandelt eine Netzwerkablehnung ohne response', () => {
    const err = appErrorFromAxios(new Error('Network Error'), 'documents_load_failed');

    expect(err.code).toBe('documents_load_failed');
    expect(err.status).toBeUndefined();
    // Die axios-Meldung überlebt als `detail` — für die Log-Zeile, nie für die UI.
    expect(err.detail).toBe('Network Error');
  });

  it('reicht einen bereits konstruierten AppError unverändert durch', () => {
    const original = new AppError('documents_not_found', 'Prompt nicht gefunden', 404);

    expect(appErrorFromAxios(original, 'documents_load_failed')).toBe(original);
  });
});
