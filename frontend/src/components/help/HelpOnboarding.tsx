/**
 * HelpOnboarding — driver.js guided tour manager.
 * Manages two modes: SPOTLIGHTING (highlight page element) and
 * NAVIGATING (highlight nav link, wait for user to navigate).
 *
 * driver.js draws the overlay and the cutout; it is deliberately called
 * WITHOUT a `popover`, so it renders none of its own (see OnboardingPopover for
 * why). The popover is rendered here as React state, anchored to the very
 * element driver.js highlighted.
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
import OnboardingPopover from './OnboardingPopover';

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

/**
 * Bring the element about to be highlighted into view — synchronously.
 *
 * driver.js cannot be relied on for this. It skips scrolling whenever the
 * element already sits inside the *window* viewport, which misses anything
 * hidden inside a nested scroll container; and when it does scroll, it does so
 * asynchronously under `smoothScroll` while computing its stage from the
 * pre-scroll rect, leaving the cutout over empty space. Either way the target
 * ends up unreachable, and since the overlay swallows every event outside the
 * cutout the user cannot scroll there by hand — the tour dead-ends.
 *
 * Two real cases hit this, both found by manual testing:
 *   - a sidebar link below the fold of the nav's own `overflow-y-auto` box
 *     ("Prompt-Bibliothek" on a laptop);
 *   - an admin tab button above the viewport after the previous step scrolled
 *     down to that tab's long content.
 *
 * Scrolling first fixes both halves: the target becomes visible, and
 * driver.js's own in-view check then short-circuits, so it never starts a
 * competing async scroll that would misplace the highlight.
 *
 * `block` mirrors driver.js's own choice so the framing matches what the
 * library would have produced. jsdom implements no scrollIntoView, hence the
 * capability check.
 */
const scrollHighlightTargetIntoView = (el: Element): void => {
  if (typeof el.scrollIntoView !== 'function') return;
  const tallerThanViewport = (el as HTMLElement).offsetHeight > window.innerHeight;
  el.scrollIntoView({
    block: tallerThanViewport ? 'start' : 'center',
    inline: 'nearest',
  });
};

export interface OnboardingStep {
  step: number;
  /**
   * Prefix of this step's i18n keys — `<i18n_key>.title` and
   * `<i18n_key>.description` live in translation.json.
   *
   * The texts used to sit in help-onboarding-steps.json as `title_de`/`title_en`
   * field pairs, which made the tour a second translation surface next to
   * translation.json and hard-capped it at two languages: everything but
   * English fell back to German, so a French user got the whole tour in German
   * (TF-670). Carrying the key explicitly rather than deriving it from the
   * position lets the file be reordered without silently repointing texts.
   */
  i18n_key: string;
  route: string | null;
  highlight_selector: string | null;
  nav_selector: string | null;
  tab_selector: string | null;
}

/** Everything the popover needs for one step, regardless of step kind. */
interface ActivePopover {
  anchorEl: HTMLElement;
  title: string;
  description: string;
  /** null on nav/tab steps — there the user advances by clicking the element. */
  nextLabel: string | null;
  onNext: () => void;
}

interface HelpOnboardingProps {
  status: OnboardingStatus;
  steps: OnboardingStep[];
  active: boolean;
  /**
   * Whether a route is reachable for this user, from the RBAC-filtered nav
   * config (HelpWidget's `isRouteAccessible`). Passed in rather than derived
   * here so this component stays free of the auth/navigation hooks.
   *
   * Optional: without it every step is treated as reachable, which is the
   * pre-TF-625 behaviour — the step then falls back to the reveal-and-poll
   * path and is skipped after the timeout, as before.
   */
  isRouteAccessible?: (path: string) => boolean;
  onCompleteStep: (step: number) => Promise<void>;
  onSkipStep: (step: number) => Promise<void>;
  onTourComplete: () => void;
  onTourCancel: () => void;
}

const HelpOnboarding: React.FC<HelpOnboardingProps> = ({
  status,
  steps,
  active,
  isRouteAccessible,
  onCompleteStep,
  onSkipStep,
  onTourComplete,
  onTourCancel,
}) => {
  const { t } = useTranslation();
  const location = useLocation();

  // Refs — used inside driver.js callbacks to avoid stale closures
  const stepsRef = useRef<OnboardingStep[]>(steps);

  /**
   * Can this step be shown to this user at all?
   *
   * A step whose route is RBAC-filtered out of the navigation can never be
   * reached: the tour would ask the sidebar to reveal a link that does not
   * exist, poll for it, and skip once the budget runs out. Knowing it up front
   * removes NAV_REVEAL_TIMEOUT_MS of dead time per such step, and — more
   * importantly — lets the last *reachable* step label its button "Finish"
   * instead of "Next", so the tour does not promise pages that will never come.
   */
  const isStepReachableRef = useRef<(step: OnboardingStep) => boolean>(() => true);
  useEffect(() => {
    isStepReachableRef.current = (step: OnboardingStep) =>
      !step?.route || !isRouteAccessible || isRouteAccessible(step.route);
  }, [isRouteAccessible]);
  const driverRef = useRef<ReturnType<typeof createDriver> | null>(null);
  const pendingSpotlightRef = useRef<number | null>(null);
  const cancelStepRef = useRef<number>(0); // step to return to if confirm is cancelled

  // Confirmation dialog state
  const [showConfirm, setShowConfirm] = useState(false);

  // The popover for the step currently on screen, or null between steps.
  const [popover, setPopover] = useState<ActivePopover | null>(null);

  // Stable setter refs so callbacks reached from driver.js/observer code can
  // trigger React state without capturing a stale closure.
  const setShowConfirmRef = useRef(setShowConfirm);
  useEffect(() => { setShowConfirmRef.current = setShowConfirm; }, []);
  const setPopoverRef = useRef(setPopover);
  useEffect(() => { setPopoverRef.current = setPopover; }, []);

  // Keep stepsRef in sync when steps prop updates
  useEffect(() => { stepsRef.current = steps; }, [steps]);

  // Keep locationRef in sync so startStep can read current pathname without stale closure
  const locationRef = useRef(location);
  useEffect(() => { locationRef.current = location; }, [location]);

  /**
   * Tear down the overlay AND the popover together. They are two objects now,
   * so every path that drops one has to drop the other — otherwise a popover
   * outlives its cutout and points at an element nothing is highlighting.
   */
  const destroyDriver = useCallback(() => {
    if (driverRef.current) {
      driverRef.current.destroy();
      driverRef.current = null;
    }
    setPopoverRef.current(null);
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
   * Two kinds of skip, deliberately reported differently:
   *
   *   - `expected` — the route is RBAC-filtered out of this user's navigation.
   *     Nothing is wrong; a Dozent simply has one page under "Auswertungen"
   *     where an admin has three. Logging it as a warning (and paging Sentry)
   *     trained everyone to ignore the very signal below.
   *   - anything else — the element should have been there and was not. That
   *     used to be completely silent, which is how TF-604 hid a whole broken
   *     tour behind a "completed" flag. console.warn makes it visible to
   *     anyone with devtools open; Sentry.captureMessage (same pattern as
   *     Aktivitaeten.tsx) makes it visible without anyone needing to be
   *     looking — the BWZ-Lyss workshop bug went unnoticed precisely because
   *     nobody was.
   */
  const skipAndAdvance = useCallback(
    (stepIdx: number, reason: string, expected = false) => {
      const step = stepsRef.current[stepIdx];
      if (expected) {
        console.debug(`[onboarding] Step ${step?.step} not applicable: ${reason}`);
      } else {
        console.warn(`[onboarding] Step ${step?.step} skipped: ${reason}`);
        Sentry.captureMessage('[onboarding] step skipped', {
          level: 'warning',
          tags: { feature: 'onboarding', step: step?.step },
          extra: { reason },
        });
      }
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

      scrollHighlightTargetIntoView(el);

      // "Last" means last step the user will actually be shown — a later step
      // whose route they cannot reach does not count. Without this the button
      // said "Weiter →" on the final visible step of a partially accessible
      // track, promising pages that were then silently skipped.
      const remainingHaveSelector = stepsRef.current
        .slice(stepIdx + 1)
        .some((s) => !!s.highlight_selector && isStepReachableRef.current(s));
      const isLastContent = !remainingHaveSelector;

      const title = t(`${step.i18n_key}.title`);
      const description = t(`${step.i18n_key}.description`);

      cancelStepRef.current = stepIdx;

      const d = createDriver({
        allowClose: false,
        overlayOpacity: 0.5,
        stagePadding: 10,
        animate: true,
        smoothScroll: true,
      });

      // No `popover` key: driver.js renders overlay and cutout only.
      d.highlight({ element: step.highlight_selector! });

      driverRef.current = d;
      setPopoverRef.current({
        anchorEl: el as HTMLElement,
        title,
        description,
        nextLabel: isLastContent
          ? t('help.tour.finish', 'Fertig ✓')
          : t('help.tour.next', 'Weiter →'),
        onNext: () => {
          destroyDriver();
          onCompleteStep(step.step).then(() => startStepRef.current(stepIdx + 1));
        },
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [t, destroyDriver, onCompleteStep, onTourComplete, skipAndAdvance],
  );

  // ── NAVIGATING ──────────────────────────────────────────────────

  const showNavHighlight = useCallback(
    (stepIdx: number, navSelector: string) => {
      const step = stepsRef.current[stepIdx];

      destroyDriver();
      pendingSpotlightRef.current = stepIdx;

      // Before driver.js measures anything: the link may be scrolled out of
      // the sidebar's own overflow container.
      const navEl = document.querySelector(navSelector);
      if (!navEl) {
        // Callers resolve the link before getting here, so this is a race, not
        // an expected state. Bailing out beats highlighting nothing: driver.js
        // would fall back to its dummy element and leave an overlay with no
        // popover and no way out.
        skipAndAdvance(stepIdx, `nav element ${navSelector} vanished before highlight`);
        return;
      }
      scrollHighlightTargetIntoView(navEl);

      const title = t(`${step.i18n_key}.title`);
      const navInstruction = t(
        'help.tour.navInstruction',
        'Klicke den markierten Menüpunkt an um fortzufahren.',
      );

      cancelStepRef.current = stepIdx;

      const d = createDriver({
        allowClose: false,
        overlayOpacity: 0.4,
        stagePadding: 4,
        animate: true,
        smoothScroll: true,
      });

      // No `popover` key: driver.js renders overlay and cutout only.
      d.highlight({ element: navSelector });

      driverRef.current = d;
      setPopoverRef.current({
        anchorEl: navEl as HTMLElement,
        title,
        description: navInstruction,
        // The user advances by clicking the highlighted link itself.
        nextLabel: null,
        onNext: () => {},
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [t, destroyDriver, skipAndAdvance],
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

      // The previous step spotlighted this tab's content, which can be long
      // enough that the tab strip is now above the viewport — the same
      // unreachable-target problem as a sidebar link below the fold.
      scrollHighlightTargetIntoView(tabEl);

      const title = t(`${step.i18n_key}.title`);
      const tabInstruction = t(
        'help.tour.tabInstruction',
        'Klicke den markierten Tab an um fortzufahren.',
      );

      const d = createDriver({
        allowClose: false,
        overlayOpacity: 0.4,
        stagePadding: 4,
        animate: true,
        smoothScroll: true,
      });

      // No `popover` key: driver.js renders overlay and cutout only.
      d.highlight({ element: step.tab_selector });

      driverRef.current = d;
      setPopoverRef.current({
        anchorEl: tabEl as HTMLElement,
        title,
        description: tabInstruction,
        // The user advances by clicking the highlighted tab itself.
        nextLabel: null,
        onNext: () => {},
      });

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
    [t, destroyDriver, disconnectObserver, skipAndAdvance, highlightStep],
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

      // RBAC says this user has no such page. Skip now instead of asking the
      // sidebar to reveal a link that does not exist and waiting out
      // NAV_REVEAL_TIMEOUT_MS to learn the same thing.
      if (!isStepReachableRef.current(step)) {
        skipAndAdvance(stepIdx, `route ${step.route} not in this user's navigation`, true);
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
    [
      highlightStep,
      highlightTabStep,
      highlightNavStep,
      onCompleteStep,
      onTourComplete,
      skipAndAdvance,
    ],
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
    () => {
      // Re-arm on every (re)mount. React 18 StrictMode runs effect → cleanup →
      // effect in development, and the cleanup below latches
      // isUnmountedRef to true. Without resetting it here that latch sticks
      // for the rest of the component's life, every waitForNavElement poll
      // bails out on its first tick, and its promise is left pending by
      // design — so the tour freezes with no highlight and no way to cancel.
      //
      // Only the reveal path notices: when the nav link is already in the DOM
      // the fast path never polls. That is precisely the collapsed-group case
      // TF-604 exists for, which made the whole mechanism untestable in dev
      // while production (no double-invoke) kept working.
      isUnmountedRef.current = false;

      return () => {
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
      };
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

  /**
   * One close path for all three step kinds. The observer is only ever live
   * during a tab step, but disconnecting unconditionally is cheap and removes
   * the chance of a tab step's observer surviving a cancel.
   */
  const handlePopoverClose = useCallback(() => {
    destroyDriver();
    disconnectObserver();
    setShowConfirm(true);
  }, [destroyDriver, disconnectObserver]);

  return (
    <>
      {popover && !showConfirm && (
        <OnboardingPopover
          anchorEl={popover.anchorEl}
          title={popover.title}
          description={popover.description}
          nextLabel={popover.nextLabel}
          closeLabel={t('help.onboarding.closeTour', 'Tour beenden')}
          onNext={popover.onNext}
          onClose={handlePopoverClose}
        />
      )}
      {showConfirm && (
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
      )}
    </>
  );
};

export default HelpOnboarding;
