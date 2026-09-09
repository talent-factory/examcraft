/**
 * Prompts API Service
 *
 * Note: This is a placeholder API for the Core package.
 * Full implementation is available in the Premium package.
 *
 * In Full deployment mode, this will dynamically load the Premium implementation.
 */

import { apiClient } from './apiClient';
import { AppError, AppErrorCode, promptsError } from '../errors';
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
  // TF-410 visibility tiers (permission-checked server-side).
  visibility?: string;
  is_institution_default?: boolean;
  // TF-641: target Org-Unit for the "team" tier. Only meaningful together
  // with visibility='team'; the editor has sent it since TF-651.
  org_unit_id?: number | null;
}

/**
 * Run one prompts request, or refuse it (TF-772).
 *
 * Collects the two things every method below used to repeat: the Core-stub
 * guard — this module is a placeholder that only forwards when
 * `REACT_APP_DEPLOYMENT_MODE=full` — and the conversion of an axios rejection
 * into an `AppError` carrying this operation's code.
 *
 * The refusal is not a developer error: a Core deployment really can route a
 * user to the prompt admin surfaces, so it needs a translated sentence rather
 * than the English `new Error` that stood in all ten methods here.
 */
async function guarded<T>(code: AppErrorCode, call: () => Promise<T>): Promise<T> {
  if (!isPremiumAvailable) {
    throw new AppError('prompts_not_available_in_core');
  }
  try {
    return await call();
  } catch (err) {
    throw promptsError(err, code);
  }
}

class PromptsApiService {

  async getPrompts(): Promise<Prompt[]> {
    return guarded('prompts_list_failed', async () => {
      const response = await apiClient.get('/api/v1/prompts');
      return response.data;
    });
  }

  async listPrompts(filters?: { category?: string; is_active?: boolean }): Promise<Prompt[]> {
    return guarded('prompts_list_failed', async () => {
      const response = await apiClient.get('/api/v1/prompts', { params: filters });
      return response.data;
    });
  }

  async getPrompt(id: string): Promise<Prompt> {
    return guarded('prompts_load_failed', async () => {
      const response = await apiClient.get(`/api/v1/prompts/${id}`);
      return response.data;
    });
  }

  async createPrompt(prompt: PromptWritePayload): Promise<Prompt> {
    return guarded('prompts_create_failed', async () => {
      const response = await apiClient.post('/api/v1/prompts', prompt);
      return response.data;
    });
  }

  async updatePrompt(id: string, prompt: Partial<PromptWritePayload>): Promise<Prompt> {
    return guarded('prompts_update_failed', async () => {
      const response = await apiClient.put(`/api/v1/prompts/${id}`, prompt);
      return response.data;
    });
  }

  async deletePrompt(id: string): Promise<void> {
    return guarded('prompts_delete_failed', async () => {
      await apiClient.delete(`/api/v1/prompts/${id}`);
    });
  }

  async getVersionHistory(promptName: string): Promise<Prompt[]> {
    return guarded('prompts_versions_load_failed', async () => {
      const response = await apiClient.get(`/api/v1/prompts/${promptName}/versions`);
      return response.data;
    });
  }

  async getUsageLogs(promptId: string, limit?: number): Promise<PromptUsageLog[]> {
    return guarded('prompts_usage_load_failed', async () => {
      const response = await apiClient.get(`/api/v1/prompts/${promptId}/usage`, {
        params: { limit }
      });
      return response.data;
    });
  }

  async searchPrompts(request: PromptSearchRequest): Promise<PromptSearchResult[]> {
    return guarded('prompts_search_failed', async () => {
      const response = await apiClient.post('/api/v1/prompts/search', request);
      return response.data;
    });
  }

  async toggleActive(id: string, isActive: boolean): Promise<Prompt> {
    return guarded('prompts_toggle_active_failed', async () => {
      const response = await apiClient.patch(`/api/v1/prompts/${id}/active`, { is_active: isActive });
      return response.data;
    });
  }
}

export const promptsApi = new PromptsApiService();
