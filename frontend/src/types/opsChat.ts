/**
 * Types for the Ops-Dashboard KI-Chat-Widget (TF-787).
 *
 * Mirrors the `POST /api/v1/ops/chat` backend contract exactly (Full
 * deployment only, superuser-gated — see `Admin.tsx`'s `isFullDeployment()`
 * gate). History is ephemeral: the frontend holds it in local state and
 * resends it in full on every request; nothing is persisted server-side.
 */

export type OpsChatRole = 'user' | 'assistant';

export interface OpsChatTurn {
  role: OpsChatRole;
  content: string;
}
