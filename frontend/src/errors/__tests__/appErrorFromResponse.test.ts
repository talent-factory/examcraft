import { appErrorFromResponse } from '../appErrorFromResponse';
import { AppError } from '../AppError';

/**
 * `appErrorFromResponse` is the single place where an untrusted JSON body
 * becomes a typed `AppErrorCode`. Everything worth testing here is a way that
 * body can be wrong: a code this build does not know, a body that is not JSON
 * at all, params that are not scalars. Each of those has a defined answer, and
 * none of them may end in a thrown parse error — the helper's whole job is to
 * produce the error the caller is about to throw, so it must not throw itself.
 */

function response(body: unknown, status = 500, throws = false): Response {
  return {
    status,
    json: throws
      ? () => Promise.reject(new SyntaxError('Unexpected token < in JSON'))
      : () => Promise.resolve(body),
  } as unknown as Response;
}

describe('appErrorFromResponse', () => {
  let warn: jest.SpyInstance;

  beforeEach(() => {
    warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    warn.mockRestore();
  });

  it('übernimmt einen registrierten error_code aus der Antwort', async () => {
    const err = await appErrorFromResponse(
      response({
        detail: 'Ein Tag mit diesem Namen existiert bereits.',
        error_code: 'documents_tag_exists',
      }, 409),
      'documents_tag_failed',
    );

    expect(err).toBeInstanceOf(AppError);
    expect(err.code).toBe('documents_tag_exists');
    expect(err.status).toBe(409);
    // detail survives for the log line, and only for that — translateError
    // never renders it.
    expect(err.detail).toBe('Ein Tag mit diesem Namen existiert bereits.');
    expect(warn).not.toHaveBeenCalled();
  });

  it('reicht error_params für die Interpolation durch', async () => {
    const err = await appErrorFromResponse(
      response({ error_code: 'documents_tag_exists', error_params: { name: 'Mathematik' } }, 409),
      'documents_tag_failed',
    );

    expect(err.params).toEqual({ name: 'Mathematik' });
  });

  it('nimmt auch Zahlen als Parameter, aber keine Objekte oder Arrays', async () => {
    const err = await appErrorFromResponse(
      response({
        error_code: 'documents_page_out_of_range',
        error_params: { page: 12, nested: { a: 1 }, list: [1, 2], name: 'x' },
      }, 400),
      'documents_list_failed',
    );

    // A nested value would reach the UI as "[object Object]"; dropping it
    // leaves the {{placeholder}} visible instead, which is legible.
    expect(err.params).toEqual({ page: 12, name: 'x' });
  });

  it('lässt params weg, wenn nichts Brauchbares übrig bleibt', async () => {
    const err = await appErrorFromResponse(
      response({ error_code: 'documents_not_found', error_params: { nested: { a: 1 } } }, 404),
      'documents_load_failed',
    );

    expect(err.params).toBeUndefined();
  });

  it('fällt auf den Fallback-Code zurück, wenn die Antwort keinen error_code trägt', async () => {
    const err = await appErrorFromResponse(
      response({ detail: 'Internal Server Error' }, 500),
      'documents_upload_failed',
    );

    expect(err.code).toBe('documents_upload_failed');
    // No error_code at all is the normal pre-TF-773 shape, not a mismatch.
    expect(warn).not.toHaveBeenCalled();
  });

  it('fällt still auf den Fallback-Code zurück, wenn error_code explizit null ist', async () => {
    const err = await appErrorFromResponse(
      response({ detail: 'Internal Server Error', error_code: null }, 500),
      'documents_upload_failed',
    );

    // `error_code: null` is the same "backend sent none" case as an absent
    // key, not an unrecognised code — it must not trigger the mismatch
    // warning (`!= null`, not `!== undefined`, in appErrorFromResponse).
    expect(err.code).toBe('documents_upload_failed');
    expect(warn).not.toHaveBeenCalled();
  });

  it('verwirft einen unbekannten error_code und warnt', async () => {
    const err = await appErrorFromResponse(
      response({ error_code: 'documents_teleported_away' }, 500),
      'documents_delete_failed',
    );

    // Adopting it would render the raw key `errors.documents_teleported_away`
    // in the UI — the exact failure mode AppErrorCode exists to prevent.
    expect(err.code).toBe('documents_delete_failed');
    expect(warn).toHaveBeenCalledWith(
      expect.stringContaining('Unknown error_code'),
      'documents_teleported_away',
      '->',
      'documents_delete_failed',
    );
  });

  it('überlebt einen Body, der kein JSON ist (HTML-Fehlerseite eines Proxys)', async () => {
    const err = await appErrorFromResponse(response(null, 502, true), 'documents_list_failed');

    expect(err.code).toBe('documents_list_failed');
    expect(err.status).toBe(502);
    expect(err.detail).toBeUndefined();
  });

  it('überlebt einen Body, der kein Objekt ist', async () => {
    const err = await appErrorFromResponse(response('nope', 500), 'documents_list_failed');

    expect(err.code).toBe('documents_list_failed');
  });

  it('ignoriert ein detail, das kein String ist', async () => {
    const err = await appErrorFromResponse(
      // FastAPI's 422 answers with a list of validation objects under `detail`.
      response({ detail: [{ loc: ['body'], msg: 'field required' }] }, 422),
      'documents_upload_failed',
    );

    expect(err.detail).toBeUndefined();
    expect(err.message).toBe('documents_upload_failed');
  });
});
