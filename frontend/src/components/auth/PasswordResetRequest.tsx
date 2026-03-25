/**
 * Password Reset Request Component
 * Request password reset email
 */

import React, { useState } from 'react';
import { useTranslation, Trans } from 'react-i18next';
import AuthService from '../../services/AuthService';

interface PasswordResetRequestProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export const PasswordResetRequest: React.FC<PasswordResetRequestProps> = ({
  onSuccess,
  onCancel,
}) => {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email) {
      setError(t('auth.resetRequest.enterEmail'));
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError(t('auth.resetRequest.invalidEmail'));
      return;
    }

    try {
      setIsLoading(true);
      await AuthService.requestPasswordReset({ email });
      setSuccess(true);
      setTimeout(() => {
        onSuccess?.();
      }, 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email');
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="w-full max-w-md mx-auto">
        <div className="bg-white shadow-md rounded-lg px-8 pt-6 pb-8 mb-4">
          <div className="text-center">
            <div className="mb-4 text-green-600 text-5xl">✓</div>
            <h2 className="text-2xl font-bold mb-4 text-gray-800">
              {t('auth.resetRequest.checkEmail')}
            </h2>
            <p className="text-gray-600 mb-6">
              <Trans i18nKey="auth.resetRequest.sentTo" values={{ email }} components={{ strong: <strong /> }} />
            </p>
            <p className="text-sm text-gray-500">
              {t('auth.resetRequest.redirecting')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-white shadow-md rounded-lg px-8 pt-6 pb-8 mb-4">
        <h2 className="text-2xl font-bold text-center mb-2 text-gray-800">
          {t('auth.resetRequest.title')}
        </h2>
        <p className="text-center text-gray-600 mb-6 text-sm">
          {t('auth.resetRequest.subtitle')}
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Email Field */}
          <div className="mb-6">
            <label
              className="block text-gray-700 text-sm font-bold mb-2"
              htmlFor="email"
            >
              {t('auth.resetRequest.email')}
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="your.email@example.com"
              disabled={isLoading}
              autoComplete="email"
              autoFocus
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? t('auth.resetRequest.sending') : t('auth.resetRequest.sendResetLink')}
            </button>
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                disabled={isLoading}
                className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t('auth.resetRequest.cancel')}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};
