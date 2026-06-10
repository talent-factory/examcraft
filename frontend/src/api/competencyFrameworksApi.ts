import axios from 'axios';
import type {
  CompetencyFramework,
  FrameworkCreatePayload,
  FrameworkUpdatePayload,
} from '../types/competencyFramework';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('examcraft_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const competencyFrameworksApi = {
  listFrameworks: async (includeArchived = false): Promise<CompetencyFramework[]> => {
    const resp = await apiClient.get<CompetencyFramework[]>('/api/v1/competency-frameworks', {
      params: { include_archived: includeArchived },
    });
    return resp.data;
  },

  getFramework: async (id: number): Promise<CompetencyFramework> => {
    const resp = await apiClient.get<CompetencyFramework>(`/api/v1/competency-frameworks/${id}`);
    return resp.data;
  },

  createFramework: async (payload: FrameworkCreatePayload): Promise<CompetencyFramework> => {
    const resp = await apiClient.post<CompetencyFramework>('/api/v1/competency-frameworks', payload);
    return resp.data;
  },

  updateFramework: async (
    id: number,
    payload: FrameworkUpdatePayload
  ): Promise<CompetencyFramework> => {
    const resp = await apiClient.put<CompetencyFramework>(
      `/api/v1/competency-frameworks/${id}`,
      payload
    );
    return resp.data;
  },

  archiveFramework: async (id: number): Promise<CompetencyFramework> => {
    const resp = await apiClient.post<CompetencyFramework>(
      `/api/v1/competency-frameworks/${id}/archive`
    );
    return resp.data;
  },

  unarchiveFramework: async (id: number): Promise<CompetencyFramework> => {
    const resp = await apiClient.post<CompetencyFramework>(
      `/api/v1/competency-frameworks/${id}/unarchive`
    );
    return resp.data;
  },
};
