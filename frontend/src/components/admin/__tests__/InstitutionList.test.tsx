/**
 * InstitutionList tests.
 *
 * TF-772 PR 3: `loadInstitutions`'s catch block migrated to `translateError`.
 * This component had no test file at all, so the migration went live with
 * zero coverage of its error path — these tests pin that behaviour.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { InstitutionList } from '../InstitutionList';
import AdminService from '../../../services/AdminService';
import { AppError } from '../../../errors';

jest.mock('../../../services/AdminService', () => ({
  __esModule: true,
  default: {
    listInstitutions: jest.fn(),
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

describe('InstitutionList', () => {
  it('renders institutions once loaded', async () => {
    (AdminService.listInstitutions as jest.Mock).mockResolvedValue([
      { id: 1, name: 'BWZ Lyss', domain: 'bwz-lyss.example', subscription_tier: 'free', is_active: true, max_users: 10, max_documents: 10, max_questions_per_month: 10 },
    ]);

    render(
      <InstitutionList onEditInstitution={jest.fn()} onCreateInstitution={jest.fn()} />,
    );

    expect(await screen.findByText('BWZ Lyss')).toBeInTheDocument();
  });

  it('shows the translated message when listInstitutions rejects with a specific code', async () => {
    (AdminService.listInstitutions as jest.Mock).mockRejectedValue(
      new AppError('admin_institutions_load_failed', 'Institutions could not be loaded', 500),
    );

    render(
      <InstitutionList onEditInstitution={jest.fn()} onCreateInstitution={jest.fn()} />,
    );

    expect(
      await screen.findByText('Institutionen konnten nicht geladen werden'),
    ).toBeInTheDocument();
  });

  it('shows the fallback banner when listInstitutions rejects without a specific code', async () => {
    (AdminService.listInstitutions as jest.Mock).mockRejectedValue(new Error('network blip'));

    render(
      <InstitutionList onEditInstitution={jest.fn()} onCreateInstitution={jest.fn()} />,
    );

    await waitFor(() => {
      expect(screen.getByText('admin.institutionList.failedLoad')).toBeInTheDocument();
    });
  });
});
