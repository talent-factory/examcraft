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

export interface OpsHealthSpecula {
  configured: boolean;
  // Both `get_backend_health()` and `get_frontend_health()` in
  // `ops_health_service.py` populate this when `configured` is `true` (TF-918
  // — replaces the retired Sentry-API integration). `null` when the
  // ClickHouse query failed. Backend and frontend errors are both logged
  // through the `examcraft-api` process and told apart server-side via the
  // `specula.signal_type` log attribute, so both cards get a real,
  // independent count.
  error_count_5m?: number | null;
}

export interface OpsComponentHealth {
  status: OpsHealthStatus;
  metric_label: OpsMetricLabel;
  metric_value: string | number | null;
  timestamp: string;
  detail: string | null;
  deep_link: string | null;
  // CLI fallback for components without a (working) browser deep-link —
  // currently only `rabbitmq` in prod (TF-817: no public IP, a fly.dev URL
  // would be dead; locally TF-800 gives `rabbitmq` a real `deep_link`
  // instead, see `docker-compose.full.yml`). Always present on the wire
  // (unconditional key in `ComponentHealth.to_dict()`, unlike the truly
  // optional `sentry` below) — non-null only when `deep_link` is `null`;
  // the card renders one or the other, never both.
  cli_hint: string | null;
  // Optional on the wire for db/rabbitmq/celery, but when the key is
  // present its value is `null` rather than omitted (Pydantic serializes
  // `Optional[dict] = None` as `null`, not as an absent field) — `frontend`
  // and `backend` always send a real object.
  specula?: OpsHealthSpecula | null;
}

export interface OpsHealthSnapshot {
  generated_at: string;
  overall_status: OpsHealthStatus;
  components: Record<OpsComponentKey, OpsComponentHealth>;
}
