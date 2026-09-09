import { GradesService } from '../gradesService';
import { AppError, isAppError } from '../../errors';

/**
 * Error path of `GradesService` (TF-772 PR 4). The file had no test at all.
 *
 * Two branches that look alike and are not: a response that arrives and is not
 * ok (body, status, possibly an `error_code`), and a `fetch` that rejects
 * outright — no response, no status. The second one is the reason
 * `appErrorFromResponse` alone is not enough here; before TF-772 it produced an
 * `ApiError` with `kind: 'network'` and the German string "Netzwerkfehler: …",
 * which the review queue rendered verbatim.
 */

const originalFetch = global.fetch;

function ok(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as unknown as Response;
}

function failing(status: number, body: unknown): Response {
  return { ok: false, status, json: async () => body } as unknown as Response;
}

/** The AppError a rejected call produced, or fail loudly. */
async function thrownBy(call: Promise<unknown>): Promise<AppError> {
  try {
    await call;
  } catch (err) {
    if (isAppError(err)) return err;
    throw new Error(`Erwartet wurde ein AppError, bekommen: ${String(err)}`);
  }
  throw new Error('Der Aufruf hat gar nicht abgelehnt');
}

describe('GradesService', () => {
  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('gibt bei Erfolg die Antwort zurück', async () => {
    global.fetch = jest.fn().mockResolvedValue(ok({ total: 0, items: [] }));

    await expect(GradesService.getReviewQueue(7)).resolves.toEqual({ total: 0, items: [] });
  });

  it('trägt je Operation einen eigenen Code', async () => {
    global.fetch = jest.fn().mockResolvedValue(failing(404, { detail: 'Grade nicht gefunden' }));

    expect((await thrownBy(GradesService.getReviewQueue(7))).code).toBe(
      'grades_review_queue_load_failed',
    );
    expect((await thrownBy(GradesService.approve(11))).code).toBe('grades_approve_failed');
    expect((await thrownBy(GradesService.override(11, { points_awarded: 2 }))).code).toBe(
      'grades_override_failed',
    );
    expect((await thrownBy(GradesService.bulkApprove({ examId: 7 }))).code).toBe(
      'grades_bulk_approve_failed',
    );
  });

  it('behält detail für die Log-Zeile, aber nicht für die UI', async () => {
    global.fetch = jest.fn().mockResolvedValue(failing(404, { detail: 'Prüfung nicht gefunden' }));

    const err = await thrownBy(GradesService.getReviewQueue(7));

    expect(err.detail).toBe('Prüfung nicht gefunden');
    expect(err.status).toBe(404);
  });

  it('übernimmt einen registrierten error_code aus einer anderen Domäne', async () => {
    // Zeigt, dass die Auswahl code-agnostisch ist: `selectCode()` prüft nur
    // Registrierung, nicht Domänenzugehörigkeit (siehe errors/AppError.ts).
    global.fetch = jest
      .fn()
      .mockResolvedValue(failing(404, { detail: 'Dokument nicht gefunden', error_code: 'documents_not_found' }));

    expect((await thrownBy(GradesService.getReviewQueue(7))).code).toBe('documents_not_found');
  });

  it('übernimmt einen echten grades_*-Code des Backends (TF-773)', async () => {
    // `grades.py` sendet seit TF-773 spezifische Codes (siehe
    // errors/codes/grades.ts) — die generische Operations-Meldung tritt nur
    // noch bei Netzwerkfehlern oder unregistrierten Codes zurück.
    global.fetch = jest
      .fn()
      .mockResolvedValue(
        failing(404, { detail: 'Prüfung nicht gefunden', error_code: 'grades_exam_not_found' }),
      );

    expect((await thrownBy(GradesService.getReviewQueue(7))).code).toBe('grades_exam_not_found');
  });

  it('verwirft einen nicht registrierten error_code zugunsten des Fallbacks', async () => {
    // `exams_not_found` steht in den Backend-Locales, ist im Frontend aber
    // nicht registriert. Ein roher Schlüssel `errors.exams_not_found` auf dem
    // Bildschirm wäre schlechter als der generische Satz.
    global.fetch = jest
      .fn()
      .mockResolvedValue(failing(404, { detail: 'Prüfung nicht gefunden', error_code: 'exams_not_found' }));
    jest.spyOn(console, 'warn').mockImplementation(() => {});

    const err = await thrownBy(GradesService.getReviewQueue(7));

    expect(err.code).toBe('grades_review_queue_load_failed');
    expect(console.warn).toHaveBeenCalled();
  });

  it('macht auch aus einer Netzwerkablehnung einen AppError mit Operationscode', async () => {
    global.fetch = jest.fn().mockRejectedValue(new TypeError('Failed to fetch'));

    const err = await thrownBy(GradesService.approve(11));

    expect(err.code).toBe('grades_approve_failed');
    expect(err.status).toBeUndefined();
    expect(err.detail).toBe('Failed to fetch');
  });
});
