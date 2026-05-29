jest.mock('../../api/apiClient');
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MemoryRouter } from 'react-router-dom';
import DocumentLibrary from '../DocumentLibrary';
import { Document, DocumentStatus } from '../../types/document';

// Preserve the real `DocumentFetchError` class (so `new DocumentFetchError(...)`
// here produces an instance the component's duck-type catch recognises) while
// stubbing every method on `DocumentService`.
jest.mock('../../services/DocumentService', () => {
  const actual = jest.requireActual('../../services/DocumentService');
  return {
    ...actual,
    DocumentService: {
      getDocuments: jest.fn(),
      listDocuments: jest.fn(),
      listDocumentTags: jest.fn(),
      getDocument: jest.fn(),
      getDocumentRaw: jest.fn(),
      getDocumentChunksPaginated: jest.fn(),
      getDocumentChunks: jest.fn(),
      getDocumentContent: jest.fn(),
      downloadDocument: jest.fn(),
      deleteDocument: jest.fn(),
      processDocument: jest.fn(),
      renameDocument: jest.fn(),
      getProcessingStatus: jest.fn(),
      uploadDocument: jest.fn(),
      uploadMultipleDocuments: jest.fn(),
      batchProcessDocuments: jest.fn(),
      reindexDocument: jest.fn(),
      getAvailableDocuments: jest.fn(),
    },
  };
});

// DocumentLibrary consumes useAuth (owner detection, TF-354). Mock it so these
// tests render without wrapping in an AuthProvider — same pattern as
// DocumentLibrary.visibility.test.tsx.
const mockUseAuth = jest.fn();
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// eslint-disable-next-line @typescript-eslint/no-var-requires
const { DocumentService, DocumentFetchError } = require('../../services/DocumentService');
const mockDocumentService = DocumentService as jest.Mocked<typeof DocumentService>;

// Stable, predictable URL.createObjectURL so we can assert revoke calls by URL
const createObjectURL = jest.fn();
const revokeObjectURL = jest.fn();
let blobCounter = 0;
beforeAll(() => {
  // @ts-expect-error - jsdom global
  global.URL.createObjectURL = (...args: unknown[]) => {
    blobCounter += 1;
    const url = `blob:mock/${blobCounter}`;
    createObjectURL(...args);
    return url;
  };
  // @ts-expect-error - jsdom global
  global.URL.revokeObjectURL = (url: string) => revokeObjectURL(url);
});

beforeEach(() => {
  jest.clearAllMocks();
  blobCounter = 0;
  mockUseAuth.mockReturnValue({
    user: { id: 1, institution_id: 7, institution: { id: 7, name: 'Test University' } },
  });
});

const theme = createTheme();
const Wrap: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    <MemoryRouter>{children}</MemoryRouter>
  </ThemeProvider>
);

const baseDoc = (overrides: Partial<Document> = {}): Document => ({
  id: 1,
  filename: 'paper.pdf',
  original_filename: 'Paper.pdf',
  title: 'Paper',
  mime_type: 'application/pdf',
  status: DocumentStatus.PROCESSED,
  created_at: '2026-04-30T10:00:00Z',
  processed_at: '2026-04-30T10:01:00Z',
  file_size: 1024,
  has_vectors: true,
  metadata: { total_chunks: 3 },
  ...overrides,
});

const openPreview = async (doc: Document) => {
  // The card menu lives behind a stopPropagation IconButton + Menu — drive
  // the preview imperatively by stubbing getDocuments and triggering
  // handlePreview via the menu item. Easier path: render with a single doc
  // and click the doc card → menu → preview.
  mockDocumentService.listDocuments.mockResolvedValue({
    documents: [doc],
    total: 1,
    page: 1,
    page_size: 24,
    total_pages: 1,
    stats: { total: 1, processed: 1, with_vectors: 1, in_progress: 0 },
  });
  mockDocumentService.listDocumentTags.mockResolvedValue([]);
  mockDocumentService.getDocumentChunksPaginated.mockResolvedValue({
    document_id: doc.id,
    total_chunks: 0,
    total_pages: 0,
    current_page: 1,
    page_size: 10,
    chunks: [],
  });

  render(
    <Wrap>
      <DocumentLibrary />
    </Wrap>,
  );

  await screen.findByText('Paper');

  // Open the card's MoreVert menu. The IconButton has no accessible name;
  // pick the one whose only child is the MoreVert icon (data-testid set
  // by MUI). Using getAllByTestId avoids direct DOM querying and survives
  // the testing-library/no-node-access lint rule.
  // eslint-disable-next-line testing-library/no-node-access
  const moreVertIcon = screen.getByTestId('MoreVertIcon');
  // eslint-disable-next-line testing-library/no-node-access
  const moreVert = moreVertIcon.closest('button');
  if (moreVert) {
    await act(async () => {
      moreVert.click();
    });
  }
  // Click the Preview menu item
  const previewItem = await screen.findByText(/Vorschau|Preview|Aperçu|Anteprima/i);
  await act(async () => {
    previewItem.click();
  });
};

describe('OriginalDocumentContent (TF-332)', () => {
  it('renders <object> for PDF and exposes a fallback link for Safari', async () => {
    const doc = baseDoc();
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' });
    mockDocumentService.getDocumentRaw.mockResolvedValue({
      ok: true,
      blob: jest.fn().mockResolvedValue(blob),
    } as unknown as Response);

    await openPreview(doc);

    // <object> is queried by its accessible name (`aria-label` on the element).
    const obj = await screen.findByLabelText('Paper.pdf');
    expect(obj.tagName.toLowerCase()).toBe('object');
    expect(obj.getAttribute('data')).toMatch(/^blob:mock\//);

    // Fallback anchor for browsers that ignore <object>
    const fallbackLink = await screen.findByRole('link', { name: /PDF|tab|onglet|scheda/i });
    expect(fallbackLink).toHaveAttribute('href', expect.stringMatching(/^blob:mock\//));
  });

  it('renders the DOCX phase-2 alert without calling the network', async () => {
    const doc = baseDoc({
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });

    await openPreview(doc);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    expect(mockDocumentService.getDocumentRaw).not.toHaveBeenCalled();
  });

  it('renders an unsupported-format alert for unknown MIME types', async () => {
    const doc = baseDoc({ mime_type: 'application/x-fictional' });
    mockDocumentService.getDocumentRaw.mockResolvedValue({
      ok: true,
      text: jest.fn().mockResolvedValue(''),
    } as unknown as Response);

    await openPreview(doc);

    await waitFor(() => {
      const alerts = screen.getAllByRole('alert');
      expect(alerts.length).toBeGreaterThan(0);
    });
  });

  it('routes chat-export sources through the Markdown branch (calls /raw with .text())', async () => {
    const doc = baseDoc({
      mime_type: 'text/plain',
      metadata: { total_chunks: 0, source: 'chat_export' },
    });
    const textFn = jest.fn().mockResolvedValue('# Heading\n\n**bold**');
    mockDocumentService.getDocumentRaw.mockResolvedValue({
      ok: true,
      text: textFn,
      // .blob() must NOT be invoked for the markdown path — leave undefined
      // so any accidental call throws a TypeError the test would surface.
    } as unknown as Response);

    await openPreview(doc);

    await waitFor(() => {
      expect(mockDocumentService.getDocumentRaw).toHaveBeenCalledWith(doc.id);
    });
    expect(textFn).toHaveBeenCalled();
    // react-markdown is intentionally not asserted on (its ESM bundle does
    // not always transpile cleanly under CRA's jest config — see the
    // existing `describe.skip` in DocumentLibrary.test.tsx for the same
    // root cause). The MIME-dispatch routing is what we care about here.
  });

  it('maps DocumentFetchError(401) to the auth-error i18n key', async () => {
    const doc = baseDoc();
    mockDocumentService.getDocumentRaw.mockRejectedValue(
      new DocumentFetchError('Could not validate credentials', 401),
    );

    await openPreview(doc);

    // German fallback text from translation files.
    await waitFor(() => {
      expect(
        screen.getByText(/Sitzung abgelaufen|Session expired|Session expirée|Sessione scaduta/i),
      ).toBeInTheDocument();
    });
  });

  it('maps DocumentFetchError(404) to the missing-file i18n key', async () => {
    const doc = baseDoc();
    mockDocumentService.getDocumentRaw.mockRejectedValue(
      new DocumentFetchError('not found', 404),
    );

    await openPreview(doc);

    await waitFor(() => {
      expect(
        screen.getByText(/Originaldatei nicht gefunden|Original file not found|Fichier original introuvable|File originale non trovato/i),
      ).toBeInTheDocument();
    });
  });

  it('treats status === 0 as a network error', async () => {
    const doc = baseDoc();
    mockDocumentService.getDocumentRaw.mockRejectedValue(
      new DocumentFetchError('Failed to fetch', 0),
    );

    await openPreview(doc);

    await waitFor(() => {
      expect(
        screen.getByText(/Netzwerkfehler|Network error|Erreur réseau|Errore di rete/i),
      ).toBeInTheDocument();
    });
  });

  it('opens ORIGINAL by default for documents with status="completed"', async () => {
    const doc = baseDoc({ status: 'completed' as unknown as DocumentStatus });
    const blob = new Blob(['%PDF'], { type: 'application/pdf' });
    mockDocumentService.getDocumentRaw.mockResolvedValue({
      ok: true,
      blob: jest.fn().mockResolvedValue(blob),
    } as unknown as Response);

    await openPreview(doc);

    // ORIGINAL = tab index 1; the OriginalDocumentContent component renders
    // an <object> with aria-label = original_filename. Finding it proves the
    // tab opened by default for status="completed".
    await screen.findByLabelText('Paper.pdf');
  });

  it('revokes the blob URL on unmount', async () => {
    const doc = baseDoc();
    const blob = new Blob(['%PDF'], { type: 'application/pdf' });
    mockDocumentService.getDocumentRaw.mockResolvedValue({
      ok: true,
      blob: jest.fn().mockResolvedValue(blob),
    } as unknown as Response);

    await openPreview(doc);

    await waitFor(() => {
      expect(createObjectURL).toHaveBeenCalled();
    });
    const createdUrl = `blob:mock/${blobCounter}`;

    // Close the dialog → unmounts OriginalDocumentContent → cleanup runs
    const closeBtn = await screen.findByRole('button', {
      name: /Schließen|Close|Fermer|Chiudi/i,
    });
    await act(async () => {
      closeBtn.click();
    });

    await waitFor(() => {
      expect(revokeObjectURL).toHaveBeenCalledWith(createdUrl);
    });
  });
});
