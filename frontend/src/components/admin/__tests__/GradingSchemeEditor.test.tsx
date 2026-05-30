/**
 * GradingSchemeEditor tests (TF-335 follow-up).
 *
 * Covers: three config types (linear/linear_segments/stepped), form
 * validation, create/update happy paths, and the live-preview evaluator.
 */

import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import GradingSchemeEditor, { evaluateGrade } from '../GradingSchemeEditor';
import { GradingSchemesService } from '../../../services/gradingSchemesService';
import { GradingSchemeOut } from '../../../types/gradingScheme';

jest.mock('../../../services/gradingSchemesService');
const mocked = GradingSchemesService as jest.Mocked<typeof GradingSchemesService>;

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

const noop = jest.fn();

beforeEach(() => jest.clearAllMocks());

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function openCreateDialog() {
  render(
    <Wrapper>
      <GradingSchemeEditor open scheme={null} onClose={noop} onSaved={noop} />
    </Wrapper>,
  );
}

function makeScheme(overrides: Partial<GradingSchemeOut> = {}): GradingSchemeOut {
  return {
    id: 42,
    institution_id: 1,
    name: 'Test Scheme',
    display_format: 'numeric',
    config: { type: 'linear', min_pct: 0, max_pct: 100, min_grade: 0, max_grade: 20 },
    is_default_for_institution: false,
    is_system_scheme: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// evaluateGrade unit tests
// ---------------------------------------------------------------------------

describe('evaluateGrade — linear', () => {
  const cfg = { type: 'linear' as const, min_pct: 0, max_pct: 100, min_grade: 0, max_grade: 20, round_to: 0.5 };

  it('returns min_grade at min_pct', () => expect(evaluateGrade(cfg, 0)).toBe('0'));
  it('returns max_grade at max_pct', () => expect(evaluateGrade(cfg, 100)).toBe('20'));
  it('returns midpoint at 50%', () => expect(evaluateGrade(cfg, 50)).toBe('10'));
  it('returns null below min_pct', () => expect(evaluateGrade(cfg, -1)).toBeNull());
  it('returns null above max_pct', () => expect(evaluateGrade(cfg, 101)).toBeNull());
  it('rounds to nearest 0.5', () => {
    const result = evaluateGrade(cfg, 30);
    expect(['5.5', '6', '6.0', '5']).toContain(result);
  });
});

describe('evaluateGrade — linear_segments (Swiss 1–6)', () => {
  const cfg = {
    type: 'linear_segments' as const,
    round_to: 0.1,
    segments: [
      { from_pct: 0, to_pct: 50, from_grade: 1.0, to_grade: 4.0 },
      { from_pct: 50, to_pct: 100, from_grade: 4.0, to_grade: 6.0 },
    ],
  };

  it('returns 1 at 0%', () => expect(evaluateGrade(cfg, 0)).toBe('1'));
  it('returns 4 at 50%', () => {
    const result = evaluateGrade(cfg, 50);
    expect(result).not.toBeNull();
    expect(parseFloat(result!)).toBeCloseTo(4.0, 1);
  });
  it('returns 6 at 100%', () => {
    const result = evaluateGrade(cfg, 100);
    expect(result).not.toBeNull();
    expect(parseFloat(result!)).toBeCloseTo(6.0, 1);
  });
  it('returns null for out-of-range', () => expect(evaluateGrade(cfg, 110)).toBeNull());
});

describe('evaluateGrade — stepped (German 1.0–5.0)', () => {
  const cfg = {
    type: 'stepped' as const,
    steps: [
      { min_pct: 92, grade_label: '1.0', is_passing: true },
      { min_pct: 81, grade_label: '2.0', is_passing: true },
      { min_pct: 67, grade_label: '3.0', is_passing: true },
      { min_pct: 50, grade_label: '4.0', is_passing: true },
      { min_pct: 0, grade_label: '5.0', is_passing: false },
    ],
  };

  it('returns 1.0 at 100%', () => expect(evaluateGrade(cfg, 100)).toBe('1.0'));
  it('returns 1.0 at 92%', () => expect(evaluateGrade(cfg, 92)).toBe('1.0'));
  it('returns 2.0 at 81%', () => expect(evaluateGrade(cfg, 81)).toBe('2.0'));
  it('returns 4.0 at 50%', () => expect(evaluateGrade(cfg, 50)).toBe('4.0'));
  it('returns 5.0 at 0%', () => expect(evaluateGrade(cfg, 0)).toBe('5.0'));
  it('returns 5.0 at 49%', () => expect(evaluateGrade(cfg, 49)).toBe('5.0'));
});

// ---------------------------------------------------------------------------
// Render tests — create dialog
// ---------------------------------------------------------------------------

describe('GradingSchemeEditor — create mode', () => {
  it('renders with name field and save/cancel buttons', () => {
    openCreateDialog();
    expect(screen.getByTestId('gs-field-name')).toBeInTheDocument();
    expect(screen.getByTestId('gs-editor-save')).toBeInTheDocument();
    expect(screen.getByTestId('gs-editor-cancel')).toBeInTheDocument();
  });

  it('defaults to linear config type', () => {
    openCreateDialog();
    expect(screen.getByTestId('gs-linear-min-pct')).toBeInTheDocument();
  });

  it('shows live preview panel', () => {
    openCreateDialog();
    expect(screen.getByTestId('gs-preview')).toBeInTheDocument();
    expect(screen.getByTestId('gs-preview-0')).toBeInTheDocument();
    expect(screen.getByTestId('gs-preview-100')).toBeInTheDocument();
  });

  it('shows validation error when name is empty and save is clicked', async () => {
    openCreateDialog();
    fireEvent.click(screen.getByTestId('gs-editor-save'));
    await screen.findByText(/Name ist erforderlich/i);
    expect(mocked.create).not.toHaveBeenCalled();
  });

  it('calls GradingSchemesService.create with correct payload for linear config', async () => {
    mocked.create.mockResolvedValue(makeScheme());
    const onSaved = jest.fn();
    const onClose = jest.fn();
    render(
      <Wrapper>
        <GradingSchemeEditor open scheme={null} onClose={onClose} onSaved={onSaved} />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('gs-field-name'), {
      target: { value: 'My Linear Scheme' },
    });
    fireEvent.click(screen.getByTestId('gs-editor-save'));

    await waitFor(() => expect(mocked.create).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const payload = mocked.create.mock.calls[0][0];
    expect(payload.name).toBe('My Linear Scheme');
    expect(payload.config.type).toBe('linear');
  });
});

// ---------------------------------------------------------------------------
// Config type switching
// ---------------------------------------------------------------------------

describe('GradingSchemeEditor — config type switching', () => {
  it('shows segment table when linear_segments is selected', () => {
    openCreateDialog();
    fireEvent.click(screen.getByTestId('gs-config-type-linear-segments'));
    expect(screen.getByTestId('gs-segments-table')).toBeInTheDocument();
    expect(screen.getByTestId('gs-seg-add')).toBeInTheDocument();
  });

  it('shows steps table when stepped is selected', () => {
    openCreateDialog();
    fireEvent.click(screen.getByTestId('gs-config-type-stepped'));
    expect(screen.getByTestId('gs-steps-table')).toBeInTheDocument();
    expect(screen.getByTestId('gs-step-add')).toBeInTheDocument();
  });

  it('adds a segment row when "Add segment" is clicked', () => {
    openCreateDialog();
    fireEvent.click(screen.getByTestId('gs-config-type-linear-segments'));
    const initialRows = screen.getAllByTestId(/gs-seg-\d+-from_pct/);
    fireEvent.click(screen.getByTestId('gs-seg-add'));
    const newRows = screen.getAllByTestId(/gs-seg-\d+-from_pct/);
    expect(newRows.length).toBe(initialRows.length + 1);
  });

  it('adds a step row when "Add step" is clicked', () => {
    openCreateDialog();
    fireEvent.click(screen.getByTestId('gs-config-type-stepped'));
    const initialRows = screen.getAllByTestId(/gs-step-\d+-min-pct/);
    fireEvent.click(screen.getByTestId('gs-step-add'));
    const newRows = screen.getAllByTestId(/gs-step-\d+-min-pct/);
    expect(newRows.length).toBe(initialRows.length + 1);
  });
});

// ---------------------------------------------------------------------------
// Edit mode
// ---------------------------------------------------------------------------

describe('GradingSchemeEditor — edit mode', () => {
  it('pre-fills name from existing scheme', () => {
    const scheme = makeScheme({ name: 'Existing Scheme' });
    render(
      <Wrapper>
        <GradingSchemeEditor open scheme={scheme} onClose={noop} onSaved={noop} />
      </Wrapper>,
    );
    expect(screen.getByTestId('gs-field-name')).toHaveValue('Existing Scheme');
  });

  it('pre-fills linear_segments config', () => {
    const scheme = makeScheme({
      config: {
        type: 'linear_segments',
        round_to: 0.1,
        segments: [
          { from_pct: 0, to_pct: 50, from_grade: 1, to_grade: 4 },
          { from_pct: 50, to_pct: 100, from_grade: 4, to_grade: 6 },
        ],
      },
    });
    render(
      <Wrapper>
        <GradingSchemeEditor open scheme={scheme} onClose={noop} onSaved={noop} />
      </Wrapper>,
    );
    expect(screen.getByTestId('gs-segments-table')).toBeInTheDocument();
    expect(screen.getAllByTestId(/gs-seg-\d+-from_pct/).length).toBe(2);
  });

  it('pre-fills stepped config', () => {
    const scheme = makeScheme({
      config: {
        type: 'stepped',
        steps: [
          { min_pct: 50, grade_label: '4.0', is_passing: true },
          { min_pct: 0, grade_label: '5.0', is_passing: false },
        ],
      },
    });
    render(
      <Wrapper>
        <GradingSchemeEditor open scheme={scheme} onClose={noop} onSaved={noop} />
      </Wrapper>,
    );
    expect(screen.getByTestId('gs-steps-table')).toBeInTheDocument();
    expect(screen.getAllByTestId(/gs-step-\d+-min-pct/).length).toBe(2);
  });

  it('calls GradingSchemesService.update with correct id', async () => {
    const scheme = makeScheme({ id: 99, name: 'Old Name' });
    mocked.update.mockResolvedValue({ ...scheme, name: 'New Name' });
    const onSaved = jest.fn();
    const onClose = jest.fn();

    render(
      <Wrapper>
        <GradingSchemeEditor open scheme={scheme} onClose={onClose} onSaved={onSaved} />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('gs-field-name'), {
      target: { value: 'New Name' },
    });
    fireEvent.click(screen.getByTestId('gs-editor-save'));

    await waitFor(() => expect(mocked.update).toHaveBeenCalledWith(99, expect.objectContaining({ name: 'New Name' })));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it('shows server error message when update fails', async () => {
    const { ApiError } = jest.requireActual('../../../services/submissionsService');
    const scheme = makeScheme();
    mocked.update.mockRejectedValue(
      new ApiError({ kind: 'server', status: 500, message: 'Datenbankfehler', detail: null, issues: [] }),
    );

    render(
      <Wrapper>
        <GradingSchemeEditor open scheme={scheme} onClose={noop} onSaved={noop} />
      </Wrapper>,
    );

    fireEvent.click(screen.getByTestId('gs-editor-save'));
    await screen.findByTestId('gs-editor-error');
  });
});
