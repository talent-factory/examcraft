/**
 * Tests for NotenexportPanel — TF-335 Phase 3.
 *
 * Covers the user-visible behaviour the silent-failure-hunter and the
 * pr-test-analyzer flagged: each format triggers the right service
 * call, the panel is disabled while reviews are pending, and the 409
 * "review pending" message is surfaced (not collapsed to "Export
 * failed (409)").
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';

import NotenexportPanel from '../NotenexportPanel';
import { GradeExportService } from '../../../services/gradeExportService';
import { ComposerService } from '../../../services/ComposerService';
import { GradingSchemesService } from '../../../services/gradingSchemesService';
import { ApiError } from '../../../services/submissionsService';
import { MoodleFeedbackPushService } from '../../../services/moodleFeedbackPushService';

// react-i18next is globally mocked in setupTests.ts to resolve keys
// against the real DE translation.json — no per-test i18n bootstrap.

jest.mock('../../../services/gradeExportService', () => ({
  GradeExportService: { download: jest.fn() },
}));

jest.mock('../../../services/ComposerService', () => ({
  ComposerService: {
    getExam: jest.fn(),
    updateExamGradingScheme: jest.fn(),
  },
}));

jest.mock('../../../services/gradingSchemesService', () => ({
  GradingSchemesService: { list: jest.fn() },
}));

jest.mock('../../../services/moodleFeedbackPushService', () => ({
  MoodleFeedbackPushService: { start: jest.fn(), poll: jest.fn() },
}));

jest.mock('../../../services/submissionsService', () => ({
  ApiError: class ApiError extends Error {
    kind: string;
    status: number;
    constructor(opts: { kind: string; status: number; message: string }) {
      super(opts.message);
      this.kind = opts.kind;
      this.status = opts.status;
    }
  },
}));

// The scheme picker is gated on the ``create_exams`` permission. Default to
// granting it so the picker renders; individual tests flip it to false.
const mockHasPermission = jest.fn<boolean, [string]>(() => true);
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ hasPermission: mockHasPermission }),
}));

const mockedDownload = GradeExportService.download as jest.MockedFunction<
  typeof GradeExportService.download
>;
const mockedGetExam = ComposerService.getExam as jest.Mock;
const mockedUpdateScheme =
  ComposerService.updateExamGradingScheme as jest.Mock;
const mockedListSchemes = GradingSchemesService.list as jest.Mock;
const mockedPushStart = MoodleFeedbackPushService.start as jest.Mock;
const mockedPushPoll = MoodleFeedbackPushService.poll as jest.Mock;

const SCHEMES = {
  schemes: [
    {
      id: 1,
      institution_id: null,
      name: 'Swiss 1.0–6.0',
      display_format: 'numeric',
      config: { type: 'linear', min_pct: 0, max_pct: 100, min_grade: 1, max_grade: 6 },
      is_default_for_institution: false,
      is_system_scheme: true,
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
    },
  ],
};

const EXAM = {
  id: 42,
  title: 'Prüfung',
  status: 'finalized',
  updated_at: '2026-06-15T10:00:00Z',
  grading_scheme_id: null,
};

const renderPanel = (props: {
  totalSubmissions?: number;
  pendingCount?: number;
}) =>
  render(
    <NotenexportPanel
      examId={42}
      totalSubmissions={props.totalSubmissions ?? 5}
      pendingCount={props.pendingCount ?? 0}
      onOpenReview={() => {}}
    />,
  );

describe('NotenexportPanel', () => {
  // jsdom doesn't ship URL.createObjectURL — the panel uses it to
  // trigger downloads, so stub once for the suite.
  beforeAll(() => {
    Object.defineProperty(URL, 'createObjectURL', {
      writable: true,
      value: jest.fn().mockReturnValue('blob:mock'),
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      writable: true,
      value: jest.fn(),
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
    mockHasPermission.mockReturnValue(true);
    // Scheme picker fetches schemes + the exam on mount; default both so
    // the existing export tests keep rendering without real HTTP.
    mockedListSchemes.mockResolvedValue(SCHEMES);
    mockedGetExam.mockResolvedValue({ ...EXAM });
    mockedUpdateScheme.mockResolvedValue({
      ...EXAM,
      grading_scheme_id: 1,
      updated_at: '2026-06-15T10:05:00Z',
    });
  });

  it('disables download while reviews are pending', () => {
    renderPanel({ pendingCount: 3 });
    const button = screen.getByRole('button', { name: /Herunterladen/ });
    expect(button).toBeDisabled();
  });

  it('disables download when there are zero submissions', () => {
    renderPanel({ totalSubmissions: 0, pendingCount: 0 });
    const button = screen.getByRole('button', { name: /Herunterladen/ });
    expect(button).toBeDisabled();
  });

  it('triggers a CSV download by default', async () => {
    mockedDownload.mockResolvedValueOnce({
      blob: new Blob(['ok'], { type: 'text/csv' }),
      filename: 'noten-X.csv',
    });
    renderPanel({ pendingCount: 0 });
    fireEvent.click(screen.getByRole('button', { name: /Herunterladen/ }));
    await waitFor(() =>
      expect(mockedDownload).toHaveBeenCalledWith(42, 'csv'),
    );
  });

  it('switches format and downloads PDF when chosen', async () => {
    mockedDownload.mockResolvedValueOnce({
      blob: new Blob([new Uint8Array([0x25, 0x50, 0x44, 0x46])], {
        type: 'application/pdf',
      }),
      filename: 'noten-X.pdf',
    });
    renderPanel({ pendingCount: 0 });
    fireEvent.click(screen.getByLabelText(/PDF/));
    fireEvent.click(screen.getByRole('button', { name: /Herunterladen/ }));
    await waitFor(() =>
      expect(mockedDownload).toHaveBeenCalledWith(42, 'pdf'),
    );
  });

  it('surfaces backend 409 detail (not the generic kind message)', async () => {
    mockedDownload.mockRejectedValueOnce(
      new ApiError({
        kind: 'conflict',
        status: 409,
        message: 'Notenexport gesperrt: Review zuerst abarbeiten.',
      }),
    );
    renderPanel({ pendingCount: 0 });
    fireEvent.click(screen.getByRole('button', { name: /Herunterladen/ }));
    expect(
      await screen.findByText(/Review zuerst abarbeiten/),
    ).toBeInTheDocument();
  });

  // --- TF-432: per-exam grading scheme picker -----------------------------

  it('renders the per-exam grading scheme picker after load', async () => {
    renderPanel({ pendingCount: 0 });
    expect(
      await screen.findByTestId('exam-grading-scheme-select'),
    ).toBeInTheDocument();
    expect(mockedGetExam).toHaveBeenCalledWith(42);
    expect(mockedListSchemes).toHaveBeenCalled();
  });

  it('assigns a system scheme via the dedicated PATCH endpoint', async () => {
    renderPanel({ pendingCount: 0 });
    await screen.findByTestId('exam-grading-scheme-select');
    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(
      await screen.findByRole('option', { name: 'Swiss 1.0–6.0' }),
    );
    await waitFor(() =>
      expect(mockedUpdateScheme).toHaveBeenCalledWith(
        42,
        expect.objectContaining({ grading_scheme_id: 1 }),
      ),
    );
  });

  it('clears the scheme back to the institution default (null)', async () => {
    mockedGetExam.mockResolvedValue({ ...EXAM, grading_scheme_id: 1 });
    renderPanel({ pendingCount: 0 });
    await screen.findByTestId('exam-grading-scheme-select');
    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(
      await screen.findByRole('option', {
        name: 'Institutions-Standard verwenden',
      }),
    );
    await waitFor(() =>
      expect(mockedUpdateScheme).toHaveBeenCalledWith(
        42,
        expect.objectContaining({ grading_scheme_id: null }),
      ),
    );
  });

  it('keeps the export usable (and logs) when scheme metadata fails to load', async () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    mockedListSchemes.mockRejectedValueOnce(new Error('boom'));
    renderPanel({ pendingCount: 0 });
    expect(
      screen.getByRole('button', { name: /Herunterladen/ }),
    ).toBeInTheDocument();
    // The failure is logged, not swallowed silently — so an auth/permission/
    // network problem stays observable instead of "the picker just vanished".
    // (Wait on the log, not on picker-absence: the picker is already absent on
    // the first frame, so a picker-absent waitFor would resolve before the
    // async catch even runs.)
    await waitFor(() =>
      expect(warn).toHaveBeenCalledWith(
        'NotenexportPanel: grading-scheme metadata load failed',
        expect.any(Error),
      ),
    );
    expect(
      screen.queryByTestId('exam-grading-scheme-select'),
    ).not.toBeInTheDocument();
    warn.mockRestore();
  });

  it('shows the success message and reflects the saved scheme after assigning', async () => {
    renderPanel({ pendingCount: 0 });
    await screen.findByTestId('exam-grading-scheme-select');
    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(
      await screen.findByRole('option', { name: 'Swiss 1.0–6.0' }),
    );
    // Success alert is rendered…
    const msg = await screen.findByTestId('exam-grading-scheme-msg');
    expect(msg).toHaveTextContent('Notenschema gespeichert.');
    // …and the Select now reflects the returned grading_scheme_id (1),
    // i.e. the picker holds the user's choice rather than resetting.
    expect(screen.getByRole('combobox')).toHaveTextContent('Swiss 1.0–6.0');
  });

  it('recovers from a 409 conflict: reloads the exam and warns the user', async () => {
    // First save clashes (409); the component must re-fetch the exam to pick
    // up a fresh updated_at and surface the conflict message.
    mockedUpdateScheme.mockRejectedValueOnce({ response: { status: 409 } });
    mockedGetExam
      .mockResolvedValueOnce({ ...EXAM })
      .mockResolvedValueOnce({
        ...EXAM,
        grading_scheme_id: 1,
        updated_at: '2026-06-15T11:00:00Z',
      });
    renderPanel({ pendingCount: 0 });
    await screen.findByTestId('exam-grading-scheme-select');
    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(
      await screen.findByRole('option', { name: 'Swiss 1.0–6.0' }),
    );
    const msg = await screen.findByTestId('exam-grading-scheme-msg');
    expect(msg).toHaveTextContent(
      'Prüfung wurde zwischenzeitlich geändert — bitte erneut versuchen.',
    );
    // Mount fetch + the post-409 reload = two getExam calls.
    expect(mockedGetExam).toHaveBeenCalledTimes(2);
  });

  it('surfaces a generic error when a non-409 save fails', async () => {
    mockedUpdateScheme.mockRejectedValueOnce({ response: { status: 500 } });
    renderPanel({ pendingCount: 0 });
    await screen.findByTestId('exam-grading-scheme-select');
    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(
      await screen.findByRole('option', { name: 'Swiss 1.0–6.0' }),
    );
    const msg = await screen.findByTestId('exam-grading-scheme-msg');
    expect(msg).toHaveTextContent('Notenschema konnte nicht gespeichert werden.');
    // A 500 is not a conflict — no reload beyond the initial mount fetch.
    expect(mockedGetExam).toHaveBeenCalledTimes(1);
  });

  // --- TF-435: Moodle feedback push -------------------------------------

  it('shows the Moodle push button when permitted', () => {
    renderPanel({ pendingCount: 0 });
    expect(screen.getByTestId('moodle-push-button')).toBeInTheDocument();
  });

  it('pushes feedback to Moodle and surfaces the completed result', async () => {
    mockedPushStart.mockResolvedValueOnce({
      id: 7,
      status: 'completed',
      transport: 'plugin',
      students_total: 3,
      students_pushed: 3,
      students_skipped: 0,
      students_failed: 0,
      error_log: null,
    });
    renderPanel({ pendingCount: 0 });
    fireEvent.click(screen.getByTestId('moodle-push-button'));
    await waitFor(() => expect(mockedPushStart).toHaveBeenCalledWith(42));
    expect(
      await screen.findByTestId('moodle-push-result'),
    ).toBeInTheDocument();
  });

  it('polls a queued job until it completes, then shows the result', async () => {
    jest.useFakeTimers();
    try {
      mockedPushStart.mockResolvedValueOnce({
        id: 7,
        status: 'processing',
        transport: null,
        students_total: 0,
        students_pushed: 0,
        students_skipped: 0,
        students_failed: 0,
        error_log: null,
      });
      mockedPushPoll.mockResolvedValueOnce({
        id: 7,
        status: 'completed',
        transport: 'gradebook',
        students_total: 2,
        students_pushed: 2,
        students_skipped: 0,
        students_failed: 0,
        error_log: null,
      });
      renderPanel({ pendingCount: 0 });
      fireEvent.click(screen.getByTestId('moodle-push-button'));
      await act(async () => {
        await Promise.resolve(); // flush start()
      });
      await act(async () => {
        jest.advanceTimersByTime(2000); // fire the poll backoff
      });
      await act(async () => {
        await Promise.resolve(); // flush poll()
      });
      expect(mockedPushPoll).toHaveBeenCalledWith(42, 7);
      expect(screen.getByTestId('moodle-push-result')).toBeInTheDocument();
    } finally {
      jest.useRealTimers();
    }
  });

  it('surfaces an ApiError from the push as a user-facing error', async () => {
    mockedPushStart.mockRejectedValueOnce(
      new ApiError({
        kind: 'validation',
        status: 412,
        message: 'Keine Moodle-Verbindung konfiguriert.',
      }),
    );
    renderPanel({ pendingCount: 0 });
    fireEvent.click(screen.getByTestId('moodle-push-button'));
    expect(
      await screen.findByText(/Keine Moodle-Verbindung konfiguriert/),
    ).toBeInTheDocument();
    expect(screen.queryByTestId('moodle-push-result')).not.toBeInTheDocument();
  });

  it('paints a completed-with-failures push as a warning, not success', async () => {
    // A completed job where most students failed must not read as green success.
    mockedPushStart.mockResolvedValueOnce({
      id: 8,
      status: 'completed',
      transport: 'plugin',
      students_total: 3,
      students_pushed: 1,
      students_skipped: 0,
      students_failed: 2,
      error_log: null,
    });
    renderPanel({ pendingCount: 0 });
    fireEvent.click(screen.getByTestId('moodle-push-button'));
    const result = await screen.findByTestId('moodle-push-result');
    expect(result.className).toMatch(/Warning/);
  });

  it('warns that the push is still running when the poll cap is hit', async () => {
    jest.useFakeTimers();
    try {
      const processing = {
        id: 9,
        status: 'processing' as const,
        transport: null,
        students_total: 0,
        students_pushed: 0,
        students_skipped: 0,
        students_failed: 0,
        error_log: null,
      };
      mockedPushStart.mockResolvedValueOnce(processing);
      mockedPushPoll.mockResolvedValue(processing); // never terminalizes
      renderPanel({ pendingCount: 0 });
      fireEvent.click(screen.getByTestId('moodle-push-button'));
      await act(async () => {
        await Promise.resolve(); // flush start()
      });
      // Drive the 60×2s poll loop all the way to its safety cap.
      for (let i = 0; i < 61; i++) {
        await act(async () => {
          jest.advanceTimersByTime(2000);
        });
        await act(async () => {
          await Promise.resolve();
        });
      }
      // No green result; instead the "still running in background" hint.
      expect(
        screen.queryByTestId('moodle-push-result'),
      ).not.toBeInTheDocument();
      expect(
        screen.getByText(/läuft noch im Hintergrund/),
      ).toBeInTheDocument();
    } finally {
      jest.useRealTimers();
    }
  });

  it('hides the Moodle push button without the push permission', () => {
    mockHasPermission.mockImplementation(
      (p: string) => p !== 'submissions:moodle_feedback_push',
    );
    renderPanel({ pendingCount: 0 });
    expect(
      screen.queryByTestId('moodle-push-button'),
    ).not.toBeInTheDocument();
  });

  it('hides the picker (and skips the fetch) without create_exams permission', async () => {
    mockHasPermission.mockReturnValue(false);
    renderPanel({ pendingCount: 0 });
    // Export still works…
    expect(
      screen.getByRole('button', { name: /Herunterladen/ }),
    ).toBeInTheDocument();
    // …but the picker is absent and no scheme/exam metadata is fetched.
    await waitFor(() =>
      expect(
        screen.queryByTestId('exam-grading-scheme-select'),
      ).not.toBeInTheDocument(),
    );
    expect(mockedListSchemes).not.toHaveBeenCalled();
    expect(mockedGetExam).not.toHaveBeenCalled();
  });
});
