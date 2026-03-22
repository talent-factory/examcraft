import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { paymentService } from '../services/paymentService';

export const BillingPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const { t } = useTranslation();

    const handleSubscribe = async (plan: string) => {
        setLoading(true);
        setError(null);
        try {
            const session = await paymentService.createCheckoutSession(plan);
            // Redirect to Stripe Checkout
            window.location.href = session.url;
        } catch (err: any) {
            console.error('Subscription error:', err);
            const errorMessage = err.response?.data?.detail || 'Failed to start subscription process. Please try again.';
            setError(errorMessage);
            setLoading(false);
        }
    };

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div className="text-center">
                <h2 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
                    {t('pages.billing.title')}
                </h2>
                <p className="mt-4 text-xl text-gray-600">
                    {t('pages.billing.subtitle')}
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
                            <span className="text-base font-medium text-gray-500">{t('pages.billing.perMonth')}</span>
                        </p>
                        <p className="mt-4 text-sm text-gray-500">
                            {t('pages.billing.freeDescription')}
                        </p>
                        <button
                            disabled
                            className="mt-8 block w-full bg-gray-100 border border-transparent rounded-md py-2 text-sm font-semibold text-gray-400 text-center cursor-not-allowed"
                        >
                            {t('pages.billing.currentPlan')}
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
                            <span className="text-base font-medium text-gray-500">{t('pages.billing.perMonth')}</span>
                        </p>
                        <p className="mt-4 text-sm text-gray-500">
                            {t('pages.billing.starterDescription')}
                        </p>
                        <button
                            onClick={() => handleSubscribe('starter')}
                            disabled={loading}
                            className="mt-8 block w-full bg-blue-600 border border-transparent rounded-md py-2 text-sm font-semibold text-white text-center hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                        >
                            {loading ? t('pages.billing.processing') : t('pages.billing.subscribe')}
                        </button>
                    </div>
                </div>

                {/* Professional Tier */}
                <div className="border border-gray-200 rounded-lg shadow-sm divide-y divide-gray-200 bg-white">
                    <div className="p-6">
                        <h2 className="text-lg leading-6 font-medium text-gray-900">Professional</h2>
                        <p className="mt-4">
                            <span className="text-4xl font-extrabold text-gray-900">€149</span>
                            <span className="text-base font-medium text-gray-500">{t('pages.billing.perMonth')}</span>
                        </p>
                        <p className="mt-4 text-sm text-gray-500">
                            {t('pages.billing.professionalDescription')}
                        </p>
                        <button
                            onClick={() => handleSubscribe('professional')}
                            disabled={loading}
                            className="mt-8 block w-full bg-blue-600 border border-transparent rounded-md py-2 text-sm font-semibold text-white text-center hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                        >
                            {loading ? t('pages.billing.processing') : t('pages.billing.subscribe')}
                        </button>
                    </div>
                </div>

            </div>
        </div>
    );
};
