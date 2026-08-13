/**
 * HelpOnboarding — driver.js guided tour manager.
 * Manages two modes: SPOTLIGHTING (highlight page element) and
 * NAVIGATING (highlight nav link, wait for user to navigate).
 * Always renders null or a confirmation dialog — no visible UI otherwise.
 */
import React, { useEffect, useRef, useCallback, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { driver as createDriver } from 'driver.js';
import 'driver.js/dist/driver.css';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
} from '@mui/material';
import * as Sentry from '@sentry/react';
import { OnboardingStatus } from '../../services/HelpService';
import { requestSidebarNavReveal } from '../layout/sidebarNavReveal';

/**
 * How long to wait for a nav link to show up after asking the sidebar to
 * reveal its group (TF-604). Only spent when the link is missing initially.
 * Revealing goes through a React state update + re-render on the Sidebar
 * side, not a synchronous DOM write, so it can take more than one poll tick —
 * the budget (10 ticks at the default interval) is deliberately generous
 * rather than tuned to a measured "usually resolves in N ticks" figure.
 */
const NAV_REVEAL_TIMEOUT_MS = 500;
const NAV_REVEAL_POLL_MS = 50;

/**
 * Resolve a nav element, asking the sidebar to open its group if it is not in
 * the DOM yet. Resolves with `null` once the budget is exhausted — this does
 * NOT necessarily mean the link is RBAC-filtered for this user; it also
 * covers the route not being in the nav config at all, or the sidebar's user
 * context not being loaded yet. Callers should treat `null` as "not
 * reachable via the sidebar right now", not as a confirmed permission check.
 *
 * `isCancelled`/`registerTimeout` let the caller cancel a pending poll on
 * unmount (TF-604 review fix): without them, an in-flight poll outlives an
 * unmounted HelpOnboarding and its resolution can fire a stale API write
 * (`onSkipStep`) or inject a driver.js overlay nothing will ever clean up.
 * When `isCancelled()` is true the returned promise is left permanently
 * pending — deliberately, so `.then()` on the caller's side never runs.
 */
const waitForNavElement = (
  selector: string,
  route: string | null,
  isCancelled: () => boolean,
  registerTimeout: (id: ReturnType<typeof setTimeout>) => void,
): Promise<Element | null> => {
  const existing = document.querySelector(selector);
  if (existing) return Promise.resolve(existing);
  // Without a route the sidebar cannot resolve a group — nothing to ask for.
  if (!route) return Promise.resolve(null);

  requestSidebarNavReveal(route);

  return new Promise((resolve) => {
    const deadline = Date.now() + NAV_REVEAL_TIMEOUT_MS;
    const poll = () => {
      if (isCancelled()) return;
      const el = document.querySelector(selector);
      if (el || Date.now() >= deadline) {
        resolve(el);
        return;
      }
      registerTimeout(setTimeout(poll, NAV_REVEAL_POLL_MS));
    };
    registerTimeout(setTimeout(poll, NAV_REVEAL_POLL_MS));
  });
};

export interface OnboardingStep {
  step: number;
  title_de: string;
  title_en: string;
  description_de: string;
  description_en: string;
  route: string | null;
  highlight_selector: string | null;
  nav_selector: string | null;
  tab_selector: string | null;
}

interface HelpOnboardingProps {
  status: OnboardingStatus;
  steps: OnboardingStep[];
  active: boolean;
  onCompleteStep: (step: number) => Promise<void>;
  onSkipStep: (step: number) => Promise<void>;
  onTourComplete: () => void;
  onTourCancel: () => void;
}

const HelpOnboarding: React.FC<HelpOnboardingProps> = ({
  status,
  steps,
  active,
  onCompleteStep,
  onSkipStep,
  onTourComplete,
  onTourCancel,
}) => {
  const { i18n, t } = useTranslation();
  const location = useLocation();
  const locale = i18n.language?.substring(0, 2) || 'de';

  // Refs — used inside driver.js callbacks to avoid stale closures
  const stepsRef = useRef<OnboardingStep[]>(steps);
  const driverRef = useRef<ReturnType<typeof createDriver> | null>(null);
  const pendingSpotlightRef = useRef<number | null>(null);
  const cancelStepRef = useRef<number>(0); // step to return to if confirm is cancelled

  // Confirmation dialog state
  const [showConfirm, setShowConfirm] = useState(false);

  // Stable setter ref so driver.js callbacks can trigger React state
  const setShowConfirmRef = useRef(setShowConfirm);
  useEffect(() => { setShowConfirmRef.current = setShowConfirm; }, []);

  // Keep stepsRef in sync when steps prop updates
  useEffect(() => { stepsRef.current = steps; }, [steps]);

  // Keep locationRef in sync so startStep can read current pathname without stale closure
  const locationRef = useRef(location);
  useEffect(() => { locationRef.current = location; }, [location]);

  const destroyDriver = useCallback(() => {
    if (driverRef.current) {
      driverRef.current.destroy();
      driverRef.current = null;
    }
  }, []);

  const observerRef = useRef<MutationObserver | null>(null);

  const disconnectObserver = useCallback(() => {
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
  }, []);

  // ── SKIPPING ────────────────────────────────────────────────────

  // Forward ref to allow mutual recursion between startStep and the highlight
  // callbacks below.
  const startStepRef = useRef<(stepIdx: number) => void>(() => {});

  // TF-604 review fix: waitForNavElement's poll chain has no cleanup of its
  // own (it is a plain module-level function, not a hook) — these let the
  // unmount effect near the bottom of this component cancel a pending poll
  // instead of letting it resolve against an unmounted component.
  const isUnmountedRef = useRef(false);
  const pendingPollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /**
   * Record the step as skipped and move on.
   *
   * Skipping is a legitimate path (a step whose route the user has no access
   * to), but it used to be completely silent — which is how TF-604 hid a whole
   * broken tour behind a "completed" flag. console.warn makes it visible to
   * anyone with devtools open; Sentry.captureMessage (same pattern as
   * Aktivitaeten.tsx) makes it visible without anyone needing to be looking —
   * the BWZ-Lyss workshop bug went unnoticed precisely because nobody was.
   */
  const skipAndAdvance = useCallback(
    (stepIdx: number, reason: string) => {
      const step = stepsRef.current[stepIdx];
      console.warn(`[onboarding] Step ${step?.step} skipped: ${reason}`);
      Sentry.captureMessage('[onboarding] step skipped', {
        level: 'warning',
        tags: { feature: 'onboarding', step: step?.step },
        extra: { reason },
      });
      onSkipStep(step.step).then(() => {
        const next = stepIdx + 1;
        if (next < stepsRef.current.length) {
          startStepRef.current(next);
        } else {
          onTourComplete();
        }
      });
    },
    [onSkipStep, onTourComplete],
  );

  // ── SPOTLIGHTING ────────────────────────────────────────────────

  const highlightStep = useCallback(
    (stepIdx: number) => {
      const step = stepsRef.current[stepIdx];

      if (!step?.highlight_selector && !step?.route) {
        onCompleteStep(step.step).then(() => onTourComplete());
        return;
      }

      if (!step?.highlight_selector && step?.route) {
        onCompleteStep(step.step).then(() => {
          const next = stepIdx + 1;
          if (next < stepsRef.current.length) {
            startStepRef.current(next);
          } else {
            onTourComplete();
          }
        });
        return;
      }

      destroyDriver();

      const el = document.querySelector(step.highlight_selector!);
      if (!el) {
        skipAndAdvance(stepIdx, `highlight element ${step.highlight_selector} not in DOM`);
        return;
      }

      const remainingHaveSelector = stepsRef.current
        .slice(stepIdx + 1)
        .some((s) => !!s.highlight_selector);
      const isLastContent = !remainingHaveSelector;

      const title = locale === 'en' ? step.title_en : step.title_de;
      const description = locale === 'en' ? step.description_en : step.description_de;

      cancelStepRef.current = stepIdx;

      const d = createDriver({
        allowClose: false,
        overlayOpacity: 0.5,
        stagePadding: 10,
        animate: true,
        smoothScroll: true,
      });

      d.highlight({
        element: step.highlight_selector!,
        popover: {
          title,
          description,
          showButtons: ['next', 'close'],
          nextBtnText: isLastContent
            ? (locale === 'en' ? 'Finish ✓' : 'Fertig ✓')
            : (locale === 'en' ? 'Next →' : 'Weiter →'),
          onNextClick: () => {
            d.destroy();
            driverRef.current = null;
            onCompleteStep(step.step).then(() => startStepRef.current(stepIdx + 1));
          },
          onCloseClick: () => {
            d.destroy();
            driverRef.current = null;
            setShowConfirmRef.current(true);
          },
        },
      });

      driverRef.current = d;
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [locale, destroyDriver, onCompleteStep, onTourComplete, skipAndAdvance],
  );

  // ── NAVIGATING ──────────────────────────────────────────────────

  const showNavHighlight = useCallback(
    (stepIdx: number, navSelector: string) => {
      const step = stepsRef.current[stepIdx];

      destroyDriver();
      pendingSpotlightRef.current = stepIdx;

      const title = locale === 'en' ? step.title_en : step.title_de;
      const navInstruction =
        locale === 'en'
          ? 'Click the highlighted menu item to continue.'
          : 'Klicke den markierten Menüpunkt an um fortzufahren.';

      cancelStepRef.current = stepIdx;

      const d = createDriver({
        allowClose: false,
        overlayOpacity: 0.4,
        stagePadding: 4,
        animate: true,
        smoothScroll: true,
      });

      d.highlight({
        element: navSelector,
        popover: {
          title,
          description: navInstruction,
          showButtons: ['close'],
          onCloseClick: () => {
            d.destroy();
            driverRef.current = null;
            setShowConfirmRef.current(true);
          },
        },
      });

      driverRef.current = d;
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [locale, destroyDriver],
  );

  const highlightNavStep = useCallback(
    (stepIdx: number, navSelector: string) => {
      const step = stepsRef.current[stepIdx];

      // Fast path: link already rendered — highlight synchronously, no flicker.
      if (document.querySelector(navSelector)) {
        showNavHighlight(stepIdx, navSelector);
        return;
      }

      // TF-604: a missing link usually means its sidebar group is collapsed
      // (TF-372 renders group items conditionally), not that the user lacks
      // access. Ask the sidebar to open the group and retry before skipping.
      waitForNavElement(
        navSelector,
        step.route,
        () => isUnmountedRef.current,
        (id) => { pendingPollTimeoutRef.current = id; },
      ).then((el) => {
        // Review fix: the user may have navigated to the step's own route
        // while the reveal was pending. Highlighting a nav link for a page
        // that's already open produces no click/navigation, so the tour
        // would stall until manually aborted — re-enter startStep so it
        // re-evaluates fresh and takes the "already there" branch instead.
        if (step.route && locationRef.current.pathname === step.route) {
          startStepRef.current(stepIdx);
          return;
        }
        if (el) {
          showNavHighlight(stepIdx, navSelector);
        } else {
          skipAndAdvance(stepIdx, `nav element ${navSelector} not in DOM after reveal`);
        }
      });
    },
    [showNavHighlight, skipAndAdvance],
  );

  // ── TAB_NAVIGATING ────────────────────────────────────────────────

  const highlightTabStep = useCallback(
    (stepIdx: number) => {
      const step = stepsRef.current[stepIdx];
      if (!step?.tab_selector) {
        setTimeout(() => highlightStep(stepIdx), 400);
        return;
      }

      // If tab button not in DOM (tab not visible for this user) — skip step
      const tabEl = document.querySelector(step.tab_selector);
      if (!tabEl) {
        skipAndAdvance(stepIdx, `tab element ${step.tab_selector} not in DOM`);
        return;
      }

      destroyDriver();
      disconnectObserver();
      cancelStepRef.current = stepIdx;

      const title = locale === 'en' ? step.title_en : step.title_de;
      const tabInstruction =
        locale === 'en'
          ? 'Click the highlighted tab to continue.'
          : 'Klicke den markierten Tab an um fortzufahren.';

      const d = createDriver({
        allowClose: false,
        overlayOpacity: 0.4,
        stagePadding: 4,
        animate: true,
        smoothScroll: true,
      });

      d.highlight({
        element: step.tab_selector,
        popover: {
          title,
          description: tabInstruction,
          showButtons: ['close'],
          onCloseClick: () => {
            d.destroy();
            driverRef.current = null;
            disconnectObserver();
            setShowConfirmRef.current(true);
          },
        },
      });

      driverRef.current = d;

      // Watch for tab content to appear in DOM
      const observer = new MutationObserver(() => {
        const contentEl = document.querySelector(step.highlight_selector!);
        if (contentEl) {
          observer.disconnect();
          observerRef.current = null;
          destroyDriver();
          setTimeout(() => highlightStep(stepIdx), 200);
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });
      observerRef.current = observer;
    },
    [locale, destroyDriver, disconnectObserver, skipAndAdvance, highlightStep],
  );

  // ── ROUTING LOGIC ───────────────────────────────────────────────

  const startStep = useCallback(
    (stepIdx: number) => {
      const step = stepsRef.current[stepIdx];
      if (!step) { onTourComplete(); return; }

      if (!step.route && !step.highlight_selector) {
        onCompleteStep(step.step).then(() => onTourComplete());
        return;
      }

      if (!step.route || locationRef.current.pathname === step.route) {
        if (step.tab_selector) {
          highlightTabStep(stepIdx);
        } else {
          setTimeout(() => highlightStep(stepIdx), 400);
        }
        return;
      }

      // Without an explicit nav_selector, derive it from the route (matches the
      // Sidebar data-testid pattern). highlightNavStep handles a link that is
      // not in the DOM — reveal first, skip only if it stays absent.
      // `||` (not `??`): an empty-string nav_selector must also fall through
      // to the derived selector — `document.querySelector('')` throws a
      // SyntaxError and would kill the tour outright (review fix).
      const derivedSelector = `[data-testid='nav-${step.route.slice(1).replace(/\//g, '-')}']`;
      highlightNavStep(stepIdx, step.nav_selector || derivedSelector);
    },
    [highlightStep, highlightTabStep, highlightNavStep, onCompleteStep, onTourComplete],
  );

  useEffect(() => { startStepRef.current = startStep; }, [startStep]);

  // Watch location — when user navigates to expected route, switch to SPOTLIGHTING
  useEffect(() => {
    if (pendingSpotlightRef.current === null) return;
    const stepIdx = pendingSpotlightRef.current;
    const step = stepsRef.current[stepIdx];
    if (!step?.route) return;
    if (location.pathname !== step.route) return;

    pendingSpotlightRef.current = null;
    destroyDriver();

    if (step.tab_selector) {
      highlightTabStep(stepIdx);
      return;
    }

    // If the highlight element is already in DOM, highlight after brief settle delay.
    // Otherwise use MutationObserver to wait for it (handles lazy-loaded pages).
    const selector = step.highlight_selector;
    if (!selector || document.querySelector(selector)) {
      const timeout = setTimeout(() => highlightStep(stepIdx), 400);
      return () => clearTimeout(timeout);
    }

    const observer = new MutationObserver(() => {
      if (document.querySelector(selector)) {
        observer.disconnect();
        clearTimeout(fallback);
        setTimeout(() => highlightStep(stepIdx), 200);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    // Fallback: if element never appears after 3s, call highlightStep anyway (handles missing gracefully)
    const fallback = setTimeout(() => {
      observer.disconnect();
      highlightStep(stepIdx);
    }, 3000);

    return () => {
      observer.disconnect();
      clearTimeout(fallback);
    };
  }, [location.pathname, destroyDriver, highlightStep, highlightTabStep]);

  // Start tour when `active` becomes true
  useEffect(() => {
    if (!active || steps.length === 0) return;
    startStepRef.current(status.current_step);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  // Cleanup on unmount
  useEffect(
    () => () => {
      // Review fix: stop any in-flight waitForNavElement poll immediately
      // (clearTimeout) and flip isUnmountedRef so a poll tick already queued
      // in the event loop bails out via its isCancelled() check instead of
      // resolving into a stale showNavHighlight/skipAndAdvance call.
      isUnmountedRef.current = true;
      if (pendingPollTimeoutRef.current) {
        clearTimeout(pendingPollTimeoutRef.current);
        pendingPollTimeoutRef.current = null;
      }
      destroyDriver();
      disconnectObserver();
    },
    [destroyDriver, disconnectObserver],
  );

  // ── CONFIRMATION DIALOG ─────────────────────────────────────────

  const handleConfirmEnd = useCallback(() => {
    setShowConfirm(false);
    pendingSpotlightRef.current = null;
    onTourCancel();
  }, [onTourCancel]);

  const handleCancelEnd = useCallback(() => {
    setShowConfirm(false);
    // Re-highlight the step the user was on
    setTimeout(() => startStepRef.current(cancelStepRef.current), 100);
  }, []);

  if (!showConfirm) return null;

  return (
    <Dialog
      open
      disableEscapeKeyDown
      PaperProps={{ sx: { borderRadius: 2, maxWidth: 420, mx: 2, zIndex: 99999 } }}
    >
      <DialogTitle>{t('help.onboarding.confirmEndTitle', 'Tour beenden?')}</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary">
          {t(
            'help.onboarding.confirmEndText',
            'Du kannst die Tour später über den Hilfe-Button unten rechts neu starten.',
          )}
        </Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
        <Button onClick={handleCancelEnd} variant="outlined">
          {t('help.onboarding.confirmEndCancel', 'Abbrechen')}
        </Button>
        <Button onClick={handleConfirmEnd} variant="contained" color="error">
          {t('help.onboarding.confirmEndConfirm', 'Ja, beenden')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default HelpOnboarding;
