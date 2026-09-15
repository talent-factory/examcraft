/**
 * The `visibility_*` codes (TF-772 PR 7).
 *
 * Raised by the visibility helpers in `core/backend/api/exams.py` (create and
 * update of an exam), and under the same names by `question_review.py` and
 * `competency_frameworks.py`. They get their own file because the prefix is
 * not any one router's; registering them once makes them resolvable from
 * every caller, since the registry is flat. Texts verbatim from
 * `core/backend/locales/t.*.json`.
 *
 * Reached today through `ExamListView` (create), `ExamMetadataBar` (save) and
 * `CompetencyFrameworkSettingsPage` (create/update), which alone also reaches
 * `visibility_institution_required`.
 */
export const VISIBILITY_ERROR_CODES = [
  'visibility_institution_required',
  'visibility_org_unit_required',
  'visibility_own_org_unit_required',
  'visibility_owner_or_superuser_only',
] as const;
