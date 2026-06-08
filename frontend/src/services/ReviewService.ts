/**
 * Review Service für ExamCraft AI
 * API Client für Question Review System
 */

import {
  QuestionReview,
  QuestionReviewDetail,
  ReviewQueueResponse,
  ReviewFilters,
  ReviewStats,
  QuestionReviewCreateRequest,
  QuestionReviewUpdateRequest,
  ReviewActionRequest,
  CommentCreateRequest,
  ReviewComment,
  ReviewHistory,
} from '../types/review';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export class ReviewService {
  /**
   * Get auth headers with token
   */
  private static getAuthHeaders(additionalHeaders: HeadersInit = {}): HeadersInit {
    const token = localStorage.getItem('examcraft_access_token');
    return {
      'Content-Type': 'application/json',
      ...additionalHeaders,
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  /**
   * Get Review Queue with filters
   */
  static async getReviewQueue(filters?: ReviewFilters): Promise<ReviewQueueResponse> {
    const params = new URLSearchParams();

    if (filters?.status) params.append('status', filters.status);
    if (filters?.difficulty) params.append('difficulty', filters.difficulty);
    if (filters?.question_type) params.append('question_type', filters.question_type);
    if (filters?.exam_id) params.append('exam_id', filters.exam_id);
    if (filters?.include_archived) params.append('include_archived', 'true');
    if (filters?.archived_only) params.append('archived_only', 'true');
    if (filters?.limit) params.append('limit', filters.limit.toString());
    if (filters?.offset) params.append('offset', filters.offset.toString());

    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/review?${params.toString()}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch review queue: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get Question Detail (single question with review info)
   */
  static async getQuestionDetail(questionId: number): Promise<QuestionReview> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}/review`,
      {
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to load question: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get Question Review Details (with comments and history)
   */
  static async getQuestionReview(questionId: number): Promise<QuestionReviewDetail> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}/review`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch question review: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Create new Question Review
   */
  static async createQuestionReview(
    request: QuestionReviewCreateRequest
  ): Promise<QuestionReview> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/review`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to create question review: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Approve Question
   */
  static async approveQuestion(
    questionId: number,
    request: ReviewActionRequest
  ): Promise<QuestionReview> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}/approve`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to approve question: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Reject Question
   */
  static async rejectQuestion(
    questionId: number,
    request: ReviewActionRequest
  ): Promise<QuestionReview> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}/reject`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to reject question: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * TF-396: Archive Question (orthogonal to review_status).
   */
  static async archiveQuestion(
    questionId: number,
    reason?: string
  ): Promise<QuestionReview> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}/archive`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ reason }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to archive question: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * TF-396: Restore an archived question.
   */
  static async restoreQuestion(questionId: number): Promise<QuestionReview> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}/restore`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to restore question: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * TF-396: Hard-delete a question (guarded backend-side).
   */
  static async deleteQuestion(questionId: number): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}`,
      {
        method: 'DELETE',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to delete question: ${response.statusText}`);
    }
  }

  /**
   * TF-396: Bulk hard-delete. Returns deleted ids and blocked entries.
   */
  static async bulkDeleteQuestions(
    ids: number[]
  ): Promise<{ deleted: number[]; blocked: { id: number; reason: string }[] }> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/bulk-delete`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ ids }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to bulk-delete questions: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Start Review (mark as in_review)
   */
  static async startReview(questionId: number): Promise<QuestionReview> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}/start-review`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to start review: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Edit Question (Inline Editing)
   */
  static async editQuestion(
    questionId: number,
    updates: QuestionReviewUpdateRequest
  ): Promise<QuestionReview> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}/edit`,
      {
        method: 'PUT',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(updates),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to edit question: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get Comments for Question
   */
  static async getComments(questionId: number): Promise<ReviewComment[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}/comments`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch comments: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Add Comment to Question
   */
  static async addComment(
    questionId: number,
    request: CommentCreateRequest
  ): Promise<ReviewComment> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}/comments`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to add comment: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get Question History
   */
  static async getQuestionHistory(questionId: number): Promise<ReviewHistory[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/${questionId}/history`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch question history: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get Review Statistics
   */
  static async getReviewStatistics(): Promise<ReviewStats> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/questions/review`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch review statistics: ${response.statusText}`);
    }

    const data: ReviewQueueResponse = await response.json();

    return {
      total: data.total,
      pending: data.pending,
      approved: data.approved,
      rejected: data.rejected,
      edited: 0, // Not included in queue response
      in_review: data.in_review,
    };
  }

  /**
   * Batch Approve Questions
   */
  static async batchApproveQuestions(
    questionIds: number[]
  ): Promise<QuestionReview[]> {
    const promises = questionIds.map(id =>
      this.approveQuestion(id, {})
    );

    return Promise.all(promises);
  }

  /**
   * Batch Reject Questions
   */
  static async batchRejectQuestions(
    questionIds: number[],
    reason?: string
  ): Promise<QuestionReview[]> {
    const promises = questionIds.map(id =>
      this.rejectQuestion(id, { reason })
    );

    return Promise.all(promises);
  }
}
