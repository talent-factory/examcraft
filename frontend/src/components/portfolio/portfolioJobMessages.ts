import type { Translate } from '../../errors';
import {
  PORTFOLIO_JOB_CODES,
  type PortfolioJobCode,
  type PortfolioJobLogEntry,
} from '../../types/portfolio';

// The code list is part of the wire contract and lives in types/portfolio.ts;
// re-exported so callers of this module need only one import.
export { PORTFOLIO_JOB_CODES };
export type { PortfolioJobCode };

const JOB_CODE_SET: ReadonlySet<string> = new Set<string>(PORTFOLIO_JOB_CODES);

export function isPortfolioJobCode(value: unknown): value is PortfolioJobCode {
  return typeof value === 'string' && JOB_CODE_SET.has(value);
}

/**
 * Files an entry is about (`paths` of the grading warnings, `skipped_files` of
 * an exhausted ingestion). The panel lists them under the sentence, which is
 * generic by design (the same text serves every phase and file set).
 */
export function portfolioJobEntryFiles(entry: PortfolioJobLogEntry): string[] {
  if (!entry || typeof entry !== 'object') return [];
  const files = Array.isArray(entry.paths) ? entry.paths : entry.skipped_files;
  return Array.isArray(files) ? files.filter((f): f is string => typeof f === 'string') : [];
}

/**
 * User-facing sentence for one `error_log`/`warnings` entry.
 *
 * A known code renders its translation and nothing else — `reason` is German
 * log text and would leak into the other three languages. An unknown code (a
 * backend newer than this frontend) renders a generic sentence plus `reason`,
 * because showing *something* the teacher can pass on beats hiding it.
 */
export function describePortfolioJobEntry(entry: PortfolioJobLogEntry, t: Translate): string {
  // `error_log` is unchecked JSON off the wire; a non-object must not crash
  // the detail page.
  if (!entry || typeof entry !== 'object') {
    console.warn('[portfolio] Malformed job log entry:', entry);
    return t('pages.portfolio.job.unknownEntry');
  }
  if (isPortfolioJobCode(entry.code)) {
    return t(`pages.portfolio.jobCodes.${entry.code}`);
  }
  // Same breadcrumb errorBody.selectCode leaves for an unknown error_code: a
  // code the backend added without a frontend translation.
  console.warn('[portfolio] Unknown job code, using fallback:', entry.code, entry);
  if (typeof entry.reason === 'string' && entry.reason.length > 0) {
    return t('pages.portfolio.job.unknownEntryWithReason', { reason: entry.reason });
  }
  return t('pages.portfolio.job.unknownEntry');
}
