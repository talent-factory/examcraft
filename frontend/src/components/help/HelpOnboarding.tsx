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
import { OnboardingStatus } from '../../services/HelpService';

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
        onSkipStep(step.step).then(() => {
          const next = stepIdx + 1;
          if (next < stepsRef.current.length) {
            startStepRef.current(next);
          } else {
            onTourComplete();
          }
        });
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
    [locale, destroyDriver, onCompleteStep, onTourComplete],
  );

  // ── NAVIGATING ──────────────────────────────────────────────────

  const highlightNavStep = useCallback(
    (stepIdx: number, navSelectorOverride?: string) => {
      const step = stepsRef.current[stepIdx];
      const navSelector = navSelectorOverride ?? step?.nav_selector;
      if (!navSelector) {
        // No nav link to guide — skip step rather than waiting silently
        onSkipStep(step.step).then(() => {
          const next = stepIdx + 1;
          if (next < stepsRef.current.length) {
            startStepRef.current(next);
          } else {
            onTourComplete();
          }
        });
        return;
      }

      // Skip immediately if nav element is not in DOM — no flicker, no delay
      if (!document.querySelector(navSelector)) {
        onSkipStep(step.step).then(() => {
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
    [locale, destroyDriver, onCompleteStep, onTourComplete],
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
        onSkipStep(step.step).then(() => {
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
    [locale, destroyDriver, disconnectObserver, onCompleteStep, onSkipStep, onTourComplete, highlightStep],
  );

  // ── ROUTING LOGIC ───────────────────────────────────────────────

  // Forward ref to allow mutual recursion between startStep and highlightStep
  const startStepRef = useRef<(stepIdx: number) => void>(() => {});

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

      if (step.nav_selector) {
        highlightNavStep(stepIdx);
      } else {
        // No explicit nav_selector — derive it from the route (matches Sidebar data-testid pattern)
        const derivedSelector = `[data-testid='nav-${step.route.slice(1).replace(/\//g, '-')}']`;
        if (document.querySelector(derivedSelector)) {
          highlightNavStep(stepIdx, derivedSelector);
        } else {
          // Nav element not in DOM → user has no access to this route → skip step
          onSkipStep(step.step).then(() => {
            const next = stepIdx + 1;
            if (next < stepsRef.current.length) {
              startStepRef.current(next);
            } else {
              onTourComplete();
            }
          });
        }
      }
    },
    [highlightStep, highlightTabStep, highlightNavStep, onCompleteStep, onSkipStep, onTourComplete],
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
  useEffect(() => () => { destroyDriver(); disconnectObserver(); }, [destroyDriver, disconnectObserver]);

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
