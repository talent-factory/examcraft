/**
 * Portfolio-Assessment API client (TF-987, P1 of TF-953).
 *
 * Like `competencyFrameworksApi`, the backend is premium
 * (`premium/backend/api/v1/portfolio_*.py`) and the UI lives in core. Unlike
 * it, this client goes through the shared `apiClient` (token refresh) and
 * converts every failure into an `AppError` with one fallback code per
 * operation, so callers only ever `translateError(err, t, …)`.
 *
 * Nothing here checks the deployment mode: the pages are wrapped in
 * `PortfolioGate`, which never renders its children in a core deployment, so
 * no request is ever issued there.
 */
import { apiClient } from './apiClient';
import { AppError, AppErrorCode, appErrorFromAxios } from '../errors';
import type {
  PortfolioAssessmentCreatePayload,
  PortfolioAssessmentDetail,
  PortfolioAssessmentListPage,
  PortfolioAssessmentListParams,
  PortfolioAssessmentSummary,
  PortfolioDocument,
  PortfolioGithubCredentialStatus,
  PortfolioPhaseOverridePayload,
  PortfolioPhaseReviewResponse,
  PortfolioStudentOption,
  PortfolioTemplate,
  PortfolioTemplateCreatePayload,
  PortfolioTemplateUpdatePayload,
} from '../types/portfolio';

const ASSESSMENTS = '/api/v1/portfolio-assessments';
const TEMPLATES = '/api/v1/portfolio-templates';
const GITHUB_CREDENTIAL = '/api/v1/portfolio-github-credential';
const UPLOAD_TIMEOUT_MS = 10 * 60 * 1000;

/** Share of the archive sent so far, 0–1. */
export type PortfolioUploadProgressHandler = (fraction: number) => void;

/**
 * 409 `portfolio_assessment_unclassified_documents` of `confirm-classification`
 * with the ids the backend listed. They travel as a list in `error_params`,
 * which `readParams` drops (it keeps scalars only), so the API reads them here.
 *
 * Callers test with `isPortfolioUnclassifiedDocumentsError`, which checks
 * `name` rather than `instanceof` (see `DocumentFetchError`): a test that
 * mocks this module would otherwise hand the component another class.
 */
export class PortfolioUnclassifiedDocumentsError extends AppError {
  constructor(
    source: AppError,
    readonly documentIds: number[],
  ) {
    super(source.code, source.detail, source.status, source.params);
    this.name = 'PortfolioUnclassifiedDocumentsError';
  }
}

export function isPortfolioUnclassifiedDocumentsError(
  err: unknown,
): err is PortfolioUnclassifiedDocumentsError {
  return (
    err instanceof AppError &&
    err.name === 'PortfolioUnclassifiedDocumentsError' &&
    Array.isArray((err as Partial<PortfolioUnclassifiedDocumentsError>).documentIds)
  );
}

function unclassifiedDocumentIdsOf(err: unknown): number[] {
  const ids = (err as { response?: { data?: { error_params?: { unclassified_document_ids?: unknown } } } })
    ?.response?.data?.error_params?.unclassified_document_ids;
  return Array.isArray(ids) ? ids.filter((id): id is number => typeof id === 'number') : [];
}

async function call<T>(fallbackCode: AppErrorCode, request: () => Promise<{ data: T }>): Promise<T> {
  try {
    const response = await request();
    return response.data;
  } catch (err) {
    throw appErrorFromAxios(err, fallbackCode);
  }
}

export const portfolioApi = {
  // -------------------------------------------------------------------------
  // Templates
  // -------------------------------------------------------------------------

  listTemplates: (): Promise<PortfolioTemplate[]> =>
    call('portfolio_template_list_failed', () => apiClient.get<PortfolioTemplate[]>(TEMPLATES)),

  getTemplate: (id: string): Promise<PortfolioTemplate> =>
    call('portfolio_template_load_failed', () =>
      apiClient.get<PortfolioTemplate>(`${TEMPLATES}/${id}`),
    ),

  createTemplate: (payload: PortfolioTemplateCreatePayload): Promise<PortfolioTemplate> =>
    call('portfolio_template_create_failed', () =>
      apiClient.post<PortfolioTemplate>(TEMPLATES, payload),
    ),

  updateTemplate: (id: string, payload: PortfolioTemplateUpdatePayload): Promise<PortfolioTemplate> =>
    call('portfolio_template_update_failed', () =>
      apiClient.put<PortfolioTemplate>(`${TEMPLATES}/${id}`, payload),
    ),

  deleteTemplate: (id: string): Promise<{ id: string }> =>
    call('portfolio_template_delete_failed', () =>
      apiClient.delete<{ id: string }>(`${TEMPLATES}/${id}`),
    ),

  // -------------------------------------------------------------------------
  // Assessments
  // -------------------------------------------------------------------------

  listAssessments: (params?: PortfolioAssessmentListParams): Promise<PortfolioAssessmentListPage> =>
    call('portfolio_assessment_list_failed', () =>
      apiClient.get<PortfolioAssessmentListPage>(ASSESSMENTS, { params }),
    ),

  /** Slim lookup under `portfolio_assessments:manage`, unlike `/api/v1/students`. */
  searchStudents: (search: string, limit = 20): Promise<PortfolioStudentOption[]> =>
    call('portfolio_assessment_student_search_failed', () =>
      apiClient.get<{ items: PortfolioStudentOption[] }>(`${ASSESSMENTS}/students`, {
        params: { search, limit },
      }),
    ).then((body) => body.items),

  getAssessment: (id: string): Promise<PortfolioAssessmentDetail> =>
    call('portfolio_assessment_load_failed', () =>
      apiClient.get<PortfolioAssessmentDetail>(`${ASSESSMENTS}/${id}`),
    ),

  createAssessment: (payload: PortfolioAssessmentCreatePayload): Promise<PortfolioAssessmentSummary> =>
    call('portfolio_assessment_create_failed', () =>
      apiClient.post<PortfolioAssessmentSummary>(ASSESSMENTS, payload),
    ),

  /** Removes documents and jobs too; 409 while a job is queued or running. */
  deleteAssessment: (id: string): Promise<{ id: string }> =>
    call('portfolio_assessment_delete_failed', () =>
      apiClient.delete<{ id: string }>(`${ASSESSMENTS}/${id}`),
    ),

  /**
   * Starts the ingestion job (202). The archive is sent as multipart field
   * `file`. With a repository URL on the assessment the job fetches the
   * repository as well.
   */
  uploadArchive: async (
    id: string,
    file: File,
    onProgress?: PortfolioUploadProgressHandler,
  ): Promise<PortfolioAssessmentSummary> => {
    const form = new FormData();
    form.append('file', file);
    try {
      const response = await apiClient.post<PortfolioAssessmentSummary>(
        `${ASSESSMENTS}/${id}/upload`,
        form,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          // The shared client's 30 s would abort a large archive mid-upload.
          timeout: UPLOAD_TIMEOUT_MS,
          onUploadProgress: onProgress
            ? (event) => {
                // `total` is missing when the browser cannot compute it.
                const total = event.total ?? file.size;
                if (total > 0) onProgress(Math.min(1, event.loaded / total));
              }
            : undefined,
        },
      );
      return response.data;
    } catch (err) {
      // axios aborts with ECONNABORTED and no response; without its own code
      // a slow connection would read like any other upload failure.
      if ((err as { code?: unknown } | null)?.code === 'ECONNABORTED') {
        throw new AppError(
          'portfolio_assessment_upload_timeout',
          err instanceof Error ? err.message : undefined,
        );
      }
      throw appErrorFromAxios(err, 'portfolio_assessment_upload_failed');
    }
  },

  /** Ingestion from the assessment's GitHub repository alone, without an archive (202). */
  startRepositoryIngestion: (id: string): Promise<PortfolioAssessmentSummary> =>
    call('portfolio_assessment_ingest_failed', () =>
      apiClient.post<PortfolioAssessmentSummary>(`${ASSESSMENTS}/${id}/ingest`),
    ),

  startClassification: (id: string): Promise<PortfolioAssessmentSummary> =>
    call('portfolio_assessment_classify_failed', () =>
      apiClient.post<PortfolioAssessmentSummary>(`${ASSESSMENTS}/${id}/classify`),
    ),

  updateDocumentPhase: (id: string, documentId: number, phaseId: string): Promise<PortfolioDocument> =>
    call('portfolio_assessment_document_update_failed', () =>
      apiClient.patch<PortfolioDocument>(`${ASSESSMENTS}/${id}/documents/${documentId}`, {
        phase_id: phaseId,
      }),
    ),

  /** 409 with files still without a phase throws `PortfolioUnclassifiedDocumentsError`. */
  confirmClassification: async (id: string): Promise<PortfolioAssessmentSummary> => {
    try {
      const response = await apiClient.post<PortfolioAssessmentSummary>(
        `${ASSESSMENTS}/${id}/confirm-classification`,
      );
      return response.data;
    } catch (err) {
      const appError = appErrorFromAxios(err, 'portfolio_assessment_confirm_classification_failed');
      if (appError.code === 'portfolio_assessment_unclassified_documents') {
        throw new PortfolioUnclassifiedDocumentsError(appError, unclassifiedDocumentIdsOf(err));
      }
      throw appError;
    }
  },

  /** First start (`ready_to_grade`) and resume after a failed phase (`grading`). */
  startGrading: (id: string): Promise<PortfolioAssessmentSummary> =>
    call('portfolio_assessment_grade_failed', () =>
      apiClient.post<PortfolioAssessmentSummary>(`${ASSESSMENTS}/${id}/grade`),
    ),

  approvePhaseResult: (id: string, phaseResultId: string): Promise<PortfolioPhaseReviewResponse> =>
    call('portfolio_assessment_review_failed', () =>
      apiClient.post<PortfolioPhaseReviewResponse>(
        `${ASSESSMENTS}/${id}/phase-results/${phaseResultId}/approve`,
      ),
    ),

  overridePhaseResult: (
    id: string,
    phaseResultId: string,
    payload: PortfolioPhaseOverridePayload,
  ): Promise<PortfolioPhaseReviewResponse> =>
    call('portfolio_assessment_review_failed', () =>
      apiClient.post<PortfolioPhaseReviewResponse>(
        `${ASSESSMENTS}/${id}/phase-results/${phaseResultId}/override`,
        payload,
      ),
    ),

  // -------------------------------------------------------------------------
  // GitHub credential (own token only; the plaintext never comes back)
  // -------------------------------------------------------------------------

  getGithubCredentialStatus: (): Promise<PortfolioGithubCredentialStatus> =>
    call('portfolio_assessment_github_credential_load_failed', () =>
      apiClient.get<PortfolioGithubCredentialStatus>(GITHUB_CREDENTIAL),
    ),

  setGithubCredential: (token: string): Promise<void> =>
    call('portfolio_assessment_github_credential_save_failed', () =>
      apiClient.put<void>(GITHUB_CREDENTIAL, { token }),
    ),
};
