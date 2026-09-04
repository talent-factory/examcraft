import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Paper,
  IconButton,
  Badge,
  Slide,
  Box,
  Typography,
  Button,
  Divider,
  Tabs,
  Tab,
  Chip,
} from '@mui/material';
import { HelpOutline, Close, PlayArrow, CheckCircle, Replay } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useHelpContext } from './useHelpContext';
import { useRoleBasedNavigation } from '../../hooks/useRoleBasedNavigation';
import OnboardingModal from './OnboardingModal';
import HelpOnboarding, { OnboardingStep } from './HelpOnboarding';
import HelpContextHint from './HelpContextHint';
import HelpChat from './HelpChat';

/** An optional deep-dive track from help-onboarding-steps.json (TF-625). */
interface OnboardingTrack {
  id: string;
  /** i18n key prefix; `.title` and `.description` live in translation.json. */
  i18n_key: string;
  steps: OnboardingStep[];
}

/** Distance from the panel's bottom edge to the viewport bottom — clears the FAB. */
const PANEL_BOTTOM_OFFSET = 88;
/** Breathing room kept above the panel. */
const PANEL_TOP_GAP = 32;
const PANEL_VERTICAL_MARGIN = PANEL_BOTTOM_OFFSET + PANEL_TOP_GAP;

/**
 * Clamp a resize dimension between a preferred minimum and a hard maximum.
 *
 * `Math.max(min, Math.min(max, value))` — the naive order — returns `min`
 * whenever `max < min`, i.e. whenever the viewport is smaller than the
 * preferred minimum: a window shorter than MIN_HEIGHT + PANEL_VERTICAL_MARGIN
 * would make this clamp itself produce a panel taller than the screen.
 * `Math.min(min, max)` as the floor lets the ceiling win that tension instead.
 * Exported standalone (rather than inlined in the mousemove handler) so the
 * clamp math is unit-testable without simulating a drag through jsdom, whose
 * layout engine wouldn't reflect the CSS this value ends up driving anyway.
 */
export function clampPanelDimension(min: number, max: number, value: number): number {
  return Math.max(Math.min(min, max), Math.min(max, value));
}

type HelpTab = 'chat' | 'tours';

const HELP_TAB_STORAGE_KEY = 'examcraft.help.tab';

/**
 * Deep dives the user has already been shown, so a newly unlocked one can be
 * flagged. Kept per browser rather than on the account: it drives a "look
 * here" marker, and getting it wrong costs a needless glance, not data.
 */
const SEEN_TRACKS_STORAGE_KEY = 'examcraft.help.seenTracks';

const readSeenTracks = (): string[] => {
  try {
    const raw = window.localStorage.getItem(SEEN_TRACKS_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return Array.isArray(parsed) && parsed.every((x) => typeof x === 'string') ? parsed : [];
  } catch {
    return [];
  }
};

const readStoredTab = (): HelpTab | null => {
  try {
    const raw = window.localStorage.getItem(HELP_TAB_STORAGE_KEY);
    return raw === 'chat' || raw === 'tours' ? raw : null;
  } catch {
    /* localStorage unavailable (private mode / quota) — fall back to the
       derived default, same as a user who has never picked a tab. */
    return null;
  }
};

const HelpWidget: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [tourActive, setTourActive] = useState(false);
  const [tourJustCompleted, setTourJustCompleted] = useState(false);
  const [modalDismissed, setModalDismissed] = useState(() =>
    localStorage.getItem('ec_onboarding_modal_dismissed') === 'true'
  );
  const [onboardingSteps, setOnboardingSteps] = useState<OnboardingStep[]>([]);
  const [tracks, setTracks] = useState<OnboardingTrack[]>([]);
  const [activeTrackId, setActiveTrackId] = useState<string | null>(null);
  const [catchUpMode, setCatchUpMode] = useState(false);
  const [catchUpSteps, setCatchUpSteps] = useState<OnboardingStep[]>([]);
  // Replay of the finished core tour. Deep dives could always be repeated
  // ("Nochmal"); the core tour could not, because its banner is gated on
  // `showOnboarding`, which goes false the moment it completes.
  const [replayMode, setReplayMode] = useState(false);
  const [panelSize, setPanelSize] = useState({ width: 360, height: 520 });
  const resizeRef = useRef<{ startX: number; startY: number; startW: number; startH: number } | null>(null);
  const { t } = useTranslation();
  const { navigationItems } = useRoleBasedNavigation();

  const MIN_WIDTH = 360;
  const MIN_HEIGHT = 520;
  const MAX_WIDTH = Math.min(800, typeof window !== 'undefined' ? window.innerWidth - 80 : 800);
  const MAX_HEIGHT =
    typeof window !== 'undefined' ? window.innerHeight - PANEL_VERTICAL_MARGIN : 900;

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    resizeRef.current = { startX: e.clientX, startY: e.clientY, startW: panelSize.width, startH: panelSize.height };
    const onMove = (ev: MouseEvent) => {
      if (!resizeRef.current) return;
      const dw = resizeRef.current.startX - ev.clientX;
      const dh = resizeRef.current.startY - ev.clientY;
      setPanelSize({
        width: clampPanelDimension(MIN_WIDTH, MAX_WIDTH, resizeRef.current.startW + dw),
        height: clampPanelDimension(MIN_HEIGHT, MAX_HEIGHT, resizeRef.current.startH + dh),
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
    contextHint,
    onboardingStatus,
    chatAvailable,
    completeStep,
    skipStep,
    updateTrackStep,
    trackProgress,
    role,
    route,
    acknowledgeHint,
  } = useHelpContext();

  // Both buttons land here. "Nicht mehr anzeigen" has already told the server
  // by the time it calls back; either way the hint goes away for this tab.
  const dismissCurrentHint = useCallback(() => {
    if (contextHint?.hint_id != null) acknowledgeHint(contextHint.hint_id);
    if (!chatAvailable) setOpen(false);
  }, [contextHint, chatAvailable, acknowledgeHint]);

  // Load core steps and deep dives. No longer tied to `showOnboarding` as
  // before: the deep dives are most interesting precisely once the core tour
  // is already finished (TF-625).
  useEffect(() => {
    if (!role) return;
    fetch('/help-onboarding-steps.json')
      .then((res) => res.json())
      .then((data) => {
        const forRole = data[role] ?? {};
        setOnboardingSteps(forRole.core ?? []);
        setTracks(forRole.tracks ?? []);
      })
      .catch((err) => console.warn('Failed to load onboarding steps:', err));
  }, [role]);

  /**
   * Whether a route is reachable for this user.
   *
   * TF-625: accessibility comes from the RBAC-filtered nav config rather than
   * a `document.querySelector` on the nav link. That DOM query was the actual
   * TF-604 trap — a collapsed sidebar group renders no items at all, so an
   * accessible step looked inaccessible.
   *
   * Deliberately derived from `navigationItems` instead of the hook's
   * `hasAccess`: the latter is a fresh function on every render and would
   * trigger a render loop as a dependency below. `navigationItems` is
   * memoised inside the hook.
   */
  const isRouteAccessible = useCallback(
    (path: string) => {
      const walk = (items: { path: string; children?: any[] }[]): boolean =>
        items.some(
          (item) => item.path === path || (item.children ? walk(item.children) : false),
        );
      return walk(navigationItems);
    },
    [navigationItems],
  );

  // Catch-up: when the panel opens, check which skipped steps are now accessible
  useEffect(() => {
    if (!open || !onboardingStatus?.completed) return;
    const skipped = onboardingStatus.skipped_steps ?? [];
    if (skipped.length === 0 || onboardingSteps.length === 0) return;

    const accessible = skipped
      .map((n: number) => onboardingSteps.find((s) => s.step === n))
      .filter((step): step is OnboardingStep => !!step)
      .filter((step) => !step.route || isRouteAccessible(step.route));

    // Only write on an actual change. Without this comparison every run sets
    // a new array and triggers the next render — a loop as soon as any
    // dependency changes identity per render.
    setCatchUpSteps((prev) =>
      prev.length === accessible.length &&
      prev.every((step, i) => step.step === accessible[i].step)
        ? prev
        : accessible,
    );
  }, [open, onboardingStatus, onboardingSteps, isRouteAccessible]);

  // A deep dive is only offered when at least one of its steps is reachable
  // for this user — otherwise the entry would lead into a tour that runs
  // entirely down the skip path.
  const availableTracks = useMemo(
    () =>
      tracks.filter((track) =>
        track.steps.some((step) => !step.route || isRouteAccessible(step.route)),
      ),
    [tracks, isRouteAccessible],
  );

  const activeTrack = useMemo(
    () => availableTracks.find((tr) => tr.id === activeTrackId) ?? null,
    [availableTracks, activeTrackId],
  );

  /** The finished core tour can be run again (TF-625 follow-up). */
  const coreTourReplayable =
    !!onboardingStatus?.completed &&
    !tourActive &&
    !tourJustCompleted &&
    onboardingSteps.length > 0;

  // ── Panel panes ─────────────────────────────────────────────────
  //
  // Tours and chat are two separate panes behind a tab strip rather than a
  // single stacked column. Stacked, they competed for the same height and the
  // chat lost: with the deep dives, the core-tour row and a context hint above
  // it, the chat input ended up below the panel edge. Tabs give each pane the
  // full height and remove the competition instead of rebalancing it.

  const showCatchUpBanner =
    !!onboardingStatus?.completed &&
    catchUpSteps.length > 0 &&
    !catchUpMode &&
    !tourJustCompleted;

  const showTourBanner =
    showOnboarding &&
    !tourActive &&
    !tourJustCompleted &&
    onboardingSteps.length > 0 &&
    (modalDismissed || (onboardingStatus?.current_step ?? 0) > 0);

  const hasToursPane =
    tourJustCompleted ||
    showCatchUpBanner ||
    showTourBanner ||
    coreTourReplayable ||
    availableTracks.length > 0;

  /** Only worth a tab strip when there is actually a choice to make. */
  const showTabs = hasToursPane && chatAvailable;

  /**
   * Deep dives unlocked since the user last looked.
   *
   * Only once the core tour is done — before that everything is new and the
   * marker would be noise. Same idea as the catch-up banner, which covers the
   * core tour's skipped steps; this covers the deep dives, which the banner
   * never saw.
   */
  const [seenTracks, setSeenTracks] = useState<string[]>(readSeenTracks);

  const newTrackIds = useMemo(() => {
    if (!onboardingStatus?.completed) return [];
    return availableTracks.map((tr) => tr.id).filter((id) => !seenTracks.includes(id));
  }, [availableTracks, seenTracks, onboardingStatus]);

  /** Something in the panel wants attention while it is closed. */
  const hasPanelNews = hasContextHint || catchUpSteps.length > 0 || newTrackIds.length > 0;

  /**
   * The pane the user was last on, remembered across openings, or null while
   * they have never picked one.
   *
   * Derived-with-override rather than state seeded by an effect: the steps
   * arrive by fetch, so an effect could only choose after the tabs had already
   * rendered, which showed one pane for a frame before flipping to the other.
   * Computing the fallback during render has no such gap.
   */
  const [rememberedTab, setRememberedTab] = useState<HelpTab | null>(readStoredTab);

  const selectTab = useCallback((tab: HelpTab) => {
    setRememberedTab(tab);
    try {
      window.localStorage.setItem(HELP_TAB_STORAGE_KEY, tab);
    } catch {
      /* Non-fatal: the choice then only lasts for this session. */
    }
  }, []);

  /**
   * Where a user who has never picked lands. Anything pending in the tours
   * pane — an unfinished tour, newly unlocked pages, a just-finished tour — is
   * what they were most likely sent here for; otherwise the chat is the reason
   * to open a help panel at all.
   */
  const defaultTab: HelpTab =
    showTourBanner || showCatchUpBanner || tourJustCompleted ? 'tours' : 'chat';
  const activeTab = rememberedTab ?? defaultTab;

  /** Mirrors the render condition below — without tabs the pane is always the visible one. */
  const toursPaneVisible = hasToursPane && (!showTabs || activeTab === 'tours');

  /**
   * Clearing the "new" markers happens on CLOSE, not on render.
   *
   * Marking them the moment the pane appears made the chip vanish in the same
   * frame it was drawn — the user never got to see the thing the marker exists
   * to point at. Remembering that the pane was shown and committing when the
   * panel closes gives the marker the whole visit to do its job.
   *
   * Keyed on `toursPaneVisible`, not `activeTab`: with only one pane there are
   * no tabs and `activeTab` still says "chat".
   */
  const sawToursRef = useRef<string[]>([]);
  useEffect(() => {
    if (open && !tourActive && toursPaneVisible) {
      sawToursRef.current = [
        ...sawToursRef.current,
        ...newTrackIds.filter((id) => !sawToursRef.current.includes(id)),
      ];
      return;
    }
    if (open || sawToursRef.current.length === 0) return;

    const shown = sawToursRef.current;
    sawToursRef.current = [];
    setSeenTracks((prev) => {
      const merged = [...prev, ...shown.filter((id) => !prev.includes(id))];
      if (merged.length === prev.length) return prev;
      try {
        window.localStorage.setItem(SEEN_TRACKS_STORAGE_KEY, JSON.stringify(merged));
      } catch {
        /* Non-fatal: the marker then reappears next session. */
      }
      return merged;
    });
  }, [open, tourActive, toursPaneVisible, newTrackIds]);

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
    localStorage.setItem('ec_onboarding_modal_dismissed', 'true');
    setModalDismissed(true);
    await completeStep(0);
    setTourActive(true);
  }, [completeStep]);

  const handleModalLater = useCallback(() => {
    localStorage.setItem('ec_onboarding_modal_dismissed', 'true');
    setModalDismissed(true);
  }, []);

  /**
   * Every path that ends a tour reopens the panel, and all of them land on the
   * tours pane: that is where the completion message, the checkmarks and the
   * next thing to start live. Reported otherwise — finishing a deep dive put
   * the user in the chat, because only the CORE tour set `tourJustCompleted`,
   * which was the sole tours signal the default consulted.
   *
   * Selecting rather than overriding keeps the tab switchable right afterwards,
   * and doubles as "remember where I was" for the next opening.
   */
  const handleTourComplete = useCallback(() => {
    setTourActive(false);
    setTourJustCompleted(true);
    selectTab('tours');
    setOpen(true);
  }, [selectTab]);

  const handleTourCancel = useCallback(() => {
    setTourActive(false);
    // Cancelling out of a deep dive returns to normal mode too — otherwise
    // `activeTour` would stay on the track and the next core-tour start would
    // run into the deep dive.
    setActiveTrackId(null);
    setCatchUpMode(false);
    setReplayMode(false);
  }, []);

  /**
   * Run the finished core tour again.
   *
   * No progress reset: the tour is already `completed`, and re-walking it
   * writes the same step numbers back, so the flag stays where it was. That
   * keeps this purely a frontend affair — there is no reset endpoint, and
   * inventing one would put "I want to see it again" and "I never finished it"
   * into the same field.
   */
  const handleStartReplay = useCallback(() => {
    setOpen(false);
    setTourJustCompleted(false);
    setReplayMode(true);
    setTourActive(true);
  }, []);

  const handleReplayComplete = useCallback(() => {
    setReplayMode(false);
    setTourActive(false);
    setTourJustCompleted(true);
    selectTab('tours');
    setOpen(true);
  }, [selectTab]);

  const handleStartCatchUp = useCallback(() => {
    setOpen(false);
    setCatchUpMode(true);
    setTourActive(true);
  }, []);

  const handleCatchUpComplete = useCallback(() => {
    setCatchUpMode(false);
    setCatchUpSteps([]);
    setTourActive(false);
    selectTab('tours');
    setOpen(true);
  }, [selectTab]);

  // ── Deep dives (TF-625) ─────────────────────────────────────────

  const handleStartTrack = useCallback((trackId: string) => {
    setOpen(false);
    setTourJustCompleted(false);
    setActiveTrackId(trackId);
    setTourActive(true);
  }, []);

  const handleTrackFinish = useCallback(() => {
    setActiveTrackId(null);
    setTourActive(false);
    selectTab('tours');
    setOpen(true);
  }, [selectTab]);

  const activeTrackTotal = activeTrack?.steps.length ?? 0;

  const handleTrackCompleteStep = useCallback(
    async (step: number) => {
      if (!activeTrackId) return;
      await updateTrackStep(activeTrackId, step, activeTrackTotal, false);
    },
    [activeTrackId, activeTrackTotal, updateTrackStep],
  );

  const handleTrackSkipStep = useCallback(
    async (step: number) => {
      if (!activeTrackId) return;
      await updateTrackStep(activeTrackId, step, activeTrackTotal, true);
    },
    [activeTrackId, activeTrackTotal, updateTrackStep],
  );

  /**
   * Which tour is currently running, and with which callbacks.
   *
   * Deep dives write into their own progress space via `updateTrackStep` —
   * they must neither advance nor complete the core tour. A finished deep
   * dive restarts at 0; a partially done one resumes.
   */
  const activeTour = useMemo(() => {
    if (activeTrack) {
      const progress = trackProgress[activeTrack.id];
      const resume =
        progress && !progress.completed
          ? Math.min(progress.current_step, activeTrack.steps.length - 1)
          : 0;
      return {
        steps: activeTrack.steps,
        startStep: resume,
        onCompleteStep: handleTrackCompleteStep,
        onSkipStep: handleTrackSkipStep,
        onFinish: handleTrackFinish,
      };
    }
    if (catchUpMode && catchUpSteps.length > 0) {
      return {
        steps: catchUpSteps,
        startStep: 0,
        onCompleteStep: completeStep,
        onSkipStep: skipStep,
        onFinish: handleCatchUpComplete,
      };
    }
    // Before the showOnboarding branch: that flag is false once the tour is
    // complete, which is exactly when a replay is asked for.
    if (replayMode && onboardingSteps.length > 0) {
      // Not index 0: step 0 is the welcome step, which carries neither a route
      // nor a selector and therefore ends the tour the moment it is entered.
      // On a first run it never reaches the tour at all — OnboardingModal shows
      // it, and handleStartTour completes it before activating. A replay has to
      // start at the first step that actually has something to show.
      const firstContent = onboardingSteps.findIndex(
        (step) => !!step.route || !!step.highlight_selector,
      );
      return {
        steps: onboardingSteps,
        startStep: firstContent === -1 ? 0 : firstContent,
        onCompleteStep: completeStep,
        onSkipStep: skipStep,
        onFinish: handleReplayComplete,
      };
    }
    if (showOnboarding && onboardingSteps.length > 0) {
      return {
        steps: onboardingSteps,
        // Clamp: TF-625 shrank the admin core tour from 13 to 8 steps (the
        // admin tabs are deep dives now). Existing users carry a higher
        // `current_step` in the DB; without clamping the tour would start
        // past its last step, immediately run into nothing and never mark
        // itself complete — the "resume tour" banner would stay forever.
        startStep: Math.min(
          onboardingStatus?.current_step ?? 0,
          onboardingSteps.length - 1,
        ),
        onCompleteStep: completeStep,
        onSkipStep: skipStep,
        onFinish: handleTourComplete,
      };
    }
    return null;
  }, [
    activeTrack,
    trackProgress,
    handleTrackCompleteStep,
    handleTrackSkipStep,
    handleTrackFinish,
    catchUpMode,
    catchUpSteps,
    completeStep,
    skipStep,
    handleCatchUpComplete,
    replayMode,
    handleReplayComplete,
    showOnboarding,
    onboardingSteps,
    onboardingStatus,
    handleTourComplete,
  ]);

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
          i18nKey={welcomeStep.i18n_key}
          onStart={handleStartTour}
          onLater={handleModalLater}
        />
      )}

      {/* Floating Action Button — hidden while panel is open (panel has its own close button) */}
      <Box sx={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1400, display: open && !tourActive ? 'none' : 'block' }}>
        <IconButton
          onClick={toggle}
          aria-label={t('help.title', 'Hilfe')}
          // TF-657: language-independent hook for E2E. The aria-label comes
          // from i18n ("Hilfe"/"Help"/…) and isn't suitable as a test selector
          // — a negative assertion on it would always pass in an English
          // browser, regardless of whether the widget is gated.
          data-testid="help-fab"
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
          {/* Also flags a pending catch-up or a newly unlocked deep dive —
              both were only discoverable by opening the panel on spec. */}
          <Badge
            variant="dot"
            color="error"
            invisible={!hasPanelNews || open || tourActive}
            data-testid="help-fab-badge"
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
            bottom: PANEL_BOTTOM_OFFSET,
            right: 24,
            width: { xs: 'calc(100vw - 48px)', sm: panelSize.width },
            height: { xs: '60vh', sm: panelSize.height },
            // The real guard, and the reason no window-resize listener is
            // needed: `panelSize` is the user's preference, this caps what is
            // actually drawn. A shrunken window no longer pushes the panel off
            // screen, and growing it back restores the chosen height.
            maxHeight: `calc(100vh - ${PANEL_VERTICAL_MARGIN}px)`,
            zIndex: 1300,
            display: 'flex',
            flexDirection: 'column',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          {/* Resize handle (top-left corner) */}
          <Box
            data-testid="help-widget-resize-handle"
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
            {/* Context hint — above the tabs on purpose: it is about the page
                the user is on right now, so it stays visible whichever pane is
                open. Dismissible, and a single short tip by construction. */}
            {!showOnboarding && hasContextHint && contextHint && (
              <Box sx={{ flexShrink: 0 }}>
                <HelpContextHint
                  hint={contextHint}
                  onDismiss={dismissCurrentHint}
                  onDismissPermanently={dismissCurrentHint}
                />
              </Box>
            )}

            {showTabs && (
              <Tabs
                value={activeTab}
                onChange={(_, value) => selectTab(value)}
                variant="fullWidth"
                sx={{ borderBottom: 1, borderColor: 'divider', flexShrink: 0, minHeight: 44 }}
              >
                <Tab
                  value="chat"
                  label={t('help.tabs.chat', 'Chat')}
                  data-testid="help-tab-chat"
                  sx={{ minHeight: 44 }}
                />
                <Tab
                  value="tours"
                  label={t('help.tabs.tours', 'Touren')}
                  data-testid="help-tab-tours"
                  sx={{ minHeight: 44 }}
                />
              </Tabs>
            )}

            {/* Tours pane */}
            {toursPaneVisible && (
            <Box
              sx={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}
              data-testid="help-tours-pane"
            >
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

            {/* Catch-up banner (when tour completed, but new pages are now accessible) */}
            {showCatchUpBanner && (
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

            {/* Tour banner — start (step 0) or resume (step > 0).
                Gate: only show the banner once the modal is already dismissed or the tour
                has already started, so the modal and banner aren't visible at the same time. */}
            {showTourBanner && (
              <Box sx={{ p: 2, m: 2, bgcolor: 'info.light', borderRadius: 1 }}>
                <Typography variant="body2" gutterBottom>
                  {t('help.onboarding.resumeText', 'Du hast die Einführungstour noch nicht abgeschlossen.')}
                </Typography>
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<PlayArrow />}
                  onClick={() => {
                    if (onboardingStatus && onboardingStatus.current_step === 0) {
                      handleStartTour();
                    } else {
                      setOpen(false);
                      setTourActive(true);
                    }
                  }}
                  sx={{ mt: 1 }}
                >
                  {onboardingStatus && onboardingStatus.current_step === 0
                    ? t('help.onboarding.startTour', 'Tour starten')
                    : t('help.onboarding.resumeButton', 'Tour fortsetzen')}
                </Button>
              </Box>
            )}

            {/* Deep dives (TF-625) — optional mini tours, startable at any
                time. Deliberately visible during a running core tour too, so
                nobody has to click through the core tour to reach a specific
                area. */}
            {/* Everything startable, in reading order. No height cap any more:
                the pane it sits in scrolls, and the chat is behind its own tab
                rather than below, so there is nothing left to squeeze. */}
            {(coreTourReplayable || availableTracks.length > 0) && (
              <Box sx={{ px: 2, pb: 2 }} data-testid="help-tours">
                <Divider sx={{ mb: 2 }} />

                {/* Replay of the finished core tour. Mirrors the deep dives'
                    "Nochmal" row, which was the only thing repeatable before.
                    Hidden while the tour is still pending — there the
                    start/resume banner above is the right control. */}
                {coreTourReplayable && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography
                        variant="body2"
                        sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
                      >
                        <CheckCircle
                          fontSize="inherit"
                          color="success"
                          aria-label={t('help.tracks.done', 'Abgeschlossen')}
                        />
                        {t('help.onboarding.coreTourTitle', 'Einführungstour')}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {t(
                          'help.onboarding.coreTourReplayHint',
                          'Die Grundlagen noch einmal durchgehen.',
                        )}
                      </Typography>
                    </Box>
                    <Button
                      size="small"
                      variant="text"
                      startIcon={<Replay />}
                      onClick={handleStartReplay}
                      data-testid="help-core-tour-replay"
                    >
                      {t('help.tracks.restart', 'Nochmal')}
                    </Button>
                  </Box>
                )}

                {availableTracks.length > 0 && (
                  <Box data-testid="help-tracks">
                <Typography variant="subtitle2" gutterBottom>
                  {t('help.tracks.title', 'Vertiefungen')}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
                  {t(
                    'help.tracks.intro',
                    'Kurze Touren zu einzelnen Bereichen — keine davon ist Pflicht.',
                  )}
                </Typography>
                {availableTracks.map((track) => {
                  const progress = trackProgress[track.id];
                  const done = progress?.completed ?? false;
                  // Three states, not two: a track that was left part-way
                  // through resumes where it stopped, so offering "start"
                  // would misdescribe what the button does.
                  const inProgress = !done && (progress?.current_step ?? 0) > 0;
                  return (
                    <Box
                      key={track.id}
                      sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}
                    >
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography
                          variant="body2"
                          sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
                        >
                          {done && (
                            <CheckCircle
                              fontSize="inherit"
                              color="success"
                              aria-label={t('help.tracks.done', 'Abgeschlossen')}
                            />
                          )}
                          {t(`${track.i18n_key}.title`)}
                          {newTrackIds.includes(track.id) && (
                            <Chip
                              label={t('help.tracks.new', 'Neu')}
                              size="small"
                              color="info"
                              data-testid={`help-track-new-${track.id}`}
                              sx={{ height: 18, fontSize: '0.65rem' }}
                            />
                          )}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {t(`${track.i18n_key}.description`)}
                        </Typography>
                      </Box>
                      <Button
                        size="small"
                        variant={done ? 'text' : 'outlined'}
                        startIcon={done ? <Replay /> : <PlayArrow />}
                        onClick={() => handleStartTrack(track.id)}
                        data-testid={`help-track-start-${track.id}`}
                      >
                        {done
                          ? t('help.tracks.restart', 'Nochmal')
                          : inProgress
                            ? t('help.tracks.resume', 'Fortsetzen')
                            : t('help.tracks.start', 'Starten')}
                      </Button>
                    </Box>
                  );
                })}
                  </Box>
                )}
              </Box>
            )}
            </Box>
            )}

            {/* Chat pane — its own tab, so it gets the panel's full height
                instead of whatever the tours left over. */}
            {chatAvailable && (!showTabs || activeTab === 'chat') && (
              <Box
                sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}
                data-testid="help-chat-region"
              >
                <HelpChat route={route} />
              </Box>
            )}

            {/* Fallback */}
            {!chatAvailable && !showOnboarding && !hasContextHint && !tourJustCompleted && availableTracks.length === 0 && (
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

      {/* HelpOnboarding — always mounted outside panel, activates when tourActive.
          `key` forces a fresh instance per tour: HelpOnboarding reads
          `status.current_step` only on the active=false → true transition, so
          switching tours within one mount would otherwise stay stuck on the
          old start index. */}
      {onboardingStatus && activeTour && (
        <HelpOnboarding
          key={
            activeTrackId ??
            (catchUpMode ? 'catch-up' : replayMode ? 'replay' : 'core')
          }
          status={{ ...onboardingStatus, current_step: activeTour.startStep }}
          steps={activeTour.steps}
          active={tourActive}
          isRouteAccessible={isRouteAccessible}
          onCompleteStep={activeTour.onCompleteStep}
          onSkipStep={activeTour.onSkipStep}
          onTourComplete={activeTour.onFinish}
          onTourCancel={handleTourCancel}
        />
      )}
    </>
  );
};

export default HelpWidget;
