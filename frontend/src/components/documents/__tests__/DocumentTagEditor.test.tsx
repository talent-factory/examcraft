/**
 * Tests for DocumentTagEditor (TF-355 Phase 3).
 *
 * (a) canEdit=false → Autocomplete input is disabled.
 * (b) Removing an existing tag chip calls detachDocumentTag + onChanged.
 * (c) Selecting an available tag calls attachDocumentTags.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import DocumentTagEditor from '../DocumentTagEditor';
import { DocumentService } from '../../../services/DocumentService';
import { Document, DocumentStatus, DocumentTag } from '../../../types/document';

jest.mock('../../../services/DocumentService');
const mockDocumentService = DocumentService as jest.Mocked<typeof DocumentService>;

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

const tag1: DocumentTag = { id: 5, name: 'Mathe', scope: 'user', is_own: true };
const tag2: DocumentTag = { id: 7, name: 'Physik', scope: 'user', is_own: true };

const makeDoc = (overrides: Partial<Document> = {}): Document => ({
  id: 42,
  filename: 'doc.pdf',
  original_filename: 'doc.pdf',
  title: 'Test Doc',
  mime_type: 'application/pdf',
  status: DocumentStatus.PROCESSED,
  created_at: '2026-05-28T10:00:00Z',
  has_vectors: true,
  tags: [],
  ...overrides,
});

beforeEach(() => {
  jest.clearAllMocks();
});

describe('DocumentTagEditor', () => {
  // (a) canEdit=false → input is disabled
  it('(a) canEdit=false renders a disabled input', () => {
    const doc = makeDoc({ tags: [tag1] });
    render(
      wrap(
        <DocumentTagEditor
          document={doc}
          availableTags={[tag1, tag2]}
          canEdit={false}
          onChanged={jest.fn()}
        />,
      ),
    );
    // MUI Autocomplete renders an input role="combobox"
    const input = screen.getByRole('combobox');
    expect(input).toBeDisabled();
  });

  // (b) Removing an existing tag chip calls detachDocumentTag + onChanged
  it('(b) removing a tag chip calls detachDocumentTag and onChanged', async () => {
    mockDocumentService.detachDocumentTag.mockResolvedValue(undefined);
    const onChanged = jest.fn();
    const doc = makeDoc({ tags: [tag1] });

    render(
      wrap(
        <DocumentTagEditor
          document={doc}
          availableTags={[tag1, tag2]}
          canEdit={true}
          onChanged={onChanged}
        />,
      ),
    );

    // The MUI Chip delete button renders a CancelIcon (data-testid="CancelIcon")
    const cancelIcon = screen.getByTestId('CancelIcon');
    fireEvent.click(cancelIcon);

    await waitFor(() => {
      expect(mockDocumentService.detachDocumentTag).toHaveBeenCalledWith(42, 5);
    });

    await waitFor(() => {
      expect(onChanged).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 42,
          tags: [],
        }),
      );
    });
  });

  // (b2) Bug-Regression: Der Fix akkumuliert `nextTags` lokal statt pro Iteration
  //      `(document.tags ?? []).filter(…)` zu berechnen.
  //      Testfall: MUI Autocomplete "Clear all" (CloseIcon) feuert onChange([]) mit einem
  //      einzigen Event — das löst removedTags=[tag1,tag2] aus. Mit dem Fix darf onChanged
  //      nur einmal mit tags:[] aufgerufen werden, nicht zweimal mit inkonsistenten Werten.
  it('(b2) Clear-All (CloseIcon) feuert ein onChange([]) → detach für beide, onChanged mit tags:[]', async () => {
    mockDocumentService.detachDocumentTag.mockResolvedValue(undefined);
    const onChanged = jest.fn();
    const doc = makeDoc({ tags: [tag1, tag2] });

    render(
      wrap(
        <DocumentTagEditor
          document={doc}
          availableTags={[tag1, tag2]}
          canEdit={true}
          onChanged={onChanged}
        />,
      ),
    );

    // MUI Autocomplete mit multiple=true und value=[tag1,tag2] zeigt einen "CloseIcon"
    // (Clear-All-Button). Ein Klick darauf feuert onChange([]) — ein einziges Event.
    // Das entspricht genau dem Szenario, das den Stale-Prop-Bug auslöst.
    const clearButton = screen.getByTestId('CloseIcon');
    fireEvent.click(clearButton);

    // Beide Detachs müssen erfolgen
    await waitFor(() => {
      expect(mockDocumentService.detachDocumentTag).toHaveBeenCalledTimes(2);
    });
    expect(mockDocumentService.detachDocumentTag).toHaveBeenCalledWith(42, tag1.id);
    expect(mockDocumentService.detachDocumentTag).toHaveBeenCalledWith(42, tag2.id);

    // onChanged muss mit tags:[] aufgerufen worden sein (nicht tags:[tag2] oder tags:[tag1])
    await waitFor(() => {
      const lastArg = onChanged.mock.calls[onChanged.mock.calls.length - 1][0];
      expect(lastArg).toMatchObject({ id: 42, tags: [] });
    });
  });

  // (c) Selecting an available tag calls attachDocumentTags
  it('(c) selecting an available tag calls attachDocumentTags', async () => {
    const updatedDoc = makeDoc({ tags: [tag2] });
    mockDocumentService.attachDocumentTags.mockResolvedValue(updatedDoc);
    const onChanged = jest.fn();
    const doc = makeDoc({ tags: [] });

    render(
      wrap(
        <DocumentTagEditor
          document={doc}
          availableTags={[tag1, tag2]}
          canEdit={true}
          onChanged={onChanged}
        />,
      ),
    );

    // Open the Autocomplete dropdown
    const input = screen.getByRole('combobox');
    fireEvent.mouseDown(input);
    fireEvent.click(input);

    // Wait for Physik option to appear and click it
    const option = await screen.findByText('Physik');
    fireEvent.click(option);

    await waitFor(() => {
      expect(mockDocumentService.attachDocumentTags).toHaveBeenCalledWith(42, [7]);
    });

    await waitFor(() => {
      expect(onChanged).toHaveBeenCalledWith(updatedDoc);
    });
  });
});
