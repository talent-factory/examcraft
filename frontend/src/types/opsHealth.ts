/**
 * Types for the Ops-Dashboard health snapshot (TF-784/785/786).
 *
 * Mirrors the `GET /api/v1/ops/health` backend contract exactly (Full
 * deployment only — see `Admin.tsx`'s `isFullDeployment()` gate). Do not
 * add fields the backend doesn't send; do not loosen the literal unions —
 * a new backend value must be a deliberate, reviewed change on both sides.
 */

export type OpsHealthStatus = 'green' | 'yellow' | 'red';

export type OpsComponentKey = 'frontend' | 'backend' | 'db' | 'rabbitmq' | 'celery';

/**
 * Backend-internal metric identifiers (never human copy — see
 * `metric_label=` call sites in `ops_health_service.py`). The frontend maps
 * each to a translated label via `pages.admin.systemHealth.metricLabel.*`.
 */
export type OpsMetricLabel =
  | 'reachable_machines'
  | 'latency_ms'
  | 'queued_messages'
  | 'online_workers'
  | 'error';

export interface OpsHealthSentry {
  configured: boolean;
}

export interface OpsComponentHealth {
  status: OpsHealthStatus;
  metric_label: OpsMetricLabel;
  metric_value: string | number | null;
  timestamp: string;
  detail: string | null;
  deep_link: string | null;
  // Optional on the wire for db/rabbitmq/celery, but when the key is
  // present its value is `null` rather than omitted (Pydantic serializes
  // `Optional[dict] = None` as `null`, not as an absent field) — `frontend`
  // and `backend` always send a real object.
  sentry?: OpsHealthSentry | null;
}

export interface OpsHealthSnapshot {
  generated_at: string;
  overall_status: OpsHealthStatus;
  components: Record<OpsComponentKey, OpsComponentHealth>;
}
