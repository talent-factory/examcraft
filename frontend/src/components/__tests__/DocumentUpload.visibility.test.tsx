/**
 * Tests for the upload visibility selector (TF-354).
 *
 * Mocks react-i18next (t returns the key, interpolating {{institution}}),
 * useAuth, react-dropzone and DocumentService so the assertions don't depend
 * on i18n initialisation or a live AuthProvider.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { useDropzone } from 'react-dropzone';
import DocumentUpload from '../DocumentUpload';
import { DocumentService } from '../../services/DocumentService';
import { DocumentVisibility } from '../../types/document';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: unknown) =>
      opts && typeof opts === 'object' && 'institution' in opts
        ? `${key}:${(opts as Record<string, unknown>).institution}`
        : key,
    i18n: { language: 'de' },
  }),
}));

const mockUseAuth = jest.fn();
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock('../../services/DocumentService');
const mockDocumentService = DocumentService as jest.Mocked<typeof DocumentService>;

jest.mock('react-dropzone', () => ({ useDropzone: jest.fn() }));
const mockUseDropzone = useDropzone as jest.MockedFunction<typeof useDropzone>;

const theme = createTheme();
const wrap = (ui: React.ReactElement) => <ThemeProvider theme={theme}>{ui}</ThemeProvider>;

const createMockFile = (name: string, size: number, type: string): File => {
  const file = new File(['content'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

const withInstitution = () =>
  mockUseAuth.mockReturnValue({
    user: { id: 1, institution_id: 7, institution: { id: 7, name: 'Test University' } },
  });

const withoutInstitution = () =>
  mockUseAuth.mockReturnValue({ user: { id: 1, institution_id: null, institution: null } });

beforeEach(() => {
  jest.clearAllMocks();
  mockUseDropzone.mockReturnValue({
    getRootProps: jest.fn(() => ({})),
    getInputProps: jest.fn(() => ({})),
    isDragActive: false,
    acceptedFiles: [],
    fileRejections: [],
    isFocused: false,
    isDragAccept: false,
    isDragReject: false,
    open: jest.fn(),
  } as ReturnType<typeof useDropzone>);
});

describe('DocumentUpload visibility selector (TF-354)', () => {
  it('renders both visibility options with private selected by default', () => {
    withInstitution();
    render(wrap(<DocumentUpload />));

    expect(screen.getByText('components.documentUpload.visibilityTitle')).toBeInTheDocument();

    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    expect(radios).toHaveLength(2);
    // First radio = private, checked by default.
    expect(radios[0]).toBeChecked();
    expect(radios[1]).not.toBeChecked();
  });

  it('interpolates the institution name into the institution option label', () => {
    withInstitution();
    render(wrap(<DocumentUpload />));
    expect(
      screen.getByText('components.documentUpload.visibilityInstitution:Test University'),
    ).toBeInTheDocument();
  });

  it('disables the institution option when the user has no institution', () => {
    withoutInstitution();
    render(wrap(<DocumentUpload />));
    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    expect(radios[1]).toBeDisabled();
  });

  it('sends the selected visibility to the upload service', async () => {
    withInstitution();
    mockDocumentService.uploadDocument.mockResolvedValue({
      document_id: 1,
      filename: 'test.pdf',
      message: 'ok',
    });
    mockDocumentService.processDocument.mockResolvedValue({
      message: 'ok',
      document_id: 1,
    });

    render(wrap(<DocumentUpload />));

    // Queue a file via the dropzone onDrop callback.
    const onDrop = mockUseDropzone.mock.calls[0][0]!.onDrop as (files: File[]) => void;
    const file = createMockFile('test.pdf', 1024, 'application/pdf');
    onDrop([file]);

    // Switch to institution visibility.
    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    fireEvent.click(radios[1]);

    fireEvent.click(screen.getByText('components.documentUpload.startUpload'));

    await waitFor(() => {
      expect(mockDocumentService.uploadDocument).toHaveBeenCalledWith(
        file,
        DocumentVisibility.INSTITUTION,
      );
    });
  });
});
