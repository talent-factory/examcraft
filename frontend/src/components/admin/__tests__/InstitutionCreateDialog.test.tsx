/**
 * InstitutionCreateDialog tests.
 *
 * TF-772 PR 3: `handleSubmit`'s catch block migrated to `translateError`.
 * This component had no test file at all, so the migration went live with
 * zero coverage of its error path — these tests pin that behaviour.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { InstitutionCreateDialog } from '../InstitutionCreateDialog';
import AdminService from '../../../services/AdminService';
import { AppError } from '../../../errors';

jest.mock('../../../services/AdminService', () => ({
  __esModule: true,
  default: {
    createInstitution: jest.fn(),
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

function fillRequiredFields() {
  fireEvent.change(screen.getByPlaceholderText('admin.institutionCreate.namePlaceholder'), {
    target: { value: 'BWZ Lyss' },
  });
  fireEvent.change(screen.getByPlaceholderText('admin.institutionCreate.domainPlaceholder'), {
    target: { value: 'bwz-lyss.example' },
  });
}

describe('InstitutionCreateDialog', () => {
  it('creates the institution and calls onSuccess', async () => {
    (AdminService.createInstitution as jest.Mock).mockResolvedValue({});
    const onSuccess = jest.fn();
    render(
      <InstitutionCreateDialog isOpen={true} onClose={jest.fn()} onSuccess={onSuccess} />,
    );

    fillRequiredFields();
    fireEvent.click(screen.getByText('admin.institutionCreate.create'));

    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });

  it('shows the translated message when createInstitution rejects with a specific code', async () => {
    (AdminService.createInstitution as jest.Mock).mockRejectedValue(
      new AppError('admin_institution_create_failed', 'Institution could not be created', 500),
    );
    render(
      <InstitutionCreateDialog isOpen={true} onClose={jest.fn()} onSuccess={jest.fn()} />,
    );

    fillRequiredFields();
    fireEvent.click(screen.getByText('admin.institutionCreate.create'));

    expect(
      await screen.findByText('Institution konnte nicht erstellt werden'),
    ).toBeInTheDocument();
  });

  it('shows the fallback banner when createInstitution rejects without a specific code', async () => {
    (AdminService.createInstitution as jest.Mock).mockRejectedValue(new Error('network blip'));
    render(
      <InstitutionCreateDialog isOpen={true} onClose={jest.fn()} onSuccess={jest.fn()} />,
    );

    fillRequiredFields();
    fireEvent.click(screen.getByText('admin.institutionCreate.create'));

    expect(
      await screen.findByText('admin.institutionCreate.failedCreate'),
    ).toBeInTheDocument();
  });
});
