/**
 * Error codes reachable through `promptsApi` — core and premium (TF-772 PR 4).
 *
 * ALL OF THEM ARE FRONTEND-ONLY. That is the exception to the pattern
 * `documents.ts` and `auth.ts` set, and it is not a shortcut: the prompts
 * router lives in `premium/backend/api/v1/prompts.py`, and the premium backend
 * has no `locales/` directory at all. There is no `prompts_*` key in
 * `core/backend/locales/t.*.json` to copy, and no endpoint that can send an
 * `error_code` for the accept-list to accept. The identity rule has nothing to
 * be identical to here, so the names below follow its *shape* — flat
 * snake_case, prefix = router — so that they need no renaming on the day the
 * premium backend gets localized codes.
 *
 * THE COST, STATED PLAINLY. `prompts.py` distinguishes about a dozen rejection
 * reasons in German prose ("Nur Superuser dürfen systemweite Prompts
 * verwalten.", "Ein Prompt mit dem Namen 'X' existiert in dieser Institution
 * bereits.", "Team-Prompts erfordern eine Org-Unit (org_unit_id)."), and until
 * TF-772 the components rendered exactly that text. One fallback per operation
 * cannot say any of it — the same regression `documents.ts` argues against at
 * length. It is unavoidable here rather than chosen: the registry is an
 * accept-list, and registering codes no endpoint can produce would put a dozen
 * permanently-unreachable keys under the i18n guard. The other half of the
 * trade is real too — the same helper also raises English ("Failed to list
 * prompts: …", "Prompt not found", "Either prompt_id or prompt_content must be
 * provided"), and that text stops reaching the UI.
 *
 * Reported for the premium backend rather than worked around here: string
 * matching on German prose to recover the distinction would be worse than the
 * generic sentence.
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
  'prompts_bulk_upload_failed',
  'prompts_create_failed',
  'prompts_delete_failed',
  'prompts_download_failed',
  'prompts_list_failed',
  'prompts_load_failed',
  'prompts_not_available_in_core',
  'prompts_render_failed',
  'prompts_search_failed',
  'prompts_template_load_failed',
  'prompts_templates_load_failed',
  'prompts_toggle_active_failed',
  'prompts_update_failed',
  'prompts_upload_failed',
  'prompts_usage_load_failed',
  'prompts_use_case_invalid',
  'prompts_validation_failed',
  'prompts_variables_load_failed',
  'prompts_version_create_failed',
  'prompts_versions_load_failed',
] as const;
