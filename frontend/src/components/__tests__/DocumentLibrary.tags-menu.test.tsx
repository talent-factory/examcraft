/**
 * Tests for the «Tags bearbeiten» context-menu entry (TF-381).
 *
 * The tag editor previously lived only in the preview dialog's Metadata tab,
 * reachable via: open card → wait for preview → Metadaten → scroll. This entry
 * gives owners a direct, discoverable jump straight to the tag editor.
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
import { Document, DocumentStatus, DocumentVisibility } from '../../types/document';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
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
  // jsdom does not implement scrollIntoView — provide a no-op spy so the
  // "scroll to tag editor" behaviour can run (and be asserted) under test.
  (window.HTMLElement.prototype as unknown as { scrollIntoView: jest.Mock }).scrollIntoView =
    jest.fn();
  mockUseAuth.mockReturnValue({
    user: { id: 42, institution_id: 7, institution: { id: 7, name: 'Test University' } },
  });
  mockDocumentService.listDocumentTags.mockResolvedValue([]);
  // handleEditTags pre-fetches chunks for ready documents (mirrors preview);
  // stub it so the async fetch resolves cleanly instead of logging an error.
  mockDocumentService.getDocumentChunksPaginated.mockResolvedValue({
    chunks: [],
    current_page: 1,
    total_pages: 1,
    total_chunks: 0,
  });
});

const openCardMenu = () => {
  // Single card → single ⋮ trigger.
  fireEvent.click(screen.getByTestId('MoreVertIcon'));
};

describe('DocumentLibrary «Tags bearbeiten» menu entry (TF-381)', () => {
  it('shows the entry in the owner\'s card context menu', async () => {
    mockDocumentService.listDocuments.mockResolvedValue(paged([makeDoc({})]));
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');

    openCardMenu();

    expect(
      await screen.findByText('components.documentLibrary.menuEditTags'),
    ).toBeInTheDocument();
  });

  it('opens the preview dialog at the Metadata tab with the tag editor', async () => {
    mockDocumentService.listDocuments.mockResolvedValue(paged([makeDoc({})]));
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');

    openCardMenu();
    fireEvent.click(await screen.findByText('components.documentLibrary.menuEditTags'));

    // Preview dialog opened on the Metadata tab → doc info + tag editor render.
    expect(
      await screen.findByText('components.documentLibrary.docInfo'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('components.documentLibrary.tagEditor.heading'),
    ).toBeInTheDocument();

    // The tag editor is scrolled into view for a direct landing.
    await waitFor(() => {
      expect(
        (window.HTMLElement.prototype as unknown as { scrollIntoView: jest.Mock })
          .scrollIntoView,
      ).toHaveBeenCalled();
    });
  });

  it('hides the entry for non-owners', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 99, institution_id: 7, institution: { id: 7, name: 'Test University' } },
    });
    mockDocumentService.listDocuments.mockResolvedValue(paged([
      makeDoc({ visibility: DocumentVisibility.INSTITUTION, user_id: 42 }),
    ]));
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');

    openCardMenu();

    // Menu is open (Preview is always present) but the tags entry is not.
    expect(
      await screen.findByText('components.documentLibrary.menuPreview'),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('components.documentLibrary.menuEditTags'),
    ).not.toBeInTheDocument();
  });
});
