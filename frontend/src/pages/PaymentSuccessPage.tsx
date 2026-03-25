import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export const PaymentSuccessPage: React.FC = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const [countdown, setCountdown] = useState(3);

    useEffect(() => {
        const interval = setInterval(() => {
            setCountdown(prev => {
                if (prev <= 1) {
                    clearInterval(interval);
                    navigate('/subscription');
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearInterval(interval);
    }, [navigate]);

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-md">
                <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10 text-center">
                    <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                        <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">{t('pages.paymentSuccess.title')}</h2>
                    <p className="text-gray-600 mb-4">
                        {t('pages.paymentSuccess.subtitle')}
                    </p>

                    <p className="text-sm text-gray-500 mb-4">
                        {t('pages.paymentSuccess.redirecting')} ({countdown}s)
                    </p>

                    <div className="mt-6">
                        <button
                            type="button"
                            onClick={() => navigate('/subscription')}
                            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        >
                            {t('pages.paymentSuccess.viewSubscription')}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
