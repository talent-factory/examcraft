/**
 * Sidebar nav reveal (TF-604)
 *
 * Since TF-372 the sidebar renders the items of a group only while that group
 * is expanded — links of a collapsed group are not in the DOM at all. Anything
 * that wants to point at a nav link (currently the onboarding tour, which
 * addresses links by `data-testid`) therefore has to ask the sidebar to open
 * the owning group first.
 *
 * A window event keeps that a one-way request: the caller names the *route* it
 * wants revealed, the sidebar — the only place that knows the group layout —
 * resolves it to a group and expands it. No context plumbing through the layout
 * tree, and callers stay decoupled from the navigation config.
 */

export const SIDEBAR_REVEAL_NAV_EVENT = 'examcraft:sidebar:reveal-nav';

export interface SidebarRevealNavDetail {
  /** Route path of the nav link to reveal, e.g. `/questions/generate`. */
  path: string;
}

/**
 * Ask the sidebar to expand the group containing `path`.
 *
 * Fire-and-forget: there is no acknowledgement. Two distinct cases both end
 * up looking the same to the caller, though they aren't the same thing: no
 * listener reacts at all when no Sidebar is mounted, versus a mounted
 * Sidebar's listener running but choosing not to act because `path` doesn't
 * resolve to a group (filtered out by RBAC, the user's nav context not
 * loaded yet, or not in the nav config at all — see Sidebar.tsx's reveal
 * handler, which logs a debug line for the latter case so it is at least
 * distinguishable from "nothing is listening" when investigating). Callers
 * must therefore poll the DOM for the element they expect.
 */
export const requestSidebarNavReveal = (path: string): void => {
  window.dispatchEvent(
    new CustomEvent<SidebarRevealNavDetail>(SIDEBAR_REVEAL_NAV_EVENT, {
      detail: { path },
    }),
  );
};
