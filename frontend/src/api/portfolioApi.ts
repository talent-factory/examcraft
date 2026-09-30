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
  PortfolioAssessmentListItem,
  PortfolioAssessmentListParams,
  PortfolioAssessmentSummary,
  PortfolioDocument,
  PortfolioGithubCredentialStatus,
  PortfolioPhaseOverridePayload,
  PortfolioPhaseReviewResponse,
  PortfolioTemplate,
  PortfolioTemplateCreatePayload,
  PortfolioTemplateUpdatePayload,
} from '../types/portfolio';

const ASSESSMENTS = '/api/v1/portfolio-assessments';
const TEMPLATES = '/api/v1/portfolio-templates';
const GITHUB_CREDENTIAL = '/api/v1/portfolio-github-credential';
const UPLOAD_TIMEOUT_MS = 10 * 60 * 1000;

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

  /** Filters and pagination are ignored by the backend until TF-986 lands. */
  listAssessments: (params?: PortfolioAssessmentListParams): Promise<PortfolioAssessmentListItem[]> =>
    call('portfolio_assessment_list_failed', () =>
      apiClient.get<PortfolioAssessmentListItem[]>(ASSESSMENTS, { params }),
    ),

  getAssessment: (id: string): Promise<PortfolioAssessmentDetail> =>
    call('portfolio_assessment_load_failed', () =>
      apiClient.get<PortfolioAssessmentDetail>(`${ASSESSMENTS}/${id}`),
    ),

  createAssessment: (payload: PortfolioAssessmentCreatePayload): Promise<PortfolioAssessmentSummary> =>
    call('portfolio_assessment_create_failed', () =>
      apiClient.post<PortfolioAssessmentSummary>(ASSESSMENTS, payload),
    ),

  // No deleteAssessment yet: `DELETE /{id}` arrives with TF-986; until then it
  // would only produce an indistinguishable 405. P3 (TF-989) adds it.

  /** Starts the ingestion job (202). The archive is sent as multipart field `file`. */
  uploadArchive: async (id: string, file: File): Promise<PortfolioAssessmentSummary> => {
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

  confirmClassification: (id: string): Promise<PortfolioAssessmentSummary> =>
    call('portfolio_assessment_confirm_classification_failed', () =>
      apiClient.post<PortfolioAssessmentSummary>(`${ASSESSMENTS}/${id}/confirm-classification`),
    ),

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
