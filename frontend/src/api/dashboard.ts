// core/frontend/src/api/dashboard.ts

import { ActivityType } from '../types/activity';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface DashboardStatsResponse {
  generated_questions: number;
  documents: number;
  validated_questions: number;
  exams: number;
}

export interface DashboardActivityItem {
  id: string;
  type: ActivityType;
  title: string;
  timestamp: string;
  metadata?: Record<string, unknown> | null;
}

export interface DashboardActivityResponse {
  activities: DashboardActivityItem[];
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
