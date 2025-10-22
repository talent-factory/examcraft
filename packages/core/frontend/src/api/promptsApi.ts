/**
 * Prompts API Service
 * 
 * Note: This is a placeholder API for the Core package.
 * Full implementation is available in the Premium package.
 */

import axios, { AxiosInstance } from 'axios';

export interface Prompt {
  id: string;
  name: string;
  description?: string;
  category: string;
  tags: string[];
  content: string;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface PromptUsageLog {
  id: string;
  promptId: string;
  timestamp: string;
  tokensUsed: number;
  cost: number;
}

export interface PromptSearchRequest {
  query: string;
  category?: string;
  tags?: string[];
  limit?: number;
}

export interface PromptSearchResult {
  id: string;
  name: string;
  description?: string;
  category: string;
  tags: string[];
  relevanceScore: number;
}

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

  async getPrompt(id: string): Promise<Prompt> {
    throw new Error('Prompts API is only available in the Premium package');
  }

  async createPrompt(prompt: Omit<Prompt, 'id' | 'version' | 'createdAt' | 'updatedAt'>): Promise<Prompt> {
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

  async getUsageLogs(promptId: string): Promise<PromptUsageLog[]> {
    throw new Error('Prompts API is only available in the Premium package');
  }

  async searchPrompts(request: PromptSearchRequest): Promise<PromptSearchResult[]> {
    throw new Error('Prompts API is only available in the Premium package');
  }
}

export const promptsApi = new PromptsApiService();

