/**
 * portfolioApi — every failure becomes an AppError (TF-987).
 */
import {
  PortfolioUnclassifiedDocumentsError,
  isPortfolioUnclassifiedDocumentsError,
  portfolioApi,
} from '../portfolioApi';
import { apiClient } from '../apiClient';
import { AppError } from '../../errors';

jest.mock('../apiClient', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  },
}));

const client = apiClient as jest.Mocked<typeof apiClient>;

beforeEach(() => {
  jest.resetAllMocks();
});

async function caught(promise: Promise<unknown>): Promise<AppError> {
  try {
    await promise;
  } catch (err) {
    expect(err).toBeInstanceOf(AppError);
    return err as AppError;
  }
  throw new Error('expected a rejection');
}

describe('portfolioApi', () => {
  it('liefert die Daten der Antwort', async () => {
    const page = { items: [{ id: 'a-1' }], total: 1, limit: 50, offset: 0 };
    client.get.mockResolvedValue({ data: page });
    await expect(portfolioApi.listAssessments({ status: 'grading' })).resolves.toEqual(page);
    expect(client.get).toHaveBeenCalledWith('/api/v1/portfolio-assessments', {
      params: { status: 'grading' },
    });
  });

  it('übernimmt einen registrierten Backend-Code samt Parametern', async () => {
    client.post.mockRejectedValue({
      response: {
        status: 413,
        data: {
          detail: 'zu gross',
          error_code: 'portfolio_assessment_archive_too_large',
          error_params: { max_mb: 50 },
        },
      },
    });
    const err = await caught(
      portfolioApi.uploadArchive('a-1', new File(['x'], 'p.zip', { type: 'application/zip' })),
    );
    expect(err.code).toBe('portfolio_assessment_archive_too_large');
    expect(err.status).toBe(413);
    expect(err.params).toEqual({ max_mb: 50 });
  });

  it('liefert beim Bestätigen die IDs der Dateien ohne Phase mit (TF-990)', async () => {
    client.post.mockRejectedValue({
      response: {
        status: 409,
        data: {
          detail: 'offen',
          error_code: 'portfolio_assessment_unclassified_documents',
          error_params: { unclassified_document_ids: [3, 'x', 5] },
        },
      },
    });
    const err = await caught(portfolioApi.confirmClassification('a-1'));
    expect(isPortfolioUnclassifiedDocumentsError(err)).toBe(true);
    expect((err as PortfolioUnclassifiedDocumentsError).documentIds).toEqual([3, 5]);
    expect(err.code).toBe('portfolio_assessment_unclassified_documents');
    expect(err.status).toBe(409);
  });

  it('gibt andere Bestätigungsfehler als gewöhnlichen AppError weiter', async () => {
    client.post.mockRejectedValue({
      response: {
        status: 409,
        data: { error_code: 'portfolio_assessment_classification_not_ready' },
      },
    });
    const err = await caught(portfolioApi.confirmClassification('a-1'));
    expect(isPortfolioUnclassifiedDocumentsError(err)).toBe(false);
    expect(err.code).toBe('portfolio_assessment_classification_not_ready');
  });

  it('fällt ohne Backend-Code auf den Code der Operation zurück', async () => {
    client.get.mockRejectedValue(new Error('Network Error'));
    const err = await caught(portfolioApi.getTemplate('t-1'));
    expect(err.code).toBe('portfolio_template_load_failed');
  });

  it('schickt das Archiv als Multipart-Feld «file» ohne 30-s-Timeout', async () => {
    client.post.mockResolvedValue({ data: { id: 'a-1' } });
    const file = new File(['x'], 'p.zip');
    await portfolioApi.uploadArchive('a-1', file);
    const [url, body, config] = client.post.mock.calls[0];
    expect(url).toBe('/api/v1/portfolio-assessments/a-1/upload');
    expect((body as FormData).get('file')).toBe(file);
    expect((config as { timeout: number }).timeout).toBeGreaterThan(30000);
  });

  it('meldet den Upload-Fortschritt als Anteil, auch ohne «total» vom Browser', async () => {
    client.post.mockResolvedValue({ data: { id: 'a-1' } });
    const file = new File(['0123456789'], 'p.zip');
    const onProgress = jest.fn();
    await portfolioApi.uploadArchive('a-1', file, onProgress);
    const config = client.post.mock.calls[0][2] as {
      onUploadProgress: (event: { loaded: number; total?: number }) => void;
    };
    config.onUploadProgress({ loaded: 25, total: 100 });
    config.onUploadProgress({ loaded: 5 });
    config.onUploadProgress({ loaded: 120, total: 100 });
    expect(onProgress.mock.calls).toEqual([[0.25], [0.5], [1]]);
  });

  it('liefert die Treffer der Studierenden-Suche als Liste', async () => {
    const hit = { id: 7, external_id: 'mia@x.ch', display_name: 'Mia', classes: [] };
    client.get.mockResolvedValue({ data: { items: [hit] } });
    await expect(portfolioApi.searchStudents('Mia')).resolves.toEqual([hit]);
    expect(client.get).toHaveBeenCalledWith('/api/v1/portfolio-assessments/students', {
      params: { search: 'Mia', limit: 20 },
    });
  });

  it('meldet einen Upload-Abbruch nach dem Timeout mit eigenem Code', async () => {
    client.post.mockRejectedValue(
      Object.assign(new Error('timeout of 600000ms exceeded'), {
        code: 'ECONNABORTED',
      }),
    );
    const err = await caught(portfolioApi.uploadArchive('a-1', new File(['x'], 'p.zip')));
    expect(err.code).toBe('portfolio_assessment_upload_timeout');
  });

  type Verb = 'get' | 'post' | 'put' | 'patch' | 'delete';
  const template = {
    name: 'T',
    description: null,
    visibility: 'private' as const,
    org_unit_id: null,
    is_active: true,
    phases: [
      {
        name: 'P',
        criteria: [{ name: 'K', max_points: 1, rubric_by_score: { '0': 'a', '1': 'b' } }],
      },
    ] as const,
  };
  const cases: Array<[string, () => Promise<unknown>, Verb, string, string]> = [
    [
      'listTemplates',
      () => portfolioApi.listTemplates(),
      'get',
      '/api/v1/portfolio-templates',
      'portfolio_template_list_failed',
    ],
    [
      'getTemplate',
      () => portfolioApi.getTemplate('t-1'),
      'get',
      '/api/v1/portfolio-templates/t-1',
      'portfolio_template_load_failed',
    ],
    [
      'createTemplate',
      () =>
        portfolioApi.createTemplate({
          name: 'T',
          phases: [...template.phases] as never,
        }),
      'post',
      '/api/v1/portfolio-templates',
      'portfolio_template_create_failed',
    ],
    [
      'updateTemplate',
      () =>
        portfolioApi.updateTemplate('t-1', {
          ...template,
          phases: [...template.phases] as never,
        }),
      'put',
      '/api/v1/portfolio-templates/t-1',
      'portfolio_template_update_failed',
    ],
    [
      'deleteTemplate',
      () => portfolioApi.deleteTemplate('t-1'),
      'delete',
      '/api/v1/portfolio-templates/t-1',
      'portfolio_template_delete_failed',
    ],
    [
      'listAssessments',
      () => portfolioApi.listAssessments(),
      'get',
      '/api/v1/portfolio-assessments',
      'portfolio_assessment_list_failed',
    ],
    [
      'getAssessment',
      () => portfolioApi.getAssessment('a-1'),
      'get',
      '/api/v1/portfolio-assessments/a-1',
      'portfolio_assessment_load_failed',
    ],
    [
      'createAssessment',
      () => portfolioApi.createAssessment({ template_id: 't-1', student_id: 7 }),
      'post',
      '/api/v1/portfolio-assessments',
      'portfolio_assessment_create_failed',
    ],
    [
      'startClassification',
      () => portfolioApi.startClassification('a-1'),
      'post',
      '/api/v1/portfolio-assessments/a-1/classify',
      'portfolio_assessment_classify_failed',
    ],
    [
      'updateDocumentPhase',
      () => portfolioApi.updateDocumentPhase('a-1', 5, 'p-1'),
      'patch',
      '/api/v1/portfolio-assessments/a-1/documents/5',
      'portfolio_assessment_document_update_failed',
    ],
    [
      'confirmClassification',
      () => portfolioApi.confirmClassification('a-1'),
      'post',
      '/api/v1/portfolio-assessments/a-1/confirm-classification',
      'portfolio_assessment_confirm_classification_failed',
    ],
    [
      'startGrading',
      () => portfolioApi.startGrading('a-1'),
      'post',
      '/api/v1/portfolio-assessments/a-1/grade',
      'portfolio_assessment_grade_failed',
    ],
    [
      'approvePhaseResult',
      () => portfolioApi.approvePhaseResult('a-1', 'pr-1'),
      'post',
      '/api/v1/portfolio-assessments/a-1/phase-results/pr-1/approve',
      'portfolio_assessment_review_failed',
    ],
    [
      'overridePhaseResult',
      () =>
        portfolioApi.overridePhaseResult('a-1', 'pr-1', {
          overrides: [{ criterion_id: 'c-1', score: 1 }],
        }),
      'post',
      '/api/v1/portfolio-assessments/a-1/phase-results/pr-1/override',
      'portfolio_assessment_review_failed',
    ],
    [
      'getGithubCredentialStatus',
      () => portfolioApi.getGithubCredentialStatus(),
      'get',
      '/api/v1/portfolio-github-credential',
      'portfolio_assessment_github_credential_load_failed',
    ],
    [
      'setGithubCredential',
      () => portfolioApi.setGithubCredential('ghp_x'),
      'put',
      '/api/v1/portfolio-github-credential',
      'portfolio_assessment_github_credential_save_failed',
    ],
    [
      'searchStudents',
      () => portfolioApi.searchStudents('Mia'),
      'get',
      '/api/v1/portfolio-assessments/students',
      'portfolio_assessment_student_search_failed',
    ],
    [
      'deleteAssessment',
      () => portfolioApi.deleteAssessment('a-1'),
      'delete',
      '/api/v1/portfolio-assessments/a-1',
      'portfolio_assessment_delete_failed',
    ],
    [
      'startRepositoryIngestion',
      () => portfolioApi.startRepositoryIngestion('a-1'),
      'post',
      '/api/v1/portfolio-assessments/a-1/ingest',
      'portfolio_assessment_ingest_failed',
    ],
  ];

  it.each(cases)('%s: Verb, URL und Fallback-Code', async (_name, invoke, verb, url, fallback) => {
    client[verb].mockResolvedValue({ data: {} });
    await invoke();
    expect(client[verb].mock.calls[0][0]).toBe(url);

    client[verb].mockReset().mockRejectedValue(new Error('Network Error'));
    const err = await caught(invoke());
    expect(err.code).toBe(fallback);
  });

  it('deckt jede Methode von portfolioApi ab', () => {
    const covered = new Set([...cases.map(([name]) => name), 'uploadArchive']);
    expect(Object.keys(portfolioApi).filter((name) => !covered.has(name))).toEqual([]);
  });
});
