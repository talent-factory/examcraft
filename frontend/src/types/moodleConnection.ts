/**
 * TypeScript types for `/api/v1/admin/moodle-connections/*` (TF-336
 * Subarea C) and `/api/v1/exams/{id}/sync-moodle-question-ids` (D).
 *
 * Tokens are *never* returned in plain text — the backend masks them
 * to `****<last 4>`.
 */

export interface MoodleConnection {
  id: number;
  institution_id: number;
  base_url: string;
  token_masked: string;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MoodleConnectionList {
  items: MoodleConnection[];
  total: number;
}

export interface MoodleConnectionTestResult {
  ok: boolean;
  site_name: string | null;
  site_url: string | null;
  user_full_name: string | null;
  error: string | null;
}

export interface SyncedQuestion {
  exam_question_id: number;
  position: number;
  moodle_slot: number;
  moodle_question_id: number | null;
  moodle_quiz_id: number;
}

export interface SyncMoodleQuestionIdsResult {
  exam_id: number;
  moodle_quiz_id: number;
  moodle_quiz_name: string | null;
  questions: SyncedQuestion[];
}
