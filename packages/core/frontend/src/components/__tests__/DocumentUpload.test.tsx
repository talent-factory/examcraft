import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import DocumentUpload from '../DocumentUpload';
import { DocumentService } from '../../services/DocumentService';

// Mock DocumentService
jest.mock('../../services/DocumentService');
const mockDocumentService = DocumentService as jest.Mocked<typeof DocumentService>;

// Mock react-dropzone
jest.mock('react-dropzone', () => ({
  useDropzone: jest.fn()
}));

import { useDropzone } from 'react-dropzone';
const mockUseDropzone = useDropzone as jest.MockedFunction<typeof useDropzone>;

// Mock theme
const theme = createTheme();

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    {children}
  </ThemeProvider>
);

// Mock file
const createMockFile = (name: string, size: number, type: string): File => {
  const file = new File(['test content'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

describe('DocumentUpload', () => {
  const mockGetRootProps = jest.fn();
  const mockGetInputProps = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    mockUseDropzone.mockReturnValue({
      getRootProps: mockGetRootProps,
      getInputProps: mockGetInputProps,
      isDragActive: false,
      acceptedFiles: [],
      fileRejections: [],
      isFocused: false,
      isDragAccept: false,
      isDragReject: false,
      open: jest.fn()
    });

    mockGetRootProps.mockReturnValue({});
    mockGetInputProps.mockReturnValue({});
  });

  describe('Rendering', () => {
    it('renders upload area with correct text', () => {
      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      expect(screen.getByText('Dokumente hochladen')).toBeInTheDocument();
      expect(screen.getByText('Ziehen Sie Dateien hierher oder klicken Sie zum Auswählen')).toBeInTheDocument();
      expect(screen.getByText(/Unterstützte Formate:/)).toBeInTheDocument();
    });

    it('shows drag active state', () => {
      mockUseDropzone.mockReturnValue({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: true,
        acceptedFiles: [],
        fileRejections: [],
        isFocused: false,
        isDragAccept: false,
        isDragReject: false,
        open: jest.fn()
      });

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      expect(screen.getByText('Dateien hier ablegen...')).toBeInTheDocument();
    });

    it('renders with custom props', () => {
      render(
        <TestWrapper>
          <DocumentUpload 
            maxFiles={5}
            acceptedFileTypes={['.pdf', '.txt']}
          />
        </TestWrapper>
      );

      expect(screen.getByText(/Max\. 5 Dateien/)).toBeInTheDocument();
    });
  });

  describe('File Upload Queue', () => {
    it('shows upload queue when files are added', () => {
      const { rerender } = render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      // Simulate files being added
      const mockFiles = [
        createMockFile('test1.pdf', 1024, 'application/pdf'),
        createMockFile('test2.txt', 512, 'text/plain')
      ];

      // Mock the onDrop callback
      const mockOnDrop = jest.fn();
      mockUseDropzone.mockReturnValue({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: mockFiles,
        fileRejections: [],
        isFocused: false,
        isDragAccept: false,
        isDragReject: false,
        open: jest.fn()
      });

      // Trigger the onDrop callback manually
      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      rerender(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      expect(screen.getByText('Upload-Warteschlange (2)')).toBeInTheDocument();
      expect(screen.getByText('test1.pdf')).toBeInTheDocument();
      expect(screen.getByText('test2.txt')).toBeInTheDocument();
    });

    it('shows correct file icons for different file types', () => {
      const mockFiles = [
        createMockFile('document.pdf', 1024, 'application/pdf'),
        createMockFile('text.txt', 512, 'text/plain'),
        createMockFile('word.docx', 2048, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
      ];

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      // Simulate adding files
      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      expect(screen.getByTestId('PictureAsPdfIcon')).toBeInTheDocument();
      expect(screen.getByTestId('TextSnippetIcon')).toBeInTheDocument();
      expect(screen.getByTestId('DescriptionIcon')).toBeInTheDocument();
    });

    it('displays file sizes correctly', () => {
      const mockFiles = [
        createMockFile('large.pdf', 1024000, 'application/pdf'), // 1 MB
        createMockFile('small.txt', 1024, 'text/plain') // 1 KB
      ];

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      expect(screen.getByText('1 MB')).toBeInTheDocument();
      expect(screen.getByText('1 KB')).toBeInTheDocument();
    });
  });

  describe('Upload Process', () => {
    it('starts upload process when button is clicked', async () => {
      mockDocumentService.uploadDocument.mockResolvedValue({
        document_id: 1,
        filename: 'test.pdf',
        message: 'Upload successful'
      });

      mockDocumentService.processDocument.mockResolvedValue({
        message: 'Processing successful',
        document_id: 1,
        processing_stats: {
          total_chunks: 5,
          embedding_dimension: 384,
          model_name: 'test-model',
          processing_time: 1.5
        }
      });

      const mockFiles = [createMockFile('test.pdf', 1024, 'application/pdf')];

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      // Add files
      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      // Start upload
      const uploadButton = screen.getByText('Upload starten');
      fireEvent.click(uploadButton);

      await waitFor(() => {
        expect(mockDocumentService.uploadDocument).toHaveBeenCalledWith(mockFiles[0]);
      });

      await waitFor(() => {
        expect(mockDocumentService.processDocument).toHaveBeenCalledWith(1, true);
      });
    });

    it('shows upload progress', async () => {
      mockDocumentService.uploadDocument.mockImplementation(
        () => new Promise(resolve => 
          setTimeout(() => resolve({
            document_id: 1,
            filename: 'test.pdf',
            message: 'Upload successful'
          }), 100)
        )
      );

      mockDocumentService.processDocument.mockResolvedValue({
        message: 'Processing successful',
        document_id: 1
      });

      const mockFiles = [createMockFile('test.pdf', 1024, 'application/pdf')];

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      const uploadButton = screen.getByText('Upload starten');
      fireEvent.click(uploadButton);

      // Should show uploading state
      await waitFor(() => {
        expect(screen.getByText('Upload...')).toBeInTheDocument();
      });
    });

    it('shows completed status after successful upload', async () => {
      mockDocumentService.uploadDocument.mockResolvedValue({
        document_id: 1,
        filename: 'test.pdf',
        message: 'Upload successful'
      });

      mockDocumentService.processDocument.mockResolvedValue({
        message: 'Processing successful',
        document_id: 1
      });

      const mockFiles = [createMockFile('test.pdf', 1024, 'application/pdf')];

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      const uploadButton = screen.getByText('Upload starten');
      fireEvent.click(uploadButton);

      await waitFor(() => {
        expect(screen.getByText('Abgeschlossen')).toBeInTheDocument();
      });
    });

    it('handles upload errors', async () => {
      const errorMessage = 'Upload failed';
      mockDocumentService.uploadDocument.mockRejectedValue(new Error(errorMessage));

      const mockFiles = [createMockFile('test.pdf', 1024, 'application/pdf')];

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      const uploadButton = screen.getByText('Upload starten');
      fireEvent.click(uploadButton);

      await waitFor(() => {
        expect(screen.getByText('Fehler')).toBeInTheDocument();
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });
    });
  });

  describe('File Management', () => {
    it('allows removing files from queue', () => {
      const mockFiles = [createMockFile('test.pdf', 1024, 'application/pdf')];

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      expect(screen.getByText('test.pdf')).toBeInTheDocument();

      // Remove file
      const deleteButton = screen.getByLabelText('delete');
      fireEvent.click(deleteButton);

      expect(screen.queryByText('test.pdf')).not.toBeInTheDocument();
    });

    it('allows retrying failed uploads', async () => {
      mockDocumentService.uploadDocument
        .mockRejectedValueOnce(new Error('Upload failed'))
        .mockResolvedValueOnce({
          document_id: 1,
          filename: 'test.pdf',
          message: 'Upload successful'
        });

      mockDocumentService.processDocument.mockResolvedValue({
        message: 'Processing successful',
        document_id: 1
      });

      const mockFiles = [createMockFile('test.pdf', 1024, 'application/pdf')];

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      // Start upload (will fail)
      const uploadButton = screen.getByText('Upload starten');
      fireEvent.click(uploadButton);

      await waitFor(() => {
        expect(screen.getByText('Fehler')).toBeInTheDocument();
      });

      // Retry upload
      const retryButton = screen.getByLabelText('refresh');
      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText('Abgeschlossen')).toBeInTheDocument();
      });
    });

    it('clears all files when clear button is clicked', () => {
      const mockFiles = [
        createMockFile('test1.pdf', 1024, 'application/pdf'),
        createMockFile('test2.txt', 512, 'text/plain')
      ];

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      expect(screen.getByText('test1.pdf')).toBeInTheDocument();
      expect(screen.getByText('test2.txt')).toBeInTheDocument();

      // Clear all files
      const clearButton = screen.getByText('Alle entfernen');
      fireEvent.click(clearButton);

      expect(screen.queryByText('test1.pdf')).not.toBeInTheDocument();
      expect(screen.queryByText('test2.txt')).not.toBeInTheDocument();
    });
  });

  describe('Upload Statistics', () => {
    it('displays upload statistics', async () => {
      mockDocumentService.uploadDocument.mockResolvedValue({
        document_id: 1,
        filename: 'test.pdf',
        message: 'Upload successful'
      });

      mockDocumentService.processDocument.mockResolvedValue({
        message: 'Processing successful',
        document_id: 1
      });

      const mockFiles = [
        createMockFile('test1.pdf', 1024, 'application/pdf'),
        createMockFile('test2.txt', 512, 'text/plain')
      ];

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      const uploadButton = screen.getByText('Upload starten');
      fireEvent.click(uploadButton);

      await waitFor(() => {
        expect(screen.getByText('Upload-Statistiken')).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument(); // Total
        expect(screen.getByText('Gesamt')).toBeInTheDocument();
      });
    });

    it('shows success summary after upload completion', async () => {
      mockDocumentService.uploadDocument.mockResolvedValue({
        document_id: 1,
        filename: 'test.pdf',
        message: 'Upload successful'
      });

      mockDocumentService.processDocument.mockResolvedValue({
        message: 'Processing successful',
        document_id: 1
      });

      const mockOnAllUploadsComplete = jest.fn();
      const mockFiles = [createMockFile('test.pdf', 1024, 'application/pdf')];

      render(
        <TestWrapper>
          <DocumentUpload onAllUploadsComplete={mockOnAllUploadsComplete} />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      const uploadButton = screen.getByText('Upload starten');
      fireEvent.click(uploadButton);

      await waitFor(() => {
        expect(screen.getByText('Upload abgeschlossen')).toBeInTheDocument();
        expect(mockOnAllUploadsComplete).toHaveBeenCalled();
      });
    });
  });

  describe('Callbacks', () => {
    it('calls onUploadComplete callback', async () => {
      const mockOnUploadComplete = jest.fn();
      
      mockDocumentService.uploadDocument.mockResolvedValue({
        document_id: 1,
        filename: 'test.pdf',
        message: 'Upload successful'
      });

      mockDocumentService.processDocument.mockResolvedValue({
        message: 'Processing successful',
        document_id: 1
      });

      const mockFiles = [createMockFile('test.pdf', 1024, 'application/pdf')];

      render(
        <TestWrapper>
          <DocumentUpload onUploadComplete={mockOnUploadComplete} />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      const uploadButton = screen.getByText('Upload starten');
      fireEvent.click(uploadButton);

      await waitFor(() => {
        expect(mockOnUploadComplete).toHaveBeenCalledWith(1, 'test.pdf');
      });
    });

    it('calls onUploadError callback', async () => {
      const mockOnUploadError = jest.fn();
      const errorMessage = 'Upload failed';
      
      mockDocumentService.uploadDocument.mockRejectedValue(new Error(errorMessage));

      const mockFiles = [createMockFile('test.pdf', 1024, 'application/pdf')];

      render(
        <TestWrapper>
          <DocumentUpload onUploadError={mockOnUploadError} />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      const uploadButton = screen.getByText('Upload starten');
      fireEvent.click(uploadButton);

      await waitFor(() => {
        expect(mockOnUploadError).toHaveBeenCalledWith('test.pdf', errorMessage);
      });
    });
  });

  describe('Processing Info', () => {
    it('shows processing info when documents are being processed', async () => {
      mockDocumentService.uploadDocument.mockResolvedValue({
        document_id: 1,
        filename: 'test.pdf',
        message: 'Upload successful'
      });

      mockDocumentService.processDocument.mockImplementation(
        () => new Promise(resolve => 
          setTimeout(() => resolve({
            message: 'Processing successful',
            document_id: 1
          }), 100)
        )
      );

      const mockFiles = [createMockFile('test.pdf', 1024, 'application/pdf')];

      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      const uploadButton = screen.getByText('Upload starten');
      fireEvent.click(uploadButton);

      await waitFor(() => {
        expect(screen.getByText(/Dokumente werden verarbeitet/)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(
        <TestWrapper>
          <DocumentUpload />
        </TestWrapper>
      );

      const mockFiles = [createMockFile('test.pdf', 1024, 'application/pdf')];
      const onDropCallback = mockUseDropzone.mock.calls[0][0].onDrop;
      onDropCallback(mockFiles);

      expect(screen.getByLabelText('delete')).toBeInTheDocument();
    });
  });
});
