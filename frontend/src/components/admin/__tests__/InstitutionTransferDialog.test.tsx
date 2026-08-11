/**
 * InstitutionTransferDialog tests (TF-352 Task 17).
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { InstitutionTransferDialog } from '../InstitutionTransferDialog';
import AdminService from '../../../services/AdminService';

jest.mock('../../../services/AdminService', () => ({
  __esModule: true,
  default: {
    previewTransfer: jest.fn(),
    transferUser: jest.fn(),
    getUsers: jest.fn(),
    getInstitutions: jest.fn(),
  },
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const mockUser = {
  id: 7,
  email: 'u@x',
  first_name: 'U',
  last_name: 'X',
  institution_id: 1,
  institution_name: 'Source',
  roles: [],
  status: 'active',
  is_superuser: false,
  last_login_at: null,
  created_at: '2026-01-01',
  updated_at: null,
};

const mockInstitutions = [
  {
    id: 1, name: 'Source', slug: 's', subscription_tier: 'free',
    max_users: 10, max_documents: 10, max_questions_per_month: 10,
    is_active: true, created_at: '2026-01-01', domain: 's.local',
    require_second_reviewer: false,
  },
  {
    id: 2, name: 'Target', slug: 't', subscription_tier: 'free',
    max_users: 10, max_documents: 10, max_questions_per_month: 10,
    is_active: true, created_at: '2026-01-01', domain: 't.local',
    require_second_reviewer: false,
  },
];

const mockPreview = {
  source_institution_id: 1,
  source_institution_name: 'Source',
  target_institution_id: 2,
  target_institution_name: 'Target',
  transferable: { documents: 5, exams: 2, questions: 10, tags: 1 },
  excluded: { students: 50, classes: 3, submissions: 200 },
  org_unit_memberships: 0,
};

describe('InstitutionTransferDialog', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('does not render when isOpen=false', () => {
    render(
      <InstitutionTransferDialog
        user={mockUser as any}
        institutions={mockInstitutions as any}
        isOpen={false}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );
    expect(screen.queryByText('admin.institutionTransfer.title')).toBeNull();
  });

  it('loads preview when target selected', async () => {
    (AdminService.previewTransfer as jest.Mock).mockResolvedValue(mockPreview);
    render(
      <InstitutionTransferDialog
        user={mockUser as any}
        institutions={mockInstitutions as any}
        isOpen={true}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '2' } });

    // Advance the 300ms debounce timer
    await act(async () => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() =>
      expect(AdminService.previewTransfer).toHaveBeenCalledWith(7, 2),
    );
    expect(
      await screen.findByText('admin.institutionTransfer.documents'),
    ).toBeInTheDocument();
  });

  it('disables checkbox when count is 0', async () => {
    (AdminService.previewTransfer as jest.Mock).mockResolvedValue({
      ...mockPreview,
      transferable: { documents: 0, exams: 2, questions: 0, tags: 0 },
    });
    render(
      <InstitutionTransferDialog
        user={mockUser as any}
        institutions={mockInstitutions as any}
        isOpen={true}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '2' } });

    await act(async () => {
      jest.advanceTimersByTime(300);
    });

    const checkboxes = await screen.findAllByRole('checkbox');
    const disabled = checkboxes.filter(
      (c) => (c as HTMLInputElement).disabled,
    );
    // documents/tags/questions have 0 → disabled; only exams enabled
    expect(disabled.length).toBe(3);
  });

  it('next button disabled until target selected and preview loaded', () => {
    render(
      <InstitutionTransferDialog
        user={mockUser as any}
        institutions={mockInstitutions as any}
        isOpen={true}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );
    const nextBtn = screen.getByRole('button', {
      name: /admin\.institutionTransfer\.next/,
    });
    expect(nextBtn).toBeDisabled();
  });

  it('executes transfer and calls onSuccess', async () => {
    (AdminService.previewTransfer as jest.Mock).mockResolvedValue(mockPreview);
    (AdminService.transferUser as jest.Mock).mockResolvedValue({
      user: { ...mockUser, institution_id: 2 },
      transferred: mockPreview.transferable,
      org_unit_memberships_cleared: 0,
    });
    const onSuccess = jest.fn();
    render(
      <InstitutionTransferDialog
        user={mockUser as any}
        institutions={mockInstitutions as any}
        isOpen={true}
        onClose={jest.fn()}
        onSuccess={onSuccess}
      />,
    );

    fireEvent.change(screen.getByRole('combobox'), { target: { value: '2' } });

    await act(async () => {
      jest.advanceTimersByTime(300);
    });

    await screen.findByText('admin.institutionTransfer.documents');
    fireEvent.click(
      screen.getByRole('button', {
        name: /admin\.institutionTransfer\.next/,
      }),
    );
    fireEvent.click(
      screen.getByRole('button', {
        name: /admin\.institutionTransfer\.execute/,
      }),
    );

    await waitFor(() => {
      expect(AdminService.transferUser).toHaveBeenCalled();
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it('shows org-unit-memberships warning on select and confirm steps when > 0 (TF-602)', async () => {
    (AdminService.previewTransfer as jest.Mock).mockResolvedValue({
      ...mockPreview,
      org_unit_memberships: 2,
    });
    render(
      <InstitutionTransferDialog
        user={mockUser as any}
        institutions={mockInstitutions as any}
        isOpen={true}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '2' } });

    await act(async () => {
      jest.advanceTimersByTime(300);
    });

    expect(await screen.findByTestId('itd-org-units-warning')).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole('button', {
        name: /admin\.institutionTransfer\.next/,
      }),
    );

    expect(
      await screen.findByTestId('itd-confirm-org-units-warning'),
    ).toBeInTheDocument();
  });

  it('debounces preview calls — rapid changes result in single fetch', async () => {
    (AdminService.previewTransfer as jest.Mock).mockResolvedValue(mockPreview);
    render(
      <InstitutionTransferDialog
        user={mockUser as any}
        institutions={mockInstitutions as any}
        isOpen={true}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );

    const combobox = screen.getByRole('combobox');
    // Three rapid changes within debounce window
    fireEvent.change(combobox, { target: { value: '2' } });
    act(() => { jest.advanceTimersByTime(100); });
    // Toggle target via a no-op (still id=2) — would re-fire if no debounce
    fireEvent.change(combobox, { target: { value: '2' } });
    act(() => { jest.advanceTimersByTime(100); });
    fireEvent.change(combobox, { target: { value: '2' } });
    // Advance past full debounce window from the LAST change
    act(() => { jest.advanceTimersByTime(300); });

    await waitFor(() => {
      expect(AdminService.previewTransfer).toHaveBeenCalledTimes(1);
    });
  });
});
