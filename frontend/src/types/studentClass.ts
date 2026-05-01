/**
 * TypeScript types for `/api/v1/student-classes/*` (TF-336 Subarea A + B).
 *
 * Mirrors the Pydantic schemas in
 * `core/backend/api/student_classes.py` plus the cross-exam stats DTOs
 * from `core/backend/services/statistics_service.py`.
 */

export interface StudentRefSummary {
  id: number;
  external_id: string;
  display_name: string | null;
}

export interface StudentClassSummary {
  id: number;
  name: string;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface StudentClassList {
  items: StudentClassSummary[];
  total: number;
}

export interface StudentClassDetail extends StudentClassSummary {
  members: StudentRefSummary[];
}

export interface StudentSubmissionRecord {
  submission_id: number;
  exam_id: number;
  exam_title: string;
  exam_date: string | null;
  percentage: number;
  grade_status: string;
}

export interface TopicAggregate {
  topic: string;
  points_awarded: number;
  points_max: number;
  percentage: number;
}

export interface ClassMemberPerformance {
  student_id: number;
  external_id: string;
  display_name: string | null;
  submission_count: number;
  avg_percentage: number | null;
  submissions: StudentSubmissionRecord[];
}

export interface ClassExamAggregate {
  exam_id: number;
  exam_title: string;
  exam_date: string | null;
  submission_count: number;
  avg_percentage: number | null;
  pass_rate: number | null;
}

export interface ClassHistoryStats {
  class_id: number;
  class_name: string;
  member_count: number;
  members: ClassMemberPerformance[];
  exam_aggregates: ClassExamAggregate[];
  topic_coverage: TopicAggregate[];
}
