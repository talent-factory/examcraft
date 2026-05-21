/**
 * TypeScript types for `/api/v1/exams/{id}/stats/*` and
 * `/api/v1/submissions/{id}/stats` (TF-335 Spec 8).
 *
 * Mirrors the Pydantic schemas in `core/backend/api/stats.py`.
 * Nullable fields stay `number | null` to surface the "n/a" cases the
 * service explicitly produces (correlations on too few samples,
 * empty exams, etc.).
 */

export interface HistogramBucket {
  from_pct: number;
  to_pct: number;
  count: number;
}

export interface OverviewStats {
  submission_count: number;
  fully_reviewed_count: number;
  avg_percentage: number | null;
  median_percentage: number | null;
  min_percentage: number | null;
  max_percentage: number | null;
  pass_rate: number | null;
  avg_duration_seconds: number | null;
  histogram: HistogramBucket[];
}

export interface TopWrongAnswer {
  answer: string;
  count: number;
}

export interface PerQuestionStat {
  exam_question_id: number;
  question_id: number;
  position: number;
  question_text: string;
  question_type: string;
  points_max: number;
  answered_count: number;
  success_rate: number | null;
  difficulty: number | null;
  discrimination: number | null;
  top_wrong_answers: TopWrongAnswer[];
  learning_effect: number | null;
}

export interface PerQuestionList {
  items: PerQuestionStat[];
}

export interface PerSubmissionAnswer {
  position: number;
  question_id: number;
  question_text: string;
  topic: string;
  bloom_level: number | null;
  points_awarded: number;
  points_max: number;
  status: string;
}

export interface TopicHeatmapEntry {
  topic: string;
  points_awarded: number;
  points_max: number;
  percentage: number;
}

export interface PerSubmissionStat {
  submission_id: number;
  student_id: number;
  student_external_id: string;
  student_display_name: string | null;
  total_points_awarded: number;
  total_points_max: number;
  percentage: number;
  grade_status: string;
  per_question: PerSubmissionAnswer[];
  bloom_mix: Record<string, number>;
  topic_heatmap: TopicHeatmapEntry[];
}
