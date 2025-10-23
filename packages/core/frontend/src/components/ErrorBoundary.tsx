/**
 * Error Boundary Component with Sentry Integration
 *
 * Catches React errors and displays a user-friendly fallback UI.
 * Automatically reports errors to Sentry.
 */

import React from 'react';
import * as Sentry from '@sentry/react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface ErrorFallbackProps {
  error: Error | unknown;
  resetError: () => void;
}

/**
 * Fallback UI displayed when an error occurs
 */
function ErrorFallback({ error, resetError }: ErrorFallbackProps) {
  const isDevelopment = process.env.REACT_APP_ENVIRONMENT === 'development';

  // Type guard to safely access error properties
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
            Ein Fehler ist aufgetreten
          </h2>
        </div>

        {/* Error Message */}
        <div className="mb-6">
          <p className="text-gray-600 mb-2">
            Entschuldigung, es ist ein unerwarteter Fehler aufgetreten.
            Wir wurden automatisch benachrichtigt und werden das Problem beheben.
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
            Erneut versuchen
          </button>
          <button
            onClick={() => window.location.href = '/'}
            className="flex-1 flex items-center justify-center gap-2 bg-gray-200 text-gray-700 py-2 px-4 rounded hover:bg-gray-300 transition-colors"
          >
            <Home className="h-4 w-4" />
            Zur Startseite
          </button>
        </div>

        {/* Support Info */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <p className="text-sm text-gray-500 text-center">
            Wenn das Problem weiterhin besteht, kontaktieren Sie bitte den Support.
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

/**
 * Test Component to trigger errors (only for development/testing)
 */
export const ErrorTestButton: React.FC = () => {
  const isDevelopment = process.env.REACT_APP_ENVIRONMENT === 'development';

  if (!isDevelopment) {
    return null;
  }

  const triggerError = () => {
    throw new Error('Test Error: This is a test error triggered manually');
  };

  return (
    <button
      onClick={triggerError}
      className="fixed bottom-4 right-4 bg-red-600 text-white px-4 py-2 rounded shadow-lg hover:bg-red-700 transition-colors text-sm"
    >
      🐛 Trigger Test Error
    </button>
  );
};
