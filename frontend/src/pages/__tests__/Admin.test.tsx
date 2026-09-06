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

// Mock useAuth
const mockHasRole = jest.fn();
const mockHasPermission = jest.fn();
const mockUser = { is_superuser: false };

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

describe('Admin Page', () => {
  beforeEach(() => {
    mockUser.is_superuser = false;
    mockHasRole.mockReturnValue(false);
    mockHasPermission.mockReturnValue(false);
    mockIsFullDeployment.mockReturnValue(true);
  });

  describe('RBAC tab visibility', () => {
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

    it('shows all tabs for superuser', () => {
      mockUser.is_superuser = true;

      render(<Admin />);

      expect(screen.getByText('Benutzer-Verwaltung')).toBeInTheDocument();
      expect(screen.getByText('Institutionen')).toBeInTheDocument();
      expect(screen.getByText('Rollen & Berechtigungen')).toBeInTheDocument();
      expect(screen.getByText('Audit Logs')).toBeInTheDocument();
      expect(screen.getByText('Abonnement')).toBeInTheDocument();
      expect(screen.getByText('Tag-Verwaltung')).toBeInTheDocument();
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

    it('switches to Institutions tab for superuser', () => {
      mockUser.is_superuser = true;

      render(<Admin />);

      fireEvent.click(screen.getByText('Institutionen'));

      expect(screen.getByTestId('admin-tab-content-institutions')).toBeInTheDocument();
    });

    it('switches to Roles tab for superuser', () => {
      mockUser.is_superuser = true;

      render(<Admin />);

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
  });

  describe('header', () => {
    it('renders Admin-Panel title and description', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      expect(screen.getByText('Admin-Panel')).toBeInTheDocument();
      expect(screen.getByText('Verwalte Benutzer, Einstellungen und Systemkonfiguration')).toBeInTheDocument();
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

      expect(screen.getByText('System Health')).toBeInTheDocument();
      fireEvent.click(screen.getByText('System Health'));

      expect(screen.getByTestId('admin-tab-content-system-health')).toBeInTheDocument();
      expect(screen.getByTestId('system-health-panel')).toBeInTheDocument();
    });

    it('hides the System Health tab for superusers in Core deployment (GET /api/v1/ops/health does not exist there)', () => {
      mockUser.is_superuser = true;
      mockIsFullDeployment.mockReturnValue(false);

      render(<Admin />);

      expect(screen.queryByText('System Health')).not.toBeInTheDocument();
    });
  });
});
