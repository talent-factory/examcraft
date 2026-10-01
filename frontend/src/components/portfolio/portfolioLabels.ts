import type { TFunction } from 'i18next';

/**
 * Label for a status-like value from the backend under `pages.portfolio.<group>`.
 *
 * A value this frontend does not know (newer backend) would otherwise render
 * as the raw i18n key; it shows «Unbekannt (value)» instead and is logged.
 */
export function portfolioLabel(
  t: TFunction,
  group: 'status' | 'reviewStatus' | 'job.status' | 'job.type' | 'phaseStatus' | 'phaseReviewStatus',
  value: string,
  known: readonly string[],
): string {
  if (known.includes(value)) {
    return t(`pages.portfolio.${group}.${value}`);
  }
  console.warn(`[portfolio] Unknown ${group} value:`, value);
  return t('pages.portfolio.unknownValue', { value });
}

export const ASSESSMENT_STATUSES = [
  'uploading',
  'classifying',
  'ready_to_grade',
  'grading',
  'completed',
  'failed',
] as const;

export const REVIEW_STATUSES = ['pending_review', 'partially_reviewed', 'fully_reviewed'] as const;

export const JOB_STATUSES = ['queued', 'running', 'completed', 'failed'] as const;

export const JOB_TYPES = ['ingest', 'classify', 'grade'] as const;

export const PHASE_STATUSES = ['pending', 'running', 'completed', 'failed'] as const;

export const PHASE_REVIEW_STATUSES = ['proposed', 'approved', 'manual_override'] as const;
