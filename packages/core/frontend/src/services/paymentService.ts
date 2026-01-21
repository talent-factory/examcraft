import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const ACCESS_TOKEN_KEY = 'examcraft_access_token';

export interface CheckoutSession {
    session_id: string;
    url: string;
}

export interface SubscriptionDetails {
    id: string | null;
    status: string;
    tier: string;
    current_period_start: string | null;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
    canceled_at: string | null;
    plan: {
        id: string | null;
        amount?: number;
        currency: string;
        interval?: string;
    } | null;
    default_payment_method: PaymentMethod | null;
}

export interface Invoice {
    id: string;
    number: string | null;
    status: string;
    amount_due: number;
    amount_paid: number;
    currency: string;
    created: string;
    due_date: string | null;
    paid_at: string | null;
    invoice_pdf: string | null;
    hosted_invoice_url: string | null;
}

export interface PaymentMethod {
    id: string;
    type: string;
    card: {
        brand: string | null;
        last4: string | null;
        exp_month: number | null;
        exp_year: number | null;
    } | null;
}

export interface CustomerPortalSession {
    url: string;
}

const getAuthHeaders = () => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    return {
        headers: {
            Authorization: `Bearer ${token}`
        }
    };
};

export const paymentService = {
    createCheckoutSession: async (priceId: string): Promise<CheckoutSession> => {
        const response = await axios.post<CheckoutSession>(
            `${API_URL}/api/v1/billing/create-checkout-session`,
            {
                price_id: priceId,
                success_url: `${window.location.origin}/billing/success`,
                cancel_url: `${window.location.origin}/billing/cancel`,
            },
            getAuthHeaders()
        );
        return response.data;
    },

    getSubscription: async (): Promise<SubscriptionDetails> => {
        const response = await axios.get<SubscriptionDetails>(
            `${API_URL}/api/v1/billing/subscription`,
            getAuthHeaders()
        );
        return response.data;
    },

    getInvoices: async (limit: number = 10): Promise<Invoice[]> => {
        const response = await axios.get<Invoice[]>(
            `${API_URL}/api/v1/billing/invoices`,
            {
                ...getAuthHeaders(),
                params: { limit }
            }
        );
        return response.data;
    },

    getPaymentMethods: async (): Promise<PaymentMethod[]> => {
        const response = await axios.get<PaymentMethod[]>(
            `${API_URL}/api/v1/billing/payment-methods`,
            getAuthHeaders()
        );
        return response.data;
    },

    createCustomerPortalSession: async (): Promise<CustomerPortalSession> => {
        const response = await axios.post<CustomerPortalSession>(
            `${API_URL}/api/v1/billing/customer-portal`,
            {
                return_url: `${window.location.origin}/subscription`,
            },
            getAuthHeaders()
        );
        return response.data;
    },
};
