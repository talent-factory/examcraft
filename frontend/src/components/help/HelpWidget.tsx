import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Paper,
  IconButton,
  Badge,
  Slide,
  Box,
  Typography,
  Button,
} from '@mui/material';
import { HelpOutline, Close, PlayArrow } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useHelpContext } from './useHelpContext';
import OnboardingModal from './OnboardingModal';
import HelpOnboarding from './HelpOnboarding';
import HelpContextHint from './HelpContextHint';
import HelpChat from './HelpChat';

const HelpWidget: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [tourActive, setTourActive] = useState(false);
  const [tourJustCompleted, setTourJustCompleted] = useState(false);
  const [modalDismissed, setModalDismissed] = useState(false);
  const [contextHintDismissed, setContextHintDismissed] = useState(false);
  const [onboardingSteps, setOnboardingSteps] = useState<any[]>([]);
  const [catchUpMode, setCatchUpMode] = useState(false);
  const [catchUpSteps, setCatchUpSteps] = useState<any[]>([]);
  const [panelSize, setPanelSize] = useState({ width: 360, height: 520 });
  const resizeRef = useRef<{ startX: number; startY: number; startW: number; startH: number } | null>(null);
  const { t } = useTranslation();

  const MIN_WIDTH = 360;
  const MIN_HEIGHT = 520;
  const MAX_WIDTH = Math.min(800, typeof window !== 'undefined' ? window.innerWidth - 80 : 800);
  const MAX_HEIGHT = typeof window !== 'undefined' ? window.innerHeight - 120 : 900;

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    resizeRef.current = { startX: e.clientX, startY: e.clientY, startW: panelSize.width, startH: panelSize.height };
    const onMove = (ev: MouseEvent) => {
      if (!resizeRef.current) return;
      const dw = resizeRef.current.startX - ev.clientX;
      const dh = resizeRef.current.startY - ev.clientY;
      setPanelSize({
        width: Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, resizeRef.current.startW + dw)),
        height: Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, resizeRef.current.startH + dh)),
      });
    };
    const onUp = () => {
      resizeRef.current = null;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [panelSize, MAX_WIDTH, MAX_HEIGHT]);

  const {
    showOnboarding,
    hasContextHint,
    hasSkippedSteps,       // add this
    contextHint,
    onboardingStatus,
    chatAvailable,
    completeStep,
    skipStep,              // add this
    role,
    route,
  } = useHelpContext();

  // Load onboarding steps JSON when onboarding is active
  useEffect(() => {
    if ((!showOnboarding && !hasSkippedSteps) || !role) return;
    fetch('/help-onboarding-steps.json')
      .then((res) => res.json())
      .then((data) => setOnboardingSteps(data[role] || []))
      .catch((err) => console.warn('Failed to load onboarding steps:', err));
  }, [showOnboarding, hasSkippedSteps, role]);

  // Catch-up: beim Panel-Öffnen prüfen, welche skipped Steps jetzt zugänglich sind
  useEffect(() => {
    if (!open || !onboardingStatus?.completed) return;
    const skipped = onboardingStatus.skipped_steps ?? [];
    if (skipped.length === 0 || onboardingSteps.length === 0) return;

    const accessible = skipped
      .map((n: number) => onboardingSteps.find((s: any) => s.step === n))
      .filter(Boolean)
      .filter((step: any) => {
        const sel =
          step.nav_selector ??
          `[data-testid='nav-${step.route?.slice(1).replace(/\//g, '-')}']`;
        return !!document.querySelector(sel);
      });

    setCatchUpSteps(accessible);
  }, [open, onboardingStatus, onboardingSteps]);

  // Keyboard shortcut: Ctrl+/ or Cmd+/
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        const active = document.activeElement;
        if (
          active &&
          (active.tagName === 'INPUT' ||
            active.tagName === 'TEXTAREA' ||
            (active as HTMLElement).isContentEditable)
        ) {
          return;
        }
        e.preventDefault();
        if (!tourActive) setOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [tourActive]);

  const toggle = useCallback(() => {
    if (!tourActive) {
      setOpen((prev) => !prev);
      if (tourJustCompleted) setTourJustCompleted(false);
    }
  }, [tourActive, tourJustCompleted]);

  const handleStartTour = useCallback(async () => {
    setModalDismissed(true);
    await completeStep(0);
    setTourActive(true);
  }, [completeStep]);

  const handleModalLater = useCallback(() => {
    setModalDismissed(true);
  }, []);

  const handleTourComplete = useCallback(() => {
    setTourActive(false);
    setTourJustCompleted(true);
    setOpen(true);
  }, []);

  const handleTourCancel = useCallback(() => {
    setTourActive(false);
  }, []);

  const handleStartCatchUp = useCallback(() => {
    setOpen(false);
    setCatchUpMode(true);
    setTourActive(true);
  }, []);

  const handleCatchUpComplete = useCallback(() => {
    setCatchUpMode(false);
    setCatchUpSteps([]);
    setTourActive(false);
    setOpen(true);
  }, []);

  // FAB pulses when onboarding is pending, panel is closed, and no active tour
  const fabPulse = showOnboarding && !open && !tourActive;

  // Show welcome modal when onboarding is at step 0 and not dismissed
  const showModal =
    showOnboarding &&
    onboardingStatus?.current_step === 0 &&
    !tourActive &&
    !modalDismissed &&
    onboardingSteps.length > 0;

  const welcomeStep = onboardingSteps[0];

  return (
    <>
      {/* Welcome Modal (auto-appears on first login) */}
      {welcomeStep && (
        <OnboardingModal
          open={showModal}
          titleDe={welcomeStep.title_de}
          titleEn={welcomeStep.title_en}
          descriptionDe={welcomeStep.description_de}
          descriptionEn={welcomeStep.description_en}
          onStart={handleStartTour}
          onLater={handleModalLater}
        />
      )}

      {/* Floating Action Button — hidden while panel is open (panel has its own close button) */}
      <Box sx={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1400, display: open && !tourActive ? 'none' : 'block' }}>
        <IconButton
          onClick={toggle}
          aria-label={t('help.title', 'Hilfe')}
          sx={{
            width: 56,
            height: 56,
            backgroundColor: 'primary.main',
            color: 'white',
            boxShadow: 3,
            '&:hover': { backgroundColor: 'primary.dark' },
            ...(fabPulse && {
              animation: 'help-heartbeat 4s ease-in-out infinite',
              '@keyframes help-heartbeat': {
                '0%, 55%, 100%': { transform: 'scale(1)' },
                '60%': { transform: 'scale(1.2)' },
                '65%': { transform: 'scale(1)' },
                '75%': { transform: 'scale(1.15)' },
                '80%': { transform: 'scale(1)' },
              },
            }),
          }}
        >
          <Badge
            variant="dot"
            color="error"
            invisible={!hasContextHint || open || tourActive}
          >
            <HelpOutline />
          </Badge>
        </IconButton>
      </Box>

      {/* Slide-in Panel */}
      <Slide direction="left" in={open && !tourActive}>
        <Paper
          elevation={8}
          sx={{
            position: 'fixed',
            bottom: 88,
            right: 24,
            width: { xs: 'calc(100vw - 48px)', sm: panelSize.width },
            height: { xs: '60vh', sm: panelSize.height },
            zIndex: 1300,
            display: 'flex',
            flexDirection: 'column',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          {/* Resize handle (top-left corner) */}
          <Box
            onMouseDown={handleResizeStart}
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: 16,
              height: 16,
              cursor: 'nw-resize',
              zIndex: 10,
              '&::after': {
                content: '""',
                position: 'absolute',
                top: 3,
                left: 3,
                width: 8,
                height: 8,
                borderTop: '2px solid rgba(255,255,255,0.5)',
                borderLeft: '2px solid rgba(255,255,255,0.5)',
              },
            }}
          />
          {/* Header */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              p: 2,
              borderBottom: 1,
              borderColor: 'divider',
              backgroundColor: 'primary.main',
              color: 'white',
            }}
          >
            <Typography variant="h6">{t('help.title', 'Hilfe')}</Typography>
            <IconButton onClick={toggle} sx={{ color: 'white' }} aria-label="close">
              <Close />
            </IconButton>
          </Box>

          {/* Content */}
          <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            {/* Tour completion message */}
            {tourJustCompleted && (
              <Box sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  {t('help.onboarding.completedTitle', '🎉 Tour abgeschlossen!')}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(
                    'help.onboarding.completedText',
                    'Du kannst das Hilfe-Widget jederzeit über den Button unten rechts öffnen.',
                  )}
                </Typography>
              </Box>
            )}

            {/* Catch-up banner (wenn completed tour, aber neue Seiten zugänglich) */}
            {onboardingStatus?.completed && catchUpSteps.length > 0 && !catchUpMode && !tourJustCompleted && (
              <Box sx={{ p: 2, m: 2, bgcolor: 'info.light', borderRadius: 1 }}>
                <Typography variant="body2" gutterBottom>
                  {t(
                    'help.catchUp.message',
                    'Neue Seiten wurden freigeschaltet — möchtest du die Tour dafür nachholen?',
                  )}
                </Typography>
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<PlayArrow />}
                  onClick={handleStartCatchUp}
                  sx={{ mt: 1 }}
                >
                  {t('help.catchUp.button', 'Jetzt erkunden')}
                </Button>
              </Box>
            )}

            {/* Resume onboarding tour (when tour is in progress but not active) */}
            {showOnboarding && !tourActive && !tourJustCompleted && onboardingStatus && onboardingStatus.current_step > 0 && onboardingSteps.length > 0 && (
              <Box sx={{ p: 3 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {t('help.onboarding.resumeText', 'Du hast die Einführungstour noch nicht abgeschlossen.')}
                </Typography>
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<PlayArrow />}
                  onClick={() => { setOpen(false); setTourActive(true); }}
                  sx={{ mt: 1 }}
                >
                  {t('help.onboarding.resumeButton', 'Tour fortsetzen')}
                </Button>
              </Box>
            )}

            {/* Context hint (when no active onboarding) */}
            {!showOnboarding && hasContextHint && contextHint && !contextHintDismissed && (
              <HelpContextHint
                hint={contextHint}
                onDismiss={() => { setContextHintDismissed(true); if (!chatAvailable) setOpen(false); }}
                onDismissPermanently={() => { setContextHintDismissed(true); if (!chatAvailable) setOpen(false); }}
              />
            )}

            {/* Chat */}
            {chatAvailable && (
              <Box sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
                <HelpChat route={route} />
              </Box>
            )}

            {/* Fallback */}
            {!chatAvailable && !showOnboarding && (!hasContextHint || contextHintDismissed) && !tourJustCompleted && (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography color="text.secondary">
                  {t(
                    'help.chatUnavailable',
                    'Der Hilfe-Chat ist derzeit nicht verfügbar.',
                  )}
                </Typography>
              </Box>
            )}
          </Box>
        </Paper>
      </Slide>

      {/* HelpOnboarding — always mounted outside panel, activates when tourActive */}
      {onboardingStatus && (showOnboarding ? onboardingSteps.length > 0 : catchUpMode && catchUpSteps.length > 0) && (
        <HelpOnboarding
          status={catchUpMode ? { ...onboardingStatus, current_step: 0 } : onboardingStatus}
          steps={catchUpMode ? catchUpSteps : onboardingSteps}
          active={tourActive}
          onCompleteStep={completeStep}
          onSkipStep={skipStep}
          onTourComplete={catchUpMode ? handleCatchUpComplete : handleTourComplete}
          onTourCancel={handleTourCancel}
        />
      )}
    </>
  );
};

export default HelpWidget;
