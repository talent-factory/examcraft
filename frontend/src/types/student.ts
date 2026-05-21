/**
 * TypeScript types for `/api/v1/students/*` (TF-336 Subarea B).
 *
 * Mirrors `core/backend/api/students.py`.
 */

import {
  StudentSubmissionRecord,
  TopicAggregate,
} from './studentClass';

export interface StudentClassRefOut {
  class_id: number;
  class_name: string;
}

export interface StudentListItem {
  id: number;
  external_id: string;
  display_name: string | null;
  submission_count: number;
  avg_percentage: number | null;
  classes: StudentClassRefOut[];
}

export interface StudentList {
  items: StudentListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface StudentDetail {
  id: number;
  external_id: string;
  display_name: string | null;
  created_at: string;
  updated_at: string;
  submission_count: number;
  classes: StudentClassRefOut[];
}

export interface StudentHistoryStats {
  student_id: number;
  external_id: string;
  display_name: string | null;
  submission_count: number;
  avg_percentage: number | null;
  submissions: StudentSubmissionRecord[];
  /** Bloom levels are JSON-serialized as strings (no integer keys). */
  bloom_mix: Record<string, number>;
  topic_heatmap: TopicAggregate[];
  classes: StudentClassRefOut[];
}
