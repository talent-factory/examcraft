import { useEffect } from 'react';
import { sendActivityHeartbeat } from '../services/liveActivityService';
import { ActivityBucketId } from '../types/liveActivity';
import { isFullDeployment } from '../utils/deploymentMode';

// TF-838: matches the ticket's "alle ~15-20s" cadence and stays comfortably
// under the backend's 10-requests-per-minute UserRateLimiter
// (premium/backend/api/v1/activity.py).
const HEARTBEAT_INTERVAL_MS = 15000;

// Module-level, shared across every mounted instance of this hook (not
// per-component) — guards against a remount storm re-sending a heartbeat
// for the same bucket within one interval window. Without this, fast
// unmount/remount cycles that share a bucket (ReviewQueue -> detail -> back,
// or clicking between Admin tabs that all report "admin_reference_data_edit")
// each fire an immediate beat on mount, which can exceed the backend's
// 10-requests-per-minute limit from normal navigation alone (PR #286 review).
const lastSentAt = new Map<ActivityBucketId, number>();

/**
 * Test-only: clears the shared dedup state between test cases. `lastSentAt`
 * is intentionally module-level (singleton, not per-hook-instance) in
 * production, which means it otherwise leaks across `it()` blocks that
 * reuse a bucket id — call this in `beforeEach` when testing the hook.
 */
export function __resetActivityHeartbeatDedupForTests(): void {
  lastSentAt.clear();
}

/**
 * Sends a presence heartbeat for `bucketId` while a Kategorie-2 Live-Activity
 * mount point is active (TF-838). Pass `null` to pause without unmounting
 * the caller — e.g. a multi-view component that only sometimes represents
 * this bucket (see `PromptLibraryWithUpload`'s `viewMode` switch).
 *
 * No-ops in Core deployment: `POST /api/v1/activity/heartbeat` is only
 * registered in Full (`core/backend/main.py`'s `is_full_deployment` gate) —
 * most of this hook's call sites live in `core/`, the tier mirrored to the
 * public OSS repo, so without this gate every Core deployment would loop a
 * failing request forever (matches the read-side `isFullDeployment()` gate
 * already used for the Live Activity tab itself in `Admin.tsx`).
 *
 * Best-effort: a failed heartbeat is logged and swallowed, never surfaced to
 * the user — presence tracking must not break the underlying workflow.
 */
export function useActivityHeartbeat(bucketId: ActivityBucketId | null): void {
  useEffect(() => {
    if (!bucketId || !isFullDeployment()) return undefined;

    const beat = async () => {
      const now = Date.now();
      const last = lastSentAt.get(bucketId);
      if (last !== undefined && now - last < HEARTBEAT_INTERVAL_MS) return;
      lastSentAt.set(bucketId, now);
      try {
        await sendActivityHeartbeat(bucketId);
      } catch (err) {
        // Logged unconditionally, including after this effect's cleanup has
        // already run: console.warn has no post-unmount hazard (unlike
        // setState), and the contract above promises failures are "logged
        // and swallowed", not silently dropped once the component is gone.
        console.warn(`[useActivityHeartbeat] heartbeat failed for bucket "${bucketId}"`, err);
      }
    };

    beat();
    const timerId = setInterval(beat, HEARTBEAT_INTERVAL_MS);

    return () => {
      clearInterval(timerId);
    };
  }, [bucketId]);
}

export default useActivityHeartbeat;
