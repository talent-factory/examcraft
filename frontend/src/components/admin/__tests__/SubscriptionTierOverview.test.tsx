import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme, alpha } from '@mui/material/styles';
import SubscriptionTierOverview from '../SubscriptionTierOverview';
import RBACService from '../../../services/RBACService';
import { SubscriptionTier, TierQuota, TIER_COLORS } from '../../../types/rbac';

// react-i18next is mocked globally in setupTests.ts (resolves keys against
// locales/de/translation.json) — no local mock needed here.

jest.mock('../../../services/RBACService');
const mockedService = RBACService as jest.Mocked<typeof RBACService>;

const tiers: SubscriptionTier[] = [
  {
    id: 'tier_free',
    name: 'free',
    display_name: 'Free',
    description: 'Free tier',
    price_monthly: 0,
    price_yearly: 0,
    is_active: true,
    sort_order: 0,
  },
  {
    id: 'tier_enterprise',
    name: 'enterprise',
    display_name: 'Enterprise',
    description: 'Enterprise tier',
    price_monthly: 149,
    price_yearly: 1490,
    is_active: true,
    sort_order: 3,
  },
];

const quotasByTier: Record<string, TierQuota[]> = {
  tier_free: [
    { tier_id: 'tier_free', resource_type: 'documents', quota_limit: 5 },
    { tier_id: 'tier_free', resource_type: 'questions_per_month', quota_limit: 20 },
    { tier_id: 'tier_free', resource_type: 'users', quota_limit: 1 },
    { tier_id: 'tier_free', resource_type: 'storage_mb', quota_limit: 100 },
  ],
  tier_enterprise: [
    { tier_id: 'tier_enterprise', resource_type: 'documents', quota_limit: -1 },
    { tier_id: 'tier_enterprise', resource_type: 'questions_per_month', quota_limit: -1 },
    { tier_id: 'tier_enterprise', resource_type: 'users', quota_limit: -1 },
    { tier_id: 'tier_enterprise', resource_type: 'storage_mb', quota_limit: -1 },
  ],
};

const theme = createTheme();
const renderComponent = () =>
  render(
    <ThemeProvider theme={theme}>
      <SubscriptionTierOverview />
    </ThemeProvider>,
  );

describe('SubscriptionTierOverview', () => {
  beforeEach(() => {
    mockedService.listSubscriptionTiers.mockResolvedValue(tiers);
    mockedService.getTierQuotas.mockImplementation(async (tierId: string) => quotasByTier[tierId] ?? []);
    // Default: admin's own institution is on the Free tier (not the highest
    // one in the `tiers` fixture, which is Enterprise) — individual tests
    // override this to exercise the "already on the highest tier" branch.
    mockedService.getMyTier.mockResolvedValue(tiers[0]);
  });
  afterEach(() => jest.clearAllMocks());

  it('shows the commercial-tiering footnote only for the Enterprise users row, not for other unlimited resources', async () => {
    renderComponent();

    await waitFor(() => expect(screen.getAllByText('Unlimited').length).toBeGreaterThan(0));

    // Footnote appears exactly once (Enterprise x users), not for Enterprise's other
    // unlimited resources (documents, questions_per_month, storage_mb).
    expect(
      screen.getAllByText(/10 Benutzer inklusive, \+CHF 10\/Benutzer ab dem 11\./)
    ).toHaveLength(1);
  });

  it('does not show the footnote for a non-Enterprise tier, even with an unlimited users value', async () => {
    // Free tier also reports unlimited users here — the footnote must still only
    // appear once (for Enterprise), proving the gate checks tier.id, not just the
    // resource type / value being unlimited.
    mockedService.getTierQuotas.mockImplementation(async (tierId: string) =>
      tierId === 'tier_free'
        ? [{ tier_id: 'tier_free', resource_type: 'users', quota_limit: -1 }]
        : (quotasByTier[tierId] ?? [])
    );

    renderComponent();

    await waitFor(() => expect(screen.getAllByText('Unlimited').length).toBeGreaterThan(0));

    expect(
      screen.getAllByText(/10 Benutzer inklusive, \+CHF 10\/Benutzer ab dem 11\./)
    ).toHaveLength(1);
  });

  it('shows the commercial-tiering explainer in the info note at the bottom', async () => {
    renderComponent();

    expect(
      await screen.findByText(/kommerziell \(nicht technisch\) gestaffelt/)
    ).toBeInTheDocument();
  });

  it('does not show the footnote for Enterprise users when the quota is a finite value', async () => {
    // Guards the isEnterpriseUsersRow gate independently of the value === -1
    // branch it's currently nested in: if a future change hoists the gate out
    // of that branch (e.g. to also annotate a finite Enterprise user quota),
    // this test fails instead of silently regressing.
    mockedService.getTierQuotas.mockImplementation(async (tierId: string) =>
      tierId === 'tier_enterprise'
        ? [
            { tier_id: 'tier_enterprise', resource_type: 'users', quota_limit: 25 },
            { tier_id: 'tier_enterprise', resource_type: 'documents', quota_limit: -1 },
          ]
        : (quotasByTier[tierId] ?? [])
    );

    renderComponent();

    expect(await screen.findByText('25')).toBeInTheDocument();

    expect(
      screen.queryByText(/10 Benutzer inklusive, \+CHF 10\/Benutzer ab dem 11\./)
    ).not.toBeInTheDocument();
  });

  it('hides the info-note explainer when no Enterprise tier is present', async () => {
    mockedService.listSubscriptionTiers.mockResolvedValue(
      tiers.filter((tier) => tier.id !== 'tier_enterprise')
    );

    renderComponent();

    expect(
      await screen.findByText(/Ressourcen-Limits werden monatlich zurückgesetzt/)
    ).toBeInTheDocument();

    expect(
      screen.queryByText(/kommerziell \(nicht technisch\) gestaffelt/)
    ).not.toBeInTheDocument();
  });

  it("marks the admin's own (non-top) tier with a 'your current tier' chip instead of the generic 'Available' chip", async () => {
    // Own tier defaults to Free (beforeEach) — not the highest tier, so the
    // price-card grid still renders, but the Free card is singled out.
    renderComponent();

    await waitFor(() => expect(screen.getAllByText('CHF 0.00').length).toBeGreaterThan(0));

    // Own-tier chip appears twice: once on the Free price card, once in the
    // resource-limits table's Free column header.
    expect(screen.getAllByText('Dein aktueller Tarif')).toHaveLength(2);

    // Enterprise isn't the admin's own tier here, so it keeps the generic chip.
    expect(screen.getByText('Verfügbar')).toBeInTheDocument();
  });

  it('replaces the price cards with a current-tier note when the institution is already on the highest tier', async () => {
    mockedService.getMyTier.mockResolvedValue(tiers[1]); // Enterprise — highest sort_order in the fixture

    renderComponent();

    expect(await screen.findByText(/Dein aktueller Tarif: Enterprise/)).toBeInTheDocument();
    expect(
      screen.getByText(/bereits im höchsten verfügbaren Tarif/)
    ).toBeInTheDocument();

    // No price cards (and thus no generic "Verfügbar" chips or list prices) are rendered.
    expect(screen.queryByText('Verfügbar')).not.toBeInTheDocument();
    expect(screen.queryByText('CHF 149.00')).not.toBeInTheDocument();

    // The resource-limits table (and its own-tier column highlight) still renders.
    expect(await screen.findByText('Ressource')).toBeInTheDocument();
    expect(screen.getByText('Dein aktueller Tarif')).toBeInTheDocument();
  });

  it('renders normally without own-tier highlighting when the own-tier lookup fails', async () => {
    mockedService.getMyTier.mockRejectedValue(new Error('not found'));

    renderComponent();

    await waitFor(() => expect(screen.getAllByText('CHF 0.00').length).toBeGreaterThan(0));

    // Both cards fall back to the generic chip since no tier is "own tier".
    expect(screen.getAllByText('Verfügbar')).toHaveLength(2);
    expect(screen.queryByText('Dein aktueller Tarif')).not.toBeInTheDocument();
  });

  it("highlights the own tier's column in the resource-limits table body, not just the header", async () => {
    // Own tier defaults to Free (beforeEach). Beyond the header chip (covered by
    // the test above), every body cell in the admin's own-tier column gets a
    // faint background tint — verify it's applied to the Free column and not to
    // the Enterprise column, for a row with an actual value (not just the header).
    renderComponent();

    await screen.findByText('Dokumente');
    const row = screen
      .getAllByRole('row')
      .find((candidate) => within(candidate).queryByText('Dokumente'));
    expect(row).not.toBeUndefined();
    const [freeCell, enterpriseCell] = within(row as HTMLElement).getAllByRole('cell');

    expect(freeCell).toHaveStyle({ backgroundColor: alpha(TIER_COLORS.tier_free, 0.06) });
    expect(enterpriseCell).not.toHaveStyle({ backgroundColor: alpha(TIER_COLORS.tier_free, 0.06) });
  });

  it('treats only the first tier encountered as "highest" when sort_order is tied, not every tier sharing the max value', async () => {
    // Documents the reduce's strict `>` tie-break: with two tiers sharing the
    // max sort_order, only the first one encountered in `tiers` counts as "the
    // highest tier". An institution on the *second*, equally-ranked tier still
    // sees the regular price-card grid, not the "already at the highest tier"
    // alert — a case worth pinning down since ties aren't validated against.
    const tiedTiers: SubscriptionTier[] = [
      { ...tiers[1], id: 'tier_pro_a', name: 'pro_a', display_name: 'Pro A', sort_order: 3 },
      { ...tiers[1], id: 'tier_pro_b', name: 'pro_b', display_name: 'Pro B', sort_order: 3 },
    ];
    mockedService.listSubscriptionTiers.mockResolvedValue(tiedTiers);
    mockedService.getMyTier.mockResolvedValue(tiedTiers[1]); // the *second* tied tier

    renderComponent();

    await waitFor(() => expect(screen.getAllByText('Pro B').length).toBeGreaterThan(0));

    expect(
      screen.queryByText(/bereits im höchsten verfügbaren Tarif/)
    ).not.toBeInTheDocument();
    // Pro B is still recognized as the admin's own tier via the regular chip
    // (once on its price card, once in the resource-limits table header).
    expect(screen.getAllByText('Dein aktueller Tarif')).toHaveLength(2);
  });

  it('degrades like a failed lookup when getMyTier resolves to a tier absent from the tiers list', async () => {
    // Simulates /tiers and /tiers/my briefly diverging (e.g. the institution is
    // on a tier listSubscriptionTiers() no longer returns) — myTier is non-null
    // but matches no tier.id in `tiers`, so no comparison ever succeeds. Should
    // degrade the same way as a failed lookup rather than mis-highlighting an
    // unrelated tier or crashing.
    mockedService.getMyTier.mockResolvedValue({
      id: 'tier_legacy',
      name: 'legacy',
      display_name: 'Legacy',
      description: 'Deprecated tier',
      price_monthly: 10,
      price_yearly: 100,
      is_active: false,
      sort_order: 1,
    });

    renderComponent();

    await waitFor(() => expect(screen.getAllByText('CHF 0.00').length).toBeGreaterThan(0));

    expect(screen.getAllByText('Verfügbar')).toHaveLength(2);
    expect(screen.queryByText('Dein aktueller Tarif')).not.toBeInTheDocument();
    expect(
      screen.queryByText(/bereits im höchsten verfügbaren Tarif/)
    ).not.toBeInTheDocument();
  });

  it('renders without crashing when no tiers are available', async () => {
    mockedService.listSubscriptionTiers.mockResolvedValue([]);

    renderComponent();

    expect(await screen.findByText('Ressource')).toBeInTheDocument();
    expect(screen.queryByText('Verfügbar')).not.toBeInTheDocument();
    expect(
      screen.queryByText(/bereits im höchsten verfügbaren Tarif/)
    ).not.toBeInTheDocument();
  });
});
