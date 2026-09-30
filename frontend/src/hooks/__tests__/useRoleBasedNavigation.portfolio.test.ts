/**
 * useRoleBasedNavigation — «Portfolio-Bewertung» entry (TF-987).
 */
import { renderHook } from '@testing-library/react';
import { useRoleBasedNavigation } from '../useRoleBasedNavigation';
import { isFullDeployment } from '../../utils/deploymentMode';

jest.mock('../../utils/deploymentMode', () => ({
  isFullDeployment: jest.fn(() => true),
}));

beforeEach(() => {
  (isFullDeployment as jest.Mock).mockReturnValue(true);
});

let mockPermissions: string[] = [];
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { is_superuser: false },
    hasRole: () => false,
    hasPermission: (permission: string) => mockPermissions.includes(permission),
  }),
}));

const evaluationPaths = () =>
  renderHook(() => useRoleBasedNavigation())
    .result.current.navigationGroups.find((group) => group.id === 'evaluation')
    ?.items.map((item) => item.path) ?? [];

describe('useRoleBasedNavigation - Portfolio', () => {
  it('fehlt ohne portfolio_assessments:read', () => {
    mockPermissions = ['submissions:read', 'portfolio_templates:read'];
    expect(evaluationPaths()).not.toContain('/portfolio');
  });

  it('steht mit portfolio_assessments:read in der Gruppe Auswertung', () => {
    mockPermissions = ['portfolio_assessments:read'];
    const { result } = renderHook(() => useRoleBasedNavigation());
    const item = result.current.navigationGroups
      .find((group) => group.id === 'evaluation')
      ?.items.find((entry) => entry.path === '/portfolio');
    expect(item?.label).toBe('Portfolio-Bewertung');
    expect(result.current.hasAccess('/portfolio')).toBe(true);
  });

  it('zeigt die Templates nur mit portfolio_templates:read', () => {
    mockPermissions = ['portfolio_assessments:read'];
    expect(evaluationPaths()).not.toContain('/portfolio/templates');

    mockPermissions = ['portfolio_templates:read'];
    expect(evaluationPaths()).toEqual(['/portfolio/templates']);
  });

  it('fehlt im Core-Deployment trotz Berechtigung', () => {
    // Core's RBAC can grant the opt-in permission, but the page would only
    // say the feature is unavailable there.
    (isFullDeployment as jest.Mock).mockReturnValue(false);
    mockPermissions = ['portfolio_assessments:read', 'portfolio_templates:read'];
    expect(evaluationPaths()).not.toContain('/portfolio');
    expect(evaluationPaths()).not.toContain('/portfolio/templates');
  });
});
