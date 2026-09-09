/**
 * Error codes reachable through `ReviewService` (TF-772 PR 2).
 *
 * All of them are raised by `core/backend/api/question_review.py` and copied
 * verbatim from `core/backend/locales/t.*.json` — see `documents.ts` for why
 * the specific codes are registered rather than one generic per method.
 *
 * `archive_failed`, `archive_already_archived`, `archive_not_archived`,
 * `delete_failed`, `delete_in_exam`, `delete_requires_archive` and
 * `restore_failed` carry no `review_` prefix. That is not a transcription
 * slip: the review router really emits them unprefixed
 * (question_review.py:1187, :1192, :1219, :1244, :1267, :1292, :1349), and
 * the identity rule says the frontend key is the backend's `error_code`
 * verbatim. Renaming them here to look tidier would break the one property the
 * rule buys — that a code seen in a backend log can be grepped for in the
 * frontend locales. The `exam_archive_*` / `exam_restore_failed` keys in the
 * backend locales are the *exams* router's separate set; they are not these.
 *
 * No frontend-only fallback codes: every ReviewService method maps to a
 * question_review.py endpoint that has a localized generic failure code.
 * `getReviewStatistics` shares `GET /api/v1/questions/review` with
 * `getReviewQueue` and therefore shares `review_fetch_queue_failed`.
 */
export const REVIEW_ERROR_CODES = [
  'archive_already_archived',
  'archive_failed',
  'archive_not_archived',
  'delete_failed',
  'delete_in_exam',
  'delete_requires_archive',
  'restore_failed',
  'review_add_comment_failed',
  'review_approve_failed',
  'review_create_failed',
  'review_edit_failed',
  'review_fetch_comments_failed',
  'review_fetch_history_failed',
  'review_fetch_question_failed',
  'review_fetch_queue_failed',
  'review_four_eyes_principle',
  'review_invalid_status_for_review',
  'review_question_not_found',
  'review_reject_failed',
  'review_start_failed',
] as const;
