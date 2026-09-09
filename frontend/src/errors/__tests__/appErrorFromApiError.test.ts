import { appErrorFromApiError } from '../appErrorFromApiError';
import { AppError } from '../AppError';
import { ApiError } from '../../services/submissionsService';

/**
 * Third constructor, third set of edge cases (TF-772 PR 4).
 *
 * What is specific here: the input is not a wire format but an object another
 * layer already built, so the interesting questions are about *that* layer's
 * conventions — `status: 0` for a network failure, `error_code` carried through
 * `httpClient` since TF-772, and the structural `name === 'ApiError'` check
 * that keeps `errors/` from importing `services/`.
 */

function apiError(overrides: Partial<ConstructorParameters<typeof ApiError>[0]> = {}): ApiError {
  return new ApiError({
    kind: 'server',
    status: 500,
    message: 'OrgUnit nicht gefunden',
    ...overrides,
  });
}

describe('appErrorFromApiError', () => {
  let warn: jest.SpyInstance;

  beforeEach(() => {
    warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    warn.mockRestore();
  });

  it('nimmt den Fallbackcode, wenn der ApiError keinen trägt', () => {
    const err = appErrorFromApiError(apiError({ status: 404 }), 'org_units_list_failed');

    expect(err).toBeInstanceOf(AppError);
    expect(err.code).toBe('org_units_list_failed');
    expect(err.status).toBe(404);
    // Die Meldung überlebt als `detail` — für die Log-Zeile, nie für die UI.
    expect(err.detail).toBe('OrgUnit nicht gefunden');
    expect(warn).not.toHaveBeenCalled();
  });

  it('übernimmt einen registrierten error_code, den httpClient durchgereicht hat', () => {
    const err = appErrorFromApiError(
      apiError({ status: 404, errorCode: 'documents_not_found' }),
      'org_units_list_failed',
    );

    expect(err.code).toBe('documents_not_found');
  });

  it('reicht error_params für die Interpolation durch', () => {
    const err = appErrorFromApiError(
      apiError({ errorCode: 'documents_not_found', errorParams: { name: 'Informatik', count: 2 } }),
      'org_units_list_failed',
    );

    expect(err.params).toEqual({ name: 'Informatik', count: 2 });
  });

  it('verwirft einen unbekannten error_code und warnt', () => {
    const err = appErrorFromApiError(
      apiError({ errorCode: 'aus_einem_neueren_backend' }),
      'org_units_list_failed',
    );

    expect(err.code).toBe('org_units_list_failed');
    expect(warn).toHaveBeenCalled();
  });

  it('macht aus status 0 kein HTTP-Status', () => {
    // `httpClient.safeFetch` benutzt 0 für einen Netzwerkfehler. Als
    // `AppError.status` durchgereicht läse sich das wie ein echter Statuscode.
    const err = appErrorFromApiError(
      apiError({ kind: 'network', status: 0, message: 'Netzwerkfehler: failed to fetch' }),
      'org_units_list_failed',
    );

    expect(err.status).toBeUndefined();
    expect(err.code).toBe('org_units_list_failed');
  });

  it('reicht einen bereits konstruierten AppError unverändert durch', () => {
    const original = new AppError('org_units_create_failed', 'x', 409);

    expect(appErrorFromApiError(original, 'org_units_list_failed')).toBe(original);
  });

  it('verträgt einen Fehler, der gar kein ApiError ist', () => {
    const err = appErrorFromApiError(new Error('Boom'), 'org_units_list_failed');

    expect(err.code).toBe('org_units_list_failed');
    expect(err.detail).toBe('Boom');
    expect(err.status).toBeUndefined();
  });
});
