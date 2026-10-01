/**
 * Error codes of `HelpService` — one fallback per method, plus the backend
 * codes `core/backend/api/v1/help.py` sends.
 *
 * Eight of the fallbacks were TF-671 dot-notation codes (`help.statusFailed`
 * …) until TF-996 moved them here in the flat form every other file uses;
 * `help_onboarding_track_step_failed` was added flat in TF-772 PR 4.
 *
 * BACKEND COUNTERPART. All nine `HelpService` methods route through
 * `appErrorFromResponse()`, so every one of them accepts a specific backend
 * code where `help.py` sends one. Two of the endpoints it hits do:
 * `PUT /help/onboarding/track/{track_id}/step` (`updateTrackStep`) can answer
 * `help_track_id_invalid` or `help_too_many_tracks`, and `POST /help/message`
 * (`sendMessage`) can answer `help_rate_limit_exceeded`. The other seven
 * endpoints raise no `error_code`, so their fallback is what a consumer gets.
 *
 * `help.py` also backs six admin-only endpoints under `/help/admin/*`
 * (feedback moderation, reindexing, FAQ candidates, doc-gap clusters) with
 * seven more real codes — `help_superadmin_required`, `help_feedback_not_found`,
 * `help_reindex_full_mode_only`, `help_reindex_conflict`,
 * `help_reindex_unavailable`, `help_faq_candidate_not_found`,
 * `help_cluster_not_found`. Deliberately not registered here: `HelpService.ts`
 * has no methods for that surface, and `HelpFeedbackQueue.tsx` calls it
 * directly rather than through a service with `AppError`/`translateError`
 * wired in. Registering codes nothing constructs would be the same kind of
 * silent drift this file exists to avoid; migrating that admin surface is its
 * own follow-up.
 *
 * SHOWN OR SILENT (TF-996). Every code below is thrown, so every one needs
 * its four-locale text whether or not a consumer renders it. Three are shown:
 *
 *   help_hint_dismiss_failed  `HelpContextHint` — «Nicht mehr anzeigen» failed,
 *                             the hint stays; without a message the click
 *                             looked ignored
 *   help_feedback_failed      `HelpFeedback` — the rating was lost while the
 *                             widget already said thanks
 *   help_rate_limit_exceeded  `HelpChat` on a 429 — the backend sentence
 *                             names the cap and the window, which the generic
 *                             `help.rateLimited` does not. The IP limiter's
 *                             429 carries no code and keeps the generic one
 *
 * The other nine are silent ON PURPOSE — the user either sees something
 * better or has nothing to do. Where each failure goes instead is named per
 * code: six reach client error reporting (`reportHandledError`, Specula),
 * three only the browser console. Silent codes outside this file:
 * `compliance_load_failed` (`compliance.ts`) and `features_load_failed`
 * (`features.ts`).
 *
 *   help_status_failed             `useHelpContext` falls back to onboarding
 *                                  and context on, chat off — a safe
 *                                  degradation, though in full mode the chat
 *                                  stays hidden until the next mount. Console
 *                                  only
 *   help_onboarding_status_failed  `useHelpContext`: the tour is not offered;
 *                                  reported, because a read that keeps
 *                                  failing would otherwise withhold the tour
 *                                  from every new user unnoticed. The next
 *                                  full reload asks again
 *   help_context_hint_failed       `useHelpContext`: no hint; failures are
 *                                  not cached, the next navigation retries.
 *                                  Console only
 *   help_onboarding_step_failed,   `useHelpContext` writers never reject, so
 *   help_onboarding_skip_failed,   the tour cannot get stuck; they are
 *   help_onboarding_track_step_failed,  reported, and a later successful
 *   help_track_id_invalid          write catches the progress up (after a
 *                                  failed last step nothing does — the
 *                                  report is the trace). `help_track_id_invalid`
 *                                  is a frontend bug (track ids come from
 *                                  `public/help-onboarding-steps.json`), not
 *                                  something the user could fix
 *   help_too_many_tracks           Same writer. Unreachable through the UI:
 *                                  the backend allows 20 tracks per user
 *                                  (`MAX_TRACKS_PER_USER`), the steps file
 *                                  defines six distinct track ids across both
 *                                  roles. It would take a frontend bug to hit
 *                                  it, so error reporting is the right
 *                                  audience
 *   help_message_failed            `HelpChat` maps the HTTP status to its own
 *                                  sentences (429 `help.rateLimited`, 401/403
 *                                  `help.sessionExpired`, else
 *                                  `help.chatUnavailable`), which say more
 *                                  than the operation fallback would.
 *                                  Console only
 */
export const HELP_ERROR_CODES = [
  'help_context_hint_failed',
  'help_feedback_failed',
  'help_hint_dismiss_failed',
  'help_message_failed',
  'help_onboarding_skip_failed',
  'help_onboarding_status_failed',
  'help_onboarding_step_failed',
  'help_onboarding_track_step_failed',
  'help_rate_limit_exceeded',
  'help_status_failed',
  'help_too_many_tracks',
  'help_track_id_invalid',
] as const;
