/**
 * TypeScript types for the Question Review System
 * ExamCraft AI - TF-60
 */

import type { Tag } from '../api/tagsApi';

/**
 * Review Status Enum
 */
export enum ReviewStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  EDITED = 'edited',
  IN_REVIEW = 'in_review'
}

/**
 * Comment Type Enum
 */
export enum CommentType {
  GENERAL = 'general',
  SUGGESTION = 'suggestion',
  ISSUE = 'issue',
  APPROVAL_NOTE = 'approval_note'
}

/**
 * Reviewer Info Interface
 * Contains information about the reviewer
 */
export interface ReviewerInfo {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

/**
 * Generation Metadata (TF-383)
 * Snapshot of the template/prompt used to generate a question.
 * Mirrors the backend envelope (core `schemas/generation_metadata.py`): the
 * envelope fields are always set (`null` where not applicable), only
 * `variables` is open-ended. The WHOLE value is `null`/`undefined` for
 * legacy data (not captured). Three states: default (is_default_template),
 * custom, and fallback (`fallback_to_default` = failed custom render →
 * default template).
 */
export interface GenerationMetadata {
  prompt_id: string | null;
  prompt_name: string | null;
  prompt_version: number | null;
  is_default_template: boolean;
  fallback_to_default: boolean;
  variables: Record<string, unknown>;
}

/**
 * Competency Brief (TF-400)
 * Slim view of the assessed competency (HK) for the question display:
 * code, title and module — without the full descriptor tree.
 */
export interface CompetencyBrief {
  id: number;
  code: string;
  title: string;
  framework_id: number;
  module_code?: string | null;
}

/**
 * Question Review Interface
 * Extends RAGQuestion with review-specific fields
 */
export interface QuestionReview {
  id: number;
  question_text: string;
  question_type: string;
  options?: string[];
  correct_answer?: string;
  explanation?: string;
  difficulty: string;
  topic: string;
  language: string;
  source_chunks?: string[];
  source_documents?: string[];
  confidence_score: number;
  bloom_level?: number;
  // TF-400: assessed competency (HK) + LN level (1-4). `competency` is
  // the slim brief for the display; null/undefined when no HK is assigned.
  competency_id?: number | null;
  ln_level?: number | null;
  competency?: CompetencyBrief | null;
  estimated_time_minutes?: number;
  quality_tier?: string;
  generation_metadata?: GenerationMetadata | null;
  review_status: ReviewStatus;
  reviewed_by?: number;
  reviewer_info?: ReviewerInfo;
  reviewed_at?: string;
  exam_id?: string;
  // TF-396: archive axis (orthogonal to review_status).
  archived_at?: string | null;
  archived_by?: number | null;
  archive_reason?: string | null;
  tags?: Tag[];
  created_at: string;
  updated_at: string;
}

/**
 * Review Comment Interface
 */
export interface ReviewComment {
  id: number;
  question_id: number;
  comment_text: string;
  comment_type: CommentType;
  author: string;
  author_role?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Review History Entry Interface
 */
export interface ReviewHistory {
  id: number;
  question_id: number;
  action: string;
  old_status?: ReviewStatus;
  new_status?: ReviewStatus;
  changed_fields?: Record<string, {
    old: any;
    new: any;
  }>;
  changed_by: string;
  change_reason?: string;
  changed_at: string;
}

/**
 * Question Review Detail Interface
 * Extends QuestionReview with comments and history
 */
export interface QuestionReviewDetail extends QuestionReview {
  comments: ReviewComment[];
  history: ReviewHistory[];
}

/**
 * Review Queue Response Interface
 */
export interface ReviewQueueResponse {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  in_review: number;
  questions: QuestionReview[];
}

/**
 * Review Filters Interface
 */
export interface ReviewFilters {
  status?: ReviewStatus;
  difficulty?: string;
  question_type?: string;
  exam_id?: string;
  // TF-396: archive filter. Default (both false) = active questions only.
  include_archived?: boolean;
  archived_only?: boolean;
  limit?: number;
  offset?: number;
}

/**
 * Review Statistics Interface
 */
export interface ReviewStats {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  edited: number;
  in_review: number;
}

/**
 * Question Review Create Request
 */
export interface QuestionReviewCreateRequest {
  question_text: string;
  question_type: string;
  options?: string[];
  correct_answer?: string;
  explanation?: string;
  difficulty: string;
  topic: string;
  language?: string;
  source_chunks?: string[];
  source_documents?: string[];
  confidence_score?: number;
  bloom_level?: number;
  estimated_time_minutes?: number;
  quality_tier?: string;
  exam_id?: string;
}

/**
 * Question Review Update Request
 */
export interface QuestionReviewUpdateRequest {
  question_text?: string;
  options?: string[];
  correct_answer?: string;
  explanation?: string;
  difficulty?: string;
  bloom_level?: number;
  estimated_time_minutes?: number;
}

/**
 * Review Action Request (Approve/Reject)
 */
export interface ReviewActionRequest {
  comment?: string;
  reason?: string;
}

/**
 * Comment Create Request
 */
export interface CommentCreateRequest {
  comment_text: string;
  comment_type?: CommentType;
}

/**
 * Review Action Type
 */
export type ReviewAction = 'approve' | 'reject' | 'edit' | 'comment';

/**
 * Review Filter Options
 */
export interface ReviewFilterOptions {
  statuses: Array<{ value: ReviewStatus; label: string }>;
  difficulties: Array<{ value: string; label: string }>;
  questionTypes: Array<{ value: string; label: string }>;
}

/**
 * Review Queue Pagination
 */
export interface ReviewQueuePagination {
  page: number;
  pageSize: number;
  total: number;
}

/**
 * Review Error Response
 */
export interface ReviewErrorResponse {
  detail: string;
  status_code: number;
}
