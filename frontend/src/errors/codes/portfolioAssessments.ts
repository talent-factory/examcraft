/**
 * Error codes reachable through `portfolioApi` (TF-987), routers
 * `premium/backend/api/v1/portfolio_assessments.py` and
 * `premium/backend/api/v1/portfolio_github_credentials.py` — the latter only
 * raises `portfolio_assessment_tier_insufficient`, so both share this file.
 *
 * BACKEND CODES, texts verbatim from `premium/backend/locales/t.*.json`
 * (`%{max_mb}` rewritten to `{{max_mb}}`): every `portfolio_assessment_*` key
 * there except the fallbacks below. `portfolio_assessment_tier_insufficient`
 * is also the signal for the pages to show `UpgradePrompt` instead of an
 * error (see `components/portfolio/PortfolioGate.tsx`).
 *
 * NOT IN THIS FILE: the job and warning codes in `job.error_log` and a phase
 * result's `warnings` (`portfolio_ingestion_*`, `portfolio_github_*`,
 * `portfolio_classification_*`, `portfolio_grading_*`). No endpoint answers
 * with them, so they are not AppError codes; the list is `PORTFOLIO_JOB_CODES`
 * in `types/portfolio.ts`, the texts are `pages.portfolio.jobCodes.*`.
 *
 * FRONTEND-ONLY FALLBACKS, one per `portfolioApi` operation:
 * `portfolio_assessment_classify_failed`,
 * `portfolio_assessment_confirm_classification_failed`,
 * `portfolio_assessment_create_failed`,
 * `portfolio_assessment_document_update_failed`,
 * `portfolio_assessment_github_credential_load_failed`,
 * `portfolio_assessment_github_credential_save_failed`,
 * `portfolio_assessment_grade_failed`, `portfolio_assessment_list_failed`,
 * `portfolio_assessment_load_failed`, `portfolio_assessment_review_failed`
 * (approve and override), `portfolio_assessment_upload_failed`,
 * `portfolio_assessment_upload_timeout` (axios gave up after the 10-minute
 * upload timeout). No delete fallback yet: `DELETE /{id}` comes with TF-986.
 */
export const PORTFOLIO_ASSESSMENTS_ERROR_CODES = [
  'portfolio_assessment_archive_too_large',
  'portfolio_assessment_classification_already_in_progress',
  'portfolio_assessment_classification_not_ready',
  'portfolio_assessment_classification_queue_unavailable',
  'portfolio_assessment_classify_failed',
  'portfolio_assessment_confirm_classification_failed',
  'portfolio_assessment_create_failed',
  'portfolio_assessment_document_invalid_phase',
  'portfolio_assessment_document_not_found',
  'portfolio_assessment_document_update_failed',
  'portfolio_assessment_github_credential_load_failed',
  'portfolio_assessment_github_credential_save_failed',
  'portfolio_assessment_grade_failed',
  'portfolio_assessment_grading_already_in_progress',
  'portfolio_assessment_grading_not_ready',
  'portfolio_assessment_grading_queue_unavailable',
  'portfolio_assessment_grading_scheme_not_found',
  'portfolio_assessment_invalid_repository_url',
  'portfolio_assessment_list_failed',
  'portfolio_assessment_load_failed',
  'portfolio_assessment_not_found',
  'portfolio_assessment_phase_result_not_found',
  'portfolio_assessment_phase_result_not_reviewable',
  'portfolio_assessment_phase_result_override_invalid',
  'portfolio_assessment_review_failed',
  'portfolio_assessment_student_not_found',
  'portfolio_assessment_template_not_found',
  'portfolio_assessment_tier_insufficient',
  'portfolio_assessment_unclassified_documents',
  'portfolio_assessment_upload_already_in_progress',
  'portfolio_assessment_upload_failed',
  'portfolio_assessment_upload_queue_unavailable',
  'portfolio_assessment_upload_timeout',
] as const;
