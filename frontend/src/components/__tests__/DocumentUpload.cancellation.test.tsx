/**
 * Focused regression coverage for the `UploadCancelled` sentinel (TF-772
 * PR 2), which replaced `error.message.includes('cancel')` in
 * `DocumentUpload.tsx`'s catch block.
 *
 * Deliberately a separate, un-skipped file rather than an addition to
 * `DocumentUpload.test.tsx` — that whole suite is `describe.skip` for
 * pre-existing reasons (dropzone-mocking complexity, UI churn) unrelated to
 * error handling; see its own header comment. Reuses the same
 * `useDropzone`/`DocumentService` mocking pattern as that file.
 */
import React from 'react';
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import DocumentUpload from '../DocumentUpload';
import { DocumentService } from '../../services/DocumentService';
import { OrgUnitsService } from '../../services/orgUnitsService';
// Not from DocumentService — that module is automocked below, so its
// AppError re-export would be a mock. The real AppError is what
// translateError() actually branches on.
import { AppError } from '../../errors';
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

const createMockFile = (name: string, type: string): File =>
  new File(['content'], name, { type });

beforeEach(() => {
  jest.clearAllMocks();
  mockOrgUnitsService.mine.mockResolvedValue({ items: [] });
  mockUseDropzone.mockReturnValue({
    getRootProps: jest.fn().mockReturnValue({}),
    getInputProps: jest.fn().mockReturnValue({}),
    isDragActive: false,
    acceptedFiles: [],
    fileRejections: [],
    isFocused: false,
    isDragAccept: false,
    isDragReject: false,
    open: jest.fn(),
  } as unknown as ReturnType<typeof useDropzone>);
});

/** Adds one file to the upload queue the same way the skipped suite does. */
function dropFile(name = 'report.pdf', type = 'application/pdf'): File {
  const file = createMockFile(name, type);
  const onDropCallback = mockUseDropzone.mock.calls[0][0]!.onDrop!;
  act(() => {
    onDropCallback([file], [], {} as never);
  });
  return file;
}

describe('DocumentUpload cancellation sentinel', () => {
  it('does not swallow a genuine upload error that arrives after the user clicked Cancel', async () => {
    // Upload never resolves on its own — we control exactly when/how it
    // settles, so we can land the rejection *after* Cancel has already
    // flipped the AbortController's flag.
    let rejectUpload!: (err: unknown) => void;
    mockDocumentService.uploadDocument.mockImplementation(
      () =>
        new Promise((_resolve, reject) => {
          rejectUpload = reject;
        }),
    );

    const onUploadError = jest.fn();
    render(wrap(<DocumentUpload onUploadError={onUploadError} />));

    dropFile();
    fireEvent.click(await screen.findByText('Upload starten'));

    // Wait for the file to reach 'uploading' (its Cancel icon button renders).
    const cancelButton = await screen.findByTitle('Upload abbrechen');
    fireEvent.click(cancelButton);

    // The optimistic UI already marked the item 'cancelled'...
    expect(await screen.findByText('Vom Benutzer abgebrochen')).toBeInTheDocument();

    // ...but the in-flight request the user tried to cancel actually fails
    // for a real, unrelated reason (the signal is not wired into fetch, so
    // this is a genuine race, not a hypothetical one).
    act(() => {
      rejectUpload(new AppError('documents_upload_failed', 'Speicher voll', 507));
    });

    // The real failure must be reported, not silently absorbed as a
    // cancellation.
    await waitFor(() => {
      expect(onUploadError).toHaveBeenCalledWith(
        'report.pdf',
        'Dokument-Upload fehlgeschlagen',
      );
    });
    expect(await screen.findByText('Dokument-Upload fehlgeschlagen')).toBeInTheDocument();
  });

  it('still treats an unresolved-but-aborted upload as a cancellation, not an error', async () => {
    // The "happy" cancellation path: the abort check inside uploadSingleFile
    // fires before the awaited call ever resolves or rejects.
    mockDocumentService.uploadDocument.mockImplementation(
      () => new Promise(() => {}), // never settles within this test
    );

    const onUploadError = jest.fn();
    render(wrap(<DocumentUpload onUploadError={onUploadError} />));

    dropFile('never-finishes.pdf');
    fireEvent.click(await screen.findByText('Upload starten'));

    const cancelButton = await screen.findByTitle('Upload abbrechen');
    fireEvent.click(cancelButton);

    expect(await screen.findByText('Vom Benutzer abgebrochen')).toBeInTheDocument();
    expect(onUploadError).not.toHaveBeenCalled();
  });
});
