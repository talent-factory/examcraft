import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import SubscriptionTierOverview from '../SubscriptionTierOverview';
import RBACService from '../../../services/RBACService';
import { SubscriptionTier, TierQuota } from '../../../types/rbac';

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
});
