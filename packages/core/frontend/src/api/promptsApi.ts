import axios from 'axios';
import type {
  Prompt,
  PromptTemplate,
  TemplateVariable,
  PromptRenderRequest,
  PromptRenderResponse,
  TemplateVariablesResponse,
  QuestionType
} from '../types/prompt';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with auth interceptor
const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

// Add auth token to all requests
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('examcraft_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Re-export types from prompt.ts for backward compatibility
export type { Prompt, PromptTemplate } from '../types/prompt';

export interface PromptSearchRequest {
  query: string;
  category?: string;
  use_case?: string;
  tags?: string[];
  limit?: number;
  score_threshold?: number;
}

export interface PromptSearchResult {
  prompt_id: string;
  name: string;
  category: string;
  use_case?: string;
  tags: string[];
  content_preview: string;
  version: number;
  similarity_score: number;
}

export interface PromptUsageLog {
  id: string;
  prompt_id: string;
  prompt_version: number;
  use_case: string;
  tokens_used?: number;
  latency_ms?: number;
  success: boolean;
  timestamp: string;
}



export const promptsApi = {
  // List all prompts
  listPrompts: async (filters?: {
    category?: string;
    use_case?: string;
    is_active?: boolean;
  }): Promise<Prompt[]> => {
    const response = await apiClient.get('/api/v1/prompts', {
      params: filters
    });
    return response.data;
  },

  // Get single prompt by ID
  getPrompt: async (id: string): Promise<Prompt> => {
    const response = await apiClient.get(`/api/v1/prompts/${id}`);
    return response.data;
  },

  // Create new prompt
  createPrompt: async (data: Partial<Prompt>): Promise<Prompt> => {
    const response = await apiClient.post('/api/v1/prompts', data);
    return response.data;
  },

  // Update existing prompt
  updatePrompt: async (id: string, data: Partial<Prompt>): Promise<Prompt> => {
    const response = await apiClient.put(`/api/v1/prompts/${id}`, data);
    return response.data;
  },

  // Create new version of prompt
  createVersion: async (id: string, content: string, description?: string): Promise<Prompt> => {
    const response = await apiClient.post(`/api/v1/prompts/${id}/versions`, {
      content,
      description
    });
    return response.data;
  },

  // Delete prompt
  deletePrompt: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/prompts/${id}`);
  },

  // Semantic search
  searchPrompts: async (searchRequest: PromptSearchRequest): Promise<PromptSearchResult[]> => {
    const response = await apiClient.post('/api/v1/prompts/search', searchRequest);
    return response.data;
  },

  // Get usage logs
  getUsageLogs: async (promptId: string, limit = 100): Promise<PromptUsageLog[]> => {
    const response = await apiClient.get(`/api/v1/prompts/${promptId}/usage`, {
      params: { limit }
    });
    return response.data;
  },

  // Get version history
  getVersionHistory: async (promptName: string): Promise<Prompt[]> => {
    const response = await apiClient.get(`/api/v1/prompts/versions/${promptName}`);
    return response.data;
  },

  // Activate/Deactivate prompt
  toggleActive: async (id: string, is_active: boolean): Promise<Prompt> => {
    const response = await apiClient.patch(`/api/v1/prompts/${id}/active`, {
      is_active
    });
    return response.data;
  },

  // List templates
  listTemplates: async (): Promise<PromptTemplate[]> => {
    const response = await apiClient.get('/api/v1/prompts/templates');
    return response.data;
  },

  // Get template by ID
  getTemplate: async (id: string): Promise<PromptTemplate> => {
    const response = await apiClient.get(`/api/v1/prompts/templates/${id}`);
    return response.data;
  },

  // ===== NEW: Prompt Template Selection Functions =====

  /**
   * Get prompts for a specific question type
   * Filters by use_case and category=system_prompt
   */
  getPromptsForQuestionType: async (questionType: QuestionType): Promise<Prompt[]> => {
    const useCase = `question_generation_${questionType}`;
    const response = await apiClient.get('/api/v1/prompts', {
      params: {
        use_case: useCase,
        category: 'system_prompt',
        is_active: true
      }
    });
    return response.data;
  },

  /**
   * Extract template variables from a prompt
   * Returns list of variables with metadata
   */
  extractTemplateVariables: async (promptId: string): Promise<TemplateVariablesResponse> => {
    const response = await apiClient.get(`/api/v1/prompts/${promptId}/variables`);
    return response.data;
  },

  /**
   * Render prompt template with variables for preview
   * Returns rendered prompt text
   */
  renderPromptPreview: async (request: PromptRenderRequest): Promise<PromptRenderResponse> => {
    const response = await apiClient.post('/api/v1/prompts/render-preview', request);
    return response.data;
  }
};

