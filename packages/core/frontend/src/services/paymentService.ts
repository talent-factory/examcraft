import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface CheckoutSession {
    session_id: string;
    url: string;
}

export const paymentService = {
    createCheckoutSession: async (priceId: string): Promise<CheckoutSession> => {
        const response = await axios.post(`${API_URL}/api/v1/billing/create-checkout-session`, {
            price_id: priceId,
            success_url: `${window.location.origin}/billing/success`,
            cancel_url: `${window.location.origin}/billing`,
        });
        return response.data;
    },
};
