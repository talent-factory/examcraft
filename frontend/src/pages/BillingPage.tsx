import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { paymentService } from '../services/paymentService';
import { STRIPE_PRICES, getStripeConfigStatus } from '../config/stripe.config';

const ENTERPRISE_CONTACT_EMAIL = process.env.REACT_APP_ENTERPRISE_CONTACT_EMAIL || 'enterprise@examcraft.ai';

export const BillingPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [currentTier, setCurrentTier] = useState<string>('free');
    const { t } = useTranslation();
    const stripeConfigStatus = getStripeConfigStatus();

    useEffect(() => {
        const loadCurrentTier = async () => {
            try {
                const subscription = await paymentService.getSubscription();
                setCurrentTier(subscription.tier || 'free');
            } catch (err: any) {
                console.error('Failed to load subscription:', err);
                setError(err.response?.data?.detail || t('pages.billing.subscriptionError'));
            }
        };
        loadCurrentTier();
    }, []);

    const handleSubscribe = async (priceId: string) => {
        setLoading(true);
        setError(null);
        try {
            const session = await paymentService.createCheckoutSession(priceId);
            window.location.href = session.url;
        } catch (err: any) {
            console.error('Subscription error:', err);
            const errorMessage = err.response?.data?.detail || t('pages.billing.subscriptionError');
            setError(errorMessage);
            setLoading(false);
        }
    };

    const handleRequestQuote = () => {
        window.location.href = `mailto:${ENTERPRISE_CONTACT_EMAIL}?subject=ExamCraft Enterprise Offerte`;
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

            {!stripeConfigStatus.configured && (
                <div className="mt-8 bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded relative" role="alert">
                    <strong className="font-bold">Configuration Required: </strong>
                    <span className="block sm:inline">{stripeConfigStatus.message}</span>
                </div>
            )}

            {error && (
                <div className="mt-8 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative" role="alert">
                    <span className="block sm:inline">{error}</span>
                </div>
            )}

            <div className="mt-12 space-y-4 sm:mt-16 sm:space-y-0 sm:grid sm:grid-cols-2 sm:gap-6 lg:max-w-5xl lg:mx-auto xl:max-w-none xl:mx-0 xl:grid-cols-4">
                {/* Free Tier */}
                <div className="border border-gray-200 rounded-lg shadow-sm divide-y divide-gray-200 bg-white">
                    <div className="p-6">
                        <h2 className="text-lg leading-6 font-medium text-gray-900">Free</h2>
                        <p className="mt-4">
                            <span className="text-4xl font-extrabold text-gray-900">CHF 0</span>
                            <span className="text-base font-medium text-gray-500">{t('pages.billing.perMonth')}</span>
                        </p>
                        <p className="mt-4 text-sm text-gray-500">
                            {t('pages.billing.freeDescription')}
                        </p>
                        <button
                            disabled
                            className="mt-8 block w-full bg-gray-100 border border-transparent rounded-md py-2 text-sm font-semibold text-gray-400 text-center cursor-not-allowed"
                        >
                            {currentTier === 'free' ? t('pages.billing.currentPlan') : 'Free Plan'}
                        </button>
                    </div>
                </div>

                {/* Starter Tier */}
                <div className="border border-blue-200 rounded-lg shadow-sm divide-y divide-gray-200 bg-white relative">
                    <div className="p-6">
                        <h2 className="text-lg leading-6 font-medium text-gray-900">Starter</h2>
                        <p className="mt-4">
                            <span className="text-4xl font-extrabold text-gray-900">CHF 9</span>
                            <span className="text-base font-medium text-gray-500">{t('pages.billing.perMonth')}</span>
                        </p>
                        <p className="mt-1 text-sm text-gray-400">{t('pages.billing.starterUsers')}</p>
                        <p className="mt-4 text-sm text-gray-500">
                            {t('pages.billing.starterDescription')}
                        </p>
                        <button
                            onClick={() => handleSubscribe(STRIPE_PRICES.starter)}
                            disabled={loading || !stripeConfigStatus.configured || currentTier === 'starter'}
                            className={`mt-8 block w-full border border-transparent rounded-md py-2 text-sm font-semibold text-center ${
                                currentTier === 'starter'
                                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                    : 'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed'
                            }`}
                        >
                            {currentTier === 'starter' ? t('pages.billing.currentPlan') : loading ? t('pages.billing.processing') : t('pages.billing.subscribe')}
                        </button>
                    </div>
                </div>

                {/* Professional Tier */}
                <div className="border border-gray-200 rounded-lg shadow-sm divide-y divide-gray-200 bg-white">
                    <div className="p-6">
                        <h2 className="text-lg leading-6 font-medium text-gray-900">Professional</h2>
                        <p className="mt-4">
                            <span className="text-4xl font-extrabold text-gray-900">CHF 49</span>
                            <span className="text-base font-medium text-gray-500">{t('pages.billing.perMonth')}</span>
                        </p>
                        <p className="mt-1 text-sm text-gray-400">{t('pages.billing.professionalUsers')}</p>
                        <p className="mt-4 text-sm text-gray-500">
                            {t('pages.billing.professionalDescription')}
                        </p>
                        <button
                            onClick={() => handleSubscribe(STRIPE_PRICES.professional)}
                            disabled={loading || !stripeConfigStatus.configured || currentTier === 'professional'}
                            className={`mt-8 block w-full border border-transparent rounded-md py-2 text-sm font-semibold text-center ${
                                currentTier === 'professional'
                                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                    : 'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed'
                            }`}
                        >
                            {currentTier === 'professional' ? t('pages.billing.currentPlan') : loading ? t('pages.billing.processing') : t('pages.billing.subscribe')}
                        </button>
                    </div>
                </div>

                {/* Enterprise Tier */}
                <div className="border border-yellow-200 rounded-lg shadow-sm divide-y divide-gray-200 bg-white">
                    <div className="p-6">
                        <h2 className="text-lg leading-6 font-medium text-gray-900">Enterprise</h2>
                        <p className="mt-4">
                            <span className="text-4xl font-extrabold text-gray-900">{t('pages.billing.enterprisePrice')}</span>
                            <span className="text-base font-medium text-gray-500">{t('pages.billing.perMonth')}</span>
                        </p>
                        <p className="mt-1 text-sm text-gray-400">{t('pages.billing.enterpriseSeats')}</p>
                        <p className="mt-4 text-sm text-gray-500">
                            {t('pages.billing.enterpriseDescription')}
                        </p>
                        <button
                            onClick={handleRequestQuote}
                            disabled={currentTier === 'enterprise'}
                            className={`mt-8 block w-full border border-transparent rounded-md py-2 text-sm font-semibold text-center ${
                                currentTier === 'enterprise'
                                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                    : 'bg-yellow-500 text-white hover:bg-yellow-600'
                            }`}
                        >
                            {currentTier === 'enterprise' ? t('pages.billing.currentPlan') : t('pages.billing.requestQuote')}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
