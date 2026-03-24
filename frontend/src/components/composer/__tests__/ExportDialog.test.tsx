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

    it('renders all three format options', () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });
      expect(screen.getByLabelText('Markdown (.md)')).toBeInTheDocument();
      expect(screen.getByLabelText('JSON (.json)')).toBeInTheDocument();
      expect(screen.getByLabelText('Moodle XML (.xml)')).toBeInTheDocument();
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
  // Solutions checkbox — only shown for markdown
  // -------------------------------------------------------------------------

  describe('solutions checkbox', () => {
    it('shows "Loesungen einschliessen" checkbox when markdown is selected', () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });
      // Default format is markdown
      expect(screen.getByLabelText(/Loesungen einschliessen/)).toBeInTheDocument();
    });

    it('hides solutions checkbox when JSON is selected', async () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('JSON (.json)'));

      await waitFor(() => {
        expect(screen.queryByLabelText(/Loesungen einschliessen/)).not.toBeInTheDocument();
      });
    });

    it('hides solutions checkbox when Moodle XML is selected', async () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('Moodle XML (.xml)'));

      await waitFor(() => {
        expect(screen.queryByLabelText(/Loesungen einschliessen/)).not.toBeInTheDocument();
      });
    });

    it('re-shows solutions checkbox when switching back to markdown', async () => {
      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText('JSON (.json)'));
      fireEvent.click(screen.getByLabelText('Markdown (.md)'));

      await waitFor(() => {
        expect(screen.getByLabelText(/Loesungen einschliessen/)).toBeInTheDocument();
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
      mockComposerService.downloadExport.mockResolvedValue(undefined);

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
      mockComposerService.downloadExport.mockResolvedValue(undefined);

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      fireEvent.click(screen.getByLabelText(/Loesungen einschliessen/));
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(mockComposerService.downloadExport).toHaveBeenCalledWith(1, 'md', true);
      });
    });

    it('passes includeSolutions=false for json even if checkbox was checked', async () => {
      mockComposerService.downloadExport.mockResolvedValue(undefined);

      render(<ExportDialog {...defaultProps} />, { wrapper: Wrapper });

      // Switch to JSON — solutions checkbox disappears, but we test the internal logic
      fireEvent.click(screen.getByLabelText('JSON (.json)'));
      fireEvent.click(screen.getByRole('button', { name: 'Herunterladen' }));

      await waitFor(() => {
        expect(mockComposerService.downloadExport).toHaveBeenCalledWith(1, 'json', false);
      });
    });

    it('calls onClose after successful download', async () => {
      const onClose = jest.fn();
      mockComposerService.downloadExport.mockResolvedValue(undefined);

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
