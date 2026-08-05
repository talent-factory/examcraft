/**
 * Sidebar Component Tests (grouped, collapsible sidebar — TF-372)
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '../Sidebar';
import { AuthProvider } from '../../../contexts/AuthContext';

// Mock apiClient (uses axios ESM which Jest cannot transform)
jest.mock('../../../api/apiClient', () => ({
  setTokenRefreshCallback: jest.fn(),
  setLogoutCallback: jest.fn(),
  setupFetchInterceptor: jest.fn(),
  apiClient: { interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } },
}));

// Mock useRoleBasedNavigation — overridable per test via mockReturnValue.
const mockUseRoleBasedNavigation = jest.fn();
jest.mock('../../../hooks/useRoleBasedNavigation', () => ({
  useRoleBasedNavigation: () => mockUseRoleBasedNavigation(),
}));

const overviewItems = [
  { label: 'Dashboard', path: '/dashboard', icon: '📊' },
  { label: 'Aktivitäten', path: '/aktivitaeten', icon: '🔔' },
];
const adminItems = [{ label: 'Admin', path: '/admin', icon: '⚙️' }];

const defaultGroups = [
  { id: 'overview', label: 'Überblick', items: overviewItems },
  { id: 'administration', label: 'Administration', items: adminItems },
];

const setNavigation = (groups: typeof defaultGroups) => {
  mockUseRoleBasedNavigation.mockReturnValue({
    navigationGroups: groups,
    navigationItems: groups.flatMap((g) => g.items),
  });
};

beforeEach(() => {
  window.localStorage.clear();
  setNavigation(defaultGroups);
});

const renderAt = (pathname: string, isOpen = true) =>
  render(
    <MemoryRouter initialEntries={[pathname]}>
      <AuthProvider>
        <Sidebar isOpen={isOpen} />
      </AuthProvider>
    </MemoryRouter>
  );

describe('Sidebar Component — groups', () => {
  it('renders the group headers', () => {
    renderAt('/dashboard');

    expect(screen.getByTestId('nav-group-overview')).toBeInTheDocument();
    expect(screen.getByTestId('nav-group-administration')).toBeInTheDocument();
  });

  it('opens only the active route group on load, others collapsed', () => {
    renderAt('/dashboard');

    // Active group (overview) is expanded → its items are visible.
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Aktivitäten')).toBeInTheDocument();
    // Non-active group (administration) is collapsed → item hidden.
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
  });

  it('toggles a group open and closed via its header', () => {
    renderAt('/dashboard');

    expect(screen.queryByText('Admin')).not.toBeInTheDocument();

    // Open administration.
    fireEvent.click(screen.getByTestId('nav-group-administration'));
    expect(screen.getByText('Admin')).toBeInTheDocument();

    // Collapse the active overview group.
    fireEvent.click(screen.getByTestId('nav-group-overview'));
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
  });

  it('keeps the active group expanded even when persisted state collapsed it', () => {
    // Persist a state where overview is NOT expanded; the active route's group
    // must still open so the current item stays visible.
    window.localStorage.setItem(
      'examcraft.sidebar.expandedGroups',
      JSON.stringify(['administration'])
    );

    renderAt('/dashboard');

    expect(screen.getByText('Dashboard')).toBeInTheDocument(); // active → forced open
    expect(screen.getByText('Admin')).toBeInTheDocument(); // restored from storage
  });

  it('persists the expanded set and restores it on remount', () => {
    const { unmount } = renderAt('/dashboard');

    // Open administration, then unmount.
    fireEvent.click(screen.getByTestId('nav-group-administration'));
    expect(screen.getByText('Admin')).toBeInTheDocument();
    unmount();

    // Storage should now hold both groups.
    const stored = JSON.parse(
      window.localStorage.getItem('examcraft.sidebar.expandedGroups') || '[]'
    );
    expect(stored).toEqual(expect.arrayContaining(['overview', 'administration']));

    // Fresh mount restores the administration group as open.
    renderAt('/dashboard');
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('falls back to the active group when stored state is corrupt JSON', () => {
    // Corrupt payload must not throw — the active route's group stays open.
    window.localStorage.setItem('examcraft.sidebar.expandedGroups', '{not json');

    expect(() => renderAt('/dashboard')).not.toThrow();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('ignores a wrong-shaped stored value and opens only the active group', () => {
    // Non-string-array payloads reset cleanly to the default instead of
    // partially restoring.
    window.localStorage.setItem(
      'examcraft.sidebar.expandedGroups',
      JSON.stringify([1, 2, 3])
    );

    renderAt('/dashboard');
    expect(screen.getByText('Dashboard')).toBeInTheDocument(); // active → open
    expect(screen.queryByText('Admin')).not.toBeInTheDocument(); // garbage ignored
  });

  it('force-opens the active group additively, without collapsing a restored one', () => {
    // Persisted: overview open. The active route lives in a different,
    // collapsed group → both end up open simultaneously (additive, no accordion).
    window.localStorage.setItem(
      'examcraft.sidebar.expandedGroups',
      JSON.stringify(['overview'])
    );

    renderAt('/admin');
    expect(screen.getByText('Dashboard')).toBeInTheDocument(); // restored, still open
    expect(screen.getByText('Admin')).toBeInTheDocument(); // active → force-opened
  });

  describe('icon-only mode (isOpen=false)', () => {
    it('hides group headers and item labels, keeping icons', () => {
      renderAt('/dashboard', false);

      expect(screen.queryByTestId('nav-group-overview')).not.toBeInTheDocument();
      expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
      expect(screen.queryByText('Admin')).not.toBeInTheDocument();
      // Icons remain (flat list of all items).
      expect(screen.getByText('📊')).toBeInTheDocument();
      expect(screen.getByText('⚙️')).toBeInTheDocument();
    });
  });
});

describe('Sidebar Component — item rendering', () => {
  it('renders icons for navigation items', () => {
    renderAt('/dashboard');

    expect(screen.getByRole('link', { name: /Dashboard/ })).toHaveTextContent('📊');
  });

  it('applies active state to current path', () => {
    renderAt('/dashboard');

    expect(screen.getByRole('link', { name: /Dashboard/ })).toHaveClass(
      'bg-primary-100',
      'text-primary-700',
    );
  });

  it('renders navigation links with correct href', () => {
    renderAt('/dashboard');

    expect(screen.getByRole('link', { name: /Dashboard/ })).toHaveAttribute(
      'href',
      '/dashboard',
    );
  });

  describe('flat sibling routes that share a prefix', () => {
    const ACTIVE_CLASS = 'bg-primary-100';

    beforeEach(() => {
      setNavigation([
        {
          id: 'evaluation',
          label: 'Auswertung',
          items: [
            { label: 'Auswertungen', path: '/auswertungen', icon: '📈' },
            { label: 'Klassen', path: '/auswertungen/klassen', icon: '🎓' },
            { label: 'Studierende', path: '/auswertungen/studierende', icon: '👥' },
          ],
        },
      ]);
    });

    it('highlights only the exact match, not the prefix-parent', () => {
      // Regression: at /auswertungen/klassen, the parent /auswertungen
      // would previously also light up because of a startsWith() check
      // without children-awareness.
      renderAt('/auswertungen/klassen');

      expect(screen.getByRole('link', { name: /Klassen/ })).toHaveClass(ACTIVE_CLASS);
      expect(screen.getByRole('link', { name: /Auswertungen/ })).not.toHaveClass(
        ACTIVE_CLASS,
      );
    });

    it('highlights the parent at its own exact path', () => {
      renderAt('/auswertungen');

      expect(screen.getByRole('link', { name: /Auswertungen/ })).toHaveClass(
        ACTIVE_CLASS,
      );
      expect(screen.getByRole('link', { name: /Klassen/ })).not.toHaveClass(
        ACTIVE_CLASS,
      );
    });
  });

  describe('items with children', () => {
    const ACTIVE_CLASS = 'bg-primary-100';

    beforeEach(() => {
      setNavigation([
        {
          id: 'overview',
          label: 'Überblick',
          items: [
            {
              label: 'Reports',
              path: '/reports',
              icon: '📊',
              children: [{ label: 'Daily', path: '/reports/daily', icon: '📅' }],
            },
          ],
        },
      ]);
    });

    it('keeps the parent active when a descendant route is open', () => {
      // Items with real children intentionally use prefix matching so
      // that the parent stays highlighted while a sub-route is shown.
      renderAt('/reports/daily');

      expect(screen.getByRole('link', { name: /Reports/ })).toHaveClass(ACTIVE_CLASS);
    });
  });
});

describe('Sidebar Component — layout', () => {
  it('applies the viewport-minus-navbar height as an arbitrary Tailwind value', () => {
    // Regression (TF-506): 'screen-minus-nav' was previously registered under
    // theme.extend.minHeight but consumed via the h-* utility (which reads
    // theme.height, not minHeight), so the class never generated any CSS and
    // the sidebar had no explicit height at all.
    const { container } = renderAt('/dashboard');

    const aside = container.querySelector('aside');
    expect(aside).not.toBeNull();
    expect(aside).toHaveClass('h-[calc(100vh_-_64px)]');
  });
});
