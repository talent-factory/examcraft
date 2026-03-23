/**
 * Password Change Component
 * Change user password or set password for OAuth-only users
 */

import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { ChangePasswordRequest } from '../../types/auth';

interface PasswordChangeProps {
  onCancel?: () => void;
  onSuccess?: () => void;
}

export const PasswordChange: React.FC<PasswordChangeProps> = ({ onCancel, onSuccess }) => {
  const { t } = useTranslation();
  const { user, changePassword, setPassword, isLoading, error, clearError } = useAuth();

  // Determine if user is OAuth-only (no password set)
  const isOAuthOnly = useMemo(() => {
    // Check if user has oauth_provider but no password_hash
    // We can infer this from the fact that they logged in via OAuth
    return user?.oauth_provider !== undefined && user?.oauth_provider !== null;
  }, [user]);

  const [formData, setFormData] = useState<ChangePasswordRequest>({
    current_password: '',
    new_password: '',
  });
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const validateForm = (): boolean => {
    if (isOAuthOnly) {
      // For OAuth users, only validate new password
      if (!formData.new_password || !confirmPassword) {
        setLocalError(t('profile.passwordChange.validationFillAll'));
        return false;
      }
    } else {
      // For regular users, validate all fields
      if (!formData.current_password || !formData.new_password || !confirmPassword) {
        setLocalError(t('profile.passwordChange.validationFillAll'));
        return false;
      }
    }

    if (formData.new_password !== confirmPassword) {
      setLocalError(t('profile.passwordChange.validationMismatch'));
      return false;
    }

    if (formData.new_password.length < 8) {
      setLocalError(t('profile.passwordChange.validationMinLength'));
      return false;
    }

    if (!isOAuthOnly && formData.current_password === formData.new_password) {
      setLocalError(t('profile.passwordChange.validationSamePassword'));
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setLocalError(null);
    setSuccess(false);

    if (!validateForm()) {
      return;
    }

    try {
      if (isOAuthOnly) {
        // Set password for OAuth-only users
        await setPassword(formData.new_password);
      } else {
        // Change password for regular users
        await changePassword(formData);
      }
      setSuccess(true);
      setFormData({ current_password: '', new_password: '' });
      setConfirmPassword('');

      setTimeout(() => {
        onSuccess?.();
      }, 2000);
    } catch (err) {
      console.error('Password operation failed:', err);
    }
  };

  const displayError = error || localError;

  if (success) {
    return (
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-8">
          <div className="text-center">
            <div className="mb-4 text-green-600 text-5xl">✓</div>
            <h2 className="text-2xl font-bold mb-4 text-gray-800">
              {isOAuthOnly ? t('profile.passwordChange.successSetTitle') : t('profile.passwordChange.successChangeTitle')}
            </h2>
            <p className="text-gray-600 mb-6">
              {isOAuthOnly
                ? t('profile.passwordChange.successSetMessage')
                : t('profile.passwordChange.successChangeMessage')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-800">
          {isOAuthOnly ? t('profile.passwordChange.headerSet') : t('profile.passwordChange.headerChange')}
        </h2>
        {isOAuthOnly && (
          <p className="text-sm text-gray-600 mt-1">
            {t('profile.passwordChange.oauthInfo', { provider: user?.oauth_provider })}
          </p>
        )}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="px-6 py-6">
        {displayError && (
          <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {displayError}
          </div>
        )}

        <div className="space-y-6">
          {/* Current Password - Only for non-OAuth users */}
          {!isOAuthOnly && (
            <div>
              <label
                htmlFor="current_password"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                {t('profile.passwordChange.currentPassword')}
              </label>
              <div className="relative">
                <input
                  type={showPasswords ? 'text' : 'password'}
                  id="current_password"
                  name="current_password"
                  value={formData.current_password}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 pr-10"
                  disabled={isLoading}
                  required
                  autoComplete="current-password"
                />
              </div>
            </div>
          )}

          {/* New Password */}
          <div>
            <label
              htmlFor="new_password"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              {t('profile.passwordChange.newPassword')}
            </label>
            <div className="relative">
              <input
                type={showPasswords ? 'text' : 'password'}
                id="new_password"
                name="new_password"
                value={formData.new_password}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 pr-10"
                disabled={isLoading}
                required
                autoComplete="new-password"
              />
            </div>
            <p className="mt-1 text-sm text-gray-500">
              {t('profile.passwordChange.passwordHint')}
            </p>
          </div>

          {/* Confirm New Password */}
          <div>
            <label
              htmlFor="confirm_password"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              {t('profile.passwordChange.confirmPassword')}
            </label>
            <div className="relative">
              <input
                type={showPasswords ? 'text' : 'password'}
                id="confirm_password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 pr-10"
                disabled={isLoading}
                required
                autoComplete="new-password"
              />
            </div>
          </div>

          {/* Show Password Toggle */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="show_passwords"
              checked={showPasswords}
              onChange={(e) => setShowPasswords(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="show_passwords" className="ml-2 block text-sm text-gray-700">
              {t('profile.passwordChange.showPasswords')}
            </label>
          </div>

          {/* Security Tips */}
          <div className="pt-6 border-t border-gray-200">
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              {t('profile.passwordChange.securityTipsTitle')}
            </h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-start">
                <svg className="w-4 h-4 text-blue-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                {t('profile.passwordChange.tip1')}
              </li>
              <li className="flex items-start">
                <svg className="w-4 h-4 text-blue-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                {t('profile.passwordChange.tip2')}
              </li>
              <li className="flex items-start">
                <svg className="w-4 h-4 text-blue-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                {t('profile.passwordChange.tip3')}
              </li>
              <li className="flex items-start">
                <svg className="w-4 h-4 text-blue-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                {t('profile.passwordChange.tip4')}
              </li>
            </ul>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-8 flex justify-end space-x-3">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              disabled={isLoading}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('profile.passwordChange.cancel')}
            </button>
          )}
          <button
            type="submit"
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading
              ? (isOAuthOnly ? t('profile.passwordChange.setting') : t('profile.passwordChange.changing'))
              : (isOAuthOnly ? t('profile.passwordChange.setPassword') : t('profile.passwordChange.changePassword'))}
          </button>
        </div>
      </form>
    </div>
  );
};
