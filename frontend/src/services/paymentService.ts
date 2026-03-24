import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const ACCESS_TOKEN_KEY = 'examcraft_access_token';

export interface CheckoutSession {
    session_id: string;
    url: string;
}

export const paymentService = {
    createCheckoutSession: async (plan: string): Promise<CheckoutSession> => {
        const token = localStorage.getItem(ACCESS_TOKEN_KEY);

        const response = await axios.post<CheckoutSession>(
            `${API_URL}/api/v1/billing/create-checkout-session`,
            { plan },
            {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            }
        );
        return response.data;
    },
};
