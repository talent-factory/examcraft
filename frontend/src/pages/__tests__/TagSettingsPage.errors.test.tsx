import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TagSettingsPage from '../TagSettingsPage';
import { tagsApi } from '../../api/tagsApi';

/**
 * Wiring test for the `apiDetail() ?? translateError(...)` invariant at all
 * 7 real call sites of `apiDetail` in TagCreateForm.tsx and TagSettingsPage.tsx
 * (TagMergeModal.tsx itself has no error handling of its own — its confirm
 * button just re-throws into TagSettingsPage's mergeMutation). Deliberately
 * NOT mocking TagCreateForm/TagRenameInline/TagMergeModal (unlike
 * TagSettingsPage.test.tsx), because the bug this test guards against — a
 * swapped fallback key, or apiDetail() precedence broken by a refactor — can
 * only be caught by exercising the real component tree end to end.
 *
 * apiDetail is the one deliberate exception to "never show raw error text":
 * the Tags API answers in German, so its `detail` string is meant to reach
 * the UI verbatim. Every test below asserts BOTH directions: a `detail`
 * present shows German backend prose, and a `detail` absent falls back to
 * the generic translated message — proving the `??` precedence actually
 * works, not just that one branch happens to render something.
 */

jest.mock('../../api/tagsApi', () => ({
  tagsApi: {
    listTags: jest.fn(),
    createTag: jest.fn(),
    unarchiveTag: jest.fn(),
    renameTag: jest.fn(),
    archiveTag: jest.fn(),
    mergeTags: jest.fn(),
    deleteTag: jest.fn(),
  },
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, is_superuser: false },
    hasPermission: (p: string) => p === 'manage_settings' || p === 'create_questions',
  }),
}));

const axiosDetailError = (detail: string) => ({ response: { data: { detail } } });
const networkError = () => new Error('Network Error');

const activeTag = (overrides: Partial<{ id: number; name: string; usage_count: number }> = {}) => ({
  id: 1,
  name: 'Alpha',
  scope: 'institution' as const,
  is_own: true,
  is_archived: false,
  usage_count: 0,
  institution_id: 10,
  ...overrides,
});

const archivedTag = (overrides: Partial<{ id: number; name: string; usage_count: number }> = {}) => ({
  id: 2,
  name: 'Beta',
  scope: 'institution' as const,
  is_own: true,
  is_archived: true,
  usage_count: 0,
  institution_id: 10,
  ...overrides,
});

const renderPage = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TagSettingsPage />
    </QueryClientProvider>,
  );
};

beforeEach(() => {
  jest.clearAllMocks();
  // TagSettingsPage defaults to filter='active' (persisted in localStorage),
  // which hides archived tags — several cases below need an archived tag visible.
  localStorage.setItem('tagSettings.filter', 'all');
});

describe('TagCreateForm — apiDetail-Verdrahtung', () => {
  beforeEach(() => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([]);
  });

  it('zeigt die deutsche Backend-Meldung, wenn apiDetail() eine liefert', async () => {
    (tagsApi.createTag as jest.Mock).mockRejectedValueOnce(
      axiosDetailError('Ein Tag mit diesem Namen existiert bereits in dieser Institution.'),
    );
    renderPage();

    const input = await screen.findByPlaceholderText('Tag-Name eingeben...');
    fireEvent.change(input, { target: { value: 'Duplikat' } });
    fireEvent.click(screen.getByRole('button', { name: 'Tag erstellen' }));

    expect(
      await screen.findByText('Ein Tag mit diesem Namen existiert bereits in dieser Institution.'),
    ).toBeInTheDocument();
  });

  it('fällt auf die übersetzte Standardmeldung zurück, wenn kein Backend-Detail vorliegt', async () => {
    (tagsApi.createTag as jest.Mock).mockRejectedValueOnce(networkError());
    renderPage();

    const input = await screen.findByPlaceholderText('Tag-Name eingeben...');
    fireEvent.change(input, { target: { value: 'Neu' } });
    fireEvent.click(screen.getByRole('button', { name: 'Tag erstellen' }));

    expect(await screen.findByText('Tag konnte nicht erstellt werden.')).toBeInTheDocument();
  });
});

describe('TagSettingsPage — apiDetail-Verdrahtung: archive/unarchive/rename/delete/merge', () => {
  it('archivieren: zeigt Backend-Detail statt Fallback', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([activeTag()]);
    (tagsApi.archiveTag as jest.Mock).mockRejectedValueOnce(
      axiosDetailError('Tag wird noch von Fragen verwendet.'),
    );
    renderPage();

    await screen.findByText('#Alpha');
    fireEvent.click(screen.getByRole('button', { name: 'Archivieren' }));

    expect(await screen.findByText('Tag wird noch von Fragen verwendet.')).toBeInTheDocument();
  });

  it('archivieren: fällt ohne Backend-Detail auf die Standardmeldung zurück', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([activeTag()]);
    (tagsApi.archiveTag as jest.Mock).mockRejectedValueOnce(networkError());
    renderPage();

    await screen.findByText('#Alpha');
    fireEvent.click(screen.getByRole('button', { name: 'Archivieren' }));

    expect(await screen.findByText('Archivieren fehlgeschlagen.')).toBeInTheDocument();
  });

  it('wiederherstellen: zeigt Backend-Detail statt Fallback', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([archivedTag()]);
    (tagsApi.unarchiveTag as jest.Mock).mockRejectedValueOnce(
      axiosDetailError('Tag ist nicht archiviert.'),
    );
    renderPage();

    await screen.findByText('#Beta');
    fireEvent.click(screen.getByRole('button', { name: 'Wiederherstellen' }));

    expect(await screen.findByText('Tag ist nicht archiviert.')).toBeInTheDocument();
  });

  it('umbenennen: zeigt Backend-Detail statt Fallback', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([activeTag()]);
    (tagsApi.renameTag as jest.Mock).mockRejectedValueOnce(
      axiosDetailError('Ein Tag mit diesem Namen existiert bereits.'),
    );
    renderPage();

    await screen.findByText('#Alpha');
    fireEvent.click(screen.getByRole('button', { name: 'Umbenennen' }));
    const input = screen.getByDisplayValue('Alpha');
    fireEvent.change(input, { target: { value: 'AlphaNeu' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(await screen.findByText('Ein Tag mit diesem Namen existiert bereits.')).toBeInTheDocument();
  });

  it('umbenennen: fällt ohne Backend-Detail auf die Standardmeldung zurück', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([activeTag()]);
    (tagsApi.renameTag as jest.Mock).mockRejectedValueOnce(networkError());
    renderPage();

    await screen.findByText('#Alpha');
    fireEvent.click(screen.getByRole('button', { name: 'Umbenennen' }));
    const input = screen.getByDisplayValue('Alpha');
    fireEvent.change(input, { target: { value: 'AlphaNeu' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(await screen.findByText('Umbenennen fehlgeschlagen.')).toBeInTheDocument();
  });

  it('löschen: zeigt Backend-Detail statt Fallback', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([archivedTag({ usage_count: 0 })]);
    (tagsApi.deleteTag as jest.Mock).mockRejectedValueOnce(
      axiosDetailError('Tag konnte nicht gelöscht werden: wird noch verwendet.'),
    );
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage();

    await screen.findByText('#Beta');
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));

    expect(
      await screen.findByText('Tag konnte nicht gelöscht werden: wird noch verwendet.'),
    ).toBeInTheDocument();
    confirmSpy.mockRestore();
  });

  it('löschen: fällt ohne Backend-Detail auf die Standardmeldung zurück', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([archivedTag({ usage_count: 0 })]);
    (tagsApi.deleteTag as jest.Mock).mockRejectedValueOnce(networkError());
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage();

    await screen.findByText('#Beta');
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));

    expect(await screen.findByText('Löschen fehlgeschlagen.')).toBeInTheDocument();
    confirmSpy.mockRestore();
  });

  it('zusammenführen: zeigt Backend-Detail statt Fallback', async () => {
    const tagA = activeTag({ id: 1, name: 'Alpha' });
    const tagB = activeTag({ id: 3, name: 'Gamma' });
    (tagsApi.listTags as jest.Mock).mockResolvedValue([tagA, tagB]);
    (tagsApi.mergeTags as jest.Mock).mockRejectedValueOnce(
      axiosDetailError('Zusammenführen fehlgeschlagen: Ziel-Tag existiert nicht mehr.'),
    );
    renderPage();

    await screen.findByText('#Alpha');
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);

    fireEvent.click(await screen.findByRole('button', { name: /zusammenführen/i }));
    const select = await screen.findByRole('combobox');
    fireEvent.mouseDown(select);
    fireEvent.click(await screen.findByRole('option', { name: /#Alpha/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Zusammenführen' }));

    expect(
      await screen.findByText('Zusammenführen fehlgeschlagen: Ziel-Tag existiert nicht mehr.'),
    ).toBeInTheDocument();
  });
});
