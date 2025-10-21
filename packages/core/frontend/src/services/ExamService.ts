import axios from 'axios';
import { ExamRequest, ExamResponse, ApiResponse } from '../types/exam';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token and logging
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('examcraft_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('Response error:', error);
    
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.detail || error.response.data?.message || 'Server error';
      throw new Error(`${error.response.status}: ${message}`);
    } else if (error.request) {
      // Request was made but no response received
      throw new Error('Keine Verbindung zum Server möglich. Bitte prüfen Sie Ihre Internetverbindung.');
    } else {
      // Something else happened
      throw new Error('Ein unerwarteter Fehler ist aufgetreten.');
    }
  }
);

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
