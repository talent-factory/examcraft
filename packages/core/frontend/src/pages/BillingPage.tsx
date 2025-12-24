import React, { useState } from 'react';
import { paymentService } from '../services/paymentService';

// This would strictly come from specific environment configuration or API in real app
// For foundation, we use a placeholder that matches the plan
const STARTER_PRICE_ID = 'price_placeholder_starter';

export const BillingPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubscribe = async (priceId: string) => {
        setLoading(true);
        setError(null);
        try {
            const session = await paymentService.createCheckoutSession(priceId);
            // Redirect to Stripe Checkout
            window.location.href = session.url;
        } catch (err: any) {
            console.error('Subscription error:', err);
            setError('Failed to start subscription process. Please try again.');
            setLoading(false);
        }
    };

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div className="text-center">
                <h2 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
                    Pricing Plans
                </h2>
                <p className="mt-4 text-xl text-gray-600">
                    Choose the plan that fits your needs.
                </p>
            </div>

            {error && (
                <div className="mt-8 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative" role="alert">
                    <span className="block sm:inline">{error}</span>
                </div>
            )}

            <div className="mt-12 space-y-4 sm:mt-16 sm:space-y-0 sm:grid sm:grid-cols-2 sm:gap-6 lg:max-w-4xl lg:mx-auto xl:max-w-none xl:mx-0 xl:grid-cols-3">
                {/* Free Tier */}
                <div className="border border-gray-200 rounded-lg shadow-sm divide-y divide-gray-200 bg-white">
                    <div className="p-6">
                        <h2 className="text-lg leading-6 font-medium text-gray-900">Free</h2>
                        <p className="mt-4">
                            <span className="text-4xl font-extrabold text-gray-900">€0</span>
                            <span className="text-base font-medium text-gray-500">/mo</span>
                        </p>
                        <p className="mt-4 text-sm text-gray-500">
                            Perfect for trying out ExamCraft.
                        </p>
                        <button
                            disabled
                            className="mt-8 block w-full bg-gray-100 border border-transparent rounded-md py-2 text-sm font-semibold text-gray-400 text-center cursor-not-allowed"
                        >
                            Current Plan
                        </button>
                    </div>
                </div>

                {/* Starter Tier */}
                <div className="border border-blue-200 rounded-lg shadow-sm divide-y divide-gray-200 bg-white relative">
                    <div className="absolute top-0 right-0 -mr-1 -mt-1 w-20 h-20 overflow-hidden">
                        {/* Ribbons could go here */}
                    </div>
                    <div className="p-6">
                        <h2 className="text-lg leading-6 font-medium text-gray-900">Starter</h2>
                        <p className="mt-4">
                            <span className="text-4xl font-extrabold text-gray-900">€19</span>
                            <span className="text-base font-medium text-gray-500">/mo</span>
                        </p>
                        <p className="mt-4 text-sm text-gray-500">
                            For serious exam creators.
                        </p>
                        <button
                            onClick={() => handleSubscribe(STARTER_PRICE_ID)}
                            disabled={loading}
                            className="mt-8 block w-full bg-blue-600 border border-transparent rounded-md py-2 text-sm font-semibold text-white text-center hover:bg-blue-700"
                        >
                            {loading ? 'Processing...' : 'Subscribe'}
                        </button>
                    </div>
                </div>

                {/* Professional Tier */}
                <div className="border border-gray-200 rounded-lg shadow-sm divide-y divide-gray-200 bg-white">
                    <div className="p-6">
                        <h2 className="text-lg leading-6 font-medium text-gray-900">Professional</h2>
                        <p className="mt-4">
                            <span className="text-4xl font-extrabold text-gray-900">€149</span>
                            <span className="text-base font-medium text-gray-500">/mo</span>
                        </p>
                        <p className="mt-4 text-sm text-gray-500">
                            Unlimited power.
                        </p>
                        <button
                            disabled
                            className="mt-8 block w-full bg-gray-50 border border-gray-200 rounded-md py-2 text-sm font-semibold text-gray-400 text-center"
                        >
                            Contact Sales
                        </button>
                    </div>
                </div>

            </div>
        </div>
    );
};
