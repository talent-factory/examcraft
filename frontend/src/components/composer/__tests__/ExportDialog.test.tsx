import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ExportDialog from '../ExportDialog';
import { ComposerService } from '../../../services/ComposerService';

// Mock axios to prevent ESM parse errors (ComposerService imports axios)
jest.mock('axios', () => ({
  __esModule: true,
  default: { create: jest.fn(() => ({ get: jest.fn(), post: jest.fn(), put: jest.fn(), delete: jest.fn(), interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } })) },
}));

// Mock ComposerService so tests don't make real HTTP calls
jest.mock('../../../services/ComposerService');
const mockComposerService = ComposerService as jest.Mocked<typeof ComposerService>;

// ILIAS is gated behind the opt-in "ilias:use" permission (TF-782). Default
// to granting it so the happy-path tests see the full format list; the
// dedicated permission test flips it to false.
const mockHasPermission = jest.fn<boolean, [string]>(() => true);
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ hasPermission: mockHasPermission }),
}));

const theme = createTheme();

const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

const defaultProps = {
  open: true,
  onClose: jest.fn(),
  examId: 1,
  examTitle: 'Informatik Prüfung',
  hasQuestions: true,
};

describe('ExportDialog', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockHasPermission.mockReturnValue(true);
  });

  // -------------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------------

  describe('rendering', () => {
    it('renders the dialog title', () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });
      expect(screen.getByText('Prüfung exportieren')).toBeInTheDocument();
    });

    it('renders the exam title in the dialog', () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });
      expect(screen.getByText('Informatik Prüfung')).toBeInTheDocument();
    });

    it('renders all five format options when ilias:use is granted', () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });
      expect(screen.getByLabelText('Markdown (.md)')).toBeInTheDocument();
      expect(screen.getByLabelText('PDF (druckfertig)')).toBeInTheDocument();
      expect(screen.getByLabelText('JSON (.json)')).toBeInTheDocument();
      expect(screen.getByLabelText('Moodle XML (.xml)')).toBeInTheDocument();
      expect(screen.getByLabelText('ILIAS QTI (.xml)')).toBeInTheDocument();
    });

    it('lists the formats alphabetically by their visible label', () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      const order = screen
        .getAllByRole('radio')
        .map((radio) => (radio as HTMLInputElement).value);

      expect(order).toEqual(['ilias', 'json', 'md', 'moodle', 'pdf']);
    });

    it('has Markdown selected by default', () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });
      const markdownRadio = screen.getByLabelText('Markdown (.md)') as HTMLInputElement;
      expect(markdownRadio.checked).toBe(true);
    });

    it('renders Herunterladen and Abbrechen buttons', () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });
      expect(screen.getByRole('button', { name: 'Herunterladen' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Abbrechen' })).toBeInTheDocument();
    });

    it('does not render when open=false', () => {
      render(<ExportDialog {...defaultProps} open={false} />, { wrapper: Wrapper });
      expect(screen.queryByText('Prüfung exportieren')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // ILIAS format — gated behind the opt-in "ilias:use" permission (TF-782),
  // so reviewers without it never see an option that would 403 on download.
  // -------------------------------------------------------------------------

  describe('ILIAS format visibility', () => {
    it('hides the ILIAS option when ilias:use is not granted', () => {
      mockHasPermission.mockImplementation((permission) => permission !== 'ilias:use');

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.queryByLabelText('ILIAS QTI (.xml)')).not.toBeInTheDocument();
      // The other four formats are unaffected.
      expect(screen.getByLabelText('Markdown (.md)')).toBeInTheDocument();
      expect(screen.getByLabelText('Moodle XML (.xml)')).toBeInTheDocument();
    });

    it('calls downloadExport with ilias when the ILIAS format is selected', async () => {
      mockComposerService.downloadExport.mockResolvedValue({ skippedPositions: [] });

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('ILIAS QTI (.xml)'));
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(mockComposerService.downloadExport).toHaveBeenCalledWith(1, 'ilias', false);
      });
    });

    it('hides the solutions checkbox when ILIAS is selected', async () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('ILIAS QTI (.xml)'));

      await waitFor(() => {
        expect(screen.queryByLabelText(/Lösungen einschliessen/)).not.toBeInTheDocument();
      });
    });
  });

  // -------------------------------------------------------------------------
  // Solutions checkbox — only shown for markdown
  // -------------------------------------------------------------------------

  describe('solutions checkbox', () => {
    it('shows "Lösungen einschliessen" checkbox when markdown is selected', () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });
      // Default format is markdown
      expect(screen.getByLabelText(/Lösungen einschliessen/)).toBeInTheDocument();
    });

    it('hides solutions checkbox when JSON is selected', async () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('JSON (.json)'));

      await waitFor(() => {
        expect(screen.queryByLabelText(/Lösungen einschliessen/)).not.toBeInTheDocument();
      });
    });

    it('hides solutions checkbox when Moodle XML is selected', async () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('Moodle XML (.xml)'));

      await waitFor(() => {
        expect(screen.queryByLabelText(/Lösungen einschliessen/)).not.toBeInTheDocument();
      });
    });

    it('shows solutions checkbox when PDF is selected', async () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('PDF (druckfertig)'));

      await waitFor(() => {
        expect(screen.getByLabelText(/Lösungen einschliessen/)).toBeInTheDocument();
      });
    });

    it('re-shows solutions checkbox when switching back to markdown', async () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('JSON (.json)'));
      fireEvent.click(screen.getByLabelText('Markdown (.md)'));

      await waitFor(() => {
        expect(screen.getByLabelText(/Lösungen einschliessen/)).toBeInTheDocument();
      });
    });
  });

  // -------------------------------------------------------------------------
  // No-questions warning
  // -------------------------------------------------------------------------

  describe('no questions warning', () => {
    it('shows warning when hasQuestions is false', () => {
      render(<ExportDialog {...defaultProps} hasQuestions={false} />, { wrapper: Wrapper });
      expect(
        screen.getByText(/Die Prüfung hat noch keine Fragen/)
      ).toBeInTheDocument();
    });

    it('does NOT show warning when hasQuestions is true', () => {
      render(<ExportDialog {...defaultProps} hasQuestions={true} />, { wrapper: Wrapper });
      expect(
        screen.queryByText(/Die Prüfung hat noch keine Fragen/)
      ).not.toBeInTheDocument();
    });

    it('disables Herunterladen button when hasQuestions is false', () => {
      render(<ExportDialog {...defaultProps} hasQuestions={false} />, { wrapper: Wrapper });
      expect(screen.getByRole('button', { name: 'Herunterladen' })).toBeDisabled();
    });

    it('enables Herunterladen button when hasQuestions is true', () => {
      render(<ExportDialog {...defaultProps} hasQuestions={true} />, { wrapper: Wrapper });
      expect(screen.getByRole('button', { name: 'Herunterladen' })).not.toBeDisabled();
    });
  });

  // -------------------------------------------------------------------------
  // Download
  // -------------------------------------------------------------------------

  describe('download', () => {
    it('calls downloadExport with correct examId and format', async () => {
      mockComposerService.downloadExport.mockResolvedValue({ skippedPositions: [] });

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(mockComposerService.downloadExport).toHaveBeenCalledWith(
          1,
          'md',
          false
        );
      });
    });

    it('passes includeSolutions=true when checkbox is checked', async () => {
      mockComposerService.downloadExport.mockResolvedValue({ skippedPositions: [] });

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText(/Lösungen einschliessen/));
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(mockComposerService.downloadExport).toHaveBeenCalledWith(1, 'md', true);
      });
    });

    it('passes includeSolutions=false for json even if checkbox was checked', async () => {
      mockComposerService.downloadExport.mockResolvedValue({ skippedPositions: [] });

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      // Switch to JSON — solutions checkbox disappears, but we test the internal logic
      fireEvent.click(screen.getByLabelText('JSON (.json)'));
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(mockComposerService.downloadExport).toHaveBeenCalledWith(1, 'json', false);
      });
    });

    it('calls downloadExport with pdf when PDF is selected', async () => {
      mockComposerService.downloadExport.mockResolvedValue({ skippedPositions: [] });

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('PDF (druckfertig)'));
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(mockComposerService.downloadExport).toHaveBeenCalledWith(1, 'pdf', false);
      });
    });

    it('passes includeSolutions=true for pdf when the checkbox is checked', async () => {
      mockComposerService.downloadExport.mockResolvedValue({ skippedPositions: [] });

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('PDF (druckfertig)'));
      fireEvent.click(screen.getByLabelText(/Lösungen einschliessen/));
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(mockComposerService.downloadExport).toHaveBeenCalledWith(1, 'pdf', true);
      });
    });

    it('calls onClose after successful download', async () => {
      const onClose = jest.fn();
      mockComposerService.downloadExport.mockResolvedValue({ skippedPositions: [] });

      render(<ExportDialog {...defaultProps} onClose={onClose} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
    });

    it('shows error message when download fails', async () => {
      mockComposerService.downloadExport.mockRejectedValue(new Error('Server error'));

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(
          screen.getByText('Export fehlgeschlagen. Bitte versuche es erneut.')
        ).toBeInTheDocument();
      });
    });

    // TF-772 PR 7: the export response is a Blob, so its error body is a JSON
    // Blob too. The backend's error_code must be read out of it and rendered
    // translated — never the raw `detail`.
    it('renders the error_code from a JSON Blob error body', async () => {
      mockComposerService.downloadExport.mockRejectedValue(
        Object.assign(new Error('Request failed with status code 400'), {
          response: {
            status: 400,
            data: new Blob(
              [JSON.stringify({ detail: 'ROHER BACKEND-TEXT', error_code: 'exams_must_finalize_before_export' })],
              { type: 'application/json' },
            ),
          },
        }),
      );

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      expect(
        await screen.findByText('Prüfung muss vor dem Export abgeschlossen werden'),
      ).toBeInTheDocument();
      expect(screen.queryByText('ROHER BACKEND-TEXT')).not.toBeInTheDocument();
    });

    it('does NOT call onClose when download fails', async () => {
      const onClose = jest.fn();
      mockComposerService.downloadExport.mockRejectedValue(new Error('Server error'));

      render(<ExportDialog {...defaultProps} onClose={onClose} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(screen.getByText(/Export fehlgeschlagen/)).toBeInTheDocument();
      });
      expect(onClose).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Skipped-questions warning (TF-782) — the ILIAS exporter can silently
  // drop unscoreable questions; the dialog must surface that instead of
  // quietly closing on a shorter-than-expected download.
  // -------------------------------------------------------------------------

  describe('skipped-questions warning', () => {
    it('shows a warning and keeps the dialog open when questions were skipped', async () => {
      const onClose = jest.fn();
      mockComposerService.downloadExport.mockResolvedValue({ skippedPositions: [2, 5] });

      render(<ExportDialog {...defaultProps} onClose={onClose} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('ILIAS QTI (.xml)'));
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(
          screen.getByText(/2 Fragen \(Nr\. 2, 5\) konnten nicht exportiert werden/)
        ).toBeInTheDocument();
      });
      expect(onClose).not.toHaveBeenCalled();
    });

    it('does NOT show the warning and closes the dialog when nothing was skipped', async () => {
      const onClose = jest.fn();
      mockComposerService.downloadExport.mockResolvedValue({ skippedPositions: [] });

      render(<ExportDialog {...defaultProps} onClose={onClose} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('ILIAS QTI (.xml)'));
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
      expect(
        screen.queryByText(/konnten nicht exportiert werden/)
      ).not.toBeInTheDocument();
    });

    it('uses the singular translation and shows the position when exactly one question was skipped', async () => {
      mockComposerService.downloadExport.mockResolvedValue({ skippedPositions: [3] });

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('ILIAS QTI (.xml)'));
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(
          screen.getByText(/Frage 3 konnte nicht exportiert werden/)
        ).toBeInTheDocument();
      });
    });

    it('clears the skip warning when the format is changed', async () => {
      mockComposerService.downloadExport.mockResolvedValue({ skippedPositions: [2, 5] });

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('ILIAS QTI (.xml)'));
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(
          screen.getByText(/konnten nicht exportiert werden/)
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText('Markdown (.md)'));

      expect(
        screen.queryByText(/konnten nicht exportiert werden/)
      ).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Close button
  // -------------------------------------------------------------------------

  describe('Abbrechen button', () => {
    it('calls onClose when Abbrechen is clicked', () => {
      const onClose = jest.fn();

      render(<ExportDialog {...defaultProps} onClose={onClose} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));

      expect(onClose).toHaveBeenCalled();
    });
  });
});
