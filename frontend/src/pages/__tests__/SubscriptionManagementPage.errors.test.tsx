/**
 * SubscriptionManagementPage error rendering (TF-772 PR 7).
 *
 * The page had no test. It rendered `response.data.detail`, and for the portal
 * a hard-coded English sentence; both now go through appErrorFromAxios +
 * translateError.
 */

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import { SubscriptionManagementPage } from '../SubscriptionManagementPage';
import { paymentService, SubscriptionDetails } from '../../services/paymentService';

jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
  useLocation: () => ({ key: 'test', state: null }),
}));

jest.mock('../../services/paymentService', () => ({
  paymentService: {
    getSubscription: jest.fn(),
    getInvoices: jest.fn(),
    getPaymentMethods: jest.fn(),
    createCustomerPortalSession: jest.fn(),
  },
}));

const mocked = paymentService as jest.Mocked<typeof paymentService>;

const RAW = 'ROHER BACKEND-TEXT';

const axiosError = (status: number, data: Record<string, unknown>) =>
  Object.assign(new Error(`Request failed with status code ${status}`), {
    response: { status, data },
  });

const activeSubscription = {
  id: 'sub_1',
  status: 'active',
  tier: 'professional',
  current_period_start: null,
  current_period_end: null,
  cancel_at_period_end: false,
  canceled_at: null,
  plan: null,
  default_payment_method: null,
  is_billing_owner: true,
} as unknown as SubscriptionDetails;

beforeEach(() => {
  jest.clearAllMocks();
  mocked.getInvoices.mockResolvedValue([]);
  mocked.getPaymentMethods.mockResolvedValue([]);
});

describe('SubscriptionManagementPage errors', () => {
  it('renders the load fallback, not the backend detail', async () => {
    mocked.getSubscription.mockRejectedValue(axiosError(500, { detail: RAW }));

    render(<SubscriptionManagementPage />);

    expect(
      await screen.findByText('Abonnement-Daten konnten nicht geladen werden.'),
    ).toBeInTheDocument();
    expect(screen.queryByText(RAW)).not.toBeInTheDocument();
  });

  it('renders a coded portal error translated instead of the English literal', async () => {
    mocked.getSubscription.mockResolvedValue(activeSubscription);
    mocked.createCustomerPortalSession.mockRejectedValue(
      axiosError(403, { detail: RAW, error_code: 'billing_portal_owner_only' }),
    );

    render(<SubscriptionManagementPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Abonnement verwalten' }));

    expect(
      await screen.findByText(
        'Nur die abrechnungsverantwortliche Person kann die Abonnementeinstellungen verwalten.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(RAW)).not.toBeInTheDocument();
    expect(screen.queryByText('Failed to open subscription management')).not.toBeInTheDocument();
  });
});
