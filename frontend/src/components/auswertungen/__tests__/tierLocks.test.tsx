/**
 * TF-1055: tier-gated evaluation actions are shown, but disabled with an
 * upgrade hint, as soon as `useFeatures().evaluationLimits` says the tier
 * lacks them — before any 402.
 *
 * `useFeatures` is mocked per tier here; `tierLocks.features.test.tsx` runs
 * the real hook against a mocked `/api/auth/features`.
 */

import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import ReviewQueue from '../ReviewQueue';
import ImportDialog from '../ImportDialog';
import AdminGradingSchemes from '../../../pages/AdminGradingSchemes';
import AuswertungenKlassenDetail from '../../../pages/AuswertungenKlassenDetail';
import AuswertungenStudiDetail from '../../../pages/AuswertungenStudiDetail';
import { EvaluationLimits } from '../../../hooks/useFeatures';
import { GradesService } from '../../../services/gradesService';
import { GradingSchemesService } from '../../../services/gradingSchemesService';
import { MoodleConnectionsService } from '../../../services/moodleConnectionsService';
import { StudentClassesService } from '../../../services/studentClassesService';
import { StudentsService } from '../../../services/studentsService';
import { GradingSchemeOut } from '../../../types/gradingScheme';
import { TIER_CONFIG } from '../../common/UpgradePrompt';

jest.mock('../../../api/apiClient');
jest.mock('../../../services/gradesService');
jest.mock('../../../services/gradingSchemesService');
jest.mock('../../../services/moodleConnectionsService');
jest.mock('../../../services/studentClassesService');
jest.mock('../../../services/studentsService');
jest.mock('../../../hooks/useActivityHeartbeat', () => ({
  useActivityHeartbeat: jest.fn(),
}));

let mockLimits: EvaluationLimits | null = null;
jest.mock('../../../hooks/useFeatures', () => ({
  useFeatures: () => ({ evaluationLimits: mockLimits, isLoading: false }),
}));

const mockGrades = GradesService as jest.Mocked<typeof GradesService>;
const mockSchemes = GradingSchemesService as jest.Mocked<typeof GradingSchemesService>;
const mockMoodle = MoodleConnectionsService as jest.Mocked<typeof MoodleConnectionsService>;
const mockClasses = StudentClassesService as jest.Mocked<typeof StudentClassesService>;
const mockStudents = StudentsService as jest.Mocked<typeof StudentsService>;

// The gated flags per tier, as in `_TIER_LIMITS` (auswertung_quotas.py). The
// backend test checks the endpoint against that table; here only the shape
// the UI reads matters.
const LIMITS: Record<string, EvaluationLimits> = {
  free: {
    tier: 'free', label: 'Free', exams_per_month: 3, submissions_per_exam: 30,
    drivers: ['moodle_json'], llm_grading: false, class_history_stats: false,
    review_bulk: false, custom_grading_schemes: false, custom_llm_model: false,
  },
  starter: {
    tier: 'starter', label: 'Starter', exams_per_month: -1, submissions_per_exam: 50,
    drivers: ['moodle_json'], llm_grading: true, class_history_stats: false,
    review_bulk: false, custom_grading_schemes: false, custom_llm_model: false,
  },
  professional: {
    tier: 'professional', label: 'Professional', exams_per_month: -1, submissions_per_exam: -1,
    drivers: ['moodle_json', 'moodle_api'], llm_grading: true, class_history_stats: false,
    review_bulk: true, custom_grading_schemes: false, custom_llm_model: false,
  },
  enterprise: {
    tier: 'enterprise', label: 'Enterprise', exams_per_month: -1, submissions_per_exam: -1,
    drivers: ['moodle_json', 'moodle_api'], llm_grading: true, class_history_stats: true,
    review_bulk: true, custom_grading_schemes: true, custom_llm_model: true,
  },
};

const institutionScheme: GradingSchemeOut = {
  id: 7,
  institution_id: 1,
  name: 'Eigene Skala',
  display_format: 'numeric',
  config: { type: 'linear', min_grade: 1, max_grade: 6, pass_grade: 4 } as GradingSchemeOut['config'],
  is_default_for_institution: false,
  is_system_scheme: false,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
};

beforeEach(() => {
  jest.clearAllMocks();
  mockLimits = null;
  mockGrades.getReviewQueue.mockResolvedValue({ total: 0, items: [] });
  mockSchemes.list.mockResolvedValue({ schemes: [institutionScheme] });
  mockMoodle.list.mockResolvedValue({ items: [{ id: 1 }] } as never);
  mockClasses.get.mockResolvedValue({
    id: 3, name: '3a', member_count: 0, members: [],
  } as never);
  mockClasses.getHistory.mockResolvedValue({
    class_id: 3, class_name: '3a', member_count: 0,
    members: [], exam_aggregates: [], topic_coverage: [],
  });
  mockStudents.getHistory.mockResolvedValue({
    student_id: 5, external_id: 'anna@example.org', display_name: 'Anna',
    submission_count: 0, avg_percentage: null, submissions: [],
    bloom_mix: {}, topic_heatmap: [], classes: [],
  });
});

// Waits until the component's own loading spinner is gone, so its last
// state update lands inside the test instead of after it.
const renderInRouter = async (ui: React.ReactElement, path = '/', route = '*') => {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path={route} element={ui} />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.queryByRole('progressbar')).not.toBeInTheDocument());
};

describe('ReviewQueue — Bulk-Leiste (review_bulk, ab Professional)', () => {
  it.each(['free', 'starter'])('%s: Bulk deaktiviert, Hinweis mit Zieltarif', async (tier) => {
    mockLimits = LIMITS[tier];
    await renderInRouter(<ReviewQueue examId={1} />);

    expect(await screen.findByTestId('bulk-tier-lock')).toHaveTextContent('Professional');
    expect(screen.getByTestId('bulk-apply-threshold')).toBeDisabled();
    expect(screen.getByTestId('bulk-apply-selection')).toBeDisabled();
  });

  it.each(['professional', 'enterprise'])('%s: Bulk aktiv, kein Hinweis', async (tier) => {
    mockLimits = LIMITS[tier];
    await renderInRouter(<ReviewQueue examId={1} />);

    await waitFor(() => expect(mockGrades.getReviewQueue).toHaveBeenCalled());
    expect(screen.getByTestId('bulk-apply-threshold')).toBeEnabled();
    expect(screen.queryByTestId('bulk-tier-lock')).not.toBeInTheDocument();
  });
});

describe('AdminGradingSchemes — eigene Notenmodelle (custom_grading_schemes, Enterprise)', () => {
  it('professional: «Anlegen» und «Bearbeiten» deaktiviert, Löschen bleibt', async () => {
    mockLimits = LIMITS.professional;
    await renderInRouter(<AdminGradingSchemes />);

    expect(await screen.findByTestId('gs-row-7')).toBeInTheDocument();
    expect(screen.getByTestId('gs-tier-lock')).toHaveTextContent('Enterprise');
    expect(screen.getByTestId('gs-page-create')).toBeDisabled();
    expect(screen.getByTestId('gs-btn-edit-7')).toBeDisabled();
    expect(screen.getByTestId('gs-btn-delete-7')).toBeEnabled();
  });

  it('enterprise: alles aktiv, kein Hinweis', async () => {
    mockLimits = LIMITS.enterprise;
    await renderInRouter(<AdminGradingSchemes />);

    expect(await screen.findByTestId('gs-row-7')).toBeInTheDocument();
    expect(screen.getByTestId('gs-page-create')).toBeEnabled();
    expect(screen.getByTestId('gs-btn-edit-7')).toBeEnabled();
    expect(screen.queryByTestId('gs-tier-lock')).not.toBeInTheDocument();
  });
});

describe('Klassen- und Studi-Verlauf (class_history_stats, Enterprise)', () => {
  it('professional: Klassen-Detail fragt /stats nicht an und zeigt den Upgrade-Hinweis', async () => {
    mockLimits = LIMITS.professional;
    await renderInRouter(<AuswertungenKlassenDetail />, '/k/3', '/k/:classId');

    expect(
      await screen.findByText('Klassen- und Studi-Verlauf'),
    ).toBeInTheDocument();
    expect(mockClasses.get).toHaveBeenCalledWith(3);
    expect(mockClasses.getHistory).not.toHaveBeenCalled();
  });

  it('enterprise: Klassen-Detail lädt /stats', async () => {
    mockLimits = LIMITS.enterprise;
    await renderInRouter(<AuswertungenKlassenDetail />, '/k/3', '/k/:classId');

    await waitFor(() => expect(mockClasses.getHistory).toHaveBeenCalledWith(3));
    expect(screen.queryByText('Klassen- und Studi-Verlauf')).not.toBeInTheDocument();
  });

  it('professional: Studi-Detail fragt /stats nicht an und zeigt den Upgrade-Hinweis', async () => {
    mockLimits = LIMITS.professional;
    await renderInRouter(<AuswertungenStudiDetail />, '/s/5', '/s/:studentId');

    expect(
      await screen.findByText('Klassen- und Studi-Verlauf'),
    ).toBeInTheDocument();
    expect(mockStudents.getHistory).not.toHaveBeenCalled();
  });

  it('enterprise: Studi-Detail lädt /stats', async () => {
    mockLimits = LIMITS.enterprise;
    await renderInRouter(<AuswertungenStudiDetail />, '/s/5', '/s/:studentId');

    await waitFor(() => expect(mockStudents.getHistory).toHaveBeenCalledWith(5));
  });

  it('unbekannte Limits: /stats wird wie bisher angefragt (402 bleibt Fallback)', async () => {
    mockLimits = null;
    await renderInRouter(<AuswertungenStudiDetail />, '/s/5', '/s/:studentId');

    await waitFor(() => expect(mockStudents.getHistory).toHaveBeenCalledWith(5));
  });
});

describe('Zieltarif in der Farbe des UpgradePrompt', () => {
  // Manual test TF-1055: the blue info hint said «Enterprise» in the Starter
  // colour next to the orange Enterprise card.
  it('Bewertungsschemata: Hinweis-Rahmen in Enterprise-Orange', async () => {
    mockLimits = LIMITS.professional;
    await renderInRouter(<AdminGradingSchemes />);

    const hint = screen.getByTestId('gs-tier-lock');
    expect(hint).toHaveStyle({ borderColor: TIER_CONFIG.enterprise.color });
    // One lock (the alert icon), not a second one on the chip.
    expect(within(hint).getAllByTestId('LockIcon')).toHaveLength(1);
    // A filled button in the tier colour, not bare text.
    const upgrade = screen.getByTestId('gs-tier-lock-upgrade');
    expect(upgrade).toHaveClass('MuiButton-contained');
    expect(upgrade).toHaveStyle({ backgroundColor: TIER_CONFIG.enterprise.color });
  });

  it('Bulk-Leiste: Hinweis-Rahmen in Professional-Grün', async () => {
    mockLimits = LIMITS.starter;
    await renderInRouter(<ReviewQueue examId={1} />);

    expect(screen.getByTestId('bulk-tier-lock')).toHaveStyle({
      borderColor: TIER_CONFIG.professional.color,
    });
  });
});

describe('ImportDialog — Driver moodle_api (ab Professional)', () => {
  const renderDialog = () =>
    renderInRouter(
      <ImportDialog
        open
        examId={42}
        examTitle="Allgemeinbildung"
        onClose={jest.fn()}
        onImported={jest.fn()}
      />,
    );

  it('starter: Radio deaktiviert, mit Zieltarif, obwohl eine Verbindung besteht', async () => {
    mockLimits = LIMITS.starter;
    await renderDialog();

    await waitFor(() => expect(mockMoodle.list).toHaveBeenCalled());
    expect(screen.getByTestId('import-driver-moodle-api')).toBeDisabled();
    const chip = screen.getByTestId('import-driver-moodle-api-tier-lock');
    expect(chip).toHaveTextContent('Professional');
    expect(chip).toHaveStyle({ color: TIER_CONFIG.professional.color });
    expect(within(chip).getByTestId('LockIcon')).toBeInTheDocument();
  });

  it.each(['professional', 'enterprise'])('%s: Radio aktiv bei bestehender Verbindung', async (tier) => {
    mockLimits = LIMITS[tier];
    await renderDialog();

    await waitFor(() =>
      expect(screen.getByTestId('import-driver-moodle-api')).toBeEnabled(),
    );
    expect(
      screen.queryByTestId('import-driver-moodle-api-tier-lock'),
    ).not.toBeInTheDocument();
  });
});
