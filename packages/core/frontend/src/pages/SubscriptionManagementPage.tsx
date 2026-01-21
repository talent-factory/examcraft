import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
    const [subscription, setSubscription] = useState<SubscriptionDetails | null>(null);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [portalLoading, setPortalLoading] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            setError(null);

            const [subscriptionData, invoicesData, paymentMethodsData] = await Promise.all([
                paymentService.getSubscription(),
                paymentService.getInvoices().catch(() => []),
                paymentService.getPaymentMethods().catch(() => []),
            ]);

            setSubscription(subscriptionData);
            setInvoices(invoicesData);
            setPaymentMethods(paymentMethodsData);
        } catch (err: any) {
            console.error('Error loading subscription data:', err);
            setError(err.response?.data?.detail || 'Failed to load subscription data');
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
            <h1 className="text-3xl font-bold text-gray-900 mb-8">Subscription Management</h1>

            {error && (
                <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                    {error}
                </div>
            )}

            {/* Subscription Overview */}
            <div className="bg-white shadow rounded-lg p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold text-gray-900">Current Plan</h2>
                    <div className="flex items-center space-x-2">
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${tierConfig.color}`}>
                            {tierConfig.name}
                        </span>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusConfig.color}`}>
                            {statusConfig.label}
                        </span>
                    </div>
                </div>

                {subscription?.status !== 'free' && subscription?.id ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <div>
                            <p className="text-sm text-gray-500">Current Period</p>
                            <p className="text-gray-900">
                                {formatDate(subscription.current_period_start)} - {formatDate(subscription.current_period_end)}
                            </p>
                        </div>
                        {subscription.plan && (
                            <div>
                                <p className="text-sm text-gray-500">Price</p>
                                <p className="text-gray-900">
                                    {formatCurrency(subscription.plan.amount || 0, subscription.plan.currency)} / {subscription.plan.interval || 'month'}
                                </p>
                            </div>
                        )}
                        {subscription.cancel_at_period_end && (
                            <div className="col-span-2">
                                <p className="text-sm text-red-600">
                                    Your subscription will be cancelled at the end of the current period.
                                </p>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="mb-6">
                        <p className="text-gray-600">
                            You are currently on the Free plan. Upgrade to unlock more features!
                        </p>
                    </div>
                )}

                <div className="flex space-x-4">
                    {subscription?.status === 'free' || !subscription?.id ? (
                        <button
                            onClick={handleUpgrade}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                        >
                            Upgrade Plan
                        </button>
                    ) : (
                        <>
                            <button
                                onClick={handleManageSubscription}
                                disabled={portalLoading}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
                            >
                                {portalLoading ? 'Loading...' : 'Manage Subscription'}
                            </button>
                            <button
                                onClick={handleUpgrade}
                                className="px-4 py-2 border border-blue-600 text-blue-600 rounded-md hover:bg-blue-50 transition-colors"
                            >
                                Change Plan
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Payment Methods */}
            <div className="bg-white shadow rounded-lg p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold text-gray-900">Payment Methods</h2>
                    {subscription?.id && subscription.status !== 'free' && (
                        <button
                            onClick={handleManageSubscription}
                            disabled={portalLoading}
                            className="text-sm text-blue-600 hover:text-blue-800"
                        >
                            Update Payment Method
                        </button>
                    )}
                </div>

                {paymentMethods.length > 0 ? (
                    <div className="space-y-3">
                        {paymentMethods.map((pm) => (
                            <div key={pm.id} className="flex items-center p-3 border rounded-md">
                                <div className="flex-shrink-0 mr-3">
                                    <span className="text-2xl">
                                        {pm.card?.brand === 'visa' && '💳'}
                                        {pm.card?.brand === 'mastercard' && '💳'}
                                        {pm.card?.brand === 'amex' && '💳'}
                                        {!pm.card?.brand && '💳'}
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
                    <p className="text-gray-500">No payment methods on file.</p>
                )}
            </div>

            {/* Billing History */}
            <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Billing History</h2>

                {invoices.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Invoice
                                    </th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Date
                                    </th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Amount
                                    </th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Status
                                    </th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Download
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
                    <p className="text-gray-500">No invoices yet.</p>
                )}
            </div>
        </div>
    );
};

export default SubscriptionManagementPage;
