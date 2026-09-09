/**
 * Error codes reachable through `OrgUnitsService` (TF-772 PR 4).
 *
 * The file is `orgUnits.ts` and the codes are `org_units_*`: the README's rule
 * is "the file name is the backend prefix", and the backend router is
 * `org_units.py` mounted at `/api/v1/org-units`. A file named `org_units.ts`
 * beside `documents.ts` and `orgUnits.ts` beside nothing was a coin toss; the
 * camelCase filename matches every other module in `services/` and `types/`
 * (`orgUnitsService.ts`, `orgUnit.ts`), the snake_case codes match the wire.
 *
 * `org_units.py` was frontend-fallback-only when this file was first written.
 * TF-773 has since migrated it onto `api_error()`/`AppHTTPException`, so
 * twelve codes below are now real backend codes, accepted off the wire:
 * `org_units_not_found`, `org_units_grant_role_admin_only`,
 * `org_units_role_not_found`, `org_units_create_conflict`,
 * `org_units_move_to_root_ambiguous`, `org_units_move_conflict`,
 * `org_units_null_parent_ambiguous`, `org_units_update_conflict`,
 * `org_units_delete_conflict`, `org_units_user_not_found`,
 * `org_units_assign_conflict`, `org_units_membership_not_found`. Six of
 * these (`not_found`, `grant_role_admin_only`, `role_not_found`,
 * `move_to_root_ambiguous`, `null_parent_ambiguous`, `user_not_found`) have a
 * static `t()` key on the backend too — their sentences below are copied
 * verbatim from `core/backend/locales/t.*.json`, not independently written.
 * The other six (`create_conflict`, `move_conflict`, `update_conflict`,
 * `delete_conflict`, `assign_conflict`, `membership_not_found`) are raised as
 * `detail=str(exc)` from a service-layer `ValueError` with no locale key
 * behind it — the sentences below are frontend-original.
 *
 * WHY THIS ONE MATTERED ENOUGH TO DO NOW. PR 3 converted
 * `OrgUnitAssignmentDialog.loadData`, whose single `catch` awaits
 * `AdminService.getUser` AND `OrgUnitsService.list`. Converting the first
 * without the second meant every OrgUnits failure in that dialog collapsed to
 * the generic fallback — a deliberate, test-documented regression handed to
 * this PR. Registering `org_units_list_failed` (below) is what retires it;
 * registering the backend's own twelve codes on top is what makes assigning
 * and removing a membership specific again too, not just listing.
 *
 * Six frontend-only fallback codes for seven `OrgUnitsService` methods:
 * `list()` and `mine()` hit different endpoints (`/org-units` is gated by
 * `manage_org_units`, `/org-units/mine` is not) but fail with the same
 * sentence for the reader — "the org units could not be loaded". Same
 * reasoning as `review_fetch_queue_failed` in `review.ts`.
 */
export const ORG_UNITS_ERROR_CODES = [
  'org_units_add_member_failed',
  'org_units_assign_conflict',
  'org_units_create_conflict',
  'org_units_create_failed',
  'org_units_delete_conflict',
  'org_units_delete_failed',
  'org_units_grant_role_admin_only',
  'org_units_list_failed',
  'org_units_membership_not_found',
  'org_units_move_conflict',
  'org_units_move_to_root_ambiguous',
  'org_units_not_found',
  'org_units_null_parent_ambiguous',
  'org_units_remove_member_failed',
  'org_units_role_not_found',
  'org_units_update_conflict',
  'org_units_update_failed',
  'org_units_user_not_found',
] as const;
