/**
 * StudentClassesService — API client for `/api/v1/student-classes/*`.
 *
 * Mirrors `core/backend/api/student_classes.py` (TF-336 Subarea A) and
 * the Cross-Exam-Verlauf-Endpoint from Subarea B.
 */

import {
  deleteVoid,
  getJson,
  patchJson,
  postJson,
} from './httpClient';
import {
  ClassHistoryStats,
  StudentClassDetail,
  StudentClassList,
  StudentClassSummary,
  StudentRefSummary,
} from '../types/studentClass';

const ROOT = '/api/v1/student-classes';

export class StudentClassesService {
  static async list(params: {
    limit?: number;
    offset?: number;
  } = {}): Promise<StudentClassList> {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set('limit', String(params.limit));
    if (params.offset !== undefined) query.set('offset', String(params.offset));
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return getJson<StudentClassList>(`${ROOT}${suffix}`);
  }

  static async create(name: string): Promise<StudentClassSummary> {
    return postJson<StudentClassSummary>(ROOT, { name });
  }

  static async get(classId: number): Promise<StudentClassDetail> {
    return getJson<StudentClassDetail>(`${ROOT}/${classId}`);
  }

  static async rename(
    classId: number,
    name: string,
  ): Promise<StudentClassSummary> {
    return patchJson<StudentClassSummary>(`${ROOT}/${classId}`, { name });
  }

  static async remove(classId: number): Promise<void> {
    return deleteVoid(`${ROOT}/${classId}`);
  }

  static async addMember(
    classId: number,
    studentId: number,
  ): Promise<StudentRefSummary> {
    return postJson<StudentRefSummary>(`${ROOT}/${classId}/members`, {
      student_id: studentId,
    });
  }

  static async removeMember(
    classId: number,
    studentId: number,
  ): Promise<void> {
    return deleteVoid(`${ROOT}/${classId}/members/${studentId}`);
  }

  static async getHistory(classId: number): Promise<ClassHistoryStats> {
    return getJson<ClassHistoryStats>(`${ROOT}/${classId}/stats`);
  }
}
