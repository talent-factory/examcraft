import { AppError, Translate, isAppErrorCode, translateError } from '../../errors';
import { readParams } from '../../errors/errorBody';
import type { ImportRowError } from '../../types/submission';

/**
 * User-facing sentence for one import `error_log`/preview row (TF-971).
 *
 * A registered code renders `errors.<code>` through `translateError`, so the
 * row follows the UI language even when the job was polled in another one.
 * An unregistered code (a backend newer than this build) falls back to
 * `reason`: for a coded row the backend already wrote the translation of that
 * code there, never the raw exception. A row without a code is a driver row
 * error, a fixed sentence by construction.
 */
export function importRowErrorMessage(row: ImportRowError, t: Translate): string {
  if (isAppErrorCode(row.error_code)) {
    const err = new AppError(row.error_code, row.reason, undefined, readParams(row.error_params));
    return translateError(err, t, 'errors.submissions_import_internal_error');
  }
  if (row.error_code != null) {
    // Same breadcrumb errorBody.selectCode leaves for an unknown error_code.
    console.warn('[i18n] Unknown import row error_code, using reason:', row.error_code);
  }
  return row.reason;
}
