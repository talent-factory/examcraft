import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Admin } from '../Admin';

// Mock child components
jest.mock('../../components/admin/UserManagementPage', () => ({
  UserManagementPage: () => <div data-testid="user-management" />,
}));
jest.mock('../../components/admin/InstitutionManagementPage', () => ({
  InstitutionManagementPage: () => <div data-testid="institution-management" />,
}));
jest.mock('../AdminRoles', () => ({
  __esModule: true,
  default: () => <div data-testid="role-management" />,
}));
jest.mock('../../components/admin/SubscriptionTierOverview', () => ({
  __esModule: true,
  default: () => <div data-testid="subscription-overview" />,
}));
jest.mock('../../components/admin/HelpFeedbackQueue', () => ({
  __esModule: true,
  default: () => <div data-testid="help-feedback" />,
}));
jest.mock('../TagSettingsPage', () => ({
  __esModule: true,
  default: () => <div data-testid="tag-settings" />,
}));
jest.mock('../CompetencyFrameworkSettingsPage', () => ({
  __esModule: true,
  default: () => <div data-testid="competency-frameworks-settings" />,
}));
jest.mock('../AdminGradingSchemes', () => ({
  __esModule: true,
  default: () => <div data-testid="grading-schemes-management" />,
}));
jest.mock('../AdminOrgUnits', () => ({
  __esModule: true,
  default: () => <div data-testid="org-units-management" />,
}));
jest.mock('../../components/admin/AuditLogView', () => ({
  __esModule: true,
  default: () => <div data-testid="audit-log-view" />,
}));
jest.mock('../../components/admin/SystemHealthPanel', () => ({
  __esModule: true,
  default: () => <div data-testid="system-health-panel" />,
}));
jest.mock('../../components/admin/OpsChatWidget', () => ({
  __esModule: true,
  default: () => <div data-testid="ops-chat-widget" />,
}));

// Mock useAuth
const mockHasRole = jest.fn();
const mockHasPermission = jest.fn();
const mockUser: { is_superuser: boolean; institution?: { name: string } } = { is_superuser: false };

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    hasRole: mockHasRole,
    hasPermission: mockHasPermission,
  }),
}));

// GET /api/v1/ops/health only exists in Full deployment (see Admin.tsx's
// isFullDeployment() gate on the System Health tab) — default to Full here
// so the existing tab-switching tests don't need to know about it; the
// dedicated 'System Health tab' tests below override this per case.
const mockIsFullDeployment = jest.fn();
jest.mock('../../utils/deploymentMode', () => ({
  isFullDeployment: () => mockIsFullDeployment(),
}));

/** Opens the scope switcher and selects "Plattform (alle Institutionen)". */
const switchToPlatformScope = () => {
  fireEvent.click(screen.getByTestId('admin-scope-switcher-toggle'));
  fireEvent.click(screen.getByTestId('admin-scope-option-platform'));
};

describe('Admin Page', () => {
  beforeEach(() => {
    mockUser.is_superuser = false;
    delete mockUser.institution;
    mockHasRole.mockReturnValue(false);
    mockHasPermission.mockReturnValue(false);
    mockIsFullDeployment.mockReturnValue(true);
  });

  describe('RBAC tab visibility (institution scope)', () => {
    it('shows correct tabs for non-superuser admin', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      expect(screen.getByText('Benutzer-Verwaltung')).toBeInTheDocument();
      expect(screen.getByText('Audit Logs')).toBeInTheDocument();
      expect(screen.getByText('Abonnement')).toBeInTheDocument();
      expect(screen.getByText('Tag-Verwaltung')).toBeInTheDocument();
      expect(screen.getByText('Kompetenzrahmen')).toBeInTheDocument();
      expect(screen.queryByText('Institutionen')).not.toBeInTheDocument();
      expect(screen.queryByText('Rollen & Berechtigungen')).not.toBeInTheDocument();
    });

    it('lands superusers in institution scope by default, without platform tabs visible', () => {
      mockUser.is_superuser = true;

      render(<Admin />);

      expect(screen.getByText('Benutzer-Verwaltung')).toBeInTheDocument();
      expect(screen.getByText('Audit Logs')).toBeInTheDocument();
      expect(screen.getByText('Abonnement')).toBeInTheDocument();
      expect(screen.queryByText('Institutionen')).not.toBeInTheDocument();
      expect(screen.queryByText('Rollen & Berechtigungen')).not.toBeInTheDocument();
      expect(screen.queryByText('Help Feedback')).not.toBeInTheDocument();
    });

    it('shows the platform tabs after switching scope for superusers', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      switchToPlatformScope();

      expect(screen.getByText('Institutionen')).toBeInTheDocument();
      expect(screen.getByText('Rollen & Berechtigungen')).toBeInTheDocument();
      expect(screen.getByText('Help Feedback')).toBeInTheDocument();
      // Institution-scope tabs are no longer shown once platform scope is active.
      expect(screen.queryByText('Benutzer-Verwaltung')).not.toBeInTheDocument();
    });
  });

  describe('tab switching', () => {
    it('shows UserManagementPage by default', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      expect(screen.getByTestId('admin-tab-content-users')).toBeInTheDocument();
    });

    it('switches to Audit Logs tab', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      fireEvent.click(screen.getByText('Audit Logs'));

      expect(screen.getByTestId('admin-tab-content-audit')).toBeInTheDocument();
      expect(screen.getByTestId('audit-log-view')).toBeInTheDocument();
      expect(screen.queryByTestId('admin-tab-content-users')).not.toBeInTheDocument();
    });

    it('switches to Subscription tab', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      fireEvent.click(screen.getByText('Abonnement'));

      expect(screen.getByTestId('admin-tab-content-subscription')).toBeInTheDocument();
    });

    it('switches to Institutions tab for superuser after switching to platform scope', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      switchToPlatformScope();
      fireEvent.click(screen.getByText('Institutionen'));

      expect(screen.getByTestId('admin-tab-content-institutions')).toBeInTheDocument();
    });

    it('switches to Roles tab for superuser after switching to platform scope', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      switchToPlatformScope();
      fireEvent.click(screen.getByText('Rollen & Berechtigungen'));

      expect(screen.getByTestId('admin-tab-content-roles')).toBeInTheDocument();
    });

    it('switches to Kompetenzrahmen tab for admin', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      fireEvent.click(screen.getByText('Kompetenzrahmen'));

      expect(screen.getByTestId('admin-tab-content-competency-frameworks')).toBeInTheDocument();
      expect(screen.getByTestId('competency-frameworks-settings')).toBeInTheDocument();
    });

    it('shows and switches to Organisationseinheiten tab when permitted', () => {
      mockHasRole.mockReturnValue(true);
      mockHasPermission.mockImplementation(
        (permission: string) => permission === 'manage_org_units',
      );

      render(<Admin />);

      expect(screen.getByText('Organisationseinheiten')).toBeInTheDocument();
      fireEvent.click(screen.getByText('Organisationseinheiten'));

      expect(screen.getByTestId('admin-tab-content-org-units')).toBeInTheDocument();
      expect(screen.getByTestId('org-units-management')).toBeInTheDocument();
    });

    it('hides Organisationseinheiten tab without the permission', () => {
      mockHasRole.mockReturnValue(true);
      mockHasPermission.mockReturnValue(false);

      render(<Admin />);

      expect(screen.queryByText('Organisationseinheiten')).not.toBeInTheDocument();
    });

    it('shows and switches to Bewertungsschemata tab when permitted', () => {
      mockHasRole.mockReturnValue(true);
      mockHasPermission.mockImplementation(
        (permission: string) => permission === 'grading_schemes:manage',
      );

      render(<Admin />);

      expect(screen.getByText('Bewertungsschemata')).toBeInTheDocument();
      fireEvent.click(screen.getByText('Bewertungsschemata'));

      expect(screen.getByTestId('admin-tab-content-grading-schemes')).toBeInTheDocument();
      expect(screen.getByTestId('grading-schemes-management')).toBeInTheDocument();
    });

    it('hides Bewertungsschemata tab without the permission', () => {
      mockHasRole.mockReturnValue(true);
      mockHasPermission.mockReturnValue(false);

      render(<Admin />);

      expect(screen.queryByText('Bewertungsschemata')).not.toBeInTheDocument();
    });

    it('shows the first platform tab immediately after switching scope, before any click', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      switchToPlatformScope();

      expect(screen.getByTestId('admin-tab-content-institutions')).toBeInTheDocument();
    });

    it('switches back to institution scope via the dropdown option, not just the banner exit', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      switchToPlatformScope();
      expect(screen.getByTestId('admin-platform-banner')).toBeInTheDocument();

      fireEvent.click(screen.getByTestId('admin-scope-switcher-toggle'));
      fireEvent.click(screen.getByTestId('admin-scope-option-institution'));

      expect(screen.queryByTestId('admin-platform-banner')).not.toBeInTheDocument();
      expect(screen.getByTestId('admin-tab-content-users')).toBeInTheDocument();
    });

    it('remembers the last active tab per scope across repeated switches', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      switchToPlatformScope();
      fireEvent.click(screen.getByText('Rollen & Berechtigungen'));
      expect(screen.getByTestId('admin-tab-content-roles')).toBeInTheDocument();

      fireEvent.click(screen.getByTestId('admin-platform-banner-exit'));
      expect(screen.getByTestId('admin-tab-content-users')).toBeInTheDocument();

      switchToPlatformScope();

      expect(screen.getByTestId('admin-tab-content-roles')).toBeInTheDocument();
    });

    it('falls back to the first institution-scope tab when returning from platform scope', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      switchToPlatformScope();
      fireEvent.click(screen.getByText('Institutionen'));
      expect(screen.getByTestId('admin-tab-content-institutions')).toBeInTheDocument();

      fireEvent.click(screen.getByTestId('admin-platform-banner-exit'));

      expect(screen.getByTestId('admin-tab-content-users')).toBeInTheDocument();
      expect(screen.queryByTestId('admin-tab-content-institutions')).not.toBeInTheDocument();
    });
  });

  describe('header', () => {
    it('renders Admin-Panel title and description', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      expect(screen.getByText('Admin-Panel')).toBeInTheDocument();
      expect(screen.getByText('Verwalte Benutzer, Einstellungen und Systemkonfiguration')).toBeInTheDocument();
    });
  });

  describe('scope switcher (Super-Admin, TF-799)', () => {
    it('does not render for non-superuser admins', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      expect(screen.queryByTestId('admin-scope-switcher-toggle')).not.toBeInTheDocument();
    });

    it('renders for superusers and shows the institution name from the auth context', () => {
      mockUser.is_superuser = true;
      mockUser.institution = { name: 'Talent Factory GmbH' };

      render(<Admin />);

      expect(screen.getByTestId('admin-scope-switcher-toggle')).toHaveTextContent('Talent Factory GmbH');
    });

    it('shows the platform banner and updated subtitle once platform scope is active', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      expect(screen.queryByTestId('admin-platform-banner')).not.toBeInTheDocument();

      switchToPlatformScope();

      expect(screen.getByTestId('admin-platform-banner')).toBeInTheDocument();
      expect(screen.getByText('Plattformweite Einstellungen für alle Institutionen')).toBeInTheDocument();
    });

    it('returns to institution scope via the banner exit action', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      switchToPlatformScope();
      expect(screen.getByTestId('admin-platform-banner')).toBeInTheDocument();

      fireEvent.click(screen.getByTestId('admin-platform-banner-exit'));

      expect(screen.queryByTestId('admin-platform-banner')).not.toBeInTheDocument();
      expect(screen.getByText('Verwalte Benutzer, Einstellungen und Systemkonfiguration')).toBeInTheDocument();
    });

    it('uses a grammatical fallback exit label when no institution name is available', () => {
      mockUser.is_superuser = true;
      // beforeEach already deletes mockUser.institution.

      render(<Admin />);
      switchToPlatformScope();

      expect(screen.getByTestId('admin-platform-banner-exit')).toHaveTextContent('Zurück zur eigenen Institution');
    });

    it('uses the institution name in the exit label when available', () => {
      mockUser.is_superuser = true;
      mockUser.institution = { name: 'Talent Factory GmbH' };

      render(<Admin />);
      switchToPlatformScope();

      expect(screen.getByTestId('admin-platform-banner-exit')).toHaveTextContent('Zurück zu Talent Factory GmbH');
    });

    it('groups institution-scope tabs under their category headings', () => {
      mockHasRole.mockReturnValue(true);
      mockHasPermission.mockReturnValue(true);

      render(<Admin />);

      expect(screen.getByText('Benutzer & Zugriff')).toBeInTheDocument();
      expect(screen.getByText('Inhalte & Bewertung')).toBeInTheDocument();
      expect(screen.getByText('Abrechnung & Compliance')).toBeInTheDocument();
    });

    it('groups platform-scope tabs under their category headings after switching', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      switchToPlatformScope();

      expect(screen.getByText('Mandanten')).toBeInTheDocument();
      expect(screen.getByText('Sicherheit')).toBeInTheDocument();
    });

    it('marks the active scope option with aria-checked', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      fireEvent.click(screen.getByTestId('admin-scope-switcher-toggle'));

      expect(screen.getByTestId('admin-scope-option-institution')).toHaveAttribute('aria-checked', 'true');
      expect(screen.getByTestId('admin-scope-option-platform')).toHaveAttribute('aria-checked', 'false');
    });

    it('closes the scope switcher menu when clicking outside it', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      fireEvent.click(screen.getByTestId('admin-scope-switcher-toggle'));
      expect(screen.getByTestId('admin-scope-switcher-menu')).toBeInTheDocument();

      fireEvent.mouseDown(document.body);

      expect(screen.queryByTestId('admin-scope-switcher-menu')).not.toBeInTheDocument();
    });

    it('closes the scope switcher menu on Escape', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      fireEvent.click(screen.getByTestId('admin-scope-switcher-toggle'));
      expect(screen.getByTestId('admin-scope-switcher-menu')).toBeInTheDocument();

      fireEvent.keyDown(document, { key: 'Escape' });

      expect(screen.queryByTestId('admin-scope-switcher-menu')).not.toBeInTheDocument();
    });

    it('does not close the scope switcher menu when clicking the onboarding tour popover (TF-799 tour dependency)', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      fireEvent.click(screen.getByTestId('admin-scope-switcher-toggle'));
      expect(screen.getByTestId('admin-scope-switcher-menu')).toBeInTheDocument();

      // The onboarding tour's own popover (OnboardingPopover.tsx) renders
      // outside this page's DOM subtree, anchored to the highlighted
      // element. Its "Weiter →" click must not be treated as an outside
      // click, or the tour's next step (targeting
      // admin-scope-option-platform) would find the menu already closed.
      const tourPopover = document.createElement('div');
      tourPopover.setAttribute('data-testid', 'onboarding-popover');
      document.body.appendChild(tourPopover);

      fireEvent.mouseDown(tourPopover);

      expect(screen.getByTestId('admin-scope-switcher-menu')).toBeInTheDocument();

      document.body.removeChild(tourPopover);
    });
  });

  describe('System Health tab', () => {
    it('hides the System Health tab for non-superusers', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      expect(screen.queryByText('System Health')).not.toBeInTheDocument();
    });

    it('shows and switches to the System Health tab for superusers in Full deployment', () => {
      mockUser.is_superuser = true;

      render(<Admin />);
      switchToPlatformScope();

      expect(screen.getByText('System Health')).toBeInTheDocument();
      fireEvent.click(screen.getByText('System Health'));

      expect(screen.getByTestId('admin-tab-content-system-health')).toBeInTheDocument();
      expect(screen.getByTestId('system-health-panel')).toBeInTheDocument();
      expect(screen.getByTestId('ops-chat-widget')).toBeInTheDocument();
    });

    it('hides the System Health tab for superusers in Core deployment (GET /api/v1/ops/health does not exist there)', () => {
      mockUser.is_superuser = true;
      mockIsFullDeployment.mockReturnValue(false);

      render(<Admin />);
      switchToPlatformScope();

      expect(screen.queryByText('System Health')).not.toBeInTheDocument();
    });
  });
});
