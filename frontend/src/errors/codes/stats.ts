/**
 * Error codes with the `stats_` prefix that a frontend surface can receive.
 *
 * BACKEND CODE: `stats_submission_not_found` («Submission nicht gefunden»).
 * `core/backend/api/stats.py` introduced it in TF-773 PR 2d, where it stayed
 * unregistered — `StatisticsService.getSubmissionStats` has no caller. TF-773
 * Teil D made `GET /api/v1/submissions/{id}` (`submissions.py`) send the same
 * code for the same fact instead of a fourth synonym (identity beats the
 * router prefix, ADR 0006). That endpoint does have a consumer: the
 * submission drawer in `AuswertungenExam`, which reaches the 404 when the
 * submission was deleted after the list was loaded (a result-import delete in
 * another tab or by a colleague).
 */
export const STATS_ERROR_CODES = ['stats_submission_not_found'] as const;
