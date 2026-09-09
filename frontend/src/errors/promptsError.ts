import { AppError, AppErrorCode } from './AppError';
import { appErrorFromAxios } from './appErrorFromAxios';

/**
 * `appErrorFromAxios`, plus the one case it cannot know about: a FastAPI 422
 * (TF-772 PR 4).
 *
 * `PromptEditor` used to unpack the Pydantic body into "field: message" pairs
 * so an unsaveable form could say *which* field it objects to. That unpacking
 * has to happen here — this is the last place the raw body exists — and the
 * result travels on as an `error_params` value that
 * `errors.prompts_validation_failed` interpolates.
 *
 * The `use_case` pattern mismatch keeps its own code and its own sentence,
 * because "use_case: string does not match regex" tells an author nothing. Its
 * text is the one `admin.promptEditor.useCaseRequired` already carried.
 *
 * Everything else is left to `appErrorFromAxios`, including the day the
 * `/api/v1/prompts` backend starts sending `error_code`.
 *
 * Shared between `core/frontend/src/api/promptsApi.ts` and
 * `premium/frontend/src/api/promptsApi.ts`: both hit the same
 * `/api/v1/prompts` endpoints, so a 422 shaped this way reaches either one.
 * Before this PR only the core file unpacked it — the premium file fell
 * straight through to `appErrorFromAxios`'s generic per-operation fallback,
 * silently losing the field-level detail on every premium caller
 * (`PromptPreview`, `PromptTemplateSelector`, `PromptUploadZone`).
 */
export function promptsError(err: unknown, code: AppErrorCode): AppError {
  const issues = validationIssues(err);
  if (!issues) return appErrorFromAxios(err, code);

  if (issues.some((issue) => issue.field === 'use_case' && /match pattern/.test(issue.msg))) {
    return new AppError('prompts_use_case_invalid', undefined, 422);
  }

  const joined = issues.map((i) => (i.field ? `${i.field}: ${i.msg}` : i.msg)).join(', ');
  return new AppError('prompts_validation_failed', joined, 422, { issues: joined });
}

interface ValidationIssue {
  field: string;
  msg: string;
}

/**
 * The field-level complaints of a 422, or null.
 *
 * Null for any other status and for a 422 whose `detail` is a plain string —
 * `prompts.py` raises those too (`HTTPException(422, detail=str(e))`), and they
 * carry no field information worth unpacking.
 */
function validationIssues(err: unknown): ValidationIssue[] | null {
  if (!err || typeof err !== 'object' || !('response' in err)) return null;

  const response = (err as {
    response?: { status?: unknown; data?: { detail?: unknown } };
  }).response;
  if (!response || response.status !== 422) return null;

  const detail = response.data?.detail;
  if (!Array.isArray(detail)) return null;

  const issues: ValidationIssue[] = [];
  for (const entry of detail) {
    if (!entry || typeof entry !== 'object' || !('msg' in entry)) continue;
    const { loc, msg, message } = entry as { loc?: unknown; msg?: unknown; message?: unknown };
    const text = String(msg ?? message ?? '');
    if (!text) continue;
    // loc is ['body', 'use_case', …]; the first element names the request part,
    // which is noise for an author staring at a form field.
    issues.push({ field: Array.isArray(loc) ? loc.slice(1).join('.') : '', msg: text });
  }

  return issues.length > 0 ? issues : null;
}
