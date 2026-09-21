/**
 * Error Boundary Component mit lokalem Fehler-Reporting (TF-866)
 *
 * Faengt React-Render-Fehler ab und zeigt eine benutzerfreundliche
 * Fallback-UI. Meldet Fehler automatisch an `utils/errorReporting`
 * (Backend-Proxy `/api/v1/monitoring/client-errors`) statt, wie zuvor, an
 * Sentry — siehe dessen Moduldoc, warum das lokal statt via
 * `@talent-factory/specula-client` implementiert ist.
 */

import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { reportClientError } from '../utils/errorReporting';

interface ErrorFallbackProps {
  error: Error;
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
    <ErrorBoundary fallback={() => <ErrorFallbackInner {...props} strings={FALLBACK_STRINGS} />}>
      <TranslatedErrorFallback {...props} />
    </ErrorBoundary>
  );
}

function ErrorFallbackInner({ error, resetError, strings }: ErrorFallbackProps & { strings: typeof FALLBACK_STRINGS }) {
  const { title, message, retry, home, support } = strings;

  const isDevelopment = process.env.REACT_APP_ENVIRONMENT === 'development';

  const errorMessage = error.message || 'An unexpected error occurred';

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

interface ErrorBoundaryProps {
  children: React.ReactNode;
  /** Fallback-Renderer, erhaelt den gefangenen Fehler + eine
   * `resetError`-Funktion (setzt die Boundary zurueck, kein automatisches
   * Retry des vorherigen Fehlers). */
  fallback: (info: { error: Error; resetError: () => void }) => React.ReactNode;
  /** Wird bei einem gefangenen Render-Fehler mit dem Fehler + dessen
   * React-Component-Stack aufgerufen — i. d. R. `reportClientError`.
   * Bewusst als expliziter Callback statt eines eingebauten Reporters:
   * entkoppelt die Komponente von einer konkreten Reporter-Konfiguration
   * und haelt sie in Tests trivial isolierbar (gleiches Design wie
   * specula-client-js' `ErrorBoundary`-Helper). */
  onError?: (error: Error, componentStack: string) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Wiederverwendbarer React-Error-Boundary. `hasError`/`error` sind ein
 * Einweg-Riegel bis zum expliziten `resetError()`-Aufruf (kein automatisches
 * Retry).
 */
class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    try {
      this.props.onError?.(error, info.componentStack ?? '');
    } catch (onErrorFailure) {
      // Ein werfender onError-Callback darf die Boundary nicht selbst zum
      // Absturz bringen — das waere genau der Fall, vor dem diese
      // Komponente eigentlich schuetzen soll.
      console.error('[ErrorBoundary] onError-Callback ist fehlgeschlagen:', onErrorFailure);
    }
  }

  resetError = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): React.ReactNode {
    const { hasError, error } = this.state;
    if (hasError && error) {
      return this.props.fallback({ error, resetError: this.resetError });
    }
    return this.props.children;
  }
}

/**
 * Error Boundary Component
 *
 * Wraps the application and catches React errors. Meldet gefangene Fehler
 * (inkl. `component_stack`/`user_agent`, Paritaet zum bisherigen
 * Sentry-Verhalten) an den `/client-errors`-Proxy-Endpoint.
 */
export const AppErrorBoundary: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <ErrorBoundary
      fallback={({ error, resetError }) => <ErrorFallback error={error} resetError={resetError} />}
      onError={(error, componentStack) => {
        void reportClientError({
          message: error.message,
          stack: error.stack ?? '',
          url: window.location.href,
          userAgent: navigator.userAgent,
          componentStack,
        });
      }}
    >
      {children}
    </ErrorBoundary>
  );
};
