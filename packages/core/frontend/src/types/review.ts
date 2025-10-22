/**
 * TypeScript Types für Question Review System
 * ExamCraft AI - TF-60
 */

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
 * Question Review Interface
 * Erweitert RAGQuestion mit Review-spezifischen Feldern
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
  estimated_time_minutes?: number;
  quality_tier?: string;
  review_status: ReviewStatus;
  reviewed_by?: string;
  reviewed_at?: string;
  exam_id?: string;
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
 * Erweitert QuestionReview mit Comments und History
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
  reviewer_id: string;
  comment?: string;
  reason?: string;
}

/**
 * Comment Create Request
 */
export interface CommentCreateRequest {
  comment_text: string;
  comment_type?: CommentType;
  author: string;
  author_role?: string;
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

