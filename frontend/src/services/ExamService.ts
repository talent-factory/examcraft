import { apiClient } from '../api/apiClient';
import { ExamRequest, ExamResponse } from '../types/exam';

export class ExamService {
  /**
   * Generate a new exam based on the provided request
   */
  static async generateExam(request: ExamRequest): Promise<ExamResponse> {
    try {
      const response = await apiClient.post<ExamResponse>('/api/v1/generate-exam', request);
      return response.data;
    } catch (error) {
      console.error('Error generating exam:', error);
      throw error;
    }
  }

  /**
   * Get available topics for exam generation
   */
  static async getAvailableTopics(): Promise<string[]> {
    try {
      const response = await apiClient.get<{ topics: string[] }>('/api/v1/topics');
      return response.data.topics;
    } catch (error) {
      console.error('Error fetching topics:', error);
      throw error;
    }
  }

  /**
   * Get a specific exam by ID
   */
  static async getExam(examId: string): Promise<ExamResponse> {
    try {
      const response = await apiClient.get<ExamResponse>(`/api/v1/exam/${examId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching exam:', error);
      throw error;
    }
  }

  /**
   * Health check for the API
   */
  static async healthCheck(): Promise<boolean> {
    try {
      const response = await apiClient.get('/health');
      return response.status === 200;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }
}
