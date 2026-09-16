/**
 * Error codes reachable through `promptsApi` — core and premium.
 *
 * TWO KINDS, AND THE LIST MIXES THEM. TF-772 PR 4 registered one fallback per
 * operation (`prompts_list_failed`, `prompts_create_failed`, …) because
 * `premium/backend/api/v1/prompts.py` had no localized codes to accept. TF-773
 * PR 2b gave the premium backend its own `premium/backend/locales/` (ADR 0006)
 * and a code at every raise site, so the specific sentences that TF-772 had to
 * trade away — "Nur Superuser dürfen systemweite Prompts verwalten.", "Ein
 * Prompt mit dem Namen '…' existiert in dieser Institution bereits.", "Team-
 * Prompts erfordern eine Org-Unit …" — now arrive as
 * `prompts_system_superuser_only`, `prompts_name_exists`,
 * `prompts_team_org_unit_required` and so on.
 *
 * * **Backend codes** (identity rule, copied from
 *   `premium/backend/locales/t.*.json`): every entry below except the eight
 *   listed next. That includes generic operation names: the backend answers an
 *   unexpected 500 with exactly the fallback's name and sentence, so e.g.
 *   `prompts_list_failed` is both a fallback and a backend code, deliberately.
 *   `prompts_upload_*` come from `PromptUploadService`; the bulk endpoint still
 *   answers 200 and reports per-file failures in its body, which
 *   `PromptUploadZone` renders verbatim — those never pass through here.
 * * **Frontend-only (8)**: `prompts_not_available_in_core`,
 *   `prompts_validation_failed` and `prompts_use_case_invalid` (see below);
 *   `prompts_download_failed`, `prompts_toggle_active_failed` and
 *   `prompts_versions_load_failed`, whose endpoints raise specific codes but
 *   have no generic 500 of their own; `prompts_template_load_failed` and
 *   `prompts_usage_load_failed`, whose routes (`/templates/{id}`,
 *   `/{id}/usage`) do not exist in `prompts.py` at all.
 *
 * `prompts_not_available_in_core` is the one code with no HTTP request behind
 * it. `core/frontend/src/api/promptsApi.ts` is a stub that refuses every call
 * unless `REACT_APP_DEPLOYMENT_MODE=full`; it threw the English literal
 * "Prompts API is only available in the Premium package" from ten methods. The
 * legacy `rag.notAvailableInCore` says the same thing for the RAG stub, but
 * `legacy.ts` is frozen and dot-notation — this one gets the current shape.
 *
 * `prompts_validation_failed` carries `{{issues}}`: `PromptEditor` used to
 * unpack a 422 into "field: message" pairs, and dropping that would have made
 * an unsaveable form silent about which field it objects to. The unpacking now
 * happens in `errors/promptsError.ts` (the only place the Pydantic body is
 * still visible) and travels as an `error_params` value — shared by both
 * `core/frontend/src/api/promptsApi.ts` and
 * `premium/frontend/src/api/promptsApi.ts`, since both hit the same
 * `/api/v1/prompts` endpoints and either one can receive the 422.
 *
 * `prompts_use_case_invalid` is the one 422 that already had a written sentence
 * — `admin.promptEditor.useCaseRequired`, "Bitte wähle einen Fragetyp (Use
 * Case) aus." Its four texts are that copy, moved rather than rewritten, so the
 * form keeps saying the useful thing instead of "use_case: string does not
 * match regex".
 */
export const PROMPTS_ERROR_CODES = [
  'prompts_access_denied',
  'prompts_bulk_too_many_files',
  'prompts_bulk_upload_failed',
  'prompts_create_failed',
  'prompts_delete_failed',
  'prompts_download_failed',
  'prompts_edit_forbidden',
  'prompts_institution_default_admin_only',
  'prompts_institution_default_requires_institution',
  'prompts_list_failed',
  'prompts_load_failed',
  'prompts_name_exists',
  'prompts_name_not_found',
  'prompts_not_available_in_core',
  'prompts_not_found',
  'prompts_render_failed',
  'prompts_render_invalid_syntax',
  'prompts_render_missing_variables',
  'prompts_render_source_required',
  'prompts_render_undefined_variable',
  'prompts_search_failed',
  'prompts_search_unavailable',
  'prompts_system_institution_missing',
  'prompts_system_not_institution_default',
  'prompts_system_superuser_only',
  'prompts_tag_conflict',
  'prompts_tags_invalid',
  'prompts_team_org_unit_not_member',
  'prompts_team_org_unit_required',
  'prompts_template_load_failed',
  'prompts_templates_load_failed',
  'prompts_toggle_active_failed',
  'prompts_update_failed',
  'prompts_upload_content_empty',
  'prompts_upload_duplicate',
  'prompts_upload_failed',
  'prompts_upload_field_invalid',
  'prompts_upload_field_missing',
  'prompts_upload_filename_missing',
  'prompts_upload_frontmatter_invalid',
  'prompts_upload_frontmatter_missing',
  'prompts_upload_frontmatter_not_mapping',
  'prompts_upload_frontmatter_unclosed',
  'prompts_upload_invalid_category',
  'prompts_upload_invalid_file_type',
  'prompts_upload_invalid_institution',
  'prompts_upload_invalid_language',
  'prompts_upload_invalid_name',
  'prompts_upload_invalid_tags',
  'prompts_upload_invalid_use_case',
  'prompts_upload_no_institution',
  'prompts_upload_not_utf8',
  'prompts_usage_load_failed',
  'prompts_use_case_invalid',
  'prompts_validation_failed',
  'prompts_variables_load_failed',
  'prompts_version_conflict',
  'prompts_version_create_failed',
  'prompts_version_name_too_long',
  'prompts_versions_load_failed',
  'prompts_versions_not_found',
] as const;
