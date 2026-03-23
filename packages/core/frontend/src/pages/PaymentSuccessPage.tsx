import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { paymentService } from '../services/paymentService';
import { useAuth } from '../contexts/AuthContext';

export const PaymentSuccessPage: React.FC = () => {
    const navigate = useNavigate();
    const { refreshProfile } = useAuth();
    const [syncing, setSyncing] = useState(true);
    const [syncError, setSyncError] = useState<string | null>(null);

    useEffect(() => {
        // Trigger subscription sync from Stripe
        const syncSubscription = async () => {
            try {
                setSyncing(true);
                setSyncError(null);

                // Wait a bit for Stripe webhook to process (usually < 1 second)
                await new Promise(resolve => setTimeout(resolve, 2000));

                // Verify subscription was synced by fetching it
                await paymentService.getSubscription();

                // Refresh user profile to pick up the new subscription tier
                await refreshProfile();

                setSyncing(false);

                // Redirect to subscription page after successful sync
                const timer = setTimeout(() => {
                    navigate('/subscription');
                }, 2000);

                return () => clearTimeout(timer);
            } catch (error: any) {
                console.error('Error syncing subscription:', error);
                setSyncError('Subscription sync delayed. Please refresh the page in a moment.');
                setSyncing(false);

                // Still try to refresh profile even on error
                try {
                    await refreshProfile();
                } catch (err) {
                    console.error('[PaymentSuccessPage] Failed to refresh profile:', err);
                    // Profile will be refreshed on next page load
                }

                // Still redirect after error, user can refresh subscription page
                const timer = setTimeout(() => {
                    navigate('/subscription');
                }, 4000);

                return () => clearTimeout(timer);
            }
        };

        syncSubscription();
    }, [navigate, refreshProfile]);

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-md">
                <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10 text-center">
                    <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                        <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">Payment Successful!</h2>
                    <p className="text-gray-600 mb-4">
                        Thank you for your subscription. Your account has been upgraded.
                    </p>

                    {syncing && (
                        <div className="flex items-center justify-center space-x-2 text-sm text-gray-500 mb-4">
                            <svg className="animate-spin h-4 w-4 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span>Syncing subscription...</span>
                        </div>
                    )}

                    {syncError && (
                        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                            <p className="text-sm text-yellow-800">{syncError}</p>
                        </div>
                    )}

                    {!syncing && !syncError && (
                        <p className="text-sm text-gray-500 mb-4">
                            Redirecting to your subscription...
                        </p>
                    )}

                    <div className="mt-6">
                        <button
                            type="button"
                            onClick={() => navigate('/subscription')}
                            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        >
                            View Subscription
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
