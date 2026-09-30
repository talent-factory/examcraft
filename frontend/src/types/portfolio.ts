/**
 * Portfolio-Assessment types (TF-987, P1 of TF-953).
 *
 * Mirrors the premium routers' serializers:
 * `premium/backend/api/v1/portfolio_templates.py::_serialize` and
 * `premium/backend/api/v1/portfolio_assessments.py::_serialize` /
 * `_serialize_phase_result` / `_serialize_document` and the enriched list of
 * `list_portfolio_assessments` (TF-986). The status unions are the CHECK
 * constraints in `premium/backend/models/portfolio_assessment.py`.
 *
 * IDs of portfolio entities are UUID strings; `student_id`, `grading_scheme_id`,
 * `document_id` and user ids are integers (core tables) — except inside job
 * log entries, where the classification task writes document ids as strings.
 */

/** The backend rejects empty lists here with 422 (`Field(min_length=1)`). */
export type NonEmptyArray<T> = [T, ...T[]];

// ---------------------------------------------------------------------------
// Status unions
// ---------------------------------------------------------------------------

export type PortfolioAssessmentStatus =
  | 'uploading'
  | 'classifying'
  | 'ready_to_grade'
  | 'grading'
  | 'completed'
  | 'failed';

export type PortfolioJobType = 'ingest' | 'classify' | 'grade';

export type PortfolioJobStatus = 'queued' | 'running' | 'completed' | 'failed';

export type PortfolioPhaseStatus = 'pending' | 'running' | 'completed' | 'failed';

/** Per phase; `null` until the phase result is `completed`. */
export type PortfolioPhaseReviewStatus = 'proposed' | 'approved' | 'manual_override';

export type PortfolioAssessmentReviewStatus =
  | 'pending_review'
  | 'partially_reviewed'
  | 'fully_reviewed';

export type PortfolioTemplateVisibility = 'private' | 'team' | 'institution' | 'system';

/** `MAX_CRITERION_POINTS` in `premium/backend/services/portfolio_template_service.py`. */
export const PORTFOLIO_MAX_CRITERION_POINTS = 100;

export type PortfolioDocumentOrigin = 'upload_zip' | 'github_repository';

export type PortfolioClassificationSource = 'auto' | 'manual';

// ---------------------------------------------------------------------------
// Templates
// ---------------------------------------------------------------------------

export interface PortfolioTemplateCriterion {
  id: string;
  position: number;
  name: string;
  type_tag: string | null;
  max_points: number;
  /** Keys are the score as a string ("0" … "max_points"). */
  rubric_by_score: Record<string, string>;
  checklist_items: string[] | null;
}

export interface PortfolioTemplatePhase {
  id: string;
  position: number;
  name: string;
  description: string | null;
  /** LLM hint for classification, not a hard rule (e.g. `["01_auftrag"]`). */
  expected_folder_patterns: string[] | null;
  criteria: PortfolioTemplateCriterion[];
}

/**
 * DB invariant (`ck_portfolio_templates_team_visibility_requires_org_unit`):
 * `org_unit_id` is set exactly when `visibility === 'team'`.
 */
export interface PortfolioTemplate {
  id: string;
  name: string;
  description: string | null;
  visibility: PortfolioTemplateVisibility;
  org_unit_id: number | null;
  institution_id: number | null;
  created_by: number | null;
  version: number;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
  phases: PortfolioTemplatePhase[];
}

export interface PortfolioTemplateCriterionPayload {
  name: string;
  type_tag?: string | null;
  max_points: number;
  rubric_by_score: Record<string, string>;
  checklist_items?: string[] | null;
}

export interface PortfolioTemplatePhasePayload {
  name: string;
  description?: string | null;
  expected_folder_patterns?: string[] | null;
  criteria: NonEmptyArray<PortfolioTemplateCriterionPayload>;
}

/**
 * `POST` body. Omitted fields take the backend defaults of `TemplateIn`
 * (`visibility: 'private'`, `is_active: true`). `org_unit_id` is required
 * exactly for `visibility: 'team'`.
 */
export interface PortfolioTemplateCreatePayload {
  name: string;
  description?: string | null;
  visibility?: PortfolioTemplateVisibility;
  org_unit_id?: number | null;
  is_active?: boolean;
  phases: NonEmptyArray<PortfolioTemplatePhasePayload>;
}

/**
 * `PUT` body. `PUT` is a full replace (TF-914) that applies the same defaults
 * as `POST` to anything omitted, so leaving out `visibility` would silently
 * make a team template private and `is_active` would re-activate it. Every
 * field is therefore required here.
 */
export type PortfolioTemplateUpdatePayload = Required<
  Omit<PortfolioTemplateCreatePayload, 'description' | 'org_unit_id'>
> & {
  description: string | null;
  org_unit_id: number | null;
};

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

export const PORTFOLIO_JOB_CODES = [
  'portfolio_classification_batch_failed',
  'portfolio_classification_internal_error',
  'portfolio_classification_interrupted',
  'portfolio_classification_missing_response',
  'portfolio_classification_no_phases',
  'portfolio_classification_queue_unavailable',
  'portfolio_classification_time_budget_exceeded',
  'portfolio_classification_timeout',
  'portfolio_classification_watchdog_reaped',
  'portfolio_github_api_error',
  'portfolio_github_auth_failed',
  'portfolio_github_corrupt_tarball',
  'portfolio_github_invalid_ref',
  'portfolio_github_invalid_url',
  'portfolio_github_path_traversal',
  'portfolio_github_repo_not_found',
  'portfolio_github_repo_size_missing',
  'portfolio_github_repo_too_large',
  'portfolio_github_token_decrypt_failed',
  'portfolio_github_token_missing',
  'portfolio_github_unreachable',
  'portfolio_github_untrusted_redirect',
  'portfolio_grading_documents_omitted',
  'portfolio_grading_documents_without_text',
  'portfolio_grading_internal_error',
  'portfolio_grading_interrupted',
  'portfolio_grading_missing_phase_result',
  'portfolio_grading_no_phases',
  'portfolio_grading_phase_failed',
  'portfolio_grading_phase_without_documents',
  'portfolio_grading_queue_unavailable',
  'portfolio_grading_time_budget_exceeded',
  'portfolio_grading_timeout',
  'portfolio_grading_watchdog_reaped',
  'portfolio_ingestion_archive_too_large',
  'portfolio_ingestion_corrupt_archive',
  'portfolio_ingestion_file_too_large',
  'portfolio_ingestion_internal_error',
  'portfolio_ingestion_interrupted',
  'portfolio_ingestion_no_files',
  'portfolio_ingestion_path_traversal',
  'portfolio_ingestion_queue_unavailable',
  'portfolio_ingestion_time_budget_exceeded',
  'portfolio_ingestion_timeout',
  'portfolio_ingestion_too_many_files',
  'portfolio_ingestion_watchdog_reaped',
] as const;

export type PortfolioJobCode = (typeof PORTFOLIO_JOB_CODES)[number];

/**
 * One entry of `job.error_log` or of a phase result's `warnings`.
 *
 * `reason` is a German free-text sentence for logs (phase warnings carry none);
 * the UI renders `code` (see `components/portfolio/portfolioJobMessages.ts`)
 * and shows `reason` only next to the generic text of an unknown code. The
 * remaining keys depend on the code and are optional on purpose.
 */
export interface PortfolioJobLogEntry {
  /** A known `PortfolioJobCode`, or a newer one this frontend cannot translate. */
  code?: PortfolioJobCode | (string & {});
  reason?: string;
  /** `'job'` on enqueue failures, `'phase'` on per-phase grading warnings. */
  scope?: 'job' | 'phase';
  /** Phase warnings and `portfolio_grading_phase_failed`. */
  phase_id?: string;
  /**
   * Classification batch failures, missing responses and an exhausted time
   * budget. Strings: the classification task serialises ids with `str()`.
   */
  document_ids?: string[];
  /** `portfolio_grading_documents_omitted` / `_documents_without_text`. */
  paths?: string[];
  /** `portfolio_ingestion_time_budget_exceeded`. */
  skipped_files?: string[];
  [key: string]: unknown;
}

export interface PortfolioAssessmentJob {
  id: string;
  job_type: PortfolioJobType;
  status: PortfolioJobStatus;
  files_total: number | null;
  files_done: number;
  error_log: PortfolioJobLogEntry[] | null;
  created_at: string | null;
  /** `null` until a worker picks the job up. */
  started_at: string | null;
  finished_at: string | null;
}

// ---------------------------------------------------------------------------
// Assessments
// ---------------------------------------------------------------------------

export interface PortfolioDocument {
  document_id: number;
  original_relative_path: string;
  origin: PortfolioDocumentOrigin;
  phase_id: string | null;
  classification_confidence: number | null;
  classification_source: PortfolioClassificationSource | null;
}

/** One criterion of a completed phase (`CriterionResultOutput` in the grading service). */
export type PortfolioCriterionResult = {
  criterion_id: string;
  score: number;
  rationale: string;
  checklist: Record<string, boolean>;
  strengths: string[];
  improvements: string[];
} & (
  | { llm_score?: undefined; llm_rationale?: undefined }
  /**
   * Both set by the first reviewer override (Epic 5) and never overwritten
   * again: the LLM's original proposal, kept for the audit trail.
   */
  | { llm_score: number; llm_rationale: string }
);

/** Aggregate the approve/override endpoints return alongside the phase result. */
export interface PortfolioAssessmentAggregate {
  review_status: PortfolioAssessmentReviewStatus;
  overall_points_awarded: number | null;
  overall_points_max: number | null;
  overall_percentage: number | null;
}

interface PortfolioPhaseResultBase {
  /** Key of the approve/override routes (`/phase-results/{phase_result_id}`, TF-986). */
  id: string;
  phase_id: string;
  warnings: PortfolioJobLogEntry[] | null;
  reviewer_id: number | null;
  reviewer_note: string | null;
  reviewed_at: string | null;
  generated_at: string | null;
}

/**
 * A phase that has been graded. The DB CHECK constraints guarantee scores and
 * `review_status` once `status === 'completed'`, so narrowing on `status`
 * spares every consumer a non-null assertion.
 */
export interface PortfolioPhaseResultCompleted extends PortfolioPhaseResultBase {
  status: 'completed';
  criterion_results: PortfolioCriterionResult[];
  total_points: number;
  max_points: number;
  review_status: PortfolioPhaseReviewStatus;
}

export interface PortfolioPhaseResultPending extends PortfolioPhaseResultBase {
  status: Exclude<PortfolioPhaseStatus, 'completed'>;
  criterion_results: null;
  total_points: number | null;
  max_points: number | null;
  review_status: null;
}

export type PortfolioPhaseResult = PortfolioPhaseResultCompleted | PortfolioPhaseResultPending;

/** Response of approve/override: the phase plus the recomputed aggregate. */
export type PortfolioPhaseReviewResponse = PortfolioPhaseResultCompleted & {
  assessment: PortfolioAssessmentAggregate;
};

/** Shape of every assessment response except the detail GET. */
export interface PortfolioAssessmentSummary {
  id: string;
  template_id: string;
  template_version: number;
  student_id: number;
  /**
   * Creator; `null` once that account is deleted. Repository ingestion uses
   * this user's GitHub token, not the token of whoever starts it.
   */
  created_by: number | null;
  status: PortfolioAssessmentStatus;
  framework_conditions: string | null;
  source_repository_url: string | null;
  source_repository_ref: string | null;
  grading_scheme_id: number | null;
  review_status: PortfolioAssessmentReviewStatus;
  overall_points_awarded: number | null;
  overall_points_max: number | null;
  overall_percentage: number | null;
  created_at: string | null;
  updated_at: string | null;
  /** Latest job, `null` before the first upload. */
  job: PortfolioAssessmentJob | null;
}

/** `GET /api/v1/portfolio-assessments/{id}`. */
export interface PortfolioAssessmentDetail extends PortfolioAssessmentSummary {
  documents: PortfolioDocument[];
  phase_results: PortfolioPhaseResult[];
  /**
   * Only set once `review_status === 'fully_reviewed'` (TF-947 gate) AND a
   * valid grading scheme is attached — there is no fallback to the
   * institution's default scheme, and an invalid scheme also yields `null`.
   */
  overall_grade: string | null;
}

/** List entry of `GET /api/v1/portfolio-assessments`. */
export interface PortfolioAssessmentListItem extends PortfolioAssessmentSummary {
  /** The student's `display_name`, or `external_id` when it has none. */
  student_name: string;
  student_external_id: string;
  template_name: string;
}

/** Page of `GET /api/v1/portfolio-assessments`, newest first. */
export interface PortfolioAssessmentListPage {
  items: PortfolioAssessmentListItem[];
  /** Matches of the filters across all pages. */
  total: number;
  limit: number;
  offset: number;
}

/** Query filters and pagination of the list endpoint (`limit` 1–200, default 50). */
export interface PortfolioAssessmentListParams {
  status?: PortfolioAssessmentStatus;
  review_status?: PortfolioAssessmentReviewStatus;
  template_id?: string;
  limit?: number;
  offset?: number;
}

/** One hit of `GET /api/v1/portfolio-assessments/students` (own institution only). */
export interface PortfolioStudentOption {
  id: number;
  external_id: string;
  display_name: string | null;
  classes: { class_id: number; class_name: string }[];
}

export interface PortfolioAssessmentCreatePayload {
  template_id: string;
  student_id: number;
  framework_conditions?: string | null;
  source_repository_url?: string | null;
  grading_scheme_id?: number | null;
}

export interface PortfolioPhaseOverrideItem {
  criterion_id: string;
  score: number;
  rationale?: string | null;
}

export interface PortfolioPhaseOverridePayload {
  overrides: NonEmptyArray<PortfolioPhaseOverrideItem>;
  reviewer_note?: string | null;
}

// ---------------------------------------------------------------------------
// GitHub credential
// ---------------------------------------------------------------------------

/** `GET /api/v1/portfolio-github-credential` — the token itself never leaves the server. */
export interface PortfolioGithubCredentialStatus {
  configured: boolean;
}
