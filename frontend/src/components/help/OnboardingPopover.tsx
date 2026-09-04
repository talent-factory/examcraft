/**
 * OnboardingPopover — the tour's popover surface, anchored to the highlighted
 * element via MUI Popper instead of driver.js's own coordinate arithmetic.
 *
 * driver.js keeps doing what it does well (overlay + cutout); it is called
 * without a `popover` so it renders none of its own. Everything the user reads
 * or clicks during a step lives here, for all three step kinds (spotlight, nav,
 * tab), so the tour looks the same everywhere.
 *
 * Why not let driver.js place it: its defaults are side "left" / align "start"
 * and the tour never overrode them, so every step was placed to the LEFT of its
 * element, top-aligned. For the content steps — all of which span the full
 * content column — "left" is the 288px sidebar gutter, which is wide enough for
 * the 250px min-width popover, so driver.js happily parked the text on the
 * sidebar, ~740px away from the thing it describes.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Box, Button, Paper, Typography } from '@mui/material';
import Popper from '@mui/material/Popper';

/**
 * Keep the anchor rect this far inside the viewport. Also the gap driver.js
 * leaves around the cutout (`stagePadding`), so the popover clears the
 * highlight ring by the same amount everywhere.
 */
const VIEWPORT_PADDING = 10;

/** Distance between the anchor edge and the popover, arrow included. */
const POPPER_OFFSET = 14;

/** Keep the popover this far from the viewport edge. */
const OVERFLOW_PADDING = 12;

/**
 * How far the anchor may sit outside the padded viewport before the arrow stops
 * being honest.
 *
 * Matched to OVERFLOW_PADDING: a trim smaller than the popover's own overflow
 * padding cannot move the popover far enough for the arrow to visibly lie.
 * Without a tolerance, a sidebar link at x=8 — fully visible, measured — was
 * "clamped" by the 2px difference to VIEWPORT_PADDING and lost its arrow.
 */
const CLAMP_TOLERANCE = OVERFLOW_PADDING;

export interface OnboardingPopoverProps {
  anchorEl: HTMLElement | null;
  title: string;
  description: string;
  /** Label for the advance button, or null for steps the user advances by
   *  clicking the highlighted element itself (nav and tab steps). */
  nextLabel: string | null;
  closeLabel: string;
  onNext: () => void;
  onClose: () => void;
}

type Clamp = { rect: DOMRect; clamped: boolean };

/**
 * The visible part of `el`, clamped to the viewport.
 *
 * Anchoring to the raw rect breaks on every content step: those elements are
 * 500–13000px tall, so "below the element" is far off-screen and popper.js has
 * no placement that fits — measured, `dashboard-content` (h=2322) put the
 * popover at y=2343 in a 900px viewport. Clamping to the visible slice gives
 * popper a box it can actually work with and puts the popover over the
 * highlighted region, which is the honest answer when the region *is* the
 * screen.
 *
 * `clamped` reports whether the arrow would be lying, in the two ways it can:
 *
 *  1. The element does not fit on screen. There is then no free side for the
 *     popover, `preventOverflow` pushes it back over the element, and it ends
 *     up nowhere near the edge the arrow claims to mark — measured on
 *     `admin-tab-content-users` (exactly viewport-height), where the popover
 *     landed 150px inside the element.
 *  2. The element fits but is scrolled materially out of view, so the clamped
 *     edge is a viewport edge rather than an element edge.
 *
 * A trim below CLAMP_TOLERANCE is neither; see that constant.
 */
const clampToViewport = (el: HTMLElement): Clamp => {
  const r = el.getBoundingClientRect();
  const top = Math.max(r.top, VIEWPORT_PADDING);
  const left = Math.max(r.left, VIEWPORT_PADDING);
  const bottom = Math.min(r.bottom, window.innerHeight - VIEWPORT_PADDING);
  const right = Math.min(r.right, window.innerWidth - VIEWPORT_PADDING);

  const width = Math.max(0, right - left);
  const height = Math.max(0, bottom - top);

  const tooBigToFit =
    r.height > window.innerHeight - 2 * VIEWPORT_PADDING ||
    r.width > window.innerWidth - 2 * VIEWPORT_PADDING;
  const scrolledOutOfView =
    r.top < top - CLAMP_TOLERANCE ||
    r.left < left - CLAMP_TOLERANCE ||
    r.bottom > bottom + CLAMP_TOLERANCE ||
    r.right > right + CLAMP_TOLERANCE;

  return {
    clamped: tooBigToFit || scrolledOutOfView,
    rect: {
      width,
      height,
      top,
      left,
      right,
      bottom,
      x: left,
      y: top,
      toJSON: () => undefined,
    } as DOMRect,
  };
};

/**
 * Visible keyboard focus for the popover buttons.
 *
 * MUI sets `.Mui-focusVisible` on both, but only paints something for the
 * contained variant — and that is a shadow, not a ring. Measured on the running
 * tour, both buttons reported `outline: none 0px` while the highlighted nav
 * link next to them showed the browser default `outline: auto 1px`, so the
 * focus simply vanished whenever it entered the popover. The offset puts the
 * ring on the paper, outside the filled button, so one colour works for both.
 */
const focusRing = {
  '&.Mui-focusVisible': {
    outline: '2px solid',
    outlineColor: 'primary.main',
    outlineOffset: '2px',
  },
} as const;

/** Elements the tour's own Tab cycle should visit, in order. */
const focusablesIn = (root: HTMLElement | null): HTMLElement[] =>
  root
    ? (Array.from(
        root.querySelectorAll('button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'),
      ) as HTMLElement[])
    : [];

const OnboardingPopover: React.FC<OnboardingPopoverProps> = ({
  anchorEl,
  title,
  description,
  nextLabel,
  closeLabel,
  onNext,
  onClose,
}) => {
  const [arrowEl, setArrowEl] = useState<HTMLElement | null>(null);
  const [clamped, setClamped] = useState(false);
  const paperRef = useRef<HTMLDivElement | null>(null);
  const updateRef = useRef<(() => void) | null>(null);

  // popper.js calls this on every update, so the popover follows the element
  // without us recomputing anything by hand.
  const virtualAnchor = useMemo(
    () =>
      anchorEl
        ? { getBoundingClientRect: () => clampToViewport(anchorEl).rect }
        : null,
    [anchorEl],
  );

  const syncClamped = useCallback(() => {
    if (!anchorEl) return;
    setClamped(clampToViewport(anchorEl).clamped);
  }, [anchorEl]);

  /**
   * Popper follows window scroll on its own (measured: anchor and popover both
   * moved exactly 300px with no manual update). It does NOT follow a scroll
   * inside the sidebar's own `overflow-y-auto` nav, because it derives its
   * scroll parents from the popover — which sits on `document.body` — not from
   * the anchor. Listening in the capture phase catches those too, cheaply.
   */
  useEffect(() => {
    if (!anchorEl) return undefined;
    syncClamped();
    const onViewportChange = () => {
      syncClamped();
      updateRef.current?.();
    };
    window.addEventListener('scroll', onViewportChange, true);
    window.addEventListener('resize', onViewportChange);
    return () => {
      window.removeEventListener('scroll', onViewportChange, true);
      window.removeEventListener('resize', onViewportChange);
    };
  }, [anchorEl, syncClamped]);

  /**
   * Restore keyboard access to the popover.
   *
   * driver.js installs its own Tab handler that cycles only between the
   * highlighted element and *its* popover wrapper. Since we no longer give it a
   * popover, that trap pins focus on the highlighted element and our buttons
   * become unreachable — measured, five Tabs in a row all landed on the same
   * nav link. `allowKeyboardControl: false` does not help: driver.js checks
   * that option in its keyup handler but not in the Tab handler.
   *
   * A capture-phase listener on `window` runs before driver.js's bubble-phase
   * one, so stopping propagation here replaces the trap rather than fighting
   * it. The cycle deliberately includes the highlighted element: on nav and tab
   * steps clicking it is how the user advances.
   */
  useEffect(() => {
    if (!anchorEl) return undefined;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      const stops = [
        ...(anchorEl.matches('a[href], button, [tabindex]:not([tabindex="-1"])')
          ? [anchorEl]
          : []),
        ...focusablesIn(paperRef.current),
      ];
      if (stops.length === 0) return;

      e.preventDefault();
      e.stopImmediatePropagation();

      const current = stops.indexOf(document.activeElement as HTMLElement);
      const next = e.shiftKey
        ? stops[current <= 0 ? stops.length - 1 : current - 1]
        : stops[current === stops.length - 1 ? 0 : current + 1];
      next?.focus();
    };
    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, [anchorEl]);

  // A step whose anchor got detached (page re-rendered under us) would leave
  // popper positioning against a stale rect — render nothing instead.
  if (!anchorEl || !virtualAnchor || !document.body.contains(anchorEl)) return null;

  const showArrow = !clamped;

  return (
    <Popper
      open
      anchorEl={virtualAnchor}
      placement="bottom"
      // Above driver.js's overlay, which sits at 10000 (measured against
      // driver.js ^1.4.0, see package.json — a driver.js upgrade that
      // changes its default z-index would need this bumped too).
      sx={{ zIndex: 10001 }}
      popperRef={(instance) => {
        updateRef.current = instance ? () => { instance.update(); } : null;
      }}
      modifiers={[
        { name: 'offset', options: { offset: [0, POPPER_OFFSET] } },
        { name: 'preventOverflow', options: { padding: OVERFLOW_PADDING, altAxis: true } },
        { name: 'flip', options: { fallbackPlacements: ['top', 'right', 'left'] } },
        { name: 'arrow', enabled: showArrow && !!arrowEl, options: { element: arrowEl, padding: 8 } },
      ]}
    >
      {showArrow && (
        <Box
          ref={setArrowEl}
          data-testid="onboarding-popover-arrow"
          sx={{
            position: 'absolute',
            width: 10,
            height: 10,
            '&::before': {
              content: '""',
              display: 'block',
              width: 10,
              height: 10,
              bgcolor: 'background.paper',
              transform: 'rotate(45deg)',
            },
            '[data-popper-placement^="bottom"] &': { top: -5 },
            '[data-popper-placement^="top"] &': { bottom: -5 },
            '[data-popper-placement^="left"] &': { right: -5 },
            '[data-popper-placement^="right"] &': { left: -5 },
          }}
        />
      )}
      <Paper
        ref={paperRef}
        elevation={8}
        role="dialog"
        aria-labelledby="onboarding-popover-title"
        aria-describedby="onboarding-popover-description"
        data-testid="onboarding-popover"
        sx={{ width: 300, p: 2, borderRadius: 2 }}
      >
        <Typography
          id="onboarding-popover-title"
          variant="subtitle1"
          sx={{ fontWeight: 700, pr: 3 }}
        >
          {title}
        </Typography>
        <Typography
          id="onboarding-popover-description"
          variant="body2"
          color="text.secondary"
          sx={{ mt: 0.5 }}
        >
          {description}
        </Typography>
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
          <Button
            size="small"
            onClick={onClose}
            data-testid="onboarding-popover-close"
            sx={focusRing}
          >
            {closeLabel}
          </Button>
          {nextLabel && (
            <Button
              size="small"
              variant="contained"
              onClick={onNext}
              data-testid="onboarding-popover-next"
              sx={focusRing}
            >
              {nextLabel}
            </Button>
          )}
        </Box>
      </Paper>
    </Popper>
  );
};

export default OnboardingPopover;
