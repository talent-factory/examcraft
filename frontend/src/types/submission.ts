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
// API errors
// ---------------------------------------------------------------------------

export type ApiErrorKind =
  | 'network'
  | 'auth'
  | 'permission'
  | 'validation'
  | 'not_found'
  | 'too_large'
  | 'server'
  | 'unknown';
