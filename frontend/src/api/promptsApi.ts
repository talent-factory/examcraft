import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export interface Prompt {
  id: string;
  name: string;
  content: string;
  description?: string;
  category: 'system_prompt' | 'user_prompt' | 'few_shot_example' | 'template';
  tags: string[];
  use_case?: string;
  version: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  usage_count?: number;
  tokens_estimated?: number;
  parent_id?: string | null;
}

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

export interface PromptTemplate {
  id: string;
  name: string;
  description?: string;
  category: 'question_generation' | 'chatbot' | 'evaluation';
  template_content: string;
  variables: string[];
  example_usage?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const promptsApi = {
  // List all prompts
  listPrompts: async (filters?: {
    category?: string;
    use_case?: string;
    is_active?: boolean;
  }): Promise<Prompt[]> => {
    const response = await axios.get(`${API_BASE_URL}/api/v1/prompts`, {
      params: filters
    });
    return response.data;
  },

  // Get single prompt by ID
  getPrompt: async (id: string): Promise<Prompt> => {
    const response = await axios.get(`${API_BASE_URL}/api/v1/prompts/${id}`);
    return response.data;
  },

  // Create new prompt
  createPrompt: async (data: Partial<Prompt>): Promise<Prompt> => {
    const response = await axios.post(`${API_BASE_URL}/api/v1/prompts`, data);
    return response.data;
  },

  // Update existing prompt
  updatePrompt: async (id: string, data: Partial<Prompt>): Promise<Prompt> => {
    const response = await axios.put(`${API_BASE_URL}/api/v1/prompts/${id}`, data);
    return response.data;
  },

  // Create new version of prompt
  createVersion: async (id: string, content: string, description?: string): Promise<Prompt> => {
    const response = await axios.post(`${API_BASE_URL}/api/v1/prompts/${id}/versions`, {
      content,
      description
    });
    return response.data;
  },

  // Delete prompt
  deletePrompt: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/api/v1/prompts/${id}`);
  },

  // Semantic search
  searchPrompts: async (searchRequest: PromptSearchRequest): Promise<PromptSearchResult[]> => {
    const response = await axios.post(`${API_BASE_URL}/api/v1/prompts/search`, searchRequest);
    return response.data;
  },

  // Get usage logs
  getUsageLogs: async (promptId: string, limit = 100): Promise<PromptUsageLog[]> => {
    const response = await axios.get(`${API_BASE_URL}/api/v1/prompts/${promptId}/usage`, {
      params: { limit }
    });
    return response.data;
  },

  // Get version history
  getVersionHistory: async (promptName: string): Promise<Prompt[]> => {
    const response = await axios.get(`${API_BASE_URL}/api/v1/prompts/versions/${promptName}`);
    return response.data;
  },

  // Activate/Deactivate prompt
  toggleActive: async (id: string, is_active: boolean): Promise<Prompt> => {
    const response = await axios.patch(`${API_BASE_URL}/api/v1/prompts/${id}/active`, {
      is_active
    });
    return response.data;
  },

  // List templates
  listTemplates: async (): Promise<PromptTemplate[]> => {
    const response = await axios.get(`${API_BASE_URL}/api/v1/prompts/templates`);
    return response.data;
  },

  // Get template by ID
  getTemplate: async (id: string): Promise<PromptTemplate> => {
    const response = await axios.get(`${API_BASE_URL}/api/v1/prompts/templates/${id}`);
    return response.data;
  }
};

