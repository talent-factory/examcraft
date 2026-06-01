/**
 * Tests for DocumentList (TF-355 Phase 3).
 *
 * (1) Both document titles render as rows.
 * (2a) Clicking the Titel TableSortLabel (sort=undefined) calls onSortChange('title_asc').
 * (2b) Clicking the Titel TableSortLabel (sort='title_asc') calls onSortChange('title_desc').
 * (3) Clicking a row checkbox calls onToggleSelect with that doc's id.
 * (4) Clicking the header checkbox calls onToggleSelectAll.
 * (5) Inline rename: Enter saves, Escape cancels.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import DocumentList from '../DocumentList';
import { Document, DocumentStatus, DocumentSort } from '../../../types/document';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback ?? key,
    i18n: { language: 'de' },
  }),
}));

const theme = createTheme();
const wrap = (ui: React.ReactElement) => (
  <ThemeProvider theme={theme}>{ui}</ThemeProvider>
);

const makeDoc = (overrides: Partial<Document>): Document => ({
  id: 1,
  filename: 'doc.pdf',
  original_filename: 'doc.pdf',
  title: 'Dokument Eins',
  mime_type: 'application/pdf',
  status: DocumentStatus.PROCESSED,
  created_at: '2026-05-28T10:00:00Z',
  has_vectors: true,
  tags: [],
  user_id: 42,
  ...overrides,
});

const doc1 = makeDoc({ id: 1, title: 'Dokument Eins', filename: 'doc1.pdf', original_filename: 'doc1.pdf' });
const doc2 = makeDoc({ id: 2, title: 'Dokument Zwei', filename: 'doc2.pdf', original_filename: 'doc2.pdf' });

const defaultProps = {
  documents: [doc1, doc2],
  selectedDocuments: [],
  sort: undefined as DocumentSort | undefined,
  onToggleSelect: jest.fn(),
  onToggleSelectAll: jest.fn(),
  onSortChange: jest.fn(),
  onPreview: jest.fn(),
  onRename: jest.fn(),
  onMenu: jest.fn(),
  isOwner: () => true,
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('DocumentList', () => {
  // (1) Both document titles render
  it('(1) renders both document titles', () => {
    render(wrap(<DocumentList {...defaultProps} />));
    expect(screen.getByText('Dokument Eins')).toBeInTheDocument();
    expect(screen.getByText('Dokument Zwei')).toBeInTheDocument();
  });

  // (2a) Clicking Titel header (sort=undefined) calls onSortChange('title_asc')
  it('(2a) clicking Titel header when sort=undefined calls onSortChange with title_asc', () => {
    render(wrap(<DocumentList {...defaultProps} sort={undefined} />));
    const titelHeader = screen.getByText('Titel');
    fireEvent.click(titelHeader);
    expect(defaultProps.onSortChange).toHaveBeenCalledWith('title_asc');
  });

  // (2b) Clicking Titel header when sort='title_asc' calls onSortChange('title_desc')
  it('(2b) clicking Titel header when sort=title_asc calls onSortChange with title_desc', () => {
    render(wrap(<DocumentList {...defaultProps} sort={'title_asc'} />));
    const titelHeader = screen.getByText('Titel');
    fireEvent.click(titelHeader);
    expect(defaultProps.onSortChange).toHaveBeenCalledWith('title_desc');
  });

  // (3) Clicking a row checkbox calls onToggleSelect with that doc's id
  // Uses stable aria-label query via inputProps instead of positional index.
  // doc1 has no display_name, so the aria-label falls back to doc1.title.
  it('(3) clicking a row checkbox calls onToggleSelect with the correct id', () => {
    render(wrap(<DocumentList {...defaultProps} />));
    // inputProps={{ 'aria-label': doc.display_name ?? doc.title }} — with no display_name, equals doc1.title
    const doc1Checkbox = screen.getByRole('checkbox', { name: doc1.display_name ?? doc1.title });
    fireEvent.click(doc1Checkbox);
    expect(defaultProps.onToggleSelect).toHaveBeenCalledWith(doc1.id);
  });

  // (4) Clicking the header checkbox calls onToggleSelectAll
  it('(4) clicking the header checkbox calls onToggleSelectAll', () => {
    render(wrap(<DocumentList {...defaultProps} />));
    const checkboxes = screen.getAllByRole('checkbox');
    // First checkbox is the header select-all
    fireEvent.click(checkboxes[0]);
    expect(defaultProps.onToggleSelectAll).toHaveBeenCalled();
  });

  // (5a) Inline rename: typing a new value and pressing Enter calls onRename
  it('(5a) inline rename: Enter saves and calls onRename with new value', async () => {
    const onRename = jest.fn().mockResolvedValue(undefined);
    render(wrap(<DocumentList {...defaultProps} onRename={onRename} />));

    // Click the pencil button for doc1 (aria-label = 'Umbenennen')
    // There are two pencil buttons (one per doc); get the first one
    const renameButtons = screen.getAllByRole('button', { name: 'Umbenennen' });
    fireEvent.click(renameButtons[0]);

    // The TextField should appear, pre-filled with doc1.title
    const textField = screen.getByRole('textbox');
    expect(textField).toBeInTheDocument();

    // Change the value
    fireEvent.change(textField, { target: { value: 'Neuer Titel' } });

    // Press Enter to save — onRename is invoked synchronously here.
    fireEvent.keyDown(textField, { key: 'Enter', code: 'Enter' });
    expect(onRename).toHaveBeenCalledWith(doc1.id, 'Neuer Titel');

    // After the async save resolves, edit mode exits (textbox removed).
    // Waiting on that DOM consequence flushes the trailing state updates
    // (setRenaming/setEditingId) inside act(), avoiding act() warnings.
    await waitFor(() => {
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    });
  });

  // (5b) Inline rename: pressing Escape cancels without calling onRename
  it('(5b) inline rename: Escape cancels without calling onRename', () => {
    const onRename = jest.fn();
    render(wrap(<DocumentList {...defaultProps} onRename={onRename} />));

    // Click the pencil button for doc1
    const renameButtons = screen.getAllByRole('button', { name: 'Umbenennen' });
    fireEvent.click(renameButtons[0]);

    // The TextField should appear
    const textField = screen.getByRole('textbox');
    expect(textField).toBeInTheDocument();

    // Press Escape to cancel
    fireEvent.keyDown(textField, { key: 'Escape', code: 'Escape' });

    // onRename should NOT have been called
    expect(onRename).not.toHaveBeenCalled();

    // The text field should be gone (back to display mode)
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });
});
