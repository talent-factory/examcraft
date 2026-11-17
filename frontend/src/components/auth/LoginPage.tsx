/**
 * Login Page
 *
 * EXAMCRAFT-126: Es gibt keine eigene Login-Maske mehr. Die Anmeldung läuft
 * über das Backend (OIDC-BFF gegen tessera/Zitadel); diese Seite leitet dorthin
 * weiter und zeigt die Fehlercodes an, mit denen der Callback des Backends auf
 * `/login?error=…` zurückkehrt.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

// Fehlercodes des Backend-Callbacks (core/backend/api/auth_oidc.py).
const LOGIN_ERROR_CODES = [
  'login_failed',
  'login_expired',
  'login_cancelled',
  'idp_unavailable',
  'email_conflict',
  'account_not_migrated',
  'user_limit',
  'claims_missing',
  'account_inactive',
  'reauth_failed',
] as const;

export const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const { login } = useAuth();
  const [searchParams] = useSearchParams();

  const errorParam = searchParams.get('error');
  // Unbekannte Codes (z. B. aus einer manipulierten URL) fallen auf den
  // allgemeinen Text zurück; der Parameter selbst wird nie angezeigt.
  const errorCode = errorParam
    ? (LOGIN_ERROR_CODES as readonly string[]).includes(errorParam)
      ? errorParam
      : 'login_failed'
    : null;

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4">
            <svg className="w-9 h-9 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">ExamCraft AI</h1>
          <p className="text-sm text-gray-600">{t('auth.authPage.tagline')}</p>
        </div>

        <div className="bg-white rounded-3xl shadow-sm border border-gray-200 p-10">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">{t('auth.login.title')}</h2>
          <p className="text-sm text-gray-600 mb-6">{t('auth.login.subtitle')}</p>

          {errorCode && (
            <div role="alert" className="mb-6 rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-800">
              {t(`auth.loginError.${errorCode}`)}
            </div>
          )}

          <button
            type="button"
            data-testid="login-button"
            onClick={() => login()}
            className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
          >
            {t('auth.login.signIn')}
          </button>

          <div className="mt-4 text-center">
            <button
              type="button"
              data-testid="login-switch-account"
              onClick={() => login({ switchAccount: true })}
              className="text-sm text-blue-600 hover:text-blue-800 underline focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded transition-colors"
            >
              {t('auth.login.switchAccount')}
            </button>
          </div>
        </div>

        <div className="mt-8 text-center text-xs text-gray-500">
          <p className="space-x-2">
            <Link to="/terms" className="text-gray-700 hover:text-gray-900 underline transition-colors">
              {t('auth.authPage.terms')}
            </Link>
            <span aria-hidden="true">·</span>
            <Link to="/privacy" className="text-gray-700 hover:text-gray-900 underline transition-colors">
              {t('auth.authPage.privacy')}
            </Link>
            <span aria-hidden="true">·</span>
            <Link to="/imprint" className="text-gray-700 hover:text-gray-900 underline transition-colors">
              {t('auth.authPage.imprint')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
