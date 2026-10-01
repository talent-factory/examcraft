/**
 * The error codes TF-671 introduced (22, now 20), before ADR 0005 fixed the backend
 * format.
 *
 * They are dot-notation camelCase (`rag.examGenerationFailed`), invented by the
 * frontend, and have no backend counterpart — the opposite of the identity rule
 * every code added since follows (`errors.` + the backend's `error_code`, flat
 * snake_case). Their translations live under nested `errors.rag.*`,
 * `errors.help.*` … blocks in the four locale files.
 *
 * FROZEN. Do not add to this list, and do not migrate it here: whether these
 * become `rag_generation_failed` and friends is TF-996's call (TF-775 Teil B
 * only pruned the two nothing threw, see below). Splitting them out of
 * `AppError.ts` is not that migration — it just keeps them from sitting in the
 * middle of the file that three branches are appending to.
 *
 * TF-775 Teil B removed two that nothing threw any more: `rag.connectionLost`
 * (its WebSocket thrower went with `generateRAGExam` in TF-772 PR 5) and
 * `rag.statusFailed` (its last fallback was replaced in TF-773 Teil D). The
 * remaining 20 are all thrown. Nine of them — the eight `help.*` and
 * `compliance.loadFailed` — never reach `translateError`: their consumers log
 * and show a generic state instead. Deciding per code whether to show it or
 * keep it silent on purpose, and the snake_case migration, is TF-996.
 */
export const LEGACY_ERROR_CODES = [
  'rag.examGenerationFailed',
  'rag.retryFailed',
  'rag.activeTasksFailed',
  'rag.taskResultFailed',
  'rag.contextRetrievalFailed',
  'rag.questionTypesFailed',
  'rag.healthCheckFailed',
  'rag.contextPreviewFailed',
  'rag.notAvailableInCore',
  'help.statusFailed',
  'help.onboardingStatusFailed',
  'help.onboardingStepFailed',
  'help.onboardingSkipFailed',
  'help.contextHintFailed',
  'help.hintDismissFailed',
  'help.messageFailed',
  'help.feedbackFailed',
  'features.loadFailed',
  'chat.downloadFailed',
  'compliance.loadFailed',
] as const;
