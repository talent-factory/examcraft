/**
 * Unauthorized Page Component
 * Shown when user doesn't have required permissions
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export const UnauthorizedPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const from = (location.state as any)?.from?.pathname;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="w-full max-w-md mx-auto">
        <div className="bg-white shadow-md rounded-lg px-8 pt-6 pb-8">
          <div className="text-center">
            {/* Icon */}
            <div className="mb-4 text-red-600 text-6xl">🚫</div>

            {/* Title */}
            <h1 className="text-3xl font-bold mb-4 text-gray-800">
              {t('guards.unauthorized.title')}
            </h1>

            {/* Message */}
            <p className="text-gray-600 mb-6">
              {t('guards.unauthorized.message')}
            </p>

            {from && (
              <p className="text-sm text-gray-500 mb-6">
                {t('guards.unauthorized.attemptedAccess')} <code className="bg-gray-100 px-2 py-1 rounded">{from}</code>
              </p>
            )}

            {user && (
              <div className="mb-6 p-4 bg-gray-50 rounded-lg text-left">
                <p className="text-sm text-gray-600 mb-2">
                  <strong>{t('guards.unauthorized.currentUser')}</strong> {user.email}
                </p>
                <p className="text-sm text-gray-600">
                  <strong>{t('guards.unauthorized.roles')}</strong> {user.roles.map(r => r.display_name).join(', ') || 'None'}
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="space-y-3">
              <button
                onClick={() => navigate(-1)}
                className="w-full bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
              >
                {t('guards.unauthorized.goBack')}
              </button>
              <button
                onClick={() => navigate('/dashboard')}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
              >
                {t('guards.unauthorized.goToDashboard')}
              </button>
            </div>

            {/* Help Text */}
            <p className="mt-6 text-sm text-gray-500">
              {t('guards.unauthorized.helpText')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
