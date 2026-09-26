/**
 * Error codes reachable through the two tag-management surfaces,
 * `TagCreateForm` and `TagSettingsPage` (TF-773 Teil D).
 *
 * BACKEND CODES, copied verbatim from `core/backend/locales/t.*.json`, raised
 * by `core/backend/api/tags.py`. Until Teil D these two components rendered
 * the raw `detail` through `apiDetail()` — correct in German only because the
 * backend already answered in the user's language. Registering the codes
 * replaces that special case with the ordinary path, so the sentence now
 * follows the UI language like every other error.
 *
 * Only the content-tag codes are here. `tags.py` also raises
 *
 *   tags_prompt_create_permission_required, tags_prompt_delete_not_allowed,
 *   tags_prompt_merge_not_allowed
 *
 * but only for `kind='prompt'` tags. Both components work on content tags
 * alone — `listTags()` and `createTag()` are called without `kind`, and the
 * backend defaults it to `content` — so none of the three can reach them.
 * `PromptEditor` creates prompt tags, but renders every failure of its save
 * with its own `admin.promptEditor.failedSave` and never converts the axios
 * error, so a registration would change nothing there either.
 *
 * `TagAutocomplete` hits the same endpoints and deliberately keeps its one
 * generic inline message; it does not go through these codes.
 *
 * FRONTEND-ONLY FALLBACKS, one per operation a component renders a failure
 * for; texts copied from the components' `components.tags.*` keys:
 *
 *   tags_archive_failed, tags_create_failed, tags_delete_failed,
 *   tags_merge_failed, tags_rename_failed, tags_restore_failed
 */
export const TAGS_ERROR_CODES = [
  'tags_access_denied',
  'tags_archive_failed',
  'tags_create_failed',
  'tags_create_questions_permission_required',
  'tags_delete_archived_only',
  'tags_delete_failed',
  'tags_global_create_superuser_only',
  'tags_global_edit_superuser_only',
  'tags_merge_failed',
  'tags_merge_target_in_sources',
  'tags_name_exists',
  'tags_name_exists_on_rename',
  'tags_not_found',
  'tags_rename_failed',
  'tags_restore_failed',
  'tags_still_in_use',
] as const;
