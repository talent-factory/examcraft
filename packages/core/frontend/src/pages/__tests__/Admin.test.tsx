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
jest.mock('../../components/admin/RoleManagementPage', () => ({
  __esModule: true,
  default: () => <div data-testid="role-management" />,
}));
jest.mock('../../components/admin/SubscriptionTierOverview', () => ({
  __esModule: true,
  default: () => <div data-testid="subscription-overview" />,
}));

// Mock useAuth
const mockHasRole = jest.fn();
const mockUser = { is_superuser: false };

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    hasRole: mockHasRole,
  }),
}));

describe('Admin Page', () => {
  beforeEach(() => {
    mockUser.is_superuser = false;
    mockHasRole.mockReturnValue(false);
  });

  describe('RBAC tab visibility', () => {
    it('shows only users tab for non-superuser admin', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      expect(screen.getByText('Benutzer-Verwaltung')).toBeInTheDocument();
      expect(screen.getByText('Audit Logs')).toBeInTheDocument();
      expect(screen.getByText('Abonnement')).toBeInTheDocument();
      expect(screen.queryByText('Institutionen')).not.toBeInTheDocument();
      expect(screen.queryByText('Rollen & Berechtigungen')).not.toBeInTheDocument();
    });

    it('shows all 5 tabs for superuser', () => {
      mockUser.is_superuser = true;

      render(<Admin />);

      expect(screen.getByText('Benutzer-Verwaltung')).toBeInTheDocument();
      expect(screen.getByText('Institutionen')).toBeInTheDocument();
      expect(screen.getByText('Rollen & Berechtigungen')).toBeInTheDocument();
      expect(screen.getByText('Audit Logs')).toBeInTheDocument();
      expect(screen.getByText('Abonnement')).toBeInTheDocument();
    });
  });

  describe('tab switching', () => {
    it('shows UserManagementPage by default', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      expect(screen.getByTestId('user-management')).toBeInTheDocument();
    });

    it('switches to Audit Logs tab', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      fireEvent.click(screen.getByText('Audit Logs'));

      expect(screen.getByText('Audit Logs — Demnachst verfugbar')).toBeInTheDocument();
      expect(screen.queryByTestId('user-management')).not.toBeInTheDocument();
    });

    it('switches to Subscription tab', () => {
      mockHasRole.mockReturnValue(true);

      render(<Admin />);

      fireEvent.click(screen.getByText('Abonnement'));

      expect(screen.getByTestId('subscription-overview')).toBeInTheDocument();
    });

    it('switches to Institutions tab for superuser', () => {
      mockUser.is_superuser = true;

      render(<Admin />);

      fireEvent.click(screen.getByText('Institutionen'));

      expect(screen.getByTestId('institution-management')).toBeInTheDocument();
    });

    it('switches to Roles tab for superuser', () => {
      mockUser.is_superuser = true;

      render(<Admin />);

      fireEvent.click(screen.getByText('Rollen & Berechtigungen'));

      expect(screen.getByTestId('role-management')).toBeInTheDocument();
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
});
