/**
 * Tests for the owner-guard on the rename pencil in the document *card* view
 * (TF-606).
 *
 * Renaming is owner-only on the backend (`documents_rename_owner_only`, 403).
 * The list view has always gated the pencil on ownership; the card view — the
 * default view — did not, so non-owners of institution-shared documents could
 * open the inline editor and only learned about the restriction on save.
 *
 * Mocks react-i18next (t returns the key), useAuth, and DocumentService.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MemoryRouter } from 'react-router-dom';
import DocumentLibrary from '../DocumentLibrary';
import { DocumentService } from '../../services/DocumentService';
import { OrgUnitsService } from '../../services/orgUnitsService';
import { Document, DocumentStatus, DocumentVisibility } from '../../types/document';
// Not from DocumentService — that module is automocked below, so its
// DocumentFetchError export would be a mock constructor. The real AppError
// plus the duck-typed `name`/`status` is what both branches actually read.
import { AppError } from '../../errors';

// `t` echoes the key, as the shared setupTests mock does — with one
// exception. translateError() detects a missing translation by comparing
// t(key) to the key itself, so an echoing mock makes EVERY error key look
// untranslated and sends every assertion down the fallback branch. The two
// codes exercised here therefore resolve to a marker string; the fallback key
// still echoes, which is what keeps the two branches distinguishable.
const TRANSLATED_ERROR_KEYS = [
  'errors.documents_rename_owner_only',
  'errors.documents_rename_failed',
];

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) =>
      TRANSLATED_ERROR_KEYS.includes(key) ? `übersetzt:${key}` : key,
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

const theme = createTheme();
const wrap = (ui: React.ReactElement) => (
  <ThemeProvider theme={theme}>
    <MemoryRouter>{ui}</MemoryRouter>
  </ThemeProvider>
);

const paged = (docs: Document[]) => ({
  documents: docs,
  total: docs.length,
  page: 1,
  page_size: 24,
  total_pages: 1,
  stats: { total: docs.length, processed: docs.length, with_vectors: 0, in_progress: 0 },
});

const makeDoc = (overrides: Partial<Document> = {}): Document => ({
  id: 1,
  filename: 'doc.pdf',
  original_filename: 'doc.pdf',
  title: 'My Document',
  mime_type: 'application/pdf',
  status: DocumentStatus.PROCESSED,
  created_at: '2026-05-28T10:00:00Z',
  has_vectors: true,
  user_id: 42,
  visibility: DocumentVisibility.INSTITUTION,
  ...overrides,
});

const RENAME_LABEL = 'components.documentLibrary.renameTooltip';

beforeEach(() => {
  jest.clearAllMocks();
  mockUseAuth.mockReturnValue({
    user: { id: 42, institution_id: 7, institution: { id: 7, name: 'Test University' } },
  });
  mockDocumentService.listDocumentTags.mockResolvedValue([]);
  mockOrgUnitsService.mine.mockResolvedValue({ items: [] });
});

describe('DocumentLibrary card view — rename owner guard (TF-606)', () => {
  it('shows the rename pencil to the owner', async () => {
    mockDocumentService.listDocuments.mockResolvedValue(paged([makeDoc()]));
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');

    expect(screen.getByLabelText(RENAME_LABEL)).toBeInTheDocument();
  });

  it('hides the rename pencil from a non-owner of a shared document', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 99, institution_id: 7, institution: { id: 7, name: 'Test University' } },
    });
    mockDocumentService.listDocuments.mockResolvedValue(paged([makeDoc({ user_id: 42 })]));
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');

    expect(screen.queryByLabelText(RENAME_LABEL)).not.toBeInTheDocument();
  });

  it('surfaces the backend message and closes the editor on a 403 save', async () => {
    // Safety net for the race where ownership is lost while the inline field
    // is open: the action can never succeed, so keeping the editor open only
    // invites a retry loop.
    mockDocumentService.listDocuments.mockResolvedValue(paged([makeDoc()]));
    mockDocumentService.renameDocument.mockRejectedValue(
      Object.assign(
        new AppError('documents_rename_owner_only', 'owner only', 403),
        { name: 'DocumentFetchError' },
      ),
    );
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');

    fireEvent.click(screen.getByLabelText(RENAME_LABEL));
    const field = await screen.findByDisplayValue('My Document');
    fireEvent.change(field, { target: { value: 'Neuer Name' } });
    fireEvent.keyDown(field, { key: 'Enter' });

    // TF-772: the message comes from the error's CODE, not from the backend's
    // prose. `t` is mocked to echo the key, so the rendered key is the proof
    // that `documents_rename_owner_only` — and not the generic renameError
    // fallback — drove the message.
    expect(
      await screen.findByText('übersetzt:errors.documents_rename_owner_only'),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByDisplayValue('Neuer Name')).not.toBeInTheDocument();
    });
  });

  it('keeps the editor open on a non-permission failure so the input is not lost', async () => {
    mockDocumentService.listDocuments.mockResolvedValue(paged([makeDoc()]));
    mockDocumentService.renameDocument.mockRejectedValue(
      new AppError('documents_rename_failed', 'Serverfehler', 500),
    );
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');

    fireEvent.click(screen.getByLabelText(RENAME_LABEL));
    const field = await screen.findByDisplayValue('My Document');
    fireEvent.change(field, { target: { value: 'Neuer Name' } });
    fireEvent.keyDown(field, { key: 'Enter' });

    expect(await screen.findByText('übersetzt:errors.documents_rename_failed')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Neuer Name')).toBeInTheDocument();
  });
});
