// core/frontend/src/api/dashboard.ts

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface DashboardStatsResponse {
  generated_questions: number;
  documents: number;
  validated_questions: number;
  exams: number;
}

export interface ActivityItem {
  id: string;
  type: 'document_uploaded' | 'document_deleted' | 'questions_generated' | 'exam_created' | 'question_approved' | 'question_rejected' | 'exam_deleted';
  title: string;
  timestamp: string;
  metadata?: Record<string, unknown> | null;
}

export interface DashboardActivityResponse {
  activities: ActivityItem[];
}

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('examcraft_access_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function fetchDashboardStats(): Promise<DashboardStatsResponse> {
  const resp = await fetch(`${API_BASE_URL}/api/dashboard/stats`, {
    headers: getAuthHeaders(),
  });
  if (!resp.ok) throw new Error(`Dashboard stats failed: ${resp.status}`);
  return resp.json();
}

export async function fetchDashboardActivity(): Promise<DashboardActivityResponse> {
  const resp = await fetch(`${API_BASE_URL}/api/dashboard/activity`, {
    headers: getAuthHeaders(),
  });
  if (!resp.ok) throw new Error(`Dashboard activity failed: ${resp.status}`);
  return resp.json();
}
