/**
 * «Neue Portfolio-Bewertung» (TF-989): active templates only, student search,
 * optional grading scheme, framework conditions and GitHub URL.
 */
import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  PortfolioAssessmentCreateDialog,
  isGithubRepoUrl,
} from '../PortfolioAssessmentCreateDialog';
import { portfolioApi } from '../../../api/portfolioApi';
import { GradingSchemesService } from '../../../services/gradingSchemesService';
import { AppError } from '../../../errors';

jest.mock('../../../hooks/useFeatures', () => ({
  useFeatures: () => ({ tier: 'professional', isLoading: false }),
}));

jest.mock('../../../api/portfolioApi', () => ({
  portfolioApi: {
    listTemplates: jest.fn(),
    searchStudents: jest.fn(),
    createAssessment: jest.fn(),
  },
}));

jest.mock('../../../services/gradingSchemesService', () => ({
  GradingSchemesService: { list: jest.fn() },
}));

const api = portfolioApi as jest.Mocked<typeof portfolioApi>;
const listSchemes = GradingSchemesService.list as jest.Mock;

const template = (id: string, name: string, is_active = true) =>
  ({ id, name, is_active, phases: [] }) as unknown as Awaited<
    ReturnType<typeof portfolioApi.listTemplates>
  >[number];

const mia = { id: 7, external_id: 'mia@schule.ch', display_name: 'Mia Muster', classes: [{ class_id: 1, class_name: 'INF21a' }] };

function renderDialog(onCreated: (id: string) => void = jest.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <PortfolioAssessmentCreateDialog open onClose={jest.fn()} onCreated={onCreated} />
    </QueryClientProvider>,
  );
}

async function pickTemplate(name: string) {
  fireEvent.mouseDown(within(screen.getByTestId('portfolio-create-template')).getByRole('combobox'));
  fireEvent.click(await screen.findByRole('option', { name }));
}

/** Typing happens in a focused field; unfocused, MUI resets the search text. */
function typeStudent(value: string) {
  const input = screen.getByTestId('portfolio-create-student');
  fireEvent.focus(input);
  fireEvent.change(input, { target: { value } });
}

async function pickStudent() {
  typeStudent('Mia');
  fireEvent.click(await screen.findByText('Mia Muster', {}, { timeout: 2000 }));
}

beforeEach(() => {
  jest.resetAllMocks();
  api.listTemplates.mockResolvedValue([
    template('t-1', 'IPA Informatik'),
    template('t-2', 'Altes Template', false),
  ]);
  api.searchStudents.mockResolvedValue([mia]);
  listSchemes.mockResolvedValue({
    schemes: [{ id: 3, name: 'Schweizer Skala 1–6', is_system_scheme: true }],
  });
});

describe('PortfolioAssessmentCreateDialog', () => {
  it('bietet nur aktive Templates an', async () => {
    renderDialog();
    fireEvent.mouseDown(
      within(screen.getByTestId('portfolio-create-template')).getByRole('combobox'),
    );
    expect(await screen.findByRole('option', { name: 'IPA Informatik' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Altes Template' })).not.toBeInTheDocument();
  });

  it('sucht Studierende serverseitig und zeigt ID und Klasse', async () => {
    renderDialog();
    typeStudent('Mia');
    await waitFor(() => expect(api.searchStudents).toHaveBeenCalledWith('Mia'));
    expect(await screen.findByText('mia@schule.ch · INF21a')).toBeInTheDocument();
  });

  it('legt die Bewertung mit bereinigten Feldern an und meldet die neue ID', async () => {
    api.createAssessment.mockResolvedValue({ id: 'a-9' } as never);
    const onCreatedSpy = jest.fn();
    renderDialog(onCreatedSpy);

    await pickTemplate('IPA Informatik');
    await pickStudent();
    fireEvent.change(screen.getByTestId('portfolio-create-framework-conditions'), {
      target: { value: '  Einzelarbeit, 10 Tage  ' },
    });
    fireEvent.change(screen.getByTestId('portfolio-create-repository-url'), {
      target: { value: ' https://github.com/mia/ipa ' },
    });
    fireEvent.click(screen.getByTestId('portfolio-create-submit'));

    await waitFor(() => expect(onCreatedSpy).toHaveBeenCalledWith('a-9'));
    expect(api.createAssessment).toHaveBeenCalledWith({
      template_id: 't-1',
      student_id: 7,
      framework_conditions: 'Einzelarbeit, 10 Tage',
      source_repository_url: 'https://github.com/mia/ipa',
      grading_scheme_id: null,
    });
  });

  it('übernimmt ein gewähltes Notenschema', async () => {
    api.createAssessment.mockResolvedValue({ id: 'a-9' } as never);
    renderDialog();
    await pickTemplate('IPA Informatik');
    await pickStudent();
    fireEvent.mouseDown(
      within(screen.getByTestId('portfolio-create-grading-scheme')).getByRole('combobox'),
    );
    fireEvent.click(await screen.findByRole('option', { name: 'Schweizer Skala 1–6' }));
    fireEvent.click(screen.getByTestId('portfolio-create-submit'));
    await waitFor(() =>
      expect(api.createAssessment).toHaveBeenCalledWith(
        expect.objectContaining({ grading_scheme_id: 3, source_repository_url: null }),
      ),
    );
  });

  it('sperrt das Anlegen, bis Template und Person gewählt sind', async () => {
    renderDialog();
    expect(screen.getByTestId('portfolio-create-submit')).toBeDisabled();
    await pickTemplate('IPA Informatik');
    expect(screen.getByTestId('portfolio-create-submit')).toBeDisabled();
    await pickStudent();
    expect(screen.getByTestId('portfolio-create-submit')).toBeEnabled();
  });

  it('weist eine Repository-URL ausserhalb von github.com ab', async () => {
    renderDialog();
    await pickTemplate('IPA Informatik');
    await pickStudent();
    const url = screen.getByTestId('portfolio-create-repository-url');
    fireEvent.change(url, { target: { value: 'https://gitlab.com/mia/ipa' } });
    fireEvent.blur(url);
    expect(
      screen.getByText('Bitte eine URL der Form https://github.com/<owner>/<repo> angeben.'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-create-submit')).toBeDisabled();
  });

  it('zeigt einen Backend-Fehler übersetzt an', async () => {
    api.createAssessment.mockRejectedValue(
      new AppError('portfolio_assessment_student_not_found', 'x', 422),
    );
    renderDialog();
    await pickTemplate('IPA Informatik');
    await pickStudent();
    fireEvent.click(screen.getByTestId('portfolio-create-submit'));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Die lernende Person wurde in deiner Institution nicht gefunden.',
    );
  });

  it('zeigt bei einer Tier-Ablehnung den Upgrade-Hinweis', async () => {
    api.createAssessment.mockRejectedValue(
      new AppError('portfolio_assessment_tier_insufficient', 'x', 403),
    );
    renderDialog();
    await pickTemplate('IPA Informatik');
    await pickStudent();
    fireEvent.click(screen.getByTestId('portfolio-create-submit'));
    expect(await screen.findByText('Benötigter Tarif')).toBeInTheDocument();
  });
});

describe('PortfolioAssessmentCreateDialog – Ladefehler', () => {
  it('sperrt das Anlegen, wenn die Notenschemata nicht geladen werden konnten', async () => {
    listSchemes.mockRejectedValue(new AppError('grading_schemes_list_failed'));
    renderDialog();
    await pickTemplate('IPA Informatik');
    await pickStudent();
    expect(
      await screen.findByText('Bewertungsschemata konnten nicht geladen werden.'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-create-submit')).toBeDisabled();
  });

  it('zeigt einen Fehler der Studierenden-Suche am Feld', async () => {
    api.searchStudents.mockRejectedValue(new AppError('portfolio_assessment_student_search_failed'));
    renderDialog();
    expect(
      await screen.findByText('Die Studierenden konnten nicht geladen werden.'),
    ).toBeInTheDocument();
  });

  it('weist auf fehlende aktive Templates hin', async () => {
    api.listTemplates.mockResolvedValue([template('t-2', 'Altes Template', false)]);
    renderDialog();
    expect(await screen.findByText(/Es gibt noch kein aktives Template/)).toBeInTheDocument();
  });
});

describe('isGithubRepoUrl', () => {
  it.each([
    ['https://github.com/mia/ipa', true],
    ['https://github.com/mia/ipa.git', true],
    ['https://github.com/mia/ipa/', true],
    ['http://github.com/mia/ipa', false],
    ['https://github.com/mia', false],
    ['https://github.com/mia/ipa/tree/main', false],
    ['https://gitlab.com/mia/ipa', false],
  ])('%s → %s', (url, expected) => {
    expect(isGithubRepoUrl(url)).toBe(expected);
  });
});
