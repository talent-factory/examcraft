/**
 * Prompts API Service
 *
 * Note: This is a placeholder API for the Core package.
 * Full implementation is available in the Premium package.
 */

import axios, { AxiosInstance } from 'axios';
import { Prompt, PromptCategory } from '../types/prompt';

export interface PromptUsageLog {
  id: string;
  prompt_id: string;
  prompt_version?: number;
  use_case?: string;
  timestamp: string;
  tokens_used?: number;
  latency_ms?: number;
  success: boolean;
  error_message?: string;
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
  id: string;
  prompt_id: string;
  name: string;
  description?: string;
  category: string;
  use_case?: string;
  tags: string[];
  content_preview?: string;
  version?: number;
  relevanceScore: number;
  similarity_score?: number;
}

// Re-export Prompt type from types/prompt.ts
export type { Prompt };

class PromptsApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token to requests
    this.api.interceptors.request.use((config) => {
      const token = localStorage.getItem('examcraft_access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }

  async getPrompts(): Promise<Prompt[]> {
    throw new Error('Prompts API is only available in the Premium package');
  }

  async listPrompts(filters?: { category?: string; is_active?: boolean }): Promise<Prompt[]> {
    throw new Error('Prompts API is only available in the Premium package');
  }

  async getPrompt(id: string): Promise<Prompt> {
    throw new Error('Prompts API is only available in the Premium package');
  }

  async createPrompt(prompt: Omit<Prompt, 'id' | 'version' | 'created_at' | 'updated_at' | 'usage_count'>): Promise<Prompt> {
    throw new Error('Prompts API is only available in the Premium package');
  }

  async updatePrompt(id: string, prompt: Partial<Prompt>): Promise<Prompt> {
    throw new Error('Prompts API is only available in the Premium package');
  }

  async deletePrompt(id: string): Promise<void> {
    throw new Error('Prompts API is only available in the Premium package');
  }

  async getVersionHistory(promptName: string): Promise<Prompt[]> {
    throw new Error('Prompts API is only available in the Premium package');
  }

  async getUsageLogs(promptId: string, limit?: number): Promise<PromptUsageLog[]> {
    throw new Error('Prompts API is only available in the Premium package');
  }

  async searchPrompts(request: PromptSearchRequest): Promise<PromptSearchResult[]> {
    throw new Error('Prompts API is only available in the Premium package');
  }

  async toggleActive(id: string, isActive: boolean): Promise<Prompt> {
    throw new Error('Prompts API is only available in the Premium package');
  }
}

export const promptsApi = new PromptsApiService();

