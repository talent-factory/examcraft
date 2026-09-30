/**
 * /portfolio routes — permission, deployment and tier gating (TF-987).
 *
 * Renders the real `AppWithAuth` route table, so these tests fail if the
 * wiring there changes; everything around the portfolio pages is stubbed.
 * Without the permission the guard redirects to `/unauthorized`, which the
 * catch-all turns into `/dashboard` (stubbed below).
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { AppWithAuth, queryClient } from '../../../AppWithAuth';
import { portfolioApi } from '../../../api/portfolioApi';
import { AppError } from '../../../errors';
import { isFullDeployment } from '../../../utils/deploymentMode';

let mockPermissions: string[] = [];
jest.mock('../../../contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => ({
    user: { id: 1, is_superuser: false },
    isAuthenticated: true,
    isLoading: false,
    hasRole: () => false,
    hasPermission: (permission: string) => mockPermissions.includes(permission),
  }),
}));

jest.mock('../../../contexts/GenerationTasksContext', () => ({
  GenerationTasksProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock('../../../components/GenerationTasksBar', () => () => null);
jest.mock('../../../components/help/HelpWidgetGate', () => () => null);
jest.mock('../../../pages/Dashboard', () => ({ Dashboard: () => <div>dashboard</div> }));
jest.mock('../../../pages/Aktivitaeten', () => () => null);

let mockTier: string | null = 'professional';
let mockFeaturesLoading = false;
jest.mock('../../../hooks/useFeatures', () => ({
  useFeatures: () => ({ tier: mockTier, isLoading: mockFeaturesLoading, error: null }),
}));

// A jest.fn, not a closure over a `let`: componentLoader calls it while
// AppWithAuth is still being imported.
jest.mock('../../../utils/deploymentMode', () => ({
  ...jest.requireActual('../../../utils/deploymentMode'),
  isFullDeployment: jest.fn(() => true),
}));

jest.mock('../../../components/layout', () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

jest.mock('../../../api/portfolioApi', () => ({
  portfolioApi: {
    listAssessments: jest.fn(),
    listTemplates: jest.fn(),
    getAssessment: jest.fn(),
  },
}));

const api = portfolioApi as jest.Mocked<typeof portfolioApi>;

function renderAt(path: string) {
  window.history.pushState({}, '', path);
  return render(<AppWithAuth />);
}

beforeEach(() => {
  // AppWithAuth's QueryClient lives at module level and caches for 5 minutes;
  // without this a later test would read an earlier one's data.
  queryClient.clear();
  mockPermissions = [];
  mockTier = 'professional';
  mockFeaturesLoading = false;
  (isFullDeployment as jest.Mock).mockReturnValue(true);
  api.listAssessments.mockReset().mockResolvedValue({ items: [], total: 0, limit: 25, offset: 0 });
  api.listTemplates.mockReset().mockResolvedValue([]);
  api.getAssessment.mockReset();
});

describe('Portfolio-Routen — Berechtigungen', () => {
  it.each([
    ['/portfolio'],
    ['/portfolio/templates'],
    ['/portfolio/3f1c2d9e-0000-4000-8000-000000000000'],
  ])('%s ist ohne Portfolio-Recht nicht erreichbar', async (path) => {
    renderAt(path);
    expect(await screen.findByText('dashboard')).toBeInTheDocument();
    expect(api.listAssessments).not.toHaveBeenCalled();
    expect(api.listTemplates).not.toHaveBeenCalled();
    expect(api.getAssessment).not.toHaveBeenCalled();
  });

  it('/portfolio braucht portfolio_assessments:read, nicht nur Template-Rechte', async () => {
    mockPermissions = ['portfolio_templates:read'];
    renderAt('/portfolio');
    expect(await screen.findByText('dashboard')).toBeInTheDocument();
  });

  it('/portfolio/templates braucht portfolio_templates:read', async () => {
    mockPermissions = ['portfolio_assessments:read'];
    renderAt('/portfolio/templates');
    expect(await screen.findByText('dashboard')).toBeInTheDocument();
  });

  it('zeigt die Liste mit portfolio_assessments:read', async () => {
    mockPermissions = ['portfolio_assessments:read'];
    renderAt('/portfolio');
    expect(await screen.findByTestId('portfolio-assessments-page')).toBeInTheDocument();
    await waitFor(() => expect(api.listAssessments).toHaveBeenCalled());
    // Template link only with the template permission.
    expect(screen.queryByRole('link', { name: 'Templates' })).not.toBeInTheDocument();
  });

  it('zeigt die Templates mit portfolio_templates:read', async () => {
    mockPermissions = ['portfolio_templates:read'];
    renderAt('/portfolio/templates');
    expect(await screen.findByTestId('portfolio-templates-page')).toBeInTheDocument();
    await waitFor(() => expect(api.listTemplates).toHaveBeenCalled());
  });

  it('verlinkt die Templates aus der Liste, wenn beide Rechte vorhanden sind', async () => {
    mockPermissions = ['portfolio_assessments:read', 'portfolio_templates:read'];
    renderAt('/portfolio');
    expect(await screen.findByRole('link', { name: 'Templates' })).toHaveAttribute(
      'href',
      '/portfolio/templates',
    );
  });
});

describe('Portfolio-Routen — Deployment und Tier', () => {
  beforeEach(() => {
    mockPermissions = ['portfolio_assessments:read', 'portfolio_templates:read'];
  });

  it.each([['/portfolio'], ['/portfolio/templates'], ['/portfolio/a-1']])(
    'ruft auf %s im Core-Deployment keine Premium-API auf',
    async (path) => {
      (isFullDeployment as jest.Mock).mockReturnValue(false);
      renderAt(path);
      expect(await screen.findByText(/ist nicht verfügbar/)).toBeInTheDocument();
      expect(api.listAssessments).not.toHaveBeenCalled();
      expect(api.listTemplates).not.toHaveBeenCalled();
      expect(api.getAssessment).not.toHaveBeenCalled();
    },
  );

  it.each([['free'], ['starter']])(
    'zeigt bei Tier %s den Upgrade-Hinweis statt der Seite',
    async (tier) => {
      mockTier = tier;
      renderAt('/portfolio/templates');
      expect((await screen.findAllByText('Professional')).length).toBeGreaterThan(0);
      expect(screen.queryByTestId('portfolio-templates-page')).not.toBeInTheDocument();
      expect(api.listTemplates).not.toHaveBeenCalled();
    },
  );

  it.each([['professional'], ['enterprise'], [null]])(
    'lässt Tier %s durch (unbekannter Tier: Backend entscheidet)',
    async (tier) => {
      mockTier = tier;
      jest.spyOn(console, 'warn').mockImplementation(() => {});
      renderAt('/portfolio/templates');
      expect(await screen.findByTestId('portfolio-templates-page')).toBeInTheDocument();
      (console.warn as jest.Mock).mockRestore();
    },
  );

  it('fragt nichts ab, solange der Tier noch lädt', async () => {
    mockFeaturesLoading = true;
    renderAt('/portfolio');
    expect(await screen.findByRole('progressbar')).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-assessments-page')).not.toBeInTheDocument();
    expect(api.listAssessments).not.toHaveBeenCalled();
  });

  it('macht auf der Liste aus der Tier-Ablehnung des Backends einen Upgrade-Hinweis', async () => {
    api.listAssessments.mockRejectedValue(
      new AppError('portfolio_assessment_tier_insufficient', 'tier', 403),
    );
    renderAt('/portfolio');
    // AppWithAuth's client retries once, so the refusal arrives after a delay.
    expect(
      (await screen.findAllByText('Professional', {}, { timeout: 5000 })).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByTestId('portfolio-assessments-page')).not.toBeInTheDocument();
  });

  it('macht aus der Tier-Ablehnung des Backends einen Upgrade-Hinweis', async () => {
    api.getAssessment.mockRejectedValue(
      new AppError('portfolio_assessment_tier_insufficient', 'tier', 403),
    );
    renderAt('/portfolio/a-1');
    // The prompt names the required tier (and here also the current one);
    // the client retries once, so the refusal arrives after a delay.
    expect(
      (await screen.findAllByText('Professional', {}, { timeout: 5000 })).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByTestId('portfolio-detail-page')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
