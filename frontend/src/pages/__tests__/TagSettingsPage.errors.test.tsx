import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TagSettingsPage from '../TagSettingsPage';
import { tagsApi } from '../../api/tagsApi';

/**
 * Wiring test for the tag-management error path at all seven call sites in
 * TagCreateForm.tsx and TagSettingsPage.tsx (TagMergeModal.tsx has no error
 * handling of its own — its confirm button re-throws into TagSettingsPage's
 * mergeMutation). Deliberately NOT mocking TagCreateForm/TagRenameInline/
 * TagMergeModal (unlike TagSettingsPage.test.tsx): a swapped fallback code or
 * key only shows when the real component tree runs end to end.
 *
 * Until TF-773 Teil D these sites rendered the backend's raw `detail` through
 * `apiDetail()`, which was right only as long as the reader spoke German. Now
 * `tags.py` sends an `error_code`, `codes/tags.ts` registers it, and the sites
 * go through `translateError(appErrorFromAxios(...))` like every other
 * component. Every case below therefore sends a German `detail` *and* a code,
 * and asserts the translated text for the code: the `detail` must never be
 * what the user reads.
 *
 * The language test switches the mocked UI language to French. That is the
 * regression `apiDetail()` could not pass — and it goes red when the code is
 * removed from `codes/tags.ts`, because `selectCode()` then drops it and the
 * generic fallback appears instead.
 */

// Overrides the de-only mock from setupTests.ts for this file: same
// resolution rules, but the language can be switched per test.
let mockLanguage: 'de' | 'fr' = 'de';
jest.mock('react-i18next', () => {
  const mockTranslations: Record<string, Record<string, unknown>> = {
    de: require('../../locales/de/translation.json'),
    fr: require('../../locales/fr/translation.json'),
  };
  const resolve = (key: string): string => {
    let current: unknown = mockTranslations[mockLanguage];
    for (const part of key.split('.')) {
      if (current == null || typeof current !== 'object') return key;
      current = (current as Record<string, unknown>)[part];
    }
    return typeof current === 'string' ? current : key;
  };
  const t = (key: string) => resolve(key);
  const i18n = { changeLanguage: jest.fn(), language: 'de' };
  return {
    useTranslation: () => ({ t, i18n }),
    Trans: ({ children }: { children: unknown }) => children,
    initReactI18next: { type: '3rdParty', init: jest.fn() },
  };
});

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

// TF-838 (PR #286 review): mocked so this suite doesn't fire real, unmocked
// heartbeat POSTs as a side effect on every render.
jest.mock('../../hooks/useActivityHeartbeat', () => ({
  useActivityHeartbeat: jest.fn(),
}));

// Shape of an ADR 0005 response as axios rejects it. The German `detail` is
// what tags.py actually sends; it is here so each test can prove it is NOT
// rendered.
const axiosCodedError = (status: number, errorCode: string, detail: string) => ({
  response: { status, data: { detail, error_code: errorCode } },
});
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
  mockLanguage = 'de';
  // TagSettingsPage defaults to filter='active' (persisted in localStorage),
  // which hides archived tags — several cases below need an archived tag visible.
  localStorage.setItem('tagSettings.filter', 'all');
});

const renameAlphaTo = async (newName: string) => {
  await screen.findByText('#Alpha');
  fireEvent.click(screen.getByRole('button', { name: /Umbenennen|Renommer/ }));
  const input = screen.getByDisplayValue('Alpha');
  fireEvent.change(input, { target: { value: newName } });
  fireEvent.keyDown(input, { key: 'Enter' });
};

describe('Tags-Meldungen folgen der UI-Sprache (TF-773 Teil D)', () => {
  it('zeigt auf Französisch den französischen Satz zum Code, nicht das deutsche detail', async () => {
    mockLanguage = 'fr';
    (tagsApi.listTags as jest.Mock).mockResolvedValue([activeTag()]);
    (tagsApi.renameTag as jest.Mock).mockRejectedValueOnce(
      axiosCodedError(409, 'tags_name_exists_on_rename', 'Ein Tag mit diesem Namen existiert bereits.'),
    );
    renderPage();

    await renameAlphaTo('AlphaNeu');

    expect(await screen.findByText('Un tag portant ce nom existe déjà.')).toBeInTheDocument();
    expect(screen.queryByText('Ein Tag mit diesem Namen existiert bereits.')).not.toBeInTheDocument();
    expect(screen.queryByText('Échec du renommage.')).not.toBeInTheDocument();
  });

  it('zeigt auf Deutsch denselben Code als deutschen Satz', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([activeTag()]);
    (tagsApi.renameTag as jest.Mock).mockRejectedValueOnce(
      axiosCodedError(409, 'tags_name_exists_on_rename', 'A tag with this name already exists.'),
    );
    renderPage();

    await renameAlphaTo('AlphaNeu');

    expect(await screen.findByText('Ein Tag mit diesem Namen existiert bereits.')).toBeInTheDocument();
    expect(screen.queryByText('A tag with this name already exists.')).not.toBeInTheDocument();
  });
});

describe('TagCreateForm — Fehlerpfad', () => {
  beforeEach(() => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([]);
  });

  it('zeigt den Satz zum Backend-Code', async () => {
    (tagsApi.createTag as jest.Mock).mockRejectedValueOnce(
      axiosCodedError(409, 'tags_name_exists', 'roh: Tag existiert'),
    );
    renderPage();

    const input = await screen.findByPlaceholderText('Tag-Name eingeben...');
    fireEvent.change(input, { target: { value: 'Duplikat' } });
    fireEvent.click(screen.getByRole('button', { name: 'Tag erstellen' }));

    expect(await screen.findByText('Tag mit diesem Namen existiert bereits.')).toBeInTheDocument();
    expect(screen.queryByText('roh: Tag existiert')).not.toBeInTheDocument();
  });

  it('fällt ohne Antwort auf die Standardmeldung zurück', async () => {
    (tagsApi.createTag as jest.Mock).mockRejectedValueOnce(networkError());
    renderPage();

    const input = await screen.findByPlaceholderText('Tag-Name eingeben...');
    fireEvent.change(input, { target: { value: 'Neu' } });
    fireEvent.click(screen.getByRole('button', { name: 'Tag erstellen' }));

    expect(await screen.findByText('Tag konnte nicht erstellt werden.')).toBeInTheDocument();
  });

  it('wiederherstellen bei Namenskollision mit einem archivierten Tag zeigt den Satz zum Backend-Code', async () => {
    // Eigener unarchiveMutation-Errorpfad von TagCreateForm (Zeile 49-57),
    // ausgelöst über den Restore-Button IN der Create-Form, nicht die
    // Zeile in TagSettingsPages Liste (die hat ihren eigenen, separat
    // getesteten unarchiveMutation weiter unten). filter='active' hält den
    // archivierten Tag aus der Liste, sonst rendert ein zweiter,
    // gleichnamiger „Wiederherstellen"-Button.
    localStorage.setItem('tagSettings.filter', 'active');
    (tagsApi.listTags as jest.Mock).mockResolvedValue([archivedTag({ name: 'Beta' })]);
    (tagsApi.unarchiveTag as jest.Mock).mockRejectedValueOnce(
      axiosCodedError(403, 'tags_access_denied', 'roh: verweigert'),
    );
    renderPage();

    const input = await screen.findByPlaceholderText('Tag-Name eingeben...');
    fireEvent.change(input, { target: { value: 'Beta' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Wiederherstellen' }));

    expect(await screen.findByText('Zugriff verweigert.')).toBeInTheDocument();
    expect(screen.queryByText('roh: verweigert')).not.toBeInTheDocument();
  });
});

describe('TagSettingsPage — Fehlerpfad: archive/unarchive/rename/delete/merge', () => {
  it('archivieren: zeigt den Satz zum Backend-Code', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([activeTag()]);
    (tagsApi.archiveTag as jest.Mock).mockRejectedValueOnce(
      axiosCodedError(404, 'tags_not_found', 'roh: nicht gefunden'),
    );
    renderPage();

    await screen.findByText('#Alpha');
    fireEvent.click(screen.getByRole('button', { name: 'Archivieren' }));

    expect(await screen.findByText('Tag nicht gefunden.')).toBeInTheDocument();
  });

  it('archivieren: fällt ohne Antwort auf die Standardmeldung zurück', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([activeTag()]);
    (tagsApi.archiveTag as jest.Mock).mockRejectedValueOnce(networkError());
    renderPage();

    await screen.findByText('#Alpha');
    fireEvent.click(screen.getByRole('button', { name: 'Archivieren' }));

    expect(await screen.findByText('Archivieren fehlgeschlagen.')).toBeInTheDocument();
  });

  it('wiederherstellen: zeigt den Satz zum Backend-Code', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([archivedTag()]);
    (tagsApi.unarchiveTag as jest.Mock).mockRejectedValueOnce(
      axiosCodedError(403, 'tags_access_denied', 'roh: verweigert'),
    );
    renderPage();

    await screen.findByText('#Beta');
    fireEvent.click(screen.getByRole('button', { name: 'Wiederherstellen' }));

    expect(await screen.findByText('Zugriff verweigert.')).toBeInTheDocument();
  });

  it('wiederherstellen: fällt ohne Antwort auf die Standardmeldung zurück', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([archivedTag()]);
    (tagsApi.unarchiveTag as jest.Mock).mockRejectedValueOnce(networkError());
    renderPage();

    await screen.findByText('#Beta');
    fireEvent.click(screen.getByRole('button', { name: 'Wiederherstellen' }));

    expect(await screen.findByText('Wiederherstellen fehlgeschlagen.')).toBeInTheDocument();
  });

  it('umbenennen: fällt ohne Antwort auf die Standardmeldung zurück', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([activeTag()]);
    (tagsApi.renameTag as jest.Mock).mockRejectedValueOnce(networkError());
    renderPage();

    await renameAlphaTo('AlphaNeu');

    expect(await screen.findByText('Umbenennen fehlgeschlagen.')).toBeInTheDocument();
  });

  it('löschen: zeigt den Satz zum Backend-Code', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([archivedTag({ usage_count: 0 })]);
    (tagsApi.deleteTag as jest.Mock).mockRejectedValueOnce(
      axiosCodedError(422, 'tags_still_in_use', 'roh: in Gebrauch'),
    );
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage();

    await screen.findByText('#Beta');
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));

    expect(await screen.findByText('Tag wird noch von Fragen verwendet.')).toBeInTheDocument();
    confirmSpy.mockRestore();
  });

  it('löschen: fällt ohne Antwort auf die Standardmeldung zurück', async () => {
    (tagsApi.listTags as jest.Mock).mockResolvedValue([archivedTag({ usage_count: 0 })]);
    (tagsApi.deleteTag as jest.Mock).mockRejectedValueOnce(networkError());
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage();

    await screen.findByText('#Beta');
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));

    expect(await screen.findByText('Löschen fehlgeschlagen.')).toBeInTheDocument();
    confirmSpy.mockRestore();
  });

  it('zusammenführen: zeigt den Satz zum Backend-Code', async () => {
    const tagA = activeTag({ id: 1, name: 'Alpha' });
    const tagB = activeTag({ id: 3, name: 'Gamma' });
    (tagsApi.listTags as jest.Mock).mockResolvedValue([tagA, tagB]);
    (tagsApi.mergeTags as jest.Mock).mockRejectedValueOnce(
      axiosCodedError(422, 'tags_merge_target_in_sources', 'roh: Ziel in Quellen'),
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
      await screen.findByText('Ziel-Tag darf nicht unter den Quell-Tags sein.'),
    ).toBeInTheDocument();
  });

  it('zusammenführen: fällt ohne Antwort auf die Standardmeldung zurück', async () => {
    const tagA = activeTag({ id: 1, name: 'Alpha' });
    const tagB = activeTag({ id: 3, name: 'Gamma' });
    (tagsApi.listTags as jest.Mock).mockResolvedValue([tagA, tagB]);
    (tagsApi.mergeTags as jest.Mock).mockRejectedValueOnce(networkError());
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

    expect(await screen.findByText('Zusammenführen fehlgeschlagen.')).toBeInTheDocument();
  });
});
