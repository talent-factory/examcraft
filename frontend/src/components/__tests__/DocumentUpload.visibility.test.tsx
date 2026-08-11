/**
 * Tests for the upload visibility selector (TF-354, TF-620 'team' tier).
 *
 * Mocks react-i18next (t returns the key, interpolating {{institution}}),
 * useAuth, react-dropzone, DocumentService and OrgUnitsService so the
 * assertions don't depend on i18n initialisation, a live AuthProvider, or a
 * real network call for the caller's Org-Unit memberships.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { useDropzone } from 'react-dropzone';
import DocumentUpload from '../DocumentUpload';
import { DocumentService } from '../../services/DocumentService';
import { OrgUnitsService } from '../../services/orgUnitsService';
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

jest.mock('../../services/orgUnitsService');
const mockOrgUnitsService = OrgUnitsService as jest.Mocked<typeof OrgUnitsService>;

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
  // Default: caller has no Org-Unit memberships (Team radio stays disabled) —
  // matches the pre-TF-620 test baseline unless a test opts in below.
  mockOrgUnitsService.mine.mockResolvedValue({ items: [] });
});

describe('DocumentUpload visibility selector (TF-354/TF-620)', () => {
  it('renders three visibility options with private selected by default', () => {
    withInstitution();
    render(wrap(<DocumentUpload />));

    expect(screen.getByText('components.documentUpload.visibilityTitle')).toBeInTheDocument();

    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    expect(radios).toHaveLength(3);
    // Order: private, team, institution.
    expect(radios[0]).toBeChecked();
    expect(radios[1]).not.toBeChecked();
    expect(radios[2]).not.toBeChecked();
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
    expect(radios[2]).toBeDisabled();
  });

  it('disables the team option when the caller has no Org-Unit memberships', async () => {
    withInstitution();
    render(wrap(<DocumentUpload />));
    await waitFor(() => expect(mockOrgUnitsService.mine).toHaveBeenCalled());
    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    expect(radios[1]).toBeDisabled();
  });

  it('enables the team option and shows the Org-Unit picker once memberships load', async () => {
    withInstitution();
    mockOrgUnitsService.mine.mockResolvedValue({
      items: [
        {
          id: 42,
          parent_org_unit_id: null,
          unit_type: 'team',
          name: 'Backend',
          descendant_count: 0,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
    });
    render(wrap(<DocumentUpload />));

    await waitFor(() => {
      const radios = screen.getAllByRole('radio') as HTMLInputElement[];
      expect(radios[1]).not.toBeDisabled();
    });
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

    // Switch to institution visibility (index 2: private, team, institution).
    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    fireEvent.click(radios[2]);

    fireEvent.click(screen.getByText('components.documentUpload.startUpload'));

    await waitFor(() => {
      expect(mockDocumentService.uploadDocument).toHaveBeenCalledWith(
        file,
        DocumentVisibility.INSTITUTION,
        null,
      );
    });
  });

  it('sends the chosen Org-Unit id when uploading with team visibility', async () => {
    withInstitution();
    mockOrgUnitsService.mine.mockResolvedValue({
      items: [
        {
          id: 42,
          parent_org_unit_id: null,
          unit_type: 'team',
          name: 'Backend',
          descendant_count: 0,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
    });
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
    const onDrop = mockUseDropzone.mock.calls[0][0]!.onDrop as (files: File[]) => void;
    const file = createMockFile('test.pdf', 1024, 'application/pdf');
    onDrop([file]);

    await waitFor(() => {
      const radios = screen.getAllByRole('radio') as HTMLInputElement[];
      expect(radios[1]).not.toBeDisabled();
    });
    fireEvent.click((screen.getAllByRole('radio') as HTMLInputElement[])[1]);

    // Picker appears; pick the (only) Org-Unit.
    fireEvent.mouseDown(screen.getByText('components.documentUpload.orgUnitPickerPlaceholder'));
    fireEvent.click(screen.getByText('Backend'));

    fireEvent.click(screen.getByText('components.documentUpload.startUpload'));

    await waitFor(() => {
      expect(mockDocumentService.uploadDocument).toHaveBeenCalledWith(
        file,
        DocumentVisibility.TEAM,
        42,
      );
    });
  });
});
