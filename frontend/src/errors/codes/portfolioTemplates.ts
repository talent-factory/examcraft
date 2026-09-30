/**
 * Error codes reachable through `portfolioApi`'s template methods (TF-987),
 * router `premium/backend/api/v1/portfolio_templates.py`.
 *
 * BACKEND CODES, texts verbatim from `premium/backend/locales/t.*.json`
 * (`%{criterion}`/`%{missing}`/`%{max}` rewritten to `{{…}}`): every
 * `portfolio_template_*` key there except the fallbacks below.
 *
 * FRONTEND-ONLY FALLBACKS, one per operation:
 * `portfolio_template_create_failed`, `portfolio_template_delete_failed`,
 * `portfolio_template_list_failed`, `portfolio_template_load_failed`,
 * `portfolio_template_update_failed`.
 */
export const PORTFOLIO_TEMPLATES_ERROR_CODES = [
  'portfolio_template_conflict',
  'portfolio_template_create_failed',
  'portfolio_template_delete_blocked',
  'portfolio_template_delete_failed',
  'portfolio_template_edit_forbidden',
  'portfolio_template_incomplete_rubric',
  'portfolio_template_invalid_max_points',
  'portfolio_template_list_failed',
  'portfolio_template_load_failed',
  'portfolio_template_not_found',
  'portfolio_template_org_unit_required',
  'portfolio_template_phases_locked',
  'portfolio_template_update_failed',
  'portfolio_template_visibility_system_forbidden',
  'portfolio_template_visibility_team_forbidden',
] as const;
