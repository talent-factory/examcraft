import axios from 'axios';
import type {
  Exam,
  ExamDetail,
  ExamListResponse,
  CreateExamRequest,
  UpdateExamRequest,
  ApprovedQuestionsResponse,
  AutoFillRequest,
} from '../types/composer';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('examcraft_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export class ComposerService {
  static async listExams(params?: {
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<ExamListResponse> {
    const response = await apiClient.get('/api/v1/exams/', { params });
    return response.data;
  }

  static async getExam(examId: number): Promise<ExamDetail> {
    const response = await apiClient.get(`/api/v1/exams/${examId}`);
    return response.data;
  }

  static async createExam(data: CreateExamRequest): Promise<Exam> {
    const response = await apiClient.post('/api/v1/exams/', data);
    return response.data;
  }

  static async updateExam(examId: number, data: UpdateExamRequest): Promise<Exam> {
    const response = await apiClient.put(`/api/v1/exams/${examId}`, data);
    return response.data;
  }

  static async deleteExam(examId: number): Promise<void> {
    await apiClient.delete(`/api/v1/exams/${examId}`);
  }

  static async addQuestions(examId: number, questionIds: number[]): Promise<ExamDetail> {
    const response = await apiClient.post(`/api/v1/exams/${examId}/questions`, {
      question_ids: questionIds,
    });
    return response.data;
  }

  static async updateExamQuestion(
    examId: number,
    eqId: number,
    data: { points?: number; section?: string }
  ): Promise<ExamDetail> {
    const response = await apiClient.put(`/api/v1/exams/${examId}/questions/${eqId}`, data);
    return response.data;
  }

  static async removeExamQuestion(examId: number, eqId: number): Promise<ExamDetail> {
    const response = await apiClient.delete(`/api/v1/exams/${examId}/questions/${eqId}`);
    return response.data;
  }

  static async reorderQuestions(
    examId: number,
    order: { id: number; position: number }[]
  ): Promise<ExamDetail> {
    const response = await apiClient.post(`/api/v1/exams/${examId}/reorder`, { order });
    return response.data;
  }

  static async autoFill(examId: number, request: AutoFillRequest): Promise<ExamDetail> {
    const response = await apiClient.post(`/api/v1/exams/${examId}/auto-fill`, request);
    return response.data;
  }

  static async finalizeExam(examId: number): Promise<Exam> {
    const response = await apiClient.post(`/api/v1/exams/${examId}/finalize`);
    return response.data;
  }

  static async unfinalizeExam(examId: number): Promise<Exam> {
    const response = await apiClient.post(`/api/v1/exams/${examId}/unfinalize`);
    return response.data;
  }

  static async listApprovedQuestions(params?: {
    topic?: string;
    difficulty?: string;
    bloom_level?: number;
    question_type?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApprovedQuestionsResponse> {
    const response = await apiClient.get('/api/v1/exams/approved-questions', { params });
    return response.data;
  }

  static async downloadExport(examId: number, format: string, includeSolutions = false): Promise<void> {
    const params = new URLSearchParams();
    if (includeSolutions) params.set('include_solutions', 'true');
    const response = await apiClient.get(
      `/api/v1/exams/${examId}/export/${format}`,
      { params, responseType: 'blob' }
    );
    const contentDisposition = response.headers['content-disposition'];
    const filename = contentDisposition?.match(/filename="(.+)"/)?.[1] || `exam_export.${format}`;
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }
}
