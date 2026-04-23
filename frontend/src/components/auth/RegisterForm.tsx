/**
 * Register Form Component
 * User registration with email/password
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { RegisterRequest } from '../../types/auth';

interface RegisterFormProps {
  onSuccess?: () => void;
  onSwitchToLogin?: () => void;
}

export const RegisterForm: React.FC<RegisterFormProps> = ({
  onSuccess,
  onSwitchToLogin,
}) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { register, error, isLoading, clearError } = useAuth();
  const [formData, setFormData] = useState<RegisterRequest>({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    institution_slug: '',
  });
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const validateForm = (): boolean => {
    if (!formData.email || !formData.password || !formData.first_name || !formData.last_name) {
      setLocalError(t('auth.validation.required'));
      return false;
    }

    if (formData.password !== confirmPassword) {
      setLocalError(t('auth.validation.passwordMismatch'));
      return false;
    }

    if (formData.password.length < 8) {
      setLocalError(t('auth.validation.passwordMinLength'));
      return false;
    }

    if (!/[A-Z]/.test(formData.password)) {
      setLocalError(t('auth.validation.passwordUppercase'));
      return false;
    }

    if (!/[a-z]/.test(formData.password)) {
      setLocalError(t('auth.validation.passwordLowercase'));
      return false;
    }

    if (!/\d/.test(formData.password)) {
      setLocalError(t('auth.validation.passwordNumber'));
      return false;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      setLocalError(t('auth.validation.invalidEmail'));
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setLocalError(null);

    if (!validateForm()) {
      return;
    }

    try {
      await register(formData);
      // Navigate to registration success page with email
      navigate('/registration-success', { state: { email: formData.email } });
    } catch (err) {
      // Error is handled by AuthContext
      console.error('Registration failed:', err);
    }
  };

  const displayError = error || localError;

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-white shadow-md rounded-lg px-8 pt-6 pb-8 mb-4">
        <h2 className="text-2xl font-bold text-center mb-6 text-gray-800">
          {t('auth.register.title')}
        </h2>

        {displayError && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {displayError}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* First Name */}
          <div className="mb-4">
            <label
              className="block text-gray-700 text-sm font-bold mb-2"
              htmlFor="first_name"
            >
              {t('auth.register.firstName')} *
            </label>
            <input
              id="first_name"
              name="first_name"
              type="text"
              value={formData.first_name}
              onChange={handleChange}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="John"
              disabled={isLoading}
              autoComplete="given-name"
            />
          </div>

          {/* Last Name */}
          <div className="mb-4">
            <label
              className="block text-gray-700 text-sm font-bold mb-2"
              htmlFor="last_name"
            >
              {t('auth.register.lastName')} *
            </label>
            <input
              id="last_name"
              name="last_name"
              type="text"
              value={formData.last_name}
              onChange={handleChange}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="Doe"
              disabled={isLoading}
              autoComplete="family-name"
            />
          </div>

          {/* Email */}
          <div className="mb-4">
            <label
              className="block text-gray-700 text-sm font-bold mb-2"
              htmlFor="email"
            >
              {t('auth.register.email')} *
            </label>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="your.email@example.com"
              disabled={isLoading}
              autoComplete="email"
            />
          </div>

          {/* Institution Slug (Optional) */}
          <div className="mb-4">
            <label
              className="block text-gray-700 text-sm font-bold mb-2"
              htmlFor="institution_slug"
            >
              {t('auth.register.institutionCode')}
            </label>
            <input
              id="institution_slug"
              name="institution_slug"
              type="text"
              value={formData.institution_slug}
              onChange={handleChange}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="university-name"
              disabled={isLoading}
            />
            <p className="text-xs text-gray-500 mt-1">
              {t('auth.register.institutionCodeHint')}
            </p>
          </div>

          {/* Password */}
          <div className="mb-4">
            <label
              className="block text-gray-700 text-sm font-bold mb-2"
              htmlFor="password"
            >
              {t('auth.register.password')} *
            </label>
            <div className="relative">
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={handleChange}
                className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline pr-10"
                placeholder="••••••••"
                disabled={isLoading}
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-sm text-gray-600 hover:text-gray-800"
                disabled={isLoading}
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">{t('auth.register.passwordReqTitle')}</p>
              <ul className="text-xs space-y-0.5 list-none">
                {[
                  { key: 'auth.register.passwordReqMinLength', met: formData.password.length >= 8 },
                  { key: 'auth.register.passwordReqUppercase', met: /[A-Z]/.test(formData.password) },
                  { key: 'auth.register.passwordReqLowercase', met: /[a-z]/.test(formData.password) },
                  { key: 'auth.register.passwordReqNumber',    met: /\d/.test(formData.password) },
                ].map(({ key, met }) => (
                  <li key={key} className={`flex items-center gap-1.5 ${met ? 'text-green-600' : 'text-gray-400'}`}>
                    <span className="text-sm leading-none">{met ? '✓' : '○'}</span>
                    {t(key)}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Confirm Password */}
          <div className="mb-6">
            <label
              className="block text-gray-700 text-sm font-bold mb-2"
              htmlFor="confirm_password"
            >
              {t('auth.register.confirmPassword')} *
            </label>
            <input
              id="confirm_password"
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              placeholder="••••••••"
              disabled={isLoading}
              autoComplete="new-password"
            />
          </div>

          {/* Submit Button */}
          <div className="mb-6">
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? t('auth.register.creatingAccount') : t('auth.register.createAccount')}
            </button>
          </div>
        </form>

        {/* Login Link */}
        {onSwitchToLogin && (
          <div className="text-center">
            <p className="text-sm text-gray-600">
              {t('auth.register.hasAccount')}{' '}
              <button
                type="button"
                onClick={onSwitchToLogin}
                className="text-blue-600 hover:text-blue-800 font-medium"
                disabled={isLoading}
              >
                {t('auth.register.loginHere')}
              </button>
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
