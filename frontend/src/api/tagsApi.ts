import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// TF-397: tag namespace. 'content' tags classify Fragen/Dokumente, 'prompt'
// tags classify Prompt-Templates. The backend defaults to 'content'.
export type TagKind = 'content' | 'prompt';

export interface Tag {
  id: number;
  name: string;
  institution_id: number | null;
  scope: 'global' | 'institution';
  kind: TagKind;
  usage_count: number;
  is_archived: boolean;
  is_own: boolean;
}

export interface PendingTag {
  __pending: true;
  name: string;
}

export type TagValue = Tag | PendingTag;

export const isPendingTag = (t: TagValue): t is PendingTag => '__pending' in t && t.__pending === true;

export interface QuestionTagsResponse {
  tags: Tag[];
}

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

export const tagsApi = {
  listTags: async (includeArchived = false, kind?: TagKind): Promise<Tag[]> => {
    const resp = await apiClient.get<Tag[]>('/api/v1/tags', {
      params: { include_archived: includeArchived, ...(kind ? { kind } : {}) },
    });
    return resp.data;
  },

  createTag: async (
    name: string,
    scope: 'global' | 'institution' = 'institution',
    kind?: TagKind
  ): Promise<Tag> => {
    const resp = await apiClient.post<Tag>('/api/v1/tags', {
      name,
      scope,
      ...(kind ? { kind } : {}),
    });
    return resp.data;
  },

  renameTag: async (tagId: number, name: string): Promise<Tag> => {
    const resp = await apiClient.patch<Tag>(`/api/v1/tags/${tagId}`, { name });
    return resp.data;
  },

  archiveTag: async (tagId: number): Promise<Tag> => {
    const resp = await apiClient.post<Tag>(`/api/v1/tags/${tagId}/archive`);
    return resp.data;
  },

  unarchiveTag: async (tagId: number): Promise<Tag> => {
    const resp = await apiClient.post<Tag>(`/api/v1/tags/${tagId}/unarchive`);
    return resp.data;
  },

  deleteTag: async (tagId: number): Promise<void> => {
    await apiClient.delete(`/api/v1/tags/${tagId}`);
  },

  mergeTags: async (sourceIds: number[], targetId: number): Promise<Tag[]> => {
    const resp = await apiClient.post<Tag[]>('/api/v1/tags/merge', {
      source_ids: sourceIds,
      target_id: targetId,
    });
    return resp.data;
  },

  setQuestionTags: async (
    questionId: number,
    tagIds: number[]
  ): Promise<QuestionTagsResponse> => {
    const resp = await apiClient.post<QuestionTagsResponse>(
      `/api/v1/questions/${questionId}/tags`,
      { tag_ids: tagIds }
    );
    return resp.data;
  },

  removeQuestionTag: async (
    questionId: number,
    tagId: number
  ): Promise<QuestionTagsResponse> => {
    const resp = await apiClient.delete<QuestionTagsResponse>(
      `/api/v1/questions/${questionId}/tags/${tagId}`
    );
    return resp.data;
  },
};
