/**
 * StudentsService — API client for `/api/v1/students/*` (TF-336 B).
 */

import { getJson } from './httpClient';
import {
  StudentDetail,
  StudentHistoryStats,
  StudentList,
} from '../types/student';

const ROOT = '/api/v1/students';

export class StudentsService {
  static async list(params: {
    search?: string;
    classId?: number;
    limit?: number;
    offset?: number;
  } = {}): Promise<StudentList> {
    const query = new URLSearchParams();
    if (params.search) query.set('search', params.search);
    if (params.classId !== undefined) query.set('class_id', String(params.classId));
    if (params.limit !== undefined) query.set('limit', String(params.limit));
    if (params.offset !== undefined) query.set('offset', String(params.offset));
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return getJson<StudentList>(`${ROOT}${suffix}`);
  }

  static async get(studentId: number): Promise<StudentDetail> {
    return getJson<StudentDetail>(`${ROOT}/${studentId}`);
  }

  static async getHistory(studentId: number): Promise<StudentHistoryStats> {
    return getJson<StudentHistoryStats>(`${ROOT}/${studentId}/stats`);
  }
}
