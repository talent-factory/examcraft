/**
 * TypeScript types for the activity API.
 *
 * Mirrors the Pydantic schemas in `core/backend/api/activity.py`.
 * The literal-union + `as const` array pattern (taken from
 * `types/submission.ts`) keeps dropdown labels and switch statements
 * sharing one source of truth.
 */

export const ACTIVITY_TYPES = [
  'document_uploaded',
  'document_deleted',
  'questions_generated',
  'question_approved',
  'question_rejected',
  'exam_created',
  'exam_deleted',
] as const;
export type ActivityType = (typeof ACTIVITY_TYPES)[number];

export const ACTIVITY_SCOPES = ['own', 'institution'] as const;
export type ActivityScope = (typeof ACTIVITY_SCOPES)[number];

export interface ActivityItem {
  id: string;
  type: ActivityType;
  title: string;
  timestamp: string;
  /** Only populated when scope=institution. */
  actor_user_id: number | null;
}

export interface ActivityListResponse {
  items: ActivityItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}
