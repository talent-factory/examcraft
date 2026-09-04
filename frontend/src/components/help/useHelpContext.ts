import { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import * as Sentry from '@sentry/react';
import { useAuth } from '../../contexts/AuthContext';
import { helpService, HelpStatus, OnboardingStatus, ContextHint } from '../../services/HelpService';

/**
 * Hints the user has acknowledged with "Verstanden" in this tab.
 *
 * Deliberately NOT the hints that were displayed: nothing hides a hint except
 * the user saying so. The old key `ec_help_hints_shown` recorded what the app
 * had put on screen and retired hints on the user's behalf — renamed rather
 * than reused so a stale list from an open tab cannot be mistaken for consent.
 */
const SESSION_HINTS_KEY = 'ec_help_hints_acknowledged';

function getAcknowledgedHintIds(): number[] {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_HINTS_KEY) || '[]');
  } catch {
    return [];
  }
}

function recordAcknowledgedHint(hintId: number): void {
  const acknowledged = getAcknowledgedHintIds();
  if (!acknowledged.includes(hintId)) {
    acknowledged.push(hintId);
    sessionStorage.setItem(SESSION_HINTS_KEY, JSON.stringify(acknowledged));
  }
}

export function useHelpContext() {
  const { accessToken, hasRole } = useAuth();
  const location = useLocation();

  const [helpStatus, setHelpStatus] = useState<HelpStatus | null>(null);
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null);
  const [contextHint, setContextHint] = useState<ContextHint | null>(null);
  const [loading, setLoading] = useState(true);

  const role = hasRole('admin') ? 'admin' : 'teacher';
  const route = location.pathname;

  useEffect(() => {
    helpService.getStatus().then(setHelpStatus).catch((err) => {
      console.warn('Help status fetch failed, using defaults:', err);
      setHelpStatus({ modes: { onboarding: true, context: true, chat: false } });
    });
  }, []);

  useEffect(() => {
    if (!accessToken) return;
    helpService
      .getOnboardingStatus(accessToken)
      .then(setOnboardingStatus)
      .catch((err) => { console.warn('Onboarding status fetch failed:', err); setOnboardingStatus(null); })
      .finally(() => setLoading(false));
  }, [accessToken]);

  /**
   * One resolved hint per route, for this mount.
   *
   * Without it every navigation hit /help/context — the widget is mounted
   * app-wide, so browsing a handful of pages with it open was enough to trip
   * the IP rate limiter and log the user out.
   *
   * Only successful lookups are cached: a transient failure must not blank a
   * route for the rest of the session.
   */
  const hintByRouteRef = useRef<Map<string, ContextHint>>(new Map());

  /**
   * A hint is hidden only by the user's own choice.
   *
   * TF-308 capped a session at three hints as flood protection. The number was
   * written when no role could reach more than two, so it never bound anything
   * — until the dead route patterns `/documents/upload` and `/exam/create`
   * were repaired (TF-625) and a teacher had four live hints. `/exams/compose`
   * is always the fourth stop in the workflow, so its hint became unreachable
   * rather than merely rare.
   *
   * The cap is gone entirely rather than re-tuned. Flooding is already
   * impossible by construction: one hint per page, collapsed to a single
   * truncated line, and visible only inside a panel the user opened. What is
   * left is the user's decision — "Verstanden" for this tab, "Nicht mehr
   * anzeigen" for good — and nothing retires a hint behind their back.
   */
  const applyHint = useCallback((hint: ContextHint) => {
    if (hint.hint_id != null && getAcknowledgedHintIds().includes(hint.hint_id)) {
      setContextHint(null);
      return;
    }
    setContextHint(hint);
  }, []);

  useEffect(() => {
    if (!accessToken || !route) return;

    const cached = hintByRouteRef.current.get(route);
    if (cached) {
      applyHint(cached);
      return;
    }

    // A stale response guard: without it, a slower response for a route the
    // user has since navigated away from can land after a faster response
    // for the new route — either overwriting the current route's hint with
    // the old one, or (on the old route's failure) blanking the new route's
    // hint via the catch below. `cancelled` makes both cases no-ops.
    let cancelled = false;
    helpService
      .getContextHint(accessToken, route)
      .then((hint) => {
        if (cancelled) return;
        hintByRouteRef.current.set(route, hint);
        applyHint(hint);
      })
      .catch((err) => {
        if (cancelled) return;
        console.warn('Context hint fetch failed:', err);
        setContextHint(null);
      });

    return () => {
      cancelled = true;
    };
  }, [accessToken, route, applyHint]);

  /**
   * "Verstanden": hide this hint for the rest of the tab.
   *
   * Recorded in sessionStorage rather than component state so the choice
   * survives navigation and a reload. It used to live in a single
   * `dismissedHintId` slot on HelpWidget, which held exactly one id — so
   * acknowledging a second hint resurrected the first.
   *
   * This is the weaker of the two dismissals; "Nicht mehr anzeigen" writes to
   * `help_dismissed_hints` on the server and outlives the tab.
   */
  const acknowledgeHint = useCallback((hintId: number) => {
    recordAcknowledgedHint(hintId);
    setContextHint(null);
  }, []);

  // The three writers below deliberately never reject: the caller (the
  // driver.js step machine in HelpOnboarding) chains .then() unconditionally
  // to advance the tour, and blocking that on a flaky connection would strand
  // the user mid-tour rather than just leaving the server-side progress one
  // write behind — it catches up on the next successful call. But a swallowed
  // failure that leaves no trace anywhere is exactly the TF-604 bug class
  // (a whole broken tour hidden behind a "completed" flag); Sentry.captureException
  // here matches the visibility skipAndAdvance already gives an unreachable step.
  const completeStep = useCallback(
    async (step: number) => {
      if (!accessToken) return;
      try {
        const updated = await helpService.completeOnboardingStep(accessToken, step);
        setOnboardingStatus(updated);
      } catch (err) {
        console.warn('Failed to complete onboarding step:', err);
        Sentry.captureException(err, {
          tags: { feature: 'onboarding', action: 'completeStep', step },
        });
      }
    },
    [accessToken]
  );

  const skipStep = useCallback(
    async (step: number) => {
      if (!accessToken) return;
      try {
        const updated = await helpService.skipOnboardingStep(accessToken, step);
        setOnboardingStatus(updated);
      } catch (err) {
        console.warn('Failed to skip onboarding step:', err);
        Sentry.captureException(err, {
          tags: { feature: 'onboarding', action: 'skipStep', step },
        });
      }
    },
    [accessToken]
  );

  // TF-625: deep-dive tracks write into their own progress space and must
  // neither advance nor complete the core tour.
  const updateTrackStep = useCallback(
    async (trackId: string, step: number, totalSteps: number, skipped = false) => {
      if (!accessToken) return;
      try {
        const updated = await helpService.updateTrackStep(
          accessToken,
          trackId,
          step,
          totalSteps,
          skipped
        );
        setOnboardingStatus(updated);
      } catch (err) {
        console.warn('Failed to update onboarding track step:', err);
        Sentry.captureException(err, {
          tags: { feature: 'onboarding', action: 'updateTrackStep', trackId, step },
        });
      }
    },
    [accessToken]
  );

  return {
    role,
    route,
    helpStatus,
    onboardingStatus,
    contextHint,
    loading,
    completeStep,
    skipStep,
    updateTrackStep,
    acknowledgeHint,
    trackProgress: onboardingStatus?.track_progress ?? {},
    chatAvailable: helpStatus?.modes.chat ?? false,
    showOnboarding: onboardingStatus !== null && !onboardingStatus.completed,
    hasContextHint: contextHint?.i18n_key !== null && contextHint?.i18n_key !== undefined,
    hasSkippedSteps: (onboardingStatus?.skipped_steps?.length ?? 0) > 0,
  };
}
