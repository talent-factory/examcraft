import React from 'react';
import { act, render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import DocumentUpload from '../DocumentUpload';
import { DocumentService } from '../../services/DocumentService';
import { OrgUnitsService } from '../../services/orgUnitsService';
import { DocumentVisibility } from '../../types/document';
import { useDropzone } from 'react-dropzone';

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, email: 'test@example.com', role: 'institution_user' } }),
}));

jest.mock('../../services/DocumentService');
const mockDocumentService = DocumentService as jest.Mocked<typeof DocumentService>;

jest.mock('../../services/orgUnitsService');
const mockOrgUnitsService = OrgUnitsService as jest.Mocked<typeof OrgUnitsService>;

jest.mock('react-dropzone', () => ({ useDropzone: jest.fn() }));
const mockUseDropzone = useDropzone as jest.MockedFunction<typeof useDropzone>;

const theme = createTheme();
const wrap = (ui: React.ReactElement) => <ThemeProvider theme={theme}>{ui}</ThemeProvider>;

/**
 * DocumentUpload tests: queue, upload flow, callbacks and statistics. The
 * suite sat on `describe.skip` until TF-1057. Two neighbours cover the rest
 * and are not repeated here: DocumentUpload.cancellation.test.tsx (cancel and
 * the UploadCancelled sentinel, including AppError translation) and
 * DocumentUpload.visibility.test.tsx (the visibility selector).
 *
 * react-dropzone is mocked; files enter the queue through the `onDrop`
 * callback the component hands to `useDropzone`.
 */

function dropzoneState(isDragActive = false): ReturnType<typeof useDropzone> {
  return {
    getRootProps: jest.fn().mockReturnValue({}),
    getInputProps: jest.fn().mockReturnValue({}),
    isDragActive,
    acceptedFiles: [],
    fileRejections: [],
    isFocused: false,
    isDragAccept: false,
    isDragReject: false,
    open: jest.fn(),
  } as unknown as ReturnType<typeof useDropzone>;
}

const createMockFile = (name: string, size: number, type: string): File => {
  const file = new File(['content'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

function dropFiles(...files: File[]): void {
  const onDrop = mockUseDropzone.mock.calls[0][0]!.onDrop!;
  act(() => {
    onDrop(files, [], {} as never);
  });
}

const uploadOk = (documentId = 1, filename = 'test.pdf') => ({
  document_id: documentId,
  filename,
  message: 'Upload successful',
});

const startUpload = () => fireEvent.click(screen.getByRole('button', { name: 'Upload starten' }));

/** The queue row (list item) that shows `filename`. */
const rowOf = (filename: string) =>
  // eslint-disable-next-line testing-library/no-node-access
  screen.getByText(filename).closest('li') as HTMLElement;

describe('DocumentUpload', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockOrgUnitsService.mine.mockResolvedValue({ items: [] });
    mockUseDropzone.mockReturnValue(dropzoneState());
    mockDocumentService.processDocument.mockResolvedValue({
      message: 'Processing started',
      document_id: 1,
    });
  });

  describe('Drop zone', () => {
    it('renders title, hint and the configured formats and file limit', () => {
      render(wrap(<DocumentUpload maxFiles={5} acceptedFileTypes={['.pdf', '.txt']} />));

      expect(screen.getByText('Dokumente hochladen')).toBeInTheDocument();
      expect(screen.getByText('Zieh Dateien hierher oder klicke zum Auswählen')).toBeInTheDocument();
      expect(screen.getByText('Unterstützte Formate: .pdf, .txt • Max. 5 Dateien')).toBeInTheDocument();
      expect(mockUseDropzone).toHaveBeenCalledWith(expect.objectContaining({ maxFiles: 5, multiple: true }));
    });

    it('switches the title while files are dragged over it', () => {
      mockUseDropzone.mockReturnValue(dropzoneState(true));

      render(wrap(<DocumentUpload />));

      expect(screen.getByText('Dateien hier ablegen...')).toBeInTheDocument();
      expect(screen.queryByText('Dokumente hochladen')).not.toBeInTheDocument();
    });
  });

  describe('Upload queue', () => {
    it('lists dropped files with type icon and size', () => {
      render(wrap(<DocumentUpload />));

      dropFiles(
        createMockFile('large.pdf', 1024 * 1024, 'application/pdf'),
        createMockFile('notes.txt', 1536, 'text/plain'),
        createMockFile('word.docx', 2048, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
      );

      expect(screen.getByText('Upload-Warteschlange (3)')).toBeInTheDocument();
      expect(within(rowOf('large.pdf')).getByTestId('PictureAsPdfIcon')).toBeInTheDocument();
      expect(within(rowOf('large.pdf')).getByText('1 MB')).toBeInTheDocument();
      expect(within(rowOf('notes.txt')).getByTestId('TextSnippetIcon')).toBeInTheDocument();
      expect(within(rowOf('notes.txt')).getByText('1.5 KB')).toBeInTheDocument();
      expect(within(rowOf('word.docx')).getByTestId('DescriptionIcon')).toBeInTheDocument();
      expect(within(rowOf('word.docx')).getByText('Wartend')).toBeInTheDocument();
    });

    it('caps the queue at maxFiles', () => {
      render(wrap(<DocumentUpload maxFiles={2} />));

      dropFiles(
        createMockFile('a.pdf', 10, 'application/pdf'),
        createMockFile('b.pdf', 10, 'application/pdf'),
        createMockFile('c.pdf', 10, 'application/pdf'),
      );

      expect(screen.getByText('Upload-Warteschlange (2)')).toBeInTheDocument();
      expect(screen.queryByText('c.pdf')).not.toBeInTheDocument();
    });

    it('removes a single file from the queue', () => {
      render(wrap(<DocumentUpload />));
      dropFiles(createMockFile('keep.pdf', 10, 'application/pdf'), createMockFile('drop.pdf', 10, 'application/pdf'));

      fireEvent.click(within(rowOf('drop.pdf')).getByTitle('Entfernen'));

      expect(screen.queryByText('drop.pdf')).not.toBeInTheDocument();
      expect(screen.getByText('keep.pdf')).toBeInTheDocument();
      expect(screen.getByText('Upload-Warteschlange (1)')).toBeInTheDocument();
    });

    it('clears the whole queue', () => {
      render(wrap(<DocumentUpload />));
      dropFiles(createMockFile('a.pdf', 10, 'application/pdf'), createMockFile('b.txt', 10, 'text/plain'));

      fireEvent.click(screen.getByRole('button', { name: 'Alle entfernen' }));

      expect(screen.queryByText('a.pdf')).not.toBeInTheDocument();
      expect(screen.queryByText('b.txt')).not.toBeInTheDocument();
      expect(screen.queryByText(/Upload-Warteschlange/)).not.toBeInTheDocument();
    });
  });

  describe('Upload flow', () => {
    it('uploads, starts processing and reports completion', async () => {
      mockDocumentService.uploadDocument.mockResolvedValue(uploadOk(7, 'test.pdf'));
      const onUploadComplete = jest.fn();
      const onAllUploadsComplete = jest.fn();
      const file = createMockFile('test.pdf', 1024, 'application/pdf');

      render(wrap(
        <DocumentUpload onUploadComplete={onUploadComplete} onAllUploadsComplete={onAllUploadsComplete} />
      ));
      dropFiles(file);
      startUpload();

      expect(await within(rowOf('test.pdf')).findByText('Abgeschlossen')).toBeInTheDocument();
      expect(mockDocumentService.uploadDocument).toHaveBeenCalledWith(file, DocumentVisibility.PRIVATE, null);
      expect(mockDocumentService.processDocument).toHaveBeenCalledWith(7, true);
      expect(onUploadComplete).toHaveBeenCalledWith(7, 'test.pdf');
      await waitFor(() => expect(onAllUploadsComplete).toHaveBeenCalledTimes(1));
      expect(screen.getByText('Upload abgeschlossen')).toBeInTheDocument();
      expect(screen.getByText('1 von 1 Dateien erfolgreich hochgeladen und verarbeitet')).toBeInTheDocument();
      // Nothing left to upload: the start button is disabled.
      expect(screen.getByRole('button', { name: 'Upload starten' })).toBeDisabled();
    });

    it('uploads several files one after another', async () => {
      const order: string[] = [];
      mockDocumentService.uploadDocument.mockImplementation(async (file: File) => {
        order.push(`start ${file.name}`);
        await Promise.resolve();
        order.push(`end ${file.name}`);
        return uploadOk(1, file.name);
      });

      render(wrap(<DocumentUpload />));
      dropFiles(createMockFile('one.pdf', 10, 'application/pdf'), createMockFile('two.pdf', 10, 'application/pdf'));
      startUpload();

      await screen.findByText('Upload abgeschlossen');
      expect(order).toEqual(['start one.pdf', 'end one.pdf', 'start two.pdf', 'end two.pdf']);
      expect(screen.getByText('2 von 2 Dateien erfolgreich hochgeladen und verarbeitet')).toBeInTheDocument();
    });

    it('shows the processing hint while the backend call is still running', async () => {
      mockDocumentService.uploadDocument.mockResolvedValue(uploadOk());
      mockDocumentService.processDocument.mockImplementation(() => new Promise(() => {}));

      render(wrap(<DocumentUpload />));
      dropFiles(createMockFile('test.pdf', 10, 'application/pdf'));
      startUpload();

      expect(await screen.findByText(/Dokumente werden verarbeitet/)).toBeInTheDocument();
      expect(within(rowOf('test.pdf')).getByText('Verarbeitung...')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Uploading...' })).toBeDisabled();
    });
  });

  describe('Errors and retry', () => {
    it('marks a failed file, reports the translated fallback and counts it', async () => {
      mockDocumentService.uploadDocument.mockRejectedValue(new Error('socket hang up'));
      const onUploadError = jest.fn();

      render(wrap(<DocumentUpload onUploadError={onUploadError} />));
      dropFiles(createMockFile('test.pdf', 10, 'application/pdf'));
      startUpload();

      const row = rowOf('test.pdf');
      expect(await within(row).findByText('Upload fehlgeschlagen')).toBeInTheDocument();
      expect(within(row).getByText('Fehler')).toBeInTheDocument();
      expect(screen.queryByText(/socket hang up/)).not.toBeInTheDocument();
      expect(onUploadError).toHaveBeenCalledWith('test.pdf', 'Upload fehlgeschlagen');
      expect(mockDocumentService.processDocument).not.toHaveBeenCalled();
      expect(await screen.findByText(/0 von 1 Dateien .* • 1 Fehler/)).toBeInTheDocument();
    });

    it('retries a failed file', async () => {
      mockDocumentService.uploadDocument
        .mockRejectedValueOnce(new Error('Upload failed'))
        .mockResolvedValueOnce(uploadOk());

      render(wrap(<DocumentUpload />));
      dropFiles(createMockFile('test.pdf', 10, 'application/pdf'));
      startUpload();

      const retry = await within(rowOf('test.pdf')).findByTitle('Erneut versuchen');
      await waitFor(() => expect(retry).toBeEnabled());
      fireEvent.click(retry);

      expect(await within(rowOf('test.pdf')).findByText('Abgeschlossen')).toBeInTheDocument();
      expect(mockDocumentService.uploadDocument).toHaveBeenCalledTimes(2);
      expect(screen.queryByText('Upload fehlgeschlagen')).not.toBeInTheDocument();
    });
  });
});
