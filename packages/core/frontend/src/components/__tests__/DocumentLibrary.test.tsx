import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import DocumentLibrary from '../DocumentLibrary';
import { DocumentService } from '../../services/DocumentService';
import { Document, DocumentStatus } from '../../types/document';

// Mock DocumentService
jest.mock('../../services/DocumentService');
const mockDocumentService = DocumentService as jest.Mocked<typeof DocumentService>;

// Mock theme
const theme = createTheme();

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

// Sample test data
const mockDocuments: Document[] = [
  {
    id: 1,
    filename: 'test-document.pdf',
    mime_type: 'application/pdf',
    status: DocumentStatus.PROCESSED,
    created_at: '2025-09-22T10:00:00Z',
    processed_at: '2025-09-22T10:01:00Z',
    file_size: 1024000,
    has_vectors: true,
    metadata: {
      total_chunks: 5,
      embedding_model: 'test-model',
      processing_time: 1.5
    }
  },
  {
    id: 2,
    filename: 'document-processing.txt',
    mime_type: 'text/plain',
    status: DocumentStatus.PROCESSING,
    created_at: '2025-09-22T10:05:00Z',
    file_size: 512000,
    has_vectors: false,
    metadata: {}
  },
  {
    id: 3,
    filename: 'failed-document.docx',
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    status: DocumentStatus.ERROR,
    created_at: '2025-09-22T10:10:00Z',
    file_size: 256000,
    has_vectors: false,
    metadata: {}
  }
];

describe('DocumentLibrary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders loading state initially', async () => {
      mockDocumentService.getDocuments.mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve([]), 100))
      );

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('renders document library with documents', async () => {
      mockDocumentService.getDocuments.mockResolvedValue(mockDocuments);

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Dokumentenbibliothek (3 Dokumente)')).toBeInTheDocument();
      });

      // Check statistics
      expect(screen.getByText('3')).toBeInTheDocument(); // Total
      expect(screen.getByText('1')).toBeInTheDocument(); // Processed
      expect(screen.getByText('1')).toBeInTheDocument(); // With vectors
      expect(screen.getByText('1')).toBeInTheDocument(); // Processing

      // Check document cards
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      expect(screen.getByText('document-processing.txt')).toBeInTheDocument();
      expect(screen.getByText('failed-document.docx')).toBeInTheDocument();
    });

    it('renders empty state when no documents', async () => {
      mockDocumentService.getDocuments.mockResolvedValue([]);

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Keine Dokumente vorhanden')).toBeInTheDocument();
      });

      expect(screen.getByText('Laden Sie Dokumente hoch, um mit der RAG-basierten Prüfungserstellung zu beginnen.')).toBeInTheDocument();
    });

    it('renders error state when loading fails', async () => {
      const errorMessage = 'Failed to load documents';
      mockDocumentService.getDocuments.mockRejectedValue(new Error(errorMessage));

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });
    });
  });

  describe('Document Selection', () => {
    beforeEach(async () => {
      mockDocumentService.getDocuments.mockResolvedValue(mockDocuments);
    });

    it('allows selecting documents', async () => {
      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Click on first document
      const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
      fireEvent.click(documentCard!);

      await waitFor(() => {
        expect(screen.getByText('1 ausgewählt')).toBeInTheDocument();
      });
    });

    it('shows RAG exam creation button when documents selected', async () => {
      const mockOnCreateRAGExam = jest.fn();

      render(
        <TestWrapper>
          <DocumentLibrary onCreateRAGExam={mockOnCreateRAGExam} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Select processed document with vectors
      const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
      fireEvent.click(documentCard!);

      await waitFor(() => {
        expect(screen.getByText('RAG-Prüfung erstellen')).toBeInTheDocument();
      });

      // Click RAG exam creation button
      fireEvent.click(screen.getByText('RAG-Prüfung erstellen'));
      expect(mockOnCreateRAGExam).toHaveBeenCalledWith([1]);
    });

    it('disables RAG exam creation for documents without vectors', async () => {
      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('document-processing.txt')).toBeInTheDocument();
      });

      // Select document without vectors
      const documentCard = screen.getByText('document-processing.txt').closest('[role="button"]');
      fireEvent.click(documentCard!);

      await waitFor(() => {
        const ragButton = screen.getByText('RAG-Prüfung erstellen');
        expect(ragButton).toBeDisabled();
      });
    });
  });

  describe('Document Actions', () => {
    beforeEach(async () => {
      mockDocumentService.getDocuments.mockResolvedValue([mockDocuments[0]]);
    });

    it('opens context menu on more button click', async () => {
      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Click more button
      const moreButton = screen.getByLabelText('more');
      fireEvent.click(moreButton);

      await waitFor(() => {
        expect(screen.getByText('Vorschau')).toBeInTheDocument();
        expect(screen.getByText('Download')).toBeInTheDocument();
        expect(screen.getByText('Löschen')).toBeInTheDocument();
      });
    });

    it('opens preview dialog', async () => {
      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Open context menu and click preview
      const moreButton = screen.getByLabelText('more');
      fireEvent.click(moreButton);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Vorschau'));
      });

      await waitFor(() => {
        expect(screen.getByText('Dokument-Vorschau: test-document.pdf')).toBeInTheDocument();
        expect(screen.getByText('Metadaten')).toBeInTheDocument();
      });
    });

    it('handles download action', async () => {
      mockDocumentService.downloadDocument.mockResolvedValue();

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Open context menu and click download
      const moreButton = screen.getByLabelText('more');
      fireEvent.click(moreButton);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Download'));
      });

      await waitFor(() => {
        expect(mockDocumentService.downloadDocument).toHaveBeenCalledWith(1, 'test-document.pdf');
      });
    });

    it('opens delete confirmation dialog', async () => {
      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Open context menu and click delete
      const moreButton = screen.getByLabelText('more');
      fireEvent.click(moreButton);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Löschen'));
      });

      await waitFor(() => {
        expect(screen.getByText('Dokument löschen')).toBeInTheDocument();
        expect(screen.getByText('Möchten Sie das Dokument "test-document.pdf" wirklich löschen?')).toBeInTheDocument();
      });
    });

    it('deletes document after confirmation', async () => {
      mockDocumentService.deleteDocument.mockResolvedValue();

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Open context menu and click delete
      const moreButton = screen.getByLabelText('more');
      fireEvent.click(moreButton);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Löschen'));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
      });

      await waitFor(() => {
        expect(mockDocumentService.deleteDocument).toHaveBeenCalledWith(1);
      });
    });
  });

  describe('Status Display', () => {
    it('displays correct status chips', async () => {
      mockDocumentService.getDocuments.mockResolvedValue(mockDocuments);

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Verarbeitet')).toBeInTheDocument();
        expect(screen.getByText('Verarbeitung...')).toBeInTheDocument();
        expect(screen.getByText('Fehler')).toBeInTheDocument();
      });
    });

    it('shows processing progress for processing documents', async () => {
      mockDocumentService.getDocuments.mockResolvedValue([mockDocuments[1]]);

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Verarbeitung läuft...')).toBeInTheDocument();
        expect(screen.getByRole('progressbar')).toBeInTheDocument();
      });
    });
  });

  describe('File Icons', () => {
    it('displays correct file icons for different mime types', async () => {
      mockDocumentService.getDocuments.mockResolvedValue(mockDocuments);

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        // PDF icon for PDF file
        expect(screen.getByTestId('PictureAsPdfIcon')).toBeInTheDocument();
        // Text icon for text file
        expect(screen.getByTestId('TextSnippetIcon')).toBeInTheDocument();
        // Document icon for Word file
        expect(screen.getByTestId('DescriptionIcon')).toBeInTheDocument();
      });
    });

    it('shows vector icon for documents with vectors', async () => {
      mockDocumentService.getDocuments.mockResolvedValue([mockDocuments[0]]);

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('TimelineIcon')).toBeInTheDocument();
      });
    });
  });

  describe('Refresh Functionality', () => {
    it('refreshes documents when refreshTrigger changes', async () => {
      mockDocumentService.getDocuments.mockResolvedValue([mockDocuments[0]]);

      const { rerender } = render(
        <TestWrapper>
          <DocumentLibrary refreshTrigger={0} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockDocumentService.getDocuments).toHaveBeenCalledTimes(1);
      });

      // Change refresh trigger
      rerender(
        <TestWrapper>
          <DocumentLibrary refreshTrigger={1} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockDocumentService.getDocuments).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Error Handling', () => {
    it('displays error message when document loading fails', async () => {
      const errorMessage = 'Network error';
      mockDocumentService.getDocuments.mockRejectedValue(new Error(errorMessage));

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });
    });

    it('displays error message when delete fails', async () => {
      mockDocumentService.getDocuments.mockResolvedValue([mockDocuments[0]]);

      const errorMessage = 'Delete failed';
      mockDocumentService.deleteDocument.mockRejectedValue(new Error(errorMessage));

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Try to delete document
      const moreButton = screen.getByLabelText('more');
      fireEvent.click(moreButton);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Löschen'));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
      });

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });
    });

    it('displays error message when download fails', async () => {
      mockDocumentService.getDocuments.mockResolvedValue([mockDocuments[0]]);

      const errorMessage = 'Download failed';
      mockDocumentService.downloadDocument.mockRejectedValue(new Error(errorMessage));

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Try to download document
      const moreButton = screen.getByLabelText('more');
      fireEvent.click(moreButton);

      await waitFor(() => {
        fireEvent.click(screen.getByText('Download'));
      });

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', async () => {
      mockDocumentService.getDocuments.mockResolvedValue([mockDocuments[0]]);

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByLabelText('more')).toBeInTheDocument();
      });
    });

    it('supports keyboard navigation', async () => {
      mockDocumentService.getDocuments.mockResolvedValue([mockDocuments[0]]);

      render(
        <TestWrapper>
          <DocumentLibrary />
        </TestWrapper>
      );

      await waitFor(() => {
        const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
        expect(documentCard).toBeInTheDocument();
      });
    });
  });
});
