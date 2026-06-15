/**
 * InstitutionEditDialog tests (TF-431).
 *
 * Focused on the new default-grading-scheme dropdown: it lists system +
 * institution schemes, pre-selects the institution's existing default, and
 * submits the chosen id as ``default_grading_scheme_id`` — the field the
 * Note-resolver reads as its institution-wide fallback.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { InstitutionEditDialog } from '../InstitutionEditDialog';
import AdminService from '../../../services/AdminService';
import { GradingSchemesService } from '../../../services/gradingSchemesService';

jest.mock('../../../services/AdminService', () => ({
  __esModule: true,
  default: {
    listInstitutions: jest.fn(),
    updateInstitution: jest.fn(),
  },
}));

jest.mock('../../../services/gradingSchemesService', () => ({
  GradingSchemesService: { list: jest.fn() },
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const institution = {
  id: 4,
  name: 'BWZ Lyss',
  slug: 'bwz-lyss',
  domain: 'bwzlyss.ch',
  subscription_tier: 'enterprise',
  max_users: -1,
  max_documents: -1,
  max_questions_per_month: -1,
  is_active: true,
  default_grading_scheme_id: null,
  created_at: '2026-01-01',
  updated_at: null,
};

const schemes = {
  schemes: [
    {
      id: 1,
      institution_id: null,
      name: 'Swiss 1.0–6.0',
      display_format: 'numeric',
      config: { type: 'linear', min_pct: 0, max_pct: 100, min_grade: 1, max_grade: 6 },
      is_default_for_institution: false,
      is_system_scheme: true,
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
    },
    {
      id: 9,
      institution_id: 4,
      name: 'BWZ Custom',
      display_format: 'pass_fail',
      config: { type: 'stepped', steps: [] },
      is_default_for_institution: false,
      is_system_scheme: false,
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
    },
  ],
};

const mockedAdmin = AdminService as jest.Mocked<typeof AdminService>;
const mockedSchemes = GradingSchemesService as jest.Mocked<
  typeof GradingSchemesService
>;

beforeEach(() => {
  jest.clearAllMocks();
  mockedAdmin.listInstitutions.mockResolvedValue([institution] as any);
  mockedAdmin.updateInstitution.mockResolvedValue(institution as any);
  mockedSchemes.list.mockResolvedValue(schemes as any);
});

test('lists system + institution schemes and submits the chosen default', async () => {
  const onSuccess = jest.fn();
  render(
    <InstitutionEditDialog
      institutionId={4}
      isOpen
      onClose={jest.fn()}
      onSuccess={onSuccess}
    />,
  );

  const select = (await screen.findByTestId(
    'institution-grading-scheme-select',
  )) as HTMLSelectElement;
  expect(
    await screen.findByRole('option', { name: 'Swiss 1.0–6.0' }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole('option', { name: 'BWZ Custom' }),
  ).toBeInTheDocument();

  fireEvent.change(select, { target: { value: '1' } });
  fireEvent.click(
    screen.getByRole('button', {
      name: 'admin.institutionEdit.saveChanges',
    }),
  );

  await waitFor(() =>
    expect(mockedAdmin.updateInstitution).toHaveBeenCalledWith(
      4,
      expect.objectContaining({ default_grading_scheme_id: 1 }),
    ),
  );
});

test('pre-selects the institution existing default scheme', async () => {
  mockedAdmin.listInstitutions.mockResolvedValue([
    { ...institution, default_grading_scheme_id: 1 },
  ] as any);

  render(
    <InstitutionEditDialog
      institutionId={4}
      isOpen
      onClose={jest.fn()}
      onSuccess={jest.fn()}
    />,
  );

  const select = (await screen.findByTestId(
    'institution-grading-scheme-select',
  )) as HTMLSelectElement;
  await waitFor(() => expect(select.value).toBe('1'));
});

test('submits null when the default is cleared', async () => {
  mockedAdmin.listInstitutions.mockResolvedValue([
    { ...institution, default_grading_scheme_id: 1 },
  ] as any);

  render(
    <InstitutionEditDialog
      institutionId={4}
      isOpen
      onClose={jest.fn()}
      onSuccess={jest.fn()}
    />,
  );

  const select = (await screen.findByTestId(
    'institution-grading-scheme-select',
  )) as HTMLSelectElement;
  await waitFor(() => expect(select.value).toBe('1'));

  fireEvent.change(select, { target: { value: '' } });
  fireEvent.click(
    screen.getByRole('button', {
      name: 'admin.institutionEdit.saveChanges',
    }),
  );

  await waitFor(() =>
    expect(mockedAdmin.updateInstitution).toHaveBeenCalledWith(
      4,
      expect.objectContaining({ default_grading_scheme_id: null }),
    ),
  );
});

test('surfaces the backend error when the update is rejected (e.g. 422)', async () => {
  // AdminService.updateInstitution throws the parsed `detail` (see the
  // service's defensive error handling); the dialog must show it, not
  // swallow it — the whole feature hinges on a validation that 422s.
  mockedAdmin.updateInstitution.mockRejectedValue(
    new Error('Ungültiges Notenschema für diese Institution'),
  );

  render(
    <InstitutionEditDialog
      institutionId={4}
      isOpen
      onClose={jest.fn()}
      onSuccess={jest.fn()}
    />,
  );

  const select = (await screen.findByTestId(
    'institution-grading-scheme-select',
  )) as HTMLSelectElement;
  fireEvent.change(select, { target: { value: '1' } });
  fireEvent.click(
    screen.getByRole('button', {
      name: 'admin.institutionEdit.saveChanges',
    }),
  );

  expect(
    await screen.findByText('Ungültiges Notenschema für diese Institution'),
  ).toBeInTheDocument();
});

test('still loads the dialog when the grading-schemes fetch fails', async () => {
  // The schemes fetch is best-effort: an outage there must not block
  // editing the institution's other fields (no Promise.all fail-fast).
  mockedSchemes.list.mockRejectedValue(new Error('schemes endpoint down'));

  render(
    <InstitutionEditDialog
      institutionId={4}
      isOpen
      onClose={jest.fn()}
      onSuccess={jest.fn()}
    />,
  );

  // The form still renders (dropdown present, just with no scheme options).
  const select = (await screen.findByTestId(
    'institution-grading-scheme-select',
  )) as HTMLSelectElement;
  expect(select).toBeInTheDocument();
  expect(
    screen.queryByRole('option', { name: 'Swiss 1.0–6.0' }),
  ).not.toBeInTheDocument();
});
