/**
 * TypeScript types for the submissions / results-import API.
 *
 * Mirrors the Pydantic schemas in `core/backend/api/submissions.py`.
 * Status enums use literal-union types **and** runtime `as const`
 * arrays so dropdowns and switch statements share one source of truth.
 */

// ---------------------------------------------------------------------------
// Status enums (literal unions + runtime constants)
// ---------------------------------------------------------------------------

export const IMPORT_JOB_STATUSES = [
  'queued',
  'running',
  'succeeded',
  'partial',
  'failed',
] as const;
export type ImportJobStatus = (typeof IMPORT_JOB_STATUSES)[number];

export const GRADE_STATUSES = ['proposed', 'approved', 'manual_override'] as const;
export type GradeStatus = (typeof GRADE_STATUSES)[number];

export const SUBMISSION_GRADE_STATUSES = [
  'pending_review',
  'partially_reviewed',
  'fully_reviewed',
] as const;
export type SubmissionGradeStatus = (typeof SUBMISSION_GRADE_STATUSES)[number];

export const SCORING_STRATEGIES = ['latest', 'best', 'first'] as const;
export type ScoringStrategy = (typeof SCORING_STRATEGIES)[number];

export const DRIVER_NAMES = ['moodle_csv', 'moodle_api'] as const;
export type DriverName = (typeof DRIVER_NAMES)[number];

export type AttemptSource = DriverName;

// ---------------------------------------------------------------------------
// Import preview
// ---------------------------------------------------------------------------

export interface ImportRowError {
  row_index: number;
  reason: string;
  /** Pipeline step that produced the error (job-level failures only). */
  step?: string | null;
  /** Structured diagnostic context (job-level failures only). */
  details?: Record<string, unknown> | null;
}

export interface ImportPayloadStudent {
  external_id: string;
  display_name: string | null;
}

export interface ImportPayloadAttempt {
  student_external_id: string;
  attempt_number: number;
  started_at: string | null;
  submitted_at: string | null;
  answer_count: number;
}

export interface ImportPreview {
  exam_id: number;
  driver_name: DriverName;
  student_count: number;
  attempt_count: number;
  students: ImportPayloadStudent[];
  attempts: ImportPayloadAttempt[];
  warnings: string[];
  errors: ImportRowError[];
  source_metadata: Record<string, unknown>;
  /** True when the preview lists were truncated for transport. */
  truncated: boolean;
}

// ---------------------------------------------------------------------------
// Import jobs
// ---------------------------------------------------------------------------

export interface ImportJob {
  id: number;
  exam_id: number;
  driver_name: DriverName;
  status: ImportJobStatus;
  rows_processed: number;
  rows_failed: number;
  error_log: ImportRowError[] | null;
  source_metadata: Record<string, unknown> | null;
  started_at: string | null;
  finished_at: string | null;
}

// ---------------------------------------------------------------------------
// Import deletion (TF-421)
// ---------------------------------------------------------------------------

export interface ImportSourceCount {
  source: AttemptSource;
  attempt_count: number;
}

/** Counts for the delete-confirmation dialog and the delete result. */
export interface ImportDeletionSummary {
  exam_id: number;
  submission_count: number;
  attempt_count: number;
  student_count: number;
  by_source: ImportSourceCount[];
}

// ---------------------------------------------------------------------------
// Submissions — list + detail
// ---------------------------------------------------------------------------

export interface SubmissionListItem {
  id: number;
  exam_id: number;
  student_id: number;
  student_external_id: string;
  student_display_name: string | null;
  attempt_count: number;
  total_points_awarded: number;
  total_points_max: number;
  percentage: number;
  grade_status: SubmissionGradeStatus;
}

export interface SubmissionList {
  items: SubmissionListItem[];
  total: number;
  /** Count of all submissions where grade_status !== 'fully_reviewed'.
   *  Server-side count, accurate even when the visible page is small. */
  pending_count: number;
  limit: number;
  offset: number;
}

export interface Grade {
  id: number;
  points_awarded: number;
  points_max: number;
  status: GradeStatus;
  is_correct: boolean | null;
  llm_confidence: number | null;
  llm_rationale: string | null;
  llm_matched_aspects: string[] | null;
  llm_missing_aspects: string[] | null;
  reviewer_id: number | null;
  reviewer_note: string | null;
}

export interface AttemptAnswer {
  id: number;
  exam_question_id: number;
  given_answer: string | null;
  moodle_points_awarded: number | null;
  grade: Grade | null;
}

export interface Attempt {
  id: number;
  attempt_number: number;
  started_at: string | null;
  submitted_at: string | null;
  source: AttemptSource;
  source_attempt_id: string | null;
  answers: AttemptAnswer[];
}

export interface SubmissionDetail {
  id: number;
  exam_id: number;
  student_id: number;
  student_external_id: string;
  student_display_name: string | null;
  scoring_strategy: ScoringStrategy;
  graded_attempt_id: number | null;
  total_points_awarded: number;
  total_points_max: number;
  percentage: number;
  grade_status: SubmissionGradeStatus;
  attempts: Attempt[];
}

// ---------------------------------------------------------------------------
// Review queue (TF-334)
// ---------------------------------------------------------------------------

export interface ReviewQueueItem {
  grade_id: number;
  submission_id: number;
  student_id: number;
  student_external_id: string;
  student_display_name: string | null;
  exam_question_id: number;
  question_id: number;
  question_text: string;
  correct_answer: string | null;
  explanation: string | null;
  given_answer: string | null;
  points_awarded: number;
  points_max: number;
  confidence: number | null;
  rationale: string | null;
  matched_aspects: string[];
  missing_aspects: string[];
  status: GradeStatus;
}

export interface ReviewQueue {
  items: ReviewQueueItem[];
  total: number;
}

export interface ReviewQueueFilter {
  confidence_min?: number;
  confidence_max?: number;
  question_id?: number;
  student_id?: number;
  limit?: number;
  offset?: number;
}

export interface GradeAction {
  id: number;
  points_awarded: number;
  points_max: number;
  status: GradeStatus;
  reviewer_id: number | null;
  reviewer_note: string | null;
  reviewed_at: string | null;
}

export interface BulkApproveResult {
  approved_count: number;
  grade_ids: number[];
}

// ---------------------------------------------------------------------------
// API errors
// ---------------------------------------------------------------------------

export type ApiErrorKind =
  | 'network'
  | 'aborted'
  | 'auth'
  | 'permission'
  | 'validation'
  | 'not_found'
  | 'too_large'
  | 'server'
  | 'unknown';
