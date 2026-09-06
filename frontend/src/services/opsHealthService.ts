import { getJson } from './httpClient';
import { OpsHealthSnapshot } from '../types/opsHealth';

/**
 * Fetches the live Ops-Dashboard health snapshot (TF-786).
 *
 * Superuser-only on the backend (403 for anyone else) — callers must gate
 * rendering on `is_superuser` themselves; this function does not check it.
 * Pure live snapshot, nothing cached: call it again to get a fresh read.
 */
export async function fetchOpsHealth(): Promise<OpsHealthSnapshot> {
  return getJson<OpsHealthSnapshot>('/api/v1/ops/health');
}
