/**
 * The 22 error codes TF-671 introduced, before ADR 0005 fixed the backend
 * format.
 *
 * They are dot-notation camelCase (`rag.examGenerationFailed`), invented by the
 * frontend, and have no backend counterpart — the opposite of the identity rule
 * every code added since follows (`errors.` + the backend's `error_code`, flat
 * snake_case). Their translations live under nested `errors.rag.*`,
 * `errors.help.*` … blocks in the four locale files.
 *
 * FROZEN. Do not add to this list, and do not migrate it here: whether these
 * become `rag_generation_failed` and friends is TF-775's call, and it needs the
 * flat codes from TF-772 in place before it can decide. Splitting them out of
 * `AppError.ts` is not that migration — it just keeps them from sitting in the
 * middle of the file that three branches are appending to.
 */
export const LEGACY_ERROR_CODES = [
  'rag.examGenerationFailed',
  'rag.connectionLost',
  'rag.statusFailed',
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
