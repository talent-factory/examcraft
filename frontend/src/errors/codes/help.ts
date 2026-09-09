/**
 * One flat code plus two backend-specific ones, next to eight legacy siblings
 * (TF-772 PR 4).
 *
 * `HelpService` has nine throw sites. Eight became `AppError('help.…')` in
 * TF-671 and live in `legacy.ts` as dot-notation camelCase;
 * `updateTrackStep` was added afterwards (TF-625) and kept
 * `throw new Error('Failed to update onboarding track step')` — the last
 * English literal in the file, and the reason the guard still listed it.
 *
 * It does NOT join its eight siblings: `legacy.ts` is frozen, and TF-775 owns
 * the question of whether that whole family migrates to flat snake_case. So
 * this code takes the current shape and sits alone in its own file. One flat
 * `help_*` code beside eight `help.*` ones looks inconsistent because it *is*
 * inconsistent — that inconsistency is TF-775's input, not something to hide by
 * writing a ninth legacy-style code.
 *
 * BACKEND COUNTERPART. All nine `HelpService` methods now route through
 * `appErrorFromResponse()`, so every one of them accepts a specific backend
 * code where `core/backend/api/v1/help.py` sends one. Two of the endpoints it
 * hits do: `PUT /help/onboarding/track/{track_id}/step` (`updateTrackStep`)
 * can answer `help_track_id_invalid` or `help_too_many_tracks`, and
 * `POST /help/message` (`sendMessage`) can answer `help_rate_limit_exceeded`.
 * The other six methods' endpoints (`/help/status`, `/onboarding/status`,
 * `/onboarding/step`, `/onboarding/skip`, `/context/{route}`,
 * `/context/dismiss`, `/feedback`) still raise no `error_code`, so their
 * legacy fallback in `legacy.ts` is what actually renders.
 *
 * `help.py` also backs six admin-only endpoints under `/help/admin/*`
 * (feedback moderation, reindexing, FAQ candidates, doc-gap clusters) with
 * five more real codes — `help_feedback_not_found`,
 * `help_reindex_full_mode_only`, `help_reindex_conflict`,
 * `help_reindex_unavailable`, `help_faq_candidate_not_found`,
 * `help_cluster_not_found`. Deliberately not registered here: `HelpService.ts`
 * has no methods for that surface, and `HelpFeedbackQueue.tsx` calls it
 * directly rather than through a service with `AppError`/`translateError`
 * wired in. Registering codes nothing constructs would be the same kind of
 * silent drift this file exists to avoid; migrating that admin surface is its
 * own follow-up.
 *
 * REACHABILITY. `useHelpContext.updateTrackStep` catches this, logs it and
 * hands it to Sentry — it never reaches a `t()` call today. The code is still
 * the right shape rather than a permanent English string: this is a user
 * action failing (a deep-dive's progress is not saved), not a programming
 * error like `apiClient`'s "No token refresh callback registered", and the day
 * it does get surfaced it should already have a sentence in four languages.
 */
export const HELP_ERROR_CODES = [
  'help_onboarding_track_step_failed',
  'help_rate_limit_exceeded',
  'help_too_many_tracks',
  'help_track_id_invalid',
] as const;
