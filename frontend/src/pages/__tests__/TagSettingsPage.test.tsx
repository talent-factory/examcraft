import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TagSettingsPage from '../TagSettingsPage';

jest.mock('../../api/tagsApi', () => ({
  tagsApi: {
    listTags: jest.fn(),
  },
}));
import { tagsApi } from '../../api/tagsApi';
const mockListTags = tagsApi.listTags as jest.Mock;

let mockIsAdmin = false;
let mockIsSuperuser = false;
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, is_superuser: mockIsSuperuser },
    hasPermission: (p: string) => (mockIsAdmin && p === 'manage_settings') || p === 'create_questions',
  }),
}));

jest.mock('../../components/tags/TagCreateForm', () => ({ existingTags }: any) => <div data-testid="tag-create-form" />);
jest.mock('../../components/tags/TagRenameInline', () => () => <div />);
jest.mock('../../components/tags/TagMergeModal', () => () => <div />);

const makeTags = () => [
  { id: 1, name: 'EigenTag', scope: 'institution', is_own: true,  is_archived: false, usage_count: 2, institution_id: 10 },
  { id: 2, name: 'KollegeTag', scope: 'institution', is_own: false, is_archived: false, usage_count: 5, institution_id: 10 },
  { id: 3, name: 'GlobalTag', scope: 'global', is_own: false, is_archived: false, usage_count: 1, institution_id: null },
];

const renderPage = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TagSettingsPage />
    </QueryClientProvider>
  );
};

beforeEach(() => {
  mockIsAdmin = false;
  mockIsSuperuser = false;
  mockListTags.mockResolvedValue(makeTags());
});

describe('Titel', () => {
  it('rendert den Titel über den Sidebar-i18n-Key (TF-506)', async () => {
    // Regression: the title used to be hardcoded German ("Tag-Verwaltung"
    // directly in the JSX), which made it never translatable for en/fr/it. Now via
    // nav.sidebar.tagSettings, so it gets translated like the rest of the app.
    renderPage();
    await screen.findByText('#EigenTag');
    expect(screen.getByText('Tag-Verwaltung')).toBeInTheDocument();
  });
});

// Section headers render with a count suffix, e.g. "Meine Tags (1)". Tests
// match the header text via regex so they don't break when the count changes.
describe('Nicht-Admin Dozent', () => {
  it('zeigt Sektion "Meine Tags" für eigene Tags', async () => {
    renderPage();
    expect(await screen.findByText(/Meine Tags/)).toBeInTheDocument();
    expect(await screen.findByText('#EigenTag')).toBeInTheDocument();
  });

  it('zeigt Sektion "Tags der Institution" für fremde Tags', async () => {
    renderPage();
    expect(await screen.findByText(/Tags der Institution/)).toBeInTheDocument();
    expect(await screen.findByText('#KollegeTag')).toBeInTheDocument();
  });

  it('zeigt Edit-Button nur für eigene Tags', async () => {
    renderPage();
    await screen.findByText('#EigenTag');
    const editButtons = screen.getAllByRole('button', { name: 'Umbenennen' });
    expect(editButtons).toHaveLength(1);
  });

  it('versteckt Sektion "Tags der Institution" wenn keine fremden Tags existieren', async () => {
    mockListTags.mockResolvedValue([
      { id: 1, name: 'EigenTag', scope: 'institution', is_own: true, is_archived: false, usage_count: 2, institution_id: 10 },
    ]);
    renderPage();
    await screen.findByText('#EigenTag');
    expect(screen.queryByText(/Tags der Institution/)).not.toBeInTheDocument();
  });
});

describe('Admin', () => {
  beforeEach(() => { mockIsAdmin = true; });

  it('zeigt NICHT die Meine-Tags/Institution-Aufteilung sondern klassische Ansicht', async () => {
    renderPage();
    await screen.findByText('#EigenTag');
    expect(screen.queryByText(/Meine Tags/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Tags der Institution/)).not.toBeInTheDocument();
  });
});

describe('Superuser', () => {
  beforeEach(() => {
    mockIsAdmin = true;
    mockIsSuperuser = true;
  });

  it('zeigt globale Tags als editierbar (readonly: false)', async () => {
    renderPage();
    // Global tag and own tag are both visible
    await screen.findByText('#EigenTag');
    await screen.findByText('#GlobalTag');
    // Edit buttons: EigenTag + KollegeTag (institution, all editable for admin) + GlobalTag (editable for superuser)
    const editButtons = screen.getAllByRole('button', { name: 'Umbenennen' });
    expect(editButtons).toHaveLength(3);
  });

  it('zeigt normale Admin-Sektionsstruktur (keine Meine-Tags-Aufteilung)', async () => {
    renderPage();
    await screen.findByText('#EigenTag');
    expect(screen.queryByText(/Meine Tags/)).not.toBeInTheDocument();
  });
});
