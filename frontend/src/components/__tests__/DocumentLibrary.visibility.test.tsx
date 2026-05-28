/**
 * Tests for the document-card visibility icon + quick-edit dialog (TF-354).
 *
 * Mocks react-i18next (t returns the key), useAuth, and DocumentService.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import DocumentLibrary from '../DocumentLibrary';
import { DocumentService } from '../../services/DocumentService';
import { Document, DocumentStatus, DocumentVisibility } from '../../types/document';

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

const theme = createTheme();
const wrap = (ui: React.ReactElement) => <ThemeProvider theme={theme}>{ui}</ThemeProvider>;

const makeDoc = (overrides: Partial<Document>): Document => ({
  id: 1,
  filename: 'doc.pdf',
  original_filename: 'doc.pdf',
  title: 'My Document',
  mime_type: 'application/pdf',
  status: DocumentStatus.PROCESSED,
  created_at: '2026-05-28T10:00:00Z',
  has_vectors: true,
  user_id: 42,
  visibility: DocumentVisibility.PRIVATE,
  ...overrides,
});

beforeEach(() => {
  jest.clearAllMocks();
  mockUseAuth.mockReturnValue({
    user: { id: 42, institution_id: 7, institution: { id: 7, name: 'Test University' } },
  });
});

describe('DocumentLibrary visibility (TF-354)', () => {
  it('renders the lock icon for a private document', async () => {
    mockDocumentService.getDocuments.mockResolvedValue([makeDoc({ visibility: DocumentVisibility.PRIVATE })]);
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');
    expect(screen.getByTestId('LockOutlinedIcon')).toBeInTheDocument();
  });

  it('renders the business icon for an institution document', async () => {
    mockDocumentService.getDocuments.mockResolvedValue([
      makeDoc({ visibility: DocumentVisibility.INSTITUTION }),
    ]);
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');
    expect(screen.getByTestId('BusinessIcon')).toBeInTheDocument();
  });

  it('owner clicking the icon opens the visibility edit dialog and saves', async () => {
    mockDocumentService.getDocuments.mockResolvedValue([makeDoc({})]);
    mockDocumentService.updateVisibility.mockResolvedValue(
      makeDoc({ visibility: DocumentVisibility.INSTITUTION }),
    );
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');

    fireEvent.click(screen.getByLabelText('components.documentLibrary.visibilityEditAria'));

    // Dialog opened.
    expect(await screen.findByText('components.documentVisibility.title')).toBeInTheDocument();

    // Pick the institution radio (2nd in the dialog) and save.
    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    fireEvent.click(radios[radios.length - 1]);
    fireEvent.click(screen.getByText('components.documentVisibility.save'));

    await waitFor(() => {
      expect(mockDocumentService.updateVisibility).toHaveBeenCalledWith(
        1,
        DocumentVisibility.INSTITUTION,
      );
    });
  });

  it('non-owner sees a static icon (no edit button)', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 99, institution_id: 7, institution: { id: 7, name: 'Test University' } },
    });
    mockDocumentService.getDocuments.mockResolvedValue([
      makeDoc({ visibility: DocumentVisibility.INSTITUTION, user_id: 42 }),
    ]);
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');
    expect(
      screen.queryByLabelText('components.documentLibrary.visibilityEditAria'),
    ).not.toBeInTheDocument();
  });
});
