/*
 * The popover is positioned against a live DOM node and its keyboard cycle is
 * asserted through `document.activeElement`, neither of which Testing Library
 * has a query for — hence the file-wide exemption from `no-node-access`.
 */
/* eslint-disable testing-library/no-node-access */
import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import OnboardingPopover from '../OnboardingPopover';

const VIEWPORT = { width: 1512, height: 900 };

/** Put an anchor in the document with a rect of our choosing (jsdom has no layout). */
const makeAnchor = (
  rect: Partial<DOMRect>,
  tag: keyof HTMLElementTagNameMap = 'div',
): HTMLElement => {
  const el = document.createElement(tag);
  el.setAttribute('data-testid', 'anchor');
  const full = {
    x: rect.left ?? 0,
    y: rect.top ?? 0,
    top: rect.top ?? 0,
    left: rect.left ?? 0,
    width: rect.width ?? 0,
    height: rect.height ?? 0,
    right: (rect.left ?? 0) + (rect.width ?? 0),
    bottom: (rect.top ?? 0) + (rect.height ?? 0),
    toJSON: () => undefined,
  } as DOMRect;
  el.getBoundingClientRect = () => full;
  document.body.appendChild(el);
  return el;
};

const renderPopover = (
  anchorEl: HTMLElement | null,
  overrides: Partial<React.ComponentProps<typeof OnboardingPopover>> = {},
) =>
  render(
    <OnboardingPopover
      anchorEl={anchorEl}
      title="Dashboard"
      description="Das ist dein Dashboard."
      nextLabel="Weiter →"
      closeLabel="Tour beenden"
      onNext={jest.fn()}
      onClose={jest.fn()}
      {...overrides}
    />,
  );

beforeEach(() => {
  window.innerWidth = VIEWPORT.width;
  window.innerHeight = VIEWPORT.height;
});

afterEach(() => {
  document.querySelectorAll('[data-testid="anchor"]').forEach((e) => e.remove());
});

describe('OnboardingPopover — rendering', () => {
  it('renders title, description and both buttons', () => {
    renderPopover(makeAnchor({ top: 180, left: 702, width: 71, height: 66 }));

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Das ist dein Dashboard.')).toBeInTheDocument();
    expect(screen.getByTestId('onboarding-popover-next')).toBeInTheDocument();
    expect(screen.getByTestId('onboarding-popover-close')).toBeInTheDocument();
  });

  it('omits the next button on nav/tab steps, where the user clicks the element', () => {
    renderPopover(makeAnchor({ top: 116, left: 8, width: 239, height: 52 }), {
      nextLabel: null,
    });

    expect(screen.queryByTestId('onboarding-popover-next')).not.toBeInTheDocument();
    expect(screen.getByTestId('onboarding-popover-close')).toBeInTheDocument();
  });

  it('renders nothing without an anchor', () => {
    renderPopover(null);
    expect(screen.queryByTestId('onboarding-popover')).not.toBeInTheDocument();
  });

  /**
   * A page can re-render under a running step (the sidebar re-rendering after a
   * group reveal, for example). Positioning against a rect from a node that is
   * no longer in the document would freeze the popover wherever it last was.
   */
  it('renders nothing once the anchor has been detached from the document', () => {
    const anchor = makeAnchor({ top: 180, left: 702, width: 71, height: 66 });
    anchor.remove();

    renderPopover(anchor);
    expect(screen.queryByTestId('onboarding-popover')).not.toBeInTheDocument();
  });
});

describe('OnboardingPopover — viewport clamping', () => {
  /**
   * The arrow marks a real element edge. Content steps span the whole content
   * column and run far past the fold (measured: `dashboard-content` is 2322px
   * tall in a 900px viewport), so the anchor gets clamped to the visible slice
   * and its edges are viewport edges, not element edges — an arrow there would
   * point at nothing.
   */
  it('drops the arrow when the element is taller than the viewport', () => {
    renderPopover(makeAnchor({ top: 88, left: 288, width: 1192, height: 2322 }));

    expect(screen.getByTestId('onboarding-popover')).toBeInTheDocument();
    expect(screen.queryByTestId('onboarding-popover-arrow')).not.toBeInTheDocument();
  });

  it('keeps the arrow for an element that fits on screen', () => {
    renderPopover(makeAnchor({ top: 180, left: 702, width: 71, height: 66 }));

    expect(screen.getByTestId('onboarding-popover-arrow')).toBeInTheDocument();
  });

  /**
   * Sidebar links start at x=8, inside the padding the anchor rect is clamped
   * to. Treating that 2px trim as "clamped" cost every nav step its arrow —
   * measured on the running app before the tolerance was added.
   */
  it('keeps the arrow for a fully visible element that only grazes the padding', () => {
    renderPopover(makeAnchor({ top: 372, left: 8, width: 239, height: 52 }));

    expect(screen.getByTestId('onboarding-popover-arrow')).toBeInTheDocument();
  });

  it('drops the arrow when the element is scrolled well past the top edge', () => {
    renderPopover(makeAnchor({ top: -240, left: 288, width: 1192, height: 400 }));

    expect(screen.queryByTestId('onboarding-popover-arrow')).not.toBeInTheDocument();
  });

  /**
   * An element exactly as tall as the viewport leaves no free side, so
   * preventOverflow pushes the popover back over it — measured on
   * `admin-tab-content-users`, where it landed 150px inside the element while
   * the arrow still claimed to mark its bottom edge.
   */
  it('drops the arrow when the element exactly fills the viewport', () => {
    renderPopover(makeAnchor({ top: 0, left: 313, width: 1166, height: 900 }));

    expect(screen.queryByTestId('onboarding-popover-arrow')).not.toBeInTheDocument();
  });

  it('re-evaluates clamping when the viewport shrinks under a fitting element', () => {
    renderPopover(makeAnchor({ top: 204, left: 288, width: 1192, height: 501 }));
    expect(screen.getByTestId('onboarding-popover-arrow')).toBeInTheDocument();

    act(() => {
      window.innerHeight = 400;
      window.dispatchEvent(new Event('resize'));
    });

    expect(screen.queryByTestId('onboarding-popover-arrow')).not.toBeInTheDocument();
  });
});

describe('OnboardingPopover — keyboard access', () => {
  /**
   * driver.js installs a Tab handler that cycles only between the highlighted
   * element and its OWN popover. Since it no longer renders one, that trap
   * would pin focus on the highlighted element and leave these buttons
   * unreachable — measured, five Tabs in a row all landed on the same nav link.
   * The component installs a capture-phase handler to replace the trap.
   */
  it('cycles Tab through the highlighted element and the popover buttons', () => {
    const anchor = makeAnchor({ top: 116, left: 8, width: 239, height: 52 }, 'a');
    anchor.setAttribute('href', '/documents');
    renderPopover(anchor, { nextLabel: null });

    const close = screen.getByTestId('onboarding-popover-close');

    fireEvent.keyDown(window, { key: 'Tab' });
    expect(document.activeElement).toBe(anchor);

    fireEvent.keyDown(window, { key: 'Tab' });
    expect(document.activeElement).toBe(close);

    // Wraps back around rather than escaping into the dimmed page.
    fireEvent.keyDown(window, { key: 'Tab' });
    expect(document.activeElement).toBe(anchor);
  });

  it('cycles backwards on Shift+Tab', () => {
    const anchor = makeAnchor({ top: 116, left: 8, width: 239, height: 52 }, 'a');
    anchor.setAttribute('href', '/documents');
    renderPopover(anchor, { nextLabel: null });

    const close = screen.getByTestId('onboarding-popover-close');

    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(close);

    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(anchor);
  });

  it('leaves the highlighted element out of the cycle when it is not focusable', () => {
    renderPopover(makeAnchor({ top: 88, left: 288, width: 1192, height: 400 }));

    const close = screen.getByTestId('onboarding-popover-close');
    const next = screen.getByTestId('onboarding-popover-next');

    fireEvent.keyDown(window, { key: 'Tab' });
    expect(document.activeElement).toBe(close);

    fireEvent.keyDown(window, { key: 'Tab' });
    expect(document.activeElement).toBe(next);
  });

  it('ignores keys other than Tab', () => {
    renderPopover(makeAnchor({ top: 180, left: 702, width: 71, height: 66 }));

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(document.activeElement).toBe(document.body);
  });
});

describe('OnboardingPopover — actions', () => {
  it('reports next and close separately', () => {
    const onNext = jest.fn();
    const onClose = jest.fn();
    renderPopover(makeAnchor({ top: 180, left: 702, width: 71, height: 66 }), {
      onNext,
      onClose,
    });

    fireEvent.click(screen.getByTestId('onboarding-popover-next'));
    expect(onNext).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('onboarding-popover-close'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
