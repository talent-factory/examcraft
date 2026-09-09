/**
 * FeaturePermissionsMatrix tests.
 *
 * TF-772 PR 3: `loadData`'s catch block migrated to `translateError`. This
 * component had no test file at all, so the migration went live with zero
 * coverage of its error path — these tests pin that behaviour.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import FeaturePermissionsMatrix from '../FeaturePermissionsMatrix';
import RBACService from '../../../services/RBACService';
import { AppError } from '../../../errors';

jest.mock('../../../services/RBACService', () => ({
  __esModule: true,
  default: {
    listRoles: jest.fn(),
    listFeatures: jest.fn(),
  },
}));

jest.mock('react-i18next', () => {
  // A mock that echoes every key would send every AppError down the fallback
  // branch and make the translated-text assertion below silently vacuous —
  // resolve the real errors.* block, same as the sibling admin dialog tests.
  const de = require('../../../locales/de/translation.json');
  return {
    useTranslation: () => ({
      t: (key: string) =>
        key.startsWith('errors.')
          ? (de.errors[key.slice('errors.'.length)] ?? key)
          : key,
    }),
  };
});

describe('FeaturePermissionsMatrix', () => {
  it('renders the matrix once roles and features load', async () => {
    (RBACService.listRoles as jest.Mock).mockResolvedValue([
      { id: 1, name: 'dozent', display_name: 'Dozent', is_system_role: true, features: [] },
    ]);
    (RBACService.listFeatures as jest.Mock).mockResolvedValue([
      { id: 'f1', display_name: 'Feature 1', category: 'generation' },
    ]);

    render(<FeaturePermissionsMatrix />);

    expect(await screen.findByText('Dozent')).toBeInTheDocument();
    expect(screen.getByText('Feature 1')).toBeInTheDocument();
  });

  it('shows the translated message when loading fails with a specific code', async () => {
    (RBACService.listRoles as jest.Mock).mockRejectedValue(
      new AppError('rbac_roles_load_failed', 'Roles could not be loaded', 500),
    );
    (RBACService.listFeatures as jest.Mock).mockResolvedValue([]);

    render(<FeaturePermissionsMatrix />);

    expect(
      await screen.findByText('Rollen konnten nicht geladen werden'),
    ).toBeInTheDocument();
  });

  it('shows the fallback banner when loading fails without a specific code', async () => {
    (RBACService.listRoles as jest.Mock).mockRejectedValue(new Error('network blip'));
    (RBACService.listFeatures as jest.Mock).mockResolvedValue([]);

    render(<FeaturePermissionsMatrix />);

    await waitFor(() => {
      expect(screen.getByText('admin.featureMatrix.failedLoad')).toBeInTheDocument();
    });
  });
});
