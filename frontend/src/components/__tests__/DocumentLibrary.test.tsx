import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import DocumentLibrary from '../DocumentLibrary';

jest.mock('../../api/apiClient');

// Mock DocumentService at module level
jest.mock('../../services/DocumentService');

// ---------------------------------------------------------------------------
// TF-355: New paginated DocumentLibrary tests
// ---------------------------------------------------------------------------

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, institution_id: 10, institution: { name: 'Inst' } } }),
}));

describe('DocumentLibrary TF-355 paginated', () => {
  beforeEach(() => jest.clearAllMocks());

  it('fetches via listDocuments and renders a page of documents + toolbar + pagination', async () => {
    const { DocumentService: DS } = require('../../services/DocumentService');
    DS.listDocuments = jest.fn().mockResolvedValue({
      documents: [{
        id: 1,
        filename: 'a.pdf',
        original_filename: 'a.pdf',
        title: 'Alpha',
        mime_type: 'application/pdf',
        status: 'completed',
        has_vectors: false,
        created_at: '2026-01-01T00:00:00Z',
        user_id: 1,
        tags: [],
      }],
      total: 30,
      page: 1,
      page_size: 24,
      total_pages: 2,
      stats: { total: 30, processed: 30, with_vectors: 0, in_progress: 0 },
    });
    DS.listDocumentTags = jest.fn().mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/documents']}>
        <ThemeProvider theme={createTheme()}>
          <DocumentLibrary />
        </ThemeProvider>
      </MemoryRouter>,
    );

    await screen.findByText('Alpha');
    expect(DS.listDocuments).toHaveBeenCalled();
    // pagination shows page 2 button (total_pages=2)
    expect(screen.getByRole('button', { name: /go to page 2/i })).toBeInTheDocument();
  });

  it('renders tag chips for a document with tags', async () => {
    const { DocumentService: DS } = require('../../services/DocumentService');
    DS.listDocuments = jest.fn().mockResolvedValue({
      documents: [{
        id: 2,
        filename: 'tagged.pdf',
        original_filename: 'tagged.pdf',
        title: 'Tagged Doc',
        mime_type: 'application/pdf',
        status: 'completed',
        has_vectors: false,
        created_at: '2026-01-01T00:00:00Z',
        user_id: 1,
        tags: [{ id: 5, name: 'Mathe', scope: 'user', is_own: true }],
      }],
      total: 1,
      page: 1,
      page_size: 24,
      total_pages: 1,
      stats: { total: 1, processed: 1, with_vectors: 0, in_progress: 0 },
    });
    DS.listDocumentTags = jest.fn().mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/documents']}>
        <ThemeProvider theme={createTheme()}>
          <DocumentLibrary />
        </ThemeProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Mathe')).toBeInTheDocument();
  });

  it('empty state no-upload: shows noDocuments text when list is empty and no filters active', async () => {
    const { DocumentService: DS } = require('../../services/DocumentService');
    DS.listDocuments = jest.fn().mockResolvedValue({
      documents: [],
      total: 0,
      page: 1,
      page_size: 24,
      total_pages: 0,
      stats: { total: 0, processed: 0, with_vectors: 0, in_progress: 0 },
    });
    DS.listDocumentTags = jest.fn().mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/documents']}>
        <ThemeProvider theme={createTheme()}>
          <DocumentLibrary />
        </ThemeProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Keine Dokumente vorhanden')).toBeInTheDocument();
  });

  it('empty state search-no-hits: shows clear-search button when search active and no results', async () => {
    const { DocumentService: DS } = require('../../services/DocumentService');
    DS.listDocuments = jest.fn().mockResolvedValue({
      documents: [],
      total: 5,
      page: 1,
      page_size: 24,
      total_pages: 1,
      stats: { total: 5, processed: 5, with_vectors: 0, in_progress: 0 },
    });
    DS.listDocumentTags = jest.fn().mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/documents?q=zzz']}>
        <ThemeProvider theme={createTheme()}>
          <DocumentLibrary />
        </ThemeProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('button', { name: 'Suche löschen' })).toBeInTheDocument();
    expect(screen.getByText(/Keine Treffer für.*zzz/)).toBeInTheDocument();
  });

  it('empty state filter-no-hits: shows reset-filters button when filter active and no results', async () => {
    const { DocumentService: DS } = require('../../services/DocumentService');
    DS.listDocuments = jest.fn().mockResolvedValue({
      documents: [],
      total: 5,
      page: 1,
      page_size: 24,
      total_pages: 1,
      stats: { total: 5, processed: 5, with_vectors: 0, in_progress: 0 },
    });
    DS.listDocumentTags = jest.fn().mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/documents?status=processed']}>
        <ThemeProvider theme={createTheme()}>
          <DocumentLibrary />
        </ThemeProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('button', { name: 'Alle Filter zurücksetzen' })).toBeInTheDocument();
  });

  it('processingOnOtherPages badge: shows caption when stats.in_progress>0 but no PROCESSING doc on page', async () => {
    const { DocumentService: DS } = require('../../services/DocumentService');
    DS.listDocuments = jest.fn().mockResolvedValue({
      documents: [{
        id: 10,
        filename: 'done.pdf',
        original_filename: 'done.pdf',
        title: 'Done Doc',
        mime_type: 'application/pdf',
        status: 'completed',
        has_vectors: false,
        created_at: '2026-01-01T00:00:00Z',
        user_id: 1,
        tags: [],
      }],
      total: 4,
      page: 1,
      page_size: 24,
      total_pages: 1,
      stats: { total: 4, processed: 1, with_vectors: 0, in_progress: 3 },
    });
    DS.listDocumentTags = jest.fn().mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/documents']}>
        <ThemeProvider theme={createTheme()}>
          <DocumentLibrary />
        </ThemeProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText(/3 weitere in Bearbeitung/)).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // F4: Bulk-Handler-Coverage (Owner-Skip, API-Fehler, Tag-No-op)
  // ---------------------------------------------------------------------------

  // Shared fixture: one owned doc (user_id=1, has tag 5) + one non-owned doc (user_id=99)
  const makePagedResponse = () => ({
    documents: [
      {
        id: 10,
        filename: 'owned.pdf',
        original_filename: 'owned.pdf',
        title: 'Owned Doc',
        mime_type: 'application/pdf',
        status: 'completed',
        has_vectors: true,
        created_at: '2026-01-01T00:00:00Z',
        user_id: 1,
        visibility: 'private',
        tags: [{ id: 5, name: 'Mathe', scope: 'user', is_own: true }],
      },
      {
        id: 20,
        filename: 'foreign.pdf',
        original_filename: 'foreign.pdf',
        title: 'Foreign Doc',
        mime_type: 'application/pdf',
        status: 'completed',
        has_vectors: true,
        created_at: '2026-01-01T00:00:00Z',
        user_id: 99,
        visibility: 'private',
        tags: [],
      },
    ],
    total: 2,
    page: 1,
    page_size: 24,
    total_pages: 1,
    stats: { total: 2, processed: 2, with_vectors: 2, in_progress: 0 },
  });

  // (a) Owner-skip warning: non-owned docs are skipped, summary shows skipped count
  it('(a) bulk visibility: updateVisibility nur für owned doc, summary enthält übersprungen', async () => {
    const { DocumentService: DS } = require('../../services/DocumentService');
    DS.updateVisibility = jest.fn().mockResolvedValue({});
    DS.listDocuments = jest.fn()
      .mockResolvedValueOnce(makePagedResponse())
      .mockResolvedValue(makePagedResponse());
    DS.listDocumentTags = jest.fn().mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/documents?view=list']}>
        <ThemeProvider theme={createTheme()}>
          <DocumentLibrary />
        </ThemeProvider>
      </MemoryRouter>,
    );

    // Wait for list to load, then select both docs by their per-row checkboxes
    await screen.findByText('Owned Doc');
    fireEvent.click(screen.getByRole('checkbox', { name: 'Owned Doc' }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Foreign Doc' }));

    // BulkActionsBar should appear; click "Sichtbarkeit…" button
    const visibilityBtn = await screen.findByRole('button', { name: /sichtbarkeit/i });
    fireEvent.click(visibilityBtn);

    // Dialog opens; pick the "Privat" radio
    const privateRadio = await screen.findByRole('radio', { name: /privat/i });
    fireEvent.click(privateRadio);

    // Save
    const saveBtn = screen.getByRole('button', { name: /speichern/i });
    fireEvent.click(saveBtn);

    // updateVisibility called only for owned doc (id=10), not for foreign doc (id=20)
    // 3rd arg (orgUnitId) is undefined here — TF-620 only sends it for 'team'.
    await waitFor(() => {
      expect(DS.updateVisibility).toHaveBeenCalledWith(10, expect.any(String), undefined);
    });
    await waitFor(() => {
      expect(DS.updateVisibility).not.toHaveBeenCalledWith(20, expect.any(String), undefined);
    });

    // Snackbar summary contains "übersprungen" (skipped count)
    await screen.findByText(/übersprungen/i);
  });

  // (b) API failure → error severity in summary
  it('(b) bulk visibility: API-Fehler → summary enthält Fehler', async () => {
    const { DocumentService: DS } = require('../../services/DocumentService');
    DS.updateVisibility = jest.fn().mockRejectedValue(new Error('Server error'));
    DS.listDocuments = jest.fn()
      .mockResolvedValueOnce(makePagedResponse())
      .mockResolvedValue(makePagedResponse());
    DS.listDocumentTags = jest.fn().mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/documents?view=list']}>
        <ThemeProvider theme={createTheme()}>
          <DocumentLibrary />
        </ThemeProvider>
      </MemoryRouter>,
    );

    await screen.findByText('Owned Doc');
    fireEvent.click(screen.getByRole('checkbox', { name: 'Owned Doc' }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Foreign Doc' }));

    const visibilityBtn = await screen.findByRole('button', { name: /sichtbarkeit/i });
    fireEvent.click(visibilityBtn);

    const privateRadio = await screen.findByRole('radio', { name: /privat/i });
    fireEvent.click(privateRadio);

    const saveBtn = screen.getByRole('button', { name: /speichern/i });
    fireEvent.click(saveBtn);

    // Summary contains "Fehler" (error count) — service call for owned doc failed
    await screen.findByText(/fehler/i);
  });

  // (c) Tags add no-op: doc already has tag id 5; attachDocumentTags NOT called for that doc
  it('(c) bulk tags add: doc mit tag 5 → attachDocumentTags nicht aufgerufen (no-op)', async () => {
    const { DocumentService: DS } = require('../../services/DocumentService');
    DS.attachDocumentTags = jest.fn().mockResolvedValue({});
    DS.listDocuments = jest.fn()
      .mockResolvedValueOnce(makePagedResponse())
      .mockResolvedValue(makePagedResponse());
    DS.listDocumentTags = jest.fn().mockResolvedValue([
      { id: 5, name: 'Mathe', scope: 'user', is_own: true },
    ]);

    render(
      <MemoryRouter initialEntries={['/documents?view=list']}>
        <ThemeProvider theme={createTheme()}>
          <DocumentLibrary />
        </ThemeProvider>
      </MemoryRouter>,
    );

    // Select only the owned doc (id=10, which already has tag 5)
    await screen.findByText('Owned Doc');
    fireEvent.click(screen.getByRole('checkbox', { name: 'Owned Doc' }));

    // Open bulk Tags dialog
    const tagsBtn = await screen.findByRole('button', { name: /tags/i });
    fireEvent.click(tagsBtn);

    // In BulkTagsDialog: select tag "Mathe" (id=5) in add mode (default mode)
    const tagInputs = screen.getAllByRole('combobox');
    const tagInput = tagInputs[tagInputs.length - 1]; // last combobox is in dialog
    fireEvent.mouseDown(tagInput);
    const matheOption = await screen.findByRole('option', { name: 'Mathe' });
    fireEvent.click(matheOption);

    // Click Apply
    const applyBtn = screen.getByRole('button', { name: /anwenden/i });
    fireEvent.click(applyBtn);

    // Anchor on the bulk-run completion (Snackbar summary) so the trailing
    // state updates flush inside act(), then assert the no-op negative.
    await screen.findByText(/aktualisiert/i);
    // attachDocumentTags should NOT be called for doc 10 because it already has tag 5
    expect(DS.attachDocumentTags).not.toHaveBeenCalledWith(10, expect.any(Array));
  });
});

// ---------------------------------------------------------------------------
// TF-366: Stale-response race on rapid filter/page changes
// ---------------------------------------------------------------------------

describe('DocumentLibrary TF-366 stale-response race', () => {
  beforeEach(() => jest.clearAllMocks());

  // Build a single-document page response keyed by the document title.
  const pageWith = (title: string, id: number) => ({
    documents: [{
      id,
      filename: `${title}.pdf`,
      original_filename: `${title}.pdf`,
      title,
      mime_type: 'application/pdf',
      status: 'completed',
      has_vectors: false,
      created_at: '2026-01-01T00:00:00Z',
      user_id: 1,
      tags: [],
    }],
    total: 1,
    page: 1,
    page_size: 24,
    total_pages: 1,
    stats: { total: 1, processed: 1, with_vectors: 0, in_progress: 0 },
  });

  it('discards a stale in-flight response that resolves after a newer request', async () => {
    const { DocumentService: DS } = require('../../services/DocumentService');

    // Two deferred responses whose resolution order we control explicitly:
    // `first` belongs to the older request, `second` to the newer one.
    let resolveFirst!: (value: unknown) => void;
    let resolveSecond!: (value: unknown) => void;
    const first = new Promise((resolve) => { resolveFirst = resolve; });
    const second = new Promise((resolve) => { resolveSecond = resolve; });

    DS.listDocuments = jest.fn()
      .mockReturnValueOnce(first)
      .mockReturnValueOnce(second);
    DS.listDocumentTags = jest.fn().mockResolvedValue([]);

    const ui = (refreshTrigger: number) => (
      <MemoryRouter initialEntries={['/documents']}>
        <ThemeProvider theme={createTheme()}>
          <DocumentLibrary refreshTrigger={refreshTrigger} />
        </ThemeProvider>
      </MemoryRouter>
    );

    // Mount fires the first (older) request — it stays in-flight.
    const { rerender } = render(ui(0));

    // Bumping refreshTrigger fires a second (newer) request while the first
    // is still pending — exactly the rapid filter/page change scenario.
    rerender(ui(1));

    // The NEWER request resolves first with fresh data...
    await act(async () => {
      resolveSecond(pageWith('Fresh', 2));
      await Promise.resolve();
    });
    // ...then the OLDER request resolves last with now-stale data.
    await act(async () => {
      resolveFirst(pageWith('Stale', 1));
      await Promise.resolve();
    });

    // The request-sequence guard must keep the fresh result and drop the
    // stale one, even though the stale response arrived last.
    expect(await screen.findByText('Fresh')).toBeInTheDocument();
    expect(screen.queryByText('Stale')).not.toBeInTheDocument();
  });
});
