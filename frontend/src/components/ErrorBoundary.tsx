/**
 * Error Boundary Component with Sentry Integration
 *
 * Catches React errors and displays a user-friendly fallback UI.
 * Automatically reports errors to Sentry.
 */

import React from 'react';
import * as Sentry from '@sentry/react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ErrorFallbackProps {
  error: Error | unknown;
  resetError: () => void;
}

/**
 * Fallback UI displayed when an error occurs
 */
const FALLBACK_STRINGS = {
  title: 'An error occurred',
  message: 'An unexpected error occurred. We have been notified.',
  retry: 'Try again',
  home: 'Go to home',
  support: 'If the problem persists, please contact support.',
};

function TranslatedErrorFallback(props: ErrorFallbackProps) {
  const { t } = useTranslation();
  return (
    <ErrorFallbackInner
      {...props}
      strings={{
        title: t('components.errorBoundary.title'),
        message: t('components.errorBoundary.message'),
        retry: t('components.errorBoundary.retry'),
        home: t('components.errorBoundary.home'),
        support: t('components.errorBoundary.support'),
      }}
    />
  );
}

function ErrorFallback(props: ErrorFallbackProps) {
  return (
    <Sentry.ErrorBoundary fallback={<ErrorFallbackInner {...props} strings={FALLBACK_STRINGS} />}>
      <TranslatedErrorFallback {...props} />
    </Sentry.ErrorBoundary>
  );
}

function ErrorFallbackInner({ error, resetError, strings }: ErrorFallbackProps & { strings: typeof FALLBACK_STRINGS }) {
  const { title, message, retry, home, support } = strings;

  const isDevelopment = process.env.REACT_APP_ENVIRONMENT === 'development';

  const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6">
        {/* Error Icon */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-shrink-0">
            <AlertTriangle className="h-8 w-8 text-red-500" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900">
            {title}
          </h2>
        </div>

        {/* Error Message */}
        <div className="mb-6">
          <p className="text-gray-600 mb-2">
            {message}
          </p>

          {/* Show error details in development */}
          {isDevelopment && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
              <p className="text-sm font-mono text-red-800 break-words">
                {errorMessage}
              </p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={resetError}
            className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            {retry}
          </button>
          <button
            onClick={() => window.location.href = '/'}
            className="flex-1 flex items-center justify-center gap-2 bg-gray-200 text-gray-700 py-2 px-4 rounded hover:bg-gray-300 transition-colors"
          >
            <Home className="h-4 w-4" />
            {home}
          </button>
        </div>

        {/* Support Info */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <p className="text-sm text-gray-500 text-center">
            {support}
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Error Boundary Component
 *
 * Wraps the application and catches React errors.
 * Integrates with Sentry for automatic error reporting.
 */
export const AppErrorBoundary: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <Sentry.ErrorBoundary
      fallback={({ error, resetError }) => (
        <ErrorFallback error={error} resetError={resetError} />
      )}
      showDialog={false} // Don't show Sentry's default dialog
    >
      {children}
    </Sentry.ErrorBoundary>
  );
};
