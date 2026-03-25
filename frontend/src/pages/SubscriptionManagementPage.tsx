import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
    paymentService,
    SubscriptionDetails,
    Invoice,
    PaymentMethod,
} from '../services/paymentService';

const TIER_CONFIG: Record<string, { name: string; color: string }> = {
    free: { name: 'Free', color: 'bg-gray-100 text-gray-800' },
    starter: { name: 'Starter', color: 'bg-blue-100 text-blue-800' },
    professional: { name: 'Professional', color: 'bg-purple-100 text-purple-800' },
    enterprise: { name: 'Enterprise', color: 'bg-yellow-100 text-yellow-800' },
};

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
    active: { label: 'Active', color: 'bg-green-100 text-green-800' },
    trialing: { label: 'Trial', color: 'bg-blue-100 text-blue-800' },
    past_due: { label: 'Past Due', color: 'bg-red-100 text-red-800' },
    canceled: { label: 'Cancelled', color: 'bg-gray-100 text-gray-800' },
    incomplete: { label: 'Incomplete', color: 'bg-yellow-100 text-yellow-800' },
    free: { label: 'Free', color: 'bg-gray-100 text-gray-800' },
};

const formatDate = (dateString: string | null): string => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('de-CH', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    });
};

const formatCurrency = (amount: number, currency: string): string => {
    return new Intl.NumberFormat('de-CH', {
        style: 'currency',
        currency: currency,
    }).format(amount);
};

export const SubscriptionManagementPage: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { t } = useTranslation();
    const [subscription, setSubscription] = useState<SubscriptionDetails | null>(null);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [invoiceError, setInvoiceError] = useState<string | null>(null);
    const [paymentMethodError, setPaymentMethodError] = useState<string | null>(null);
    const [portalLoading, setPortalLoading] = useState(false);

    useEffect(() => {
        loadData();
    }, [location.key]); // eslint-disable-line react-hooks/exhaustive-deps

    const loadData = async () => {
        try {
            setLoading(true);
            setError(null);

            const subscriptionData = await paymentService.getSubscription();
            setSubscription(subscriptionData);

            try {
                const invoicesData = await paymentService.getInvoices();
                setInvoices(invoicesData);
                setInvoiceError(null);
            } catch (err) {
                console.error('Error loading invoices:', err);
                setInvoiceError(t('pages.subscription.invoicesLoadError'));
                setInvoices([]);
            }

            try {
                const paymentMethodsData = await paymentService.getPaymentMethods();
                setPaymentMethods(paymentMethodsData);
                setPaymentMethodError(null);
            } catch (err) {
                console.error('Error loading payment methods:', err);
                setPaymentMethodError(t('pages.subscription.paymentMethodsLoadError'));
                setPaymentMethods([]);
            }
        } catch (err: any) {
            console.error('Error loading subscription data:', err);
            setError(err.response?.data?.detail || t('pages.subscription.loadError'));
        } finally {
            setLoading(false);
        }
    };

    const handleManageSubscription = async () => {
        try {
            setPortalLoading(true);
            const session = await paymentService.createCustomerPortalSession();
            window.location.href = session.url;
        } catch (err: any) {
            console.error('Error opening customer portal:', err);
            setError(err.response?.data?.detail || 'Failed to open subscription management');
            setPortalLoading(false);
        }
    };

    const handleUpgrade = () => {
        navigate('/billing');
    };

    if (loading) {
        return (
            <div className="max-w-4xl mx-auto px-4 py-12">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded w-1/3 mb-8"></div>
                    <div className="h-48 bg-gray-200 rounded mb-6"></div>
                    <div className="h-64 bg-gray-200 rounded"></div>
                </div>
            </div>
        );
    }

    const tierConfig = TIER_CONFIG[subscription?.tier || 'free'] || TIER_CONFIG.free;
    const statusConfig = STATUS_CONFIG[subscription?.status || 'free'] || STATUS_CONFIG.free;

    return (
        <div className="max-w-4xl mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-8">{t('pages.subscription.title')}</h1>

            {error && (
                <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                    {error}
                </div>
            )}

            {/* Subscription Overview */}
            <div className="bg-white shadow rounded-lg p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold text-gray-900">{t('pages.subscription.currentPlan')}</h2>
                    <div className="flex items-center space-x-2">
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${tierConfig.color}`}>
                            {tierConfig.name}
                        </span>
                        {subscription?.status !== 'free' && (
                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusConfig.color}`}>
                                {statusConfig.label}
                            </span>
                        )}
                    </div>
                </div>

                {subscription?.tier !== 'free' && subscription?.status !== 'free' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <div>
                            <p className="text-sm text-gray-500">{t('pages.subscription.period')}</p>
                            <p className="text-gray-900">
                                {formatDate(subscription.current_period_start)} - {formatDate(subscription.current_period_end)}
                            </p>
                        </div>
                        {subscription.plan && (
                            <div>
                                <p className="text-sm text-gray-500">{t('pages.subscription.price')}</p>
                                <p className="text-gray-900">
                                    {formatCurrency(subscription.plan.amount || 0, subscription.plan.currency)} / {subscription.plan.interval || 'month'}
                                </p>
                            </div>
                        )}
                        {subscription.cancel_at_period_end && (
                            <div className="col-span-2">
                                <p className="text-sm text-red-600">
                                    {t('pages.subscription.cancelWarning')}
                                </p>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="mb-6">
                        <p className="text-gray-600">
                            {t('pages.subscription.freePlanMessage')}
                        </p>
                    </div>
                )}

                <div className="flex space-x-4">
                    {subscription?.tier === 'free' || subscription?.status === 'free' ? (
                        <button
                            onClick={handleUpgrade}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                        >
                            {t('pages.subscription.upgradePlan')}
                        </button>
                    ) : (
                        <>
                            {subscription?.is_billing_owner && (
                                <button
                                    onClick={handleManageSubscription}
                                    disabled={portalLoading}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
                                >
                                    {portalLoading ? t('pages.subscription.loading') : t('pages.subscription.manageSubscription')}
                                </button>
                            )}
                            <button
                                onClick={handleUpgrade}
                                className="px-4 py-2 border border-blue-600 text-blue-600 rounded-md hover:bg-blue-50 transition-colors"
                            >
                                {t('pages.subscription.changePlan')}
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Payment Methods - Only visible to billing owner */}
            {subscription?.is_billing_owner && (
                <div className="bg-white shadow rounded-lg p-6 mb-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-semibold text-gray-900">{t('pages.subscription.paymentMethods')}</h2>
                        {subscription?.id && subscription.status !== 'free' && (
                            <button
                                onClick={handleManageSubscription}
                                disabled={portalLoading}
                                className="text-sm text-blue-600 hover:text-blue-800"
                            >
                                {t('pages.subscription.updatePaymentMethod')}
                            </button>
                        )}
                    </div>

                    {paymentMethodError && (
                        <div className="mb-4 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded">
                            {paymentMethodError}
                        </div>
                    )}

                    {paymentMethods.length > 0 ? (
                        <div className="space-y-3">
                            {paymentMethods.map((pm) => (
                                <div key={pm.id} className="flex items-center p-3 border rounded-md">
                                    <div className="flex-shrink-0 mr-3">
                                        <span className="text-2xl">
                                            {'\uD83D\uDCB3'}
                                        </span>
                                    </div>
                                    <div>
                                        <p className="font-medium text-gray-900">
                                            {pm.card?.brand?.toUpperCase() || 'Card'} ending in {pm.card?.last4 || '****'}
                                        </p>
                                        <p className="text-sm text-gray-500">
                                            Expires {pm.card?.exp_month}/{pm.card?.exp_year}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-gray-500">{t('pages.subscription.noPaymentMethods')}</p>
                    )}
                </div>
            )}

            {/* Billing History - Only visible to billing owner */}
            {subscription?.is_billing_owner && (
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-xl font-semibold text-gray-900 mb-4">{t('pages.subscription.billingHistory')}</h2>

                    {invoiceError && (
                        <div className="mb-4 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded">
                            {invoiceError}
                        </div>
                    )}

                    {invoices.length > 0 ? (
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            {t('pages.subscription.invoiceCol')}
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            {t('pages.subscription.dateCol')}
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            {t('pages.subscription.amountCol')}
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            {t('pages.subscription.statusCol')}
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            {t('pages.subscription.downloadCol')}
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {invoices.map((invoice) => (
                                        <tr key={invoice.id}>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                                                {invoice.number || invoice.id.slice(0, 8)}
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {formatDate(invoice.created)}
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                                                {formatCurrency(invoice.amount_paid || invoice.amount_due, invoice.currency)}
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap">
                                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                                    invoice.status === 'paid'
                                                        ? 'bg-green-100 text-green-800'
                                                        : invoice.status === 'open'
                                                        ? 'bg-yellow-100 text-yellow-800'
                                                        : 'bg-gray-100 text-gray-800'
                                                }`}>
                                                    {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                                                </span>
                                            </td>
                                            <td className="px-4 py-4 whitespace-nowrap text-sm">
                                                {invoice.invoice_pdf && (
                                                    <a
                                                        href={invoice.invoice_pdf}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-blue-600 hover:text-blue-800"
                                                    >
                                                        PDF
                                                    </a>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <p className="text-gray-500">{t('pages.subscription.noInvoices')}</p>
                    )}
                </div>
            )}
        </div>
    );
};

export default SubscriptionManagementPage;
