/**
 * Upload step of the detail page (TF-989): ZIP with progress and size check,
 * GitHub-only ingestion, inline token, retry after `failed`, error codes.
 */
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PortfolioAssessmentDetailPage from '../../../pages/portfolio/PortfolioAssessmentDetailPage';
import { portfolioApi } from '../../../api/portfolioApi';
import { AppError } from '../../../errors';
import type {
  PortfolioAssessmentDetail,
  PortfolioAssessmentJob,
  PortfolioAssessmentStatus,
} from '../../../types/portfolio';

jest.mock('../../../hooks/useFeatures', () => ({
  useFeatures: () => ({ tier: 'professional', isLoading: false }),
}));

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1 },
    hasPermission: (p: string) => p === 'portfolio_assessments:manage',
  }),
}));

jest.mock('../../../api/portfolioApi', () => ({
  portfolioApi: {
    getAssessment: jest.fn(),
    uploadArchive: jest.fn(),
    startRepositoryIngestion: jest.fn(),
    getGithubCredentialStatus: jest.fn(),
    setGithubCredential: jest.fn(),
  },
}));

const api = portfolioApi as jest.Mocked<typeof portfolioApi>;

function job(overrides: Partial<PortfolioAssessmentJob> = {}): PortfolioAssessmentJob {
  return {
    id: 'job-1',
    job_type: 'ingest',
    status: 'queued',
    files_total: null,
    files_done: 0,
    error_log: null,
    created_at: new Date().toISOString(),
    started_at: null,
    finished_at: null,
    ...overrides,
  };
}

function assessment(
  status: PortfolioAssessmentStatus,
  overrides: Partial<PortfolioAssessmentDetail> = {},
): PortfolioAssessmentDetail {
  return {
    id: 'a-1',
    template_id: 't-1',
    template_version: 1,
    student_id: 7,
    created_by: 1,
    status,
    framework_conditions: null,
    source_repository_url: null,
    source_repository_ref: null,
    grading_scheme_id: null,
    review_status: 'pending_review',
    overall_points_awarded: null,
    overall_points_max: null,
    overall_percentage: null,
    created_at: null,
    updated_at: null,
    job: null,
    documents: [],
    phase_results: [],
    overall_grade: null,
    ...overrides,
  };
}

function zip(name = 'portfolio.zip', size?: number): File {
  const file = new File(['PK'], name, { type: 'application/zip' });
  if (size !== undefined) Object.defineProperty(file, 'size', { value: size });
  return file;
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/portfolio/a-1']}>
        <Routes>
          <Route path="/portfolio/:id" element={<PortfolioAssessmentDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** The start buttons wait for the token status; clicking earlier is a no-op. */
async function clickWhenEnabled(testId: string) {
  await waitFor(() => expect(screen.getByTestId(testId)).toBeEnabled());
  fireEvent.click(screen.getByTestId(testId));
}

function chooseFile(file: File) {
  fireEvent.change(screen.getByTestId('portfolio-ingestion-file-input'), {
    target: { files: [file] },
  });
}

beforeEach(() => {
  jest.resetAllMocks();
  api.getGithubCredentialStatus.mockResolvedValue({ configured: true });
});

describe('PortfolioIngestionPanel', () => {
  it('führt vom Upload mit Fortschritt ohne Reload bis zur Klassifikation', async () => {
    api.getAssessment.mockResolvedValueOnce(assessment('uploading'));
    let finishUpload: (value: PortfolioAssessmentDetail) => void = () => undefined;
    api.uploadArchive.mockImplementation((_id, _file, onProgress) => {
      onProgress?.(0.4);
      return new Promise((resolve) => {
        finishUpload = resolve;
      });
    });
    renderPage();

    await screen.findByTestId('portfolio-ingestion-panel');
    chooseFile(zip());
    expect(screen.getByTestId('portfolio-ingestion-file-name')).toHaveTextContent('portfolio.zip');
    fireEvent.click(screen.getByTestId('portfolio-ingestion-upload'));

    expect(await screen.findByText('Wird hochgeladen … 40 %')).toBeInTheDocument();
    expect(api.uploadArchive).toHaveBeenCalledWith('a-1', expect.any(File), expect.any(Function));

    // Worker done by the next poll: the assessment moved on to classification.
    api.getAssessment.mockResolvedValue(
      assessment('classifying', { job: job({ status: 'completed', files_total: 3, files_done: 3 }) }),
    );
    finishUpload(assessment('uploading', { job: job() }));

    expect(
      await screen.findByTestId('portfolio-detail-section-classification'),
    ).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-ingestion-panel')).not.toBeInTheDocument();
  });

  it('zeigt während eines laufenden Imports den Fortschritt statt des Panels', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('uploading', {
        job: job({ status: 'running', files_total: 10, files_done: 4, started_at: new Date().toISOString() }),
      }),
    );
    renderPage();
    expect(await screen.findByText('4 von 10 Dateien')).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-ingestion-panel')).not.toBeInTheDocument();
    expect(screen.getByText(/Das Portfolio wird importiert/)).toBeInTheDocument();
  });

  it('lehnt ein Archiv über 500 MB vor dem Upload ab', async () => {
    api.getAssessment.mockResolvedValue(assessment('uploading'));
    renderPage();
    await screen.findByTestId('portfolio-ingestion-panel');

    chooseFile(zip('gross.zip', 501 * 1024 * 1024));
    expect(
      screen.getByText('Das hochgeladene Archiv ist zu gross (maximal 500 MB).'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-ingestion-upload')).toBeDisabled();
    expect(api.uploadArchive).not.toHaveBeenCalled();
  });

  it('zeigt nach einem Fehlschlag die übersetzte Ursache und erlaubt einen neuen Upload', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('failed', {
        job: job({
          status: 'failed',
          error_log: [{ code: 'portfolio_ingestion_no_files', reason: 'Keine Dateien' }],
        }),
      }),
    );
    api.uploadArchive.mockResolvedValue(assessment('uploading', { job: job({ id: 'job-2' }) }));
    renderPage();

    expect(
      await screen.findByText(
        'Im Archiv bzw. Repository wurden keine verarbeitbaren Dateien gefunden.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Der letzte Import ist fehlgeschlagen/)).toBeInTheDocument();

    chooseFile(zip());
    fireEvent.click(screen.getByTestId('portfolio-ingestion-upload'));
    await waitFor(() => expect(api.uploadArchive).toHaveBeenCalledTimes(1));
  });

  it.each<[string, AppError, string]>([
    [
      '413',
      new AppError('portfolio_assessment_archive_too_large', 'x', 413, { max_mb: 500 }),
      'Das hochgeladene Archiv ist zu gross (maximal 500 MB).',
    ],
    [
      '409',
      new AppError('portfolio_assessment_upload_already_in_progress', 'x', 409),
      'Für diese Portfolio-Bewertung läuft bereits eine Verarbeitung oder sie wurde bereits abgeschlossen. Ein erneuter Upload ist nur nach einem fehlgeschlagenen Versuch möglich.',
    ],
    [
      '503',
      new AppError('portfolio_assessment_upload_queue_unavailable', 'x', 503),
      'Die Ingestion konnte nicht gestartet werden — der Hintergrund-Dienst war nicht erreichbar. Bitte erneut versuchen.',
    ],
  ])('übersetzt die Upload-Ablehnung %s', async (_status, error, text) => {
    api.getAssessment.mockResolvedValue(assessment('uploading'));
    api.uploadArchive.mockRejectedValue(error);
    renderPage();
    await screen.findByTestId('portfolio-ingestion-panel');

    chooseFile(zip());
    fireEvent.click(screen.getByTestId('portfolio-ingestion-upload'));
    expect(await screen.findByText(text)).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-ingestion-upload-progress')).not.toBeInTheDocument();
  });

  it('lädt nach einer abgelehnten Upload-Anfrage neu, damit ein fremder Auftrag erscheint', async () => {
    api.getAssessment.mockResolvedValueOnce(assessment('uploading'));
    api.uploadArchive.mockRejectedValue(
      new AppError('portfolio_assessment_upload_already_in_progress', 'x', 409),
    );
    renderPage();
    await screen.findByTestId('portfolio-ingestion-panel');

    api.getAssessment.mockResolvedValue(
      assessment('uploading', { job: job({ status: 'running', files_total: 5, files_done: 1 }) }),
    );
    chooseFile(zip());
    fireEvent.click(screen.getByTestId('portfolio-ingestion-upload'));
    expect(await screen.findByText('1 von 5 Dateien')).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-ingestion-panel')).not.toBeInTheDocument();
  });

  it('erlaubt nach einer Ablehnung einen neuen Versuch und löscht den Fehler bei neuer Datei', async () => {
    api.getAssessment.mockResolvedValue(assessment('uploading'));
    api.uploadArchive.mockRejectedValue(
      new AppError('portfolio_assessment_upload_queue_unavailable', 'x', 503),
    );
    renderPage();
    await screen.findByTestId('portfolio-ingestion-panel');

    chooseFile(zip());
    fireEvent.click(screen.getByTestId('portfolio-ingestion-upload'));
    const message = /Die Ingestion konnte nicht gestartet werden/;
    expect(await screen.findByText(message)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('portfolio-ingestion-upload')).toBeEnabled());
    fireEvent.click(screen.getByTestId('portfolio-ingestion-upload'));
    await waitFor(() => expect(api.uploadArchive).toHaveBeenCalledTimes(2));

    chooseFile(zip('neu.zip'));
    await waitFor(() => expect(screen.queryByText(message)).not.toBeInTheDocument());
  });

  it('lässt ein Archiv von genau 500 MB zu', async () => {
    api.getAssessment.mockResolvedValue(assessment('uploading'));
    renderPage();
    await screen.findByTestId('portfolio-ingestion-panel');
    chooseFile(zip('grenze.zip', 500 * 1024 * 1024));
    expect(screen.getByTestId('portfolio-ingestion-upload')).toBeEnabled();
  });

  it.each<[string, AppError, string | RegExp]>([
    [
      '503',
      new AppError('portfolio_assessment_upload_queue_unavailable', 'x', 503),
      /Die Ingestion konnte nicht gestartet werden/,
    ],
    [
      '422 ohne Repository',
      new AppError('portfolio_assessment_repository_missing', 'x', 422),
      /kein GitHub-Repository hinterlegt/,
    ],
    ['Netzfehler', new AppError('portfolio_assessment_ingest_failed'), 'Der Import aus GitHub konnte nicht gestartet werden.'],
  ])('übersetzt beim GitHub-Import die Ablehnung %s', async (_case, error, text) => {
    api.getAssessment.mockResolvedValue(
      assessment('uploading', { source_repository_url: 'https://github.com/mia/portfolio' }),
    );
    api.startRepositoryIngestion.mockRejectedValue(error);
    renderPage();
    await clickWhenEnabled('portfolio-ingestion-github');
    expect(await screen.findByText(text)).toBeInTheDocument();
  });

  it('zeigt beim GitHub-Import eine Tier-Ablehnung als Upgrade-Hinweis', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('uploading', { source_repository_url: 'https://github.com/mia/portfolio' }),
    );
    api.startRepositoryIngestion.mockRejectedValue(
      new AppError('portfolio_assessment_tier_insufficient', 'x', 403),
    );
    renderPage();
    await clickWhenEnabled('portfolio-ingestion-github');
    expect(await screen.findByText('Benötigter Tarif')).toBeInTheDocument();
  });

  it('sperrt auch den ZIP-Upload, solange mit Repository kein Token hinterlegt ist', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('uploading', { source_repository_url: 'https://github.com/mia/portfolio' }),
    );
    api.getGithubCredentialStatus.mockResolvedValue({ configured: false });
    api.setGithubCredential.mockResolvedValue(undefined);
    renderPage();
    await screen.findByTestId('portfolio-github-token-form');

    chooseFile(zip());
    expect(screen.getByTestId('portfolio-ingestion-upload')).toBeDisabled();
    fireEvent.change(screen.getByTestId('portfolio-github-token-input'), {
      target: { value: 'ghp_test' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Token speichern' }));
    await waitFor(() => expect(screen.getByTestId('portfolio-ingestion-upload')).toBeEnabled());
  });

  it('bietet bei einem Ladefehler des Token-Status Retry und Token-Eingabe an', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('uploading', { source_repository_url: 'https://github.com/mia/portfolio' }),
    );
    api.getGithubCredentialStatus
      .mockRejectedValueOnce(new AppError('portfolio_assessment_github_credential_load_failed'))
      .mockResolvedValue({ configured: true });
    renderPage();

    expect(
      await screen.findByText('Der Status des GitHub-Tokens konnte nicht geladen werden.'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-github-token-form')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Erneut versuchen' }));
    await waitFor(() => expect(screen.getByTestId('portfolio-ingestion-github')).toBeEnabled());
  });

  it('meldet einen Fehler beim Speichern des Tokens', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('uploading', { source_repository_url: 'https://github.com/mia/portfolio' }),
    );
    api.getGithubCredentialStatus.mockResolvedValue({ configured: false });
    api.setGithubCredential.mockRejectedValue(
      new AppError('portfolio_assessment_github_credential_save_failed'),
    );
    renderPage();
    fireEvent.change(await screen.findByTestId('portfolio-github-token-input'), {
      target: { value: 'ghp_test' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Token speichern' }));
    expect(
      await screen.findByText('Der GitHub-Token konnte nicht gespeichert werden.'),
    ).toBeInTheDocument();
  });

  it('zeigt bei einer Tier-Ablehnung den Upgrade-Hinweis', async () => {
    api.getAssessment.mockResolvedValue(assessment('uploading'));
    api.uploadArchive.mockRejectedValue(
      new AppError('portfolio_assessment_tier_insufficient', 'x', 403),
    );
    renderPage();
    await screen.findByTestId('portfolio-ingestion-panel');

    chooseFile(zip());
    fireEvent.click(screen.getByTestId('portfolio-ingestion-upload'));
    expect(await screen.findByText('Benötigter Tarif')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('fragt ohne hinterlegten Token inline danach und startet dann den GitHub-Import', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('uploading', { source_repository_url: 'https://github.com/mia/portfolio' }),
    );
    api.getGithubCredentialStatus.mockResolvedValue({ configured: false });
    api.setGithubCredential.mockResolvedValue(undefined);
    api.startRepositoryIngestion.mockResolvedValue(assessment('uploading', { job: job() }));
    renderPage();

    expect(await screen.findByTestId('portfolio-github-token-form')).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-ingestion-github')).toBeDisabled();

    fireEvent.change(screen.getByTestId('portfolio-github-token-input'), {
      target: { value: ' ghp_test ' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Token speichern' }));
    await waitFor(() => expect(api.setGithubCredential).toHaveBeenCalledWith('ghp_test'));
    await waitFor(() =>
      expect(screen.queryByTestId('portfolio-github-token-form')).not.toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId('portfolio-ingestion-github'));
    await waitFor(() => expect(api.startRepositoryIngestion).toHaveBeenCalledWith('a-1'));
  });

  it('sperrt bei fremden Bewertungen nichts, sondern verweist auf den Token der erstellenden Person', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('uploading', {
        created_by: 2,
        source_repository_url: 'https://github.com/mia/portfolio',
      }),
    );
    renderPage();
    expect(
      await screen.findByText(/verwendet den GitHub-Token der Person, die diese/),
    ).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-ingestion-github')).toBeEnabled();
    expect(screen.queryByTestId('portfolio-github-token-form')).not.toBeInTheDocument();
    expect(api.getGithubCredentialStatus).not.toHaveBeenCalled();
  });

  it('bietet bei fremden Bewertungen nach einem Token-Fehler kein Formular an', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('failed', {
        created_by: 2,
        source_repository_url: 'https://github.com/mia/portfolio',
        job: job({ status: 'failed', error_log: [{ code: 'portfolio_github_token_missing' }] }),
      }),
    );
    renderPage();
    expect(await screen.findByText(/Nur sie kann ihn ersetzen/)).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-github-token-form')).not.toBeInTheDocument();
  });

  it('bietet nach einem Token-Fehler an, den Token zu ersetzen', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('failed', {
        source_repository_url: 'https://github.com/mia/portfolio',
        job: job({ status: 'failed', error_log: [{ code: 'portfolio_github_auth_failed' }] }),
      }),
    );
    renderPage();

    expect(
      await screen.findByText(/Der gespeicherte GitHub-Token hat nicht funktioniert/),
    ).toBeInTheDocument();
    // A token is stored, so the retry is not blocked on it.
    expect(screen.getByTestId('portfolio-ingestion-github')).toBeEnabled();
  });

  it('zeigt ohne Repository keinen GitHub-Import und fragt keinen Token ab', async () => {
    api.getAssessment.mockResolvedValue(assessment('uploading'));
    renderPage();
    await screen.findByTestId('portfolio-ingestion-panel');
    expect(screen.queryByTestId('portfolio-ingestion-github')).not.toBeInTheDocument();
    expect(api.getGithubCredentialStatus).not.toHaveBeenCalled();
  });
});
