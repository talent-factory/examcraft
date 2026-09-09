import { ReviewService } from '../ReviewService';

/**
 * ReviewService had no test file at all before TF-772, and the component suite
 * that exercised it (`components/__tests__/ReviewQueue.test.tsx`) is
 * `describe.skip`. So the error path this ticket rewrote had no live coverage
 * whatsoever — this closes that, scoped to the part TF-772 changed.
 *
 * The mechanics of reading `error_code` live in
 * `errors/__tests__/appErrorFromResponse.test.ts`. What is worth pinning HERE
 * is the wiring: that each method passes the fallback code its own endpoint
 * needs, and that a specific backend code survives the trip. The second half
 * is the one that would silently regress — mapping every failure of
 * `approveQuestion` to `review_approve_failed` still looks correct in a diff,
 * and still shows the user a sentence, just the wrong one.
 */

global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

function failWith(body: unknown, status = 500): void {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    statusText: 'Error',
    json: async () => body,
  } as Response);
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.setItem('examcraft_access_token', 'test-token');
});

describe('ReviewService — Fallback-Codes je Endpunkt', () => {
  // One case per distinct fallback code rather than per method: the mapping
  // table is what this guards, and two methods sharing a code (the two
  // question-detail reads, the two delete paths) share a row by design.
  const CASES: Array<[string, () => Promise<unknown>, string]> = [
    ['getReviewQueue', () => ReviewService.getReviewQueue(), 'review_fetch_queue_failed'],
    ['getQuestionReview', () => ReviewService.getQuestionReview(1), 'review_fetch_question_failed'],
    ['createQuestionReview', () => ReviewService.createQuestionReview(1, {} as never), 'review_create_failed'],
    ['approveQuestion', () => ReviewService.approveQuestion(1, {} as never), 'review_approve_failed'],
    ['rejectQuestion', () => ReviewService.rejectQuestion(1, {} as never), 'review_reject_failed'],
    ['archiveQuestion', () => ReviewService.archiveQuestion(1), 'archive_failed'],
    ['restoreQuestion', () => ReviewService.restoreQuestion(1), 'restore_failed'],
    ['deleteQuestion', () => ReviewService.deleteQuestion(1), 'delete_failed'],
    ['startReview', () => ReviewService.startReview(1), 'review_start_failed'],
    ['editQuestion', () => ReviewService.editQuestion(1, {} as never), 'review_edit_failed'],
    ['getComments', () => ReviewService.getComments(1), 'review_fetch_comments_failed'],
    ['addComment', () => ReviewService.addComment(1, {} as never), 'review_add_comment_failed'],
    ['getQuestionHistory', () => ReviewService.getQuestionHistory(1), 'review_fetch_history_failed'],
  ];

  for (const [name, call, code] of CASES) {
    it(`${name} → ${code}`, async () => {
      // No error_code in the body: the pre-ADR-0005 shape, and still what a
      // framework 500 produces.
      failWith({ detail: 'Internal Server Error' });
      await expect(call()).rejects.toMatchObject({ code });
    });
  }

  // Not in the table above: archive_failed and the unprefixed delete/restore
  // codes look like transcription slips next to their review_-prefixed
  // siblings. They are not — question_review.py emits them without a prefix,
  // and the identity rule copies error_code verbatim. Pinned so nobody
  // "corrects" them into review_archive_failed and breaks the lookup.
  it('behält die präfixlosen Backend-Codes bei', async () => {
    failWith({}, 500);
    await expect(ReviewService.archiveQuestion(1)).rejects.toMatchObject({
      code: 'archive_failed',
    });
  });
});

describe('ReviewService — spezifischer Backend-Code schlägt den Fallback', () => {
  it('reicht review_four_eyes_principle durch statt review_approve_failed', async () => {
    // The case the whole exercise is for. Before TF-772 the component rendered
    // the backend's `detail` prose, so the four-eyes rule was explained to the
    // user; collapsing it into the generic approve-failed code would have been
    // a regression dressed up as a translation.
    failWith(
      {
        detail: 'Vier-Augen-Prinzip: Ersteller kann eigene Frage nicht genehmigen',
        error_code: 'review_four_eyes_principle',
      },
      403,
    );

    await expect(ReviewService.approveQuestion(1, {} as never)).rejects.toMatchObject({
      code: 'review_four_eyes_principle',
      status: 403,
    });
  });

  it('reicht delete_requires_archive durch statt delete_failed', async () => {
    failWith(
      { detail: 'Frage muss zuerst archiviert werden', error_code: 'delete_requires_archive' },
      409,
    );

    await expect(ReviewService.deleteQuestion(1)).rejects.toMatchObject({
      code: 'delete_requires_archive',
    });
  });

  it('ignoriert einen error_code, den dieses Build nicht kennt', async () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    failWith({ error_code: 'review_invented_by_a_newer_backend' }, 500);

    await expect(ReviewService.getReviewQueue()).rejects.toMatchObject({
      code: 'review_fetch_queue_failed',
    });
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });
});
