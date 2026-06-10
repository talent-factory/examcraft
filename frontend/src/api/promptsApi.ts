/**
 * Prompts API Service
 *
 * Note: This is a placeholder API for the Core package.
 * Full implementation is available in the Premium package.
 *
 * In Full deployment mode, this will dynamically load the Premium implementation.
 */

import { apiClient } from './apiClient';
import { Prompt } from '../types/prompt';

// Check if Premium package is available
const DEPLOYMENT_MODE = process.env.REACT_APP_DEPLOYMENT_MODE || 'core';
const isPremiumAvailable = DEPLOYMENT_MODE === 'full';

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

/**
 * TF-397: write payload for creating/updating prompts.
 * Tags are sent as managed `tag_ids` (kind='prompt'), not free-text strings.
 */
export interface PromptWritePayload {
  name: string;
  content: string;
  description?: string;
  category: string;
  use_case: string;
  is_active?: boolean;
  tag_ids: number[];
}

class PromptsApiService {

  async getPrompts(): Promise<Prompt[]> {
    if (!isPremiumAvailable) {
      throw new Error('Prompts API is only available in the Premium package');
    }
    const response = await apiClient.get('/api/v1/prompts');
    return response.data;
  }

  async listPrompts(filters?: { category?: string; is_active?: boolean }): Promise<Prompt[]> {
    if (!isPremiumAvailable) {
      throw new Error('Prompts API is only available in the Premium package');
    }
    const response = await apiClient.get('/api/v1/prompts', { params: filters });
    return response.data;
  }

  async getPrompt(id: string): Promise<Prompt> {
    if (!isPremiumAvailable) {
      throw new Error('Prompts API is only available in the Premium package');
    }
    const response = await apiClient.get(`/api/v1/prompts/${id}`);
    return response.data;
  }

  async createPrompt(prompt: PromptWritePayload): Promise<Prompt> {
    if (!isPremiumAvailable) {
      throw new Error('Prompts API is only available in the Premium package');
    }
    const response = await apiClient.post('/api/v1/prompts', prompt);
    return response.data;
  }

  async updatePrompt(id: string, prompt: Partial<PromptWritePayload>): Promise<Prompt> {
    if (!isPremiumAvailable) {
      throw new Error('Prompts API is only available in the Premium package');
    }
    const response = await apiClient.put(`/api/v1/prompts/${id}`, prompt);
    return response.data;
  }

  async deletePrompt(id: string): Promise<void> {
    if (!isPremiumAvailable) {
      throw new Error('Prompts API is only available in the Premium package');
    }
    await apiClient.delete(`/api/v1/prompts/${id}`);
  }

  async getVersionHistory(promptName: string): Promise<Prompt[]> {
    if (!isPremiumAvailable) {
      throw new Error('Prompts API is only available in the Premium package');
    }
    const response = await apiClient.get(`/api/v1/prompts/${promptName}/versions`);
    return response.data;
  }

  async getUsageLogs(promptId: string, limit?: number): Promise<PromptUsageLog[]> {
    if (!isPremiumAvailable) {
      throw new Error('Prompts API is only available in the Premium package');
    }
    const response = await apiClient.get(`/api/v1/prompts/${promptId}/usage`, {
      params: { limit }
    });
    return response.data;
  }

  async searchPrompts(request: PromptSearchRequest): Promise<PromptSearchResult[]> {
    if (!isPremiumAvailable) {
      throw new Error('Prompts API is only available in the Premium package');
    }
    const response = await apiClient.post('/api/v1/prompts/search', request);
    return response.data;
  }

  async toggleActive(id: string, isActive: boolean): Promise<Prompt> {
    if (!isPremiumAvailable) {
      throw new Error('Prompts API is only available in the Premium package');
    }
    const response = await apiClient.patch(`/api/v1/prompts/${id}/active`, { is_active: isActive });
    return response.data;
  }
}

export const promptsApi = new PromptsApiService();
