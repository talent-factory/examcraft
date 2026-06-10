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
import {
  Document,
  DocumentStatus,
  DocumentTag,
  DocumentVisibility,
} from '../../../types/document';

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
// TF-382: an institution-scope tag — only attachable to INSTITUTION-visible docs.
const instTag: DocumentTag = {
  id: 9,
  name: 'Lehrgang',
  scope: 'institution',
  is_own: false,
};

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
          isOwner={true}
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
          isOwner={true}
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
          isOwner={true}
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
          isOwner={true}
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

  // (d) TF-382: on a PRIVATE document, an institution-scope tag must not be a
  //     dead end — its dropdown option is disabled so it can't be selected.
  it('(d) institution tag option is disabled on a private document', async () => {
    const doc = makeDoc({ tags: [], visibility: DocumentVisibility.PRIVATE });

    render(
      wrap(
        <DocumentTagEditor
          document={doc}
          availableTags={[tag1, instTag]}
          canEdit={true}
          isOwner={true}
          onChanged={jest.fn()}
        />,
      ),
    );

    const input = screen.getByRole('combobox');
    fireEvent.mouseDown(input);
    fireEvent.click(input);

    // The institution tag renders as an option but is aria-disabled.
    const option = await screen.findByRole('option', { name: /Lehrgang/ });
    expect(option).toHaveAttribute('aria-disabled', 'true');
    // The disabled reason is surfaced inline.
    expect(
      screen.getByText('Nur für institutionsweit geteilte Dokumente'),
    ).toBeInTheDocument();
  });

  // (e) TF-382: on an INSTITUTION-visible document the same tag is selectable.
  it('(e) institution tag option is enabled on an institution document', async () => {
    const doc = makeDoc({ tags: [], visibility: DocumentVisibility.INSTITUTION });

    render(
      wrap(
        <DocumentTagEditor
          document={doc}
          availableTags={[tag1, instTag]}
          canEdit={true}
          isOwner={true}
          onChanged={jest.fn()}
        />,
      ),
    );

    const input = screen.getByRole('combobox');
    fireEvent.mouseDown(input);
    fireEvent.click(input);

    const option = await screen.findByRole('option', { name: /Lehrgang/ });
    expect(option).toHaveAttribute('aria-disabled', 'false');
  });

  // (f) TF-382: the proactive "create a tag by typing" hint is shown when editable.
  it('(f) shows the create-tag hint when canEdit', () => {
    const doc = makeDoc({ tags: [] });

    const { rerender } = render(
      wrap(
        <DocumentTagEditor
          document={doc}
          availableTags={[tag1]}
          canEdit={true}
          isOwner={true}
          onChanged={jest.fn()}
        />,
      ),
    );
    expect(
      screen.getByText(
        'Neuen Tag erstellen: einfach tippen und mit Enter bestätigen.',
      ),
    ).toBeInTheDocument();

    // Hidden when the user can't edit (no actionable path to surface).
    rerender(
      wrap(
        <DocumentTagEditor
          document={doc}
          availableTags={[tag1]}
          canEdit={false}
          isOwner={true}
          onChanged={jest.fn()}
        />,
      ),
    );
    expect(
      screen.queryByText(
        'Neuen Tag erstellen: einfach tippen und mit Enter bestätigen.',
      ),
    ).not.toBeInTheDocument();
  });

  // (g) TF-399: a non-owner may only remove their own personal tag chip; the
  //     shared institution chip has no delete affordance.
  it('(g) non-owner: only the personal tag chip is removable', async () => {
    mockDocumentService.detachDocumentTag.mockResolvedValue(undefined);
    const onChanged = jest.fn();
    const sharedTag: DocumentTag = {
      id: 9,
      name: 'Lehrgang',
      scope: 'institution',
      is_own: false,
      is_personal: false,
    };
    const personalTag: DocumentTag = {
      id: 5,
      name: 'Mathe',
      scope: 'user',
      is_own: true,
      is_personal: true,
    };
    const doc = makeDoc({
      tags: [sharedTag, personalTag],
      visibility: DocumentVisibility.INSTITUTION,
    });

    render(
      wrap(
        <DocumentTagEditor
          document={doc}
          availableTags={[]}
          canEdit
          isOwner={false}
          onChanged={onChanged}
        />,
      ),
    );

    // Exactly one chip delete button (CancelIcon) — the personal one.
    const cancelIcons = screen.getAllByTestId('CancelIcon');
    expect(cancelIcons).toHaveLength(1);
    fireEvent.click(cancelIcons[0]);

    await waitFor(() => {
      expect(mockDocumentService.detachDocumentTag).toHaveBeenCalledWith(
        42,
        personalTag.id,
      );
    });
    // The shared tag is never detached by a non-owner.
    expect(mockDocumentService.detachDocumentTag).not.toHaveBeenCalledWith(
      42,
      sharedTag.id,
    );
  });

  // (h) TF-399: a non-owner can attach a personal (user-scope) tag to a visible
  //     foreign doc, but the institution-scope option stays disabled.
  it('(h) non-owner can attach a user-scope tag; institution option disabled', async () => {
    const updatedDoc = makeDoc({ tags: [{ ...tag2, is_personal: true }] });
    mockDocumentService.attachDocumentTags.mockResolvedValue(updatedDoc);
    const onChanged = jest.fn();
    const doc = makeDoc({
      tags: [],
      visibility: DocumentVisibility.INSTITUTION,
    });

    render(
      wrap(
        <DocumentTagEditor
          document={doc}
          availableTags={[tag2, instTag]}
          canEdit
          isOwner={false}
          onChanged={onChanged}
        />,
      ),
    );

    const input = screen.getByRole('combobox');
    fireEvent.mouseDown(input);
    fireEvent.click(input);

    // The institution-scope option is offered but disabled for a non-owner.
    const instOption = await screen.findByRole('option', { name: /Lehrgang/ });
    expect(instOption).toHaveAttribute('aria-disabled', 'true');

    // The user-scope (personal) option is enabled → clicking it attaches.
    fireEvent.click(screen.getByText('Physik'));
    await waitFor(() => {
      expect(mockDocumentService.attachDocumentTags).toHaveBeenCalledWith(42, [
        tag2.id,
      ]);
    });
  });
});
