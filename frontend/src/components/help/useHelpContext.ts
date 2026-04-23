import { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { helpService, HelpStatus, OnboardingStatus, ContextHint } from '../../services/HelpService';

const SESSION_HINTS_KEY = 'ec_help_hints_shown';

function getSessionHintIds(): number[] {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_HINTS_KEY) || '[]');
  } catch {
    return [];
  }
}

function recordSessionHint(hintId: number): void {
  const shown = getSessionHintIds();
  if (!shown.includes(hintId)) {
    shown.push(hintId);
    sessionStorage.setItem(SESSION_HINTS_KEY, JSON.stringify(shown));
  }
}

export function useHelpContext() {
  const { accessToken, hasRole } = useAuth();
  const location = useLocation();
  const { i18n } = useTranslation();

  const [helpStatus, setHelpStatus] = useState<HelpStatus | null>(null);
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null);
  const [contextHint, setContextHint] = useState<ContextHint | null>(null);
  const [loading, setLoading] = useState(true);

  const role = hasRole('admin') ? 'admin' : 'teacher';
  const locale = i18n.language?.substring(0, 2) || 'de';
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

  useEffect(() => {
    if (!accessToken || !route) return;
    if (getSessionHintIds().length >= 3) return; // Max 3 per session
    helpService
      .getContextHint(accessToken, route)
      .then((hint) => {
        if (hint.hint_text && hint.hint_id) {
          recordSessionHint(hint.hint_id);
        }
        setContextHint(hint);
      })
      .catch((err) => { console.warn('Context hint fetch failed:', err); setContextHint(null); });
  }, [accessToken, route]);

  const completeStep = useCallback(
    async (step: number) => {
      if (!accessToken) return;
      try {
        const updated = await helpService.completeOnboardingStep(accessToken, step);
        setOnboardingStatus(updated);
      } catch (err) {
        console.warn('Failed to complete onboarding step:', err);
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
      }
    },
    [accessToken]
  );

  return {
    role,
    locale,
    route,
    helpStatus,
    onboardingStatus,
    contextHint,
    loading,
    completeStep,
    skipStep,
    chatAvailable: helpStatus?.modes.chat ?? false,
    showOnboarding: onboardingStatus !== null && !onboardingStatus.completed,
    hasContextHint: contextHint?.hint_text !== null && contextHint?.hint_text !== undefined,
    hasSkippedSteps: (onboardingStatus?.skipped_steps?.length ?? 0) > 0,
  };
}
