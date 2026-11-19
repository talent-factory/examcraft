import { getJson, postVoid } from './httpClient';
import { ActivityBucketId, LiveActivitySnapshot } from '../types/liveActivity';

/**
 * Fetches the live Activity-Count snapshot (TF-838).
 *
 * Superuser-only on the backend (403 for anyone else) — callers must gate
 * rendering on `is_superuser` themselves, matching `opsHealthService`. Pure
 * live snapshot, nothing cached: call it again to get a fresh read.
 */
export async function fetchLiveActivity(): Promise<LiveActivitySnapshot> {
  return getJson<LiveActivitySnapshot>('/api/v1/ops/activity');
}

/**
 * Sends a presence heartbeat for `bucketId` (TF-838). The backend keys
 * presence off the session's user id, not the request body — a person with
 * multiple open tabs on the same bucket still counts once (ADR-0007).
 *
 * A failed heartbeat is swallowed by `useActivityHeartbeat`.
 */
export async function sendActivityHeartbeat(bucketId: ActivityBucketId): Promise<void> {
  await postVoid('/api/v1/activity/heartbeat', { bucket_id: bucketId });
}
