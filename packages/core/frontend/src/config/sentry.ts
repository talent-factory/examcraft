/**
 * Sentry Configuration for ExamCraft Frontend
 *
 * Initializes Sentry for error tracking and performance monitoring.
 * Only enabled in staging and production environments.
 */

import * as Sentry from "@sentry/react";

/**
 * Initialize Sentry with environment-specific configuration
 */
export function initSentry() {
  const dsn = process.env.REACT_APP_SENTRY_DSN;
  const environment = process.env.REACT_APP_ENVIRONMENT || "development";
  const version = process.env.REACT_APP_VERSION || "unknown";
  const enableSentry = process.env.REACT_APP_ENABLE_SENTRY === "true";

  // Only initialize if DSN is provided and Sentry is enabled
  if (!dsn || !enableSentry) {
    console.log("[Sentry] Disabled in", environment);
    return;
  }

  Sentry.init({
    dsn,
    environment,
    release: `examcraft-frontend@${version}`,

    // Integrations
    integrations: [
      // Browser Tracing for Performance Monitoring
      Sentry.browserTracingIntegration(),

      // Session Replay for debugging (captures user interactions)
      Sentry.replayIntegration({
        maskAllText: true, // GDPR: Mask all text content
        blockAllMedia: true, // GDPR: Block all media (images, videos)
      }),
    ],

    // Performance Monitoring
    // Sample 100% of transactions in development, 10% in production
    tracesSampleRate: environment === "production" ? 0.1 : 1.0,

    // Session Replay Sampling
    // Capture 10% of all sessions
    replaysSessionSampleRate: 0.1,
    // Capture 100% of sessions with errors
    replaysOnErrorSampleRate: 1.0,

    // Error Filtering
    beforeSend(event, hint) {
      // Filter out non-critical errors
      if (event.exception) {
        const error = hint.originalException as any;

        // Don't send 404 errors
        if (error?.message?.includes("404")) {
          return null;
        }

        // Don't send network errors in development
        if (environment === "development" && error?.message?.includes("Network Error")) {
          return null;
        }

        // Don't send cancelled requests
        if (error?.message?.includes("canceled") || error?.message?.includes("cancelled")) {
          return null;
        }
      }

      return event;
    },

    // Ignore specific errors
    ignoreErrors: [
      // Browser extensions
      "top.GLOBALS",
      "chrome-extension://",
      "moz-extension://",
      // Random plugins/extensions
      "Can't find variable: ZiteReader",
      "jigsaw is not defined",
      "ComboSearch is not defined",
      // Network errors
      "NetworkError",
      "Network request failed",
      // React DevTools
      "__REACT_DEVTOOLS_GLOBAL_HOOK__",
    ],
  });

  console.log("[Sentry] Initialized for", environment, "with version", version);
}
