import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import RolePermissionsEditor from '../RolePermissionsEditor';
import { RolesService } from '../../../services/rolesService';
import { ApiError } from '../../../services/httpClient';

jest.mock('../../../services/rolesService');
const mockedService = RolesService as jest.Mocked<typeof RolesService>;

jest.mock('react-i18next', () => {
  const mockTranslations = require('../../../locales/de/translation.json');
  function mockResolveKey(obj: Record<string, any>, key: string): string {
    const parts = key.split('.');
    let current: any = obj;
    for (const part of parts) {
      if (current == null || typeof current !== 'object') return key;
      current = current[part];
    }
    return typeof current === 'string' ? current : key;
  }
  const stableT = (key: string, params?: Record<string, any>) => {
    let value = mockResolveKey(mockTranslations, key);
    if (params && typeof value === 'string') {
      Object.entries(params).forEach(([k, v]) => {
        value = (value as string).replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
      });
    }
    return value;
  };
  return {
    useTranslation: () => ({
      t: stableT,
      i18n: { changeLanguage: jest.fn().mockResolvedValue(undefined), language: 'de' },
    }),
    Trans: ({ children }: { children: React.ReactNode }) => children,
    initReactI18next: { type: '3rdParty', init: jest.fn() },
  };
});

const permissions = [
  { key: 'manage_org_units', label: 'Organisationseinheiten verwalten', category: 'Organisation' },
  { key: 'review_questions', label: 'Fragen begutachten', category: 'Fragen' },
];

const theme = createTheme();
const renderEditor = (props: Partial<React.ComponentProps<typeof RolePermissionsEditor>> = {}) =>
  render(
    <ThemeProvider theme={theme}>
      <RolePermissionsEditor
        open
        role={null}
        onClose={jest.fn()}
        onSaved={jest.fn()}
        {...props}
      />
    </ThemeProvider>,
  );

describe('RolePermissionsEditor', () => {
  beforeEach(() => {
    mockedService.listPermissions.mockResolvedValue(permissions);
  });
  afterEach(() => jest.clearAllMocks());

  it('create mode: allows entering name and toggling a permission, then saves', async () => {
    mockedService.create.mockResolvedValue({
      id: 1,
      name: 'fachbereichsleiter',
      display_name: 'Fachbereichsleiter',
      description: null,
      permissions: ['manage_org_units'],
      is_system_role: false,
      created_at: '2026-08-10T00:00:00Z',
    });
    const onSaved = jest.fn();
    renderEditor({ onSaved });

    await waitFor(() => expect(screen.getByLabelText('Name')).toBeInTheDocument());
    await waitFor(() =>
      expect(
        screen.getByRole('checkbox', { name: /Organisationseinheiten verwalten/ }),
      ).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'fachbereichsleiter' } });
    fireEvent.change(screen.getByLabelText('Anzeigename'), { target: { value: 'Fachbereichsleiter' } });
    fireEvent.click(screen.getByRole('checkbox', { name: /Organisationseinheiten verwalten/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));

    await waitFor(() =>
      expect(mockedService.create).toHaveBeenCalledWith({
        name: 'fachbereichsleiter',
        display_name: 'Fachbereichsleiter',
        description: null,
        permissions: ['manage_org_units'],
      }),
    );
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
  });

  it('shows the backend detail message when save fails with a 409', async () => {
    mockedService.create.mockRejectedValueOnce(
      new ApiError({
        kind: 'validation',
        status: 409,
        message: "Rolle 'fachbereichsleiter' existiert bereits",
        detail: "Rolle 'fachbereichsleiter' existiert bereits",
      }),
    );
    renderEditor();

    await waitFor(() => expect(screen.getByLabelText('Name')).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'fachbereichsleiter' } });
    fireEvent.change(screen.getByLabelText('Anzeigename'), { target: { value: 'Fachbereichsleiter' } });
    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));

    expect(
      await screen.findByText("Rolle 'fachbereichsleiter' existiert bereits"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('Rolle konnte nicht erstellt werden.'),
    ).not.toBeInTheDocument();
  });

  it('create mode: save button is disabled while name or display name is empty', async () => {
    renderEditor();

    await waitFor(() => expect(screen.getByLabelText('Name')).toBeInTheDocument());
    await waitFor(() =>
      expect(
        screen.getByRole('checkbox', { name: /Organisationseinheiten verwalten/ }),
      ).toBeInTheDocument(),
    );

    expect(screen.getByRole('button', { name: 'Speichern' })).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'fachbereichsleiter' } });
    expect(screen.getByRole('button', { name: 'Speichern' })).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Anzeigename'), { target: { value: 'Fachbereichsleiter' } });
    expect(screen.getByRole('button', { name: 'Speichern' })).not.toBeDisabled();

    expect(mockedService.create).not.toHaveBeenCalled();
  });

  it('edit mode on a system role: name field is disabled, permissions remain editable', async () => {
    renderEditor({
      role: {
        id: 1,
        name: 'admin',
        display_name: 'Administrator',
        description: 'Full access',
        permissions: ['manage_org_units'],
        is_system_role: true,
        created_at: '2026-08-10T00:00:00Z',
      },
    });

    await waitFor(() => expect(screen.getByLabelText('Name')).toBeInTheDocument());
    expect(screen.getByLabelText('Name')).toBeDisabled();
    await waitFor(() =>
      expect(screen.getByRole('checkbox', { name: /Organisationseinheiten verwalten/ })).toBeChecked(),
    );
    expect(screen.getByRole('checkbox', { name: /Organisationseinheiten verwalten/ })).not.toBeDisabled();
  });

  it('edit mode: toggling a permission and saving calls RolesService.update with the new permission set', async () => {
    mockedService.update.mockResolvedValue({
      id: 1,
      name: 'admin',
      display_name: 'Administrator geändert',
      description: 'Full access',
      permissions: ['manage_org_units', 'review_questions'],
      is_system_role: true,
      created_at: '2026-08-10T00:00:00Z',
    });
    const onSaved = jest.fn();
    renderEditor({
      onSaved,
      role: {
        id: 1,
        name: 'admin',
        display_name: 'Administrator',
        description: 'Full access',
        permissions: ['manage_org_units'],
        is_system_role: true,
        created_at: '2026-08-10T00:00:00Z',
      },
    });

    await waitFor(() =>
      expect(screen.getByRole('checkbox', { name: /Fragen begutachten/ })).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByLabelText('Anzeigename'), {
      target: { value: 'Administrator geändert' },
    });
    fireEvent.click(screen.getByRole('checkbox', { name: /Fragen begutachten/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));

    await waitFor(() =>
      expect(mockedService.update).toHaveBeenCalledWith(1, {
        display_name: 'Administrator geändert',
        description: 'Full access',
        permissions: ['manage_org_units', 'review_questions'],
      }),
    );
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
  });

  it('shows an error and leaves the checklist empty when loading permissions fails', async () => {
    mockedService.listPermissions.mockReset();
    mockedService.listPermissions.mockRejectedValueOnce(new Error('network down'));
    renderEditor();

    expect(
      await screen.findByText('Berechtigungsliste konnte nicht geladen werden.'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });
});
