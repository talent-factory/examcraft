/**
 * MoodleConnectionsService — API client for
 * `/api/v1/admin/moodle-connections/*` and
 * `/api/v1/exams/{id}/sync-moodle-question-ids` (TF-336 C + D).
 */

import {
  deleteVoid,
  getJson,
  patchJson,
  postJson,
} from './httpClient';
import {
  MoodleConnection,
  MoodleConnectionList,
  MoodleConnectionTestResult,
  SyncMoodleQuestionIdsResult,
} from '../types/moodleConnection';

const ROOT = '/api/v1/admin/moodle-connections';

export class MoodleConnectionsService {
  static async list(): Promise<MoodleConnectionList> {
    return getJson<MoodleConnectionList>(ROOT);
  }

  static async create(params: {
    base_url: string;
    token: string;
  }): Promise<MoodleConnection> {
    return postJson<MoodleConnection>(ROOT, params);
  }

  static async update(
    id: number,
    params: { base_url?: string; token?: string },
  ): Promise<MoodleConnection> {
    return patchJson<MoodleConnection>(`${ROOT}/${id}`, params);
  }

  static async remove(id: number): Promise<void> {
    return deleteVoid(`${ROOT}/${id}`);
  }

  static async test(id: number): Promise<MoodleConnectionTestResult> {
    return postJson<MoodleConnectionTestResult>(`${ROOT}/${id}/test`, {});
  }

  static async syncQuestionIds(
    examId: number,
    params: {
      moodle_quiz_id: number;
      moodle_question_ids?: number[];
    },
  ): Promise<SyncMoodleQuestionIdsResult> {
    return postJson<SyncMoodleQuestionIdsResult>(
      `/api/v1/exams/${examId}/sync-moodle-question-ids`,
      params,
    );
  }
}
