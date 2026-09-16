/**
 * Types for the Live-Activity heartbeat/snapshot API (TF-833/TF-838).
 *
 * Mirrors `GET /api/v1/ops/activity` and `POST /api/v1/activity/heartbeat`
 * exactly (Full deployment only, same `isFullDeployment()` gate as
 * `opsHealth.ts`). Bucket display order/labels are a frontend-only concern
 * — see `LiveActivityPanel.tsx`'s `BUCKET_ORDER`, not this file.
 */

export const ACTIVITY_BUCKET_IDS = [
  'documents_upload',
  'questions_generate_rag',
  'questions_review',
  'exam_compose',
  'exam_results_import',
  'prompt_template_edit',
  'prompt_wizard_chat',
  'document_chat_session',
  'admin_reference_data_edit',
] as const;
export type ActivityBucketId = (typeof ACTIVITY_BUCKET_IDS)[number];

export interface ActivityBucketValue {
  value: number;
  /** `false` means `value` is the clamped Kleinstzahl-Schwelle (TF-826/ADR-0006), not a raw count. */
  exact: boolean;
}

export interface LiveActivitySnapshot {
  generated_at: string;
  // A bucket_id from ACTIVITY_BUCKET_IDS missing from this record means its
  // fetch failed server-side (Redis/DB error, logged there) — NOT zero
  // activity. A genuine zero is always present as `{ value: 0, exact: true
  // }` (see `ActivitySnapshotOut`'s docstring in
  // `premium/backend/api/v1/ops.py`).
  buckets: Partial<Record<ActivityBucketId, ActivityBucketValue>>;
}
