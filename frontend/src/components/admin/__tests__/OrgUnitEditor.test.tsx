/**
 * OrgUnitEditor tests (org-unit hierarchy, Stufe 0 follow-up).
 *
 * Covers what AdminOrgUnits.test.tsx doesn't: actually submitting the
 * create/edit dialog (name + unit_type dropdown + parent selection), the
 * move_to_root wiring on edit, and the cycle-prevention filter that excludes
 * a unit's own descendants from its parent dropdown.
 *
 * TF-637 adds the Granted Role picker: which Role (if any) this OrgUnit
 * grants to its direct members. Distinct from the Membership Label free
 * text (OrgUnitAssignmentDialog.tsx) -- see CONTEXT.md.
 */

import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import OrgUnitEditor from '../OrgUnitEditor';
import { OrgUnitsService } from '../../../services/orgUnitsService';
import AdminService from '../../../services/AdminService';
import { OrgUnitOut } from '../../../types/orgUnit';
import { Role } from '../../../types/auth';

jest.mock('../../../services/orgUnitsService');
jest.mock('../../../services/AdminService', () => ({
  __esModule: true,
  default: {
    listRoles: jest.fn(),
  },
}));

const mockedService = OrgUnitsService as jest.Mocked<typeof OrgUnitsService>;
const mockedAdminService = AdminService as jest.Mocked<typeof AdminService>;

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

function makeUnit(overrides: Partial<OrgUnitOut> = {}): OrgUnitOut {
  return {
    id: 1,
    parent_org_unit_id: null,
    unit_type: 'abteilung',
    name: 'Informatik',
    descendant_count: 0,
    role_id: null,
    role_name: null,
    created_at: '2026-08-07T00:00:00Z',
    updated_at: '2026-08-07T00:00:00Z',
    ...overrides,
  };
}

function makeRole(overrides: Partial<Role> = {}): Role {
  return {
    id: 1,
    name: 'backend_grader',
    display_name: 'Backend-Grader',
    description: null,
    permissions: [],
    is_system_role: false,
    created_at: '2026-08-01T00:00:00Z',
    ...overrides,
  };
}

async function selectDropdownOption(labelName: string, optionName: string) {
  const combo = screen.getByRole('combobox', { name: labelName });
  fireEvent.mouseDown(combo);
  const option = await screen.findByRole('option', { name: optionName });
  fireEvent.click(option);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockedAdminService.listRoles.mockResolvedValue([]);
});

describe('OrgUnitEditor — create', () => {
  it('submits unit_type from the dropdown, not free text', async () => {
    const onSaved = jest.fn();
    const onClose = jest.fn();
    mockedService.create.mockResolvedValue(makeUnit());

    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={null}
          allOrgUnits={[]}
          onClose={onClose}
          onSaved={onSaved}
        />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('ou-editor-field-name'), {
      target: { value: 'Backend-Team' },
    });
    await selectDropdownOption('Typ', 'Team');

    fireEvent.click(screen.getByTestId('ou-editor-btn-save'));

    await waitFor(() => expect(mockedService.create).toHaveBeenCalledTimes(1));
    expect(mockedService.create).toHaveBeenCalledWith({
      name: 'Backend-Team',
      unit_type: 'team',
      parent_org_unit_id: null,
      role_id: null,
    });
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it('offers exactly the known unit types (Abteilung, Team)', () => {
    render(
      <Wrapper>
        <OrgUnitEditor open orgUnit={null} allOrgUnits={[]} onClose={jest.fn()} onSaved={jest.fn()} />
      </Wrapper>,
    );

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Typ' }));
    expect(screen.getByRole('option', { name: 'Abteilung' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Team' })).toBeInTheDocument();
    expect(screen.getAllByRole('option')).toHaveLength(2);
  });

  it('sends move_to_root: false and the chosen parent when a parent is picked', async () => {
    const abteilung = makeUnit({ id: 1, name: 'Informatik' });
    mockedService.create.mockResolvedValue(makeUnit({ id: 2 }));

    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={null}
          allOrgUnits={[abteilung]}
          onClose={jest.fn()}
          onSaved={jest.fn()}
        />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('ou-editor-field-name'), {
      target: { value: 'Backend' },
    });
    await selectDropdownOption('Typ', 'Team');
    await selectDropdownOption('Übergeordnete Einheit', 'Informatik');

    fireEvent.click(screen.getByTestId('ou-editor-btn-save'));

    await waitFor(() => expect(mockedService.create).toHaveBeenCalledTimes(1));
    expect(mockedService.create).toHaveBeenCalledWith({
      name: 'Backend',
      unit_type: 'team',
      parent_org_unit_id: 1,
      role_id: null,
    });
  });

  it('offers a "none" option plus every role from the catalogue', async () => {
    mockedAdminService.listRoles.mockResolvedValue([
      makeRole({ id: 1, display_name: 'Backend-Grader' }),
      makeRole({ id: 2, display_name: 'Frontend-Grader' }),
    ]);

    render(
      <Wrapper>
        <OrgUnitEditor open orgUnit={null} allOrgUnits={[]} onClose={jest.fn()} onSaved={jest.fn()} />
      </Wrapper>,
    );

    await waitFor(() => expect(mockedAdminService.listRoles).toHaveBeenCalled());
    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Verliehene Rolle' }));
    expect(screen.getByRole('option', { name: '— Keine —' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Backend-Grader' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Frontend-Grader' })).toBeInTheDocument();
  });

  it('sends the selected role_id on create', async () => {
    mockedAdminService.listRoles.mockResolvedValue([
      makeRole({ id: 5, display_name: 'Backend-Grader' }),
    ]);
    mockedService.create.mockResolvedValue(makeUnit());

    render(
      <Wrapper>
        <OrgUnitEditor open orgUnit={null} allOrgUnits={[]} onClose={jest.fn()} onSaved={jest.fn()} />
      </Wrapper>,
    );

    await waitFor(() => expect(mockedAdminService.listRoles).toHaveBeenCalled());
    fireEvent.change(screen.getByTestId('ou-editor-field-name'), {
      target: { value: 'Team Backend' },
    });
    await selectDropdownOption('Typ', 'Team');
    await selectDropdownOption('Verliehene Rolle', 'Backend-Grader');

    fireEvent.click(screen.getByTestId('ou-editor-btn-save'));

    await waitFor(() => expect(mockedService.create).toHaveBeenCalledTimes(1));
    expect(mockedService.create).toHaveBeenCalledWith({
      name: 'Team Backend',
      unit_type: 'team',
      parent_org_unit_id: null,
      role_id: 5,
    });
  });

  // TF-637 review fix: a failed role-catalogue fetch must be surfaced to
  // the user, not silently swallowed into an empty (and indistinguishable
  // from "no roles exist") dropdown.
  it('shows an error when the role catalogue fails to load', async () => {
    mockedAdminService.listRoles.mockRejectedValue(new Error('network error'));

    render(
      <Wrapper>
        <OrgUnitEditor open orgUnit={null} allOrgUnits={[]} onClose={jest.fn()} onSaved={jest.fn()} />
      </Wrapper>,
    );

    expect(await screen.findByTestId('ou-editor-error')).toHaveTextContent(
      'Rollen-Katalog konnte nicht geladen werden',
    );
    // the picker itself must still render, just with no selectable roles
    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Verliehene Rolle' }));
    expect(screen.getByRole('option', { name: '— Keine —' })).toBeInTheDocument();
    expect(screen.getAllByRole('option')).toHaveLength(1);
  });
});

describe('OrgUnitEditor — edit', () => {
  it('excludes the unit itself and all of its descendants from the parent dropdown', () => {
    const root = makeUnit({ id: 1, name: 'Informatik', parent_org_unit_id: null });
    const child = makeUnit({ id: 2, name: 'Backend', parent_org_unit_id: 1 });
    const grandchild = makeUnit({ id: 3, name: 'Platform', parent_org_unit_id: 2 });
    const unrelated = makeUnit({ id: 4, name: 'HR', parent_org_unit_id: null });

    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={root}
          allOrgUnits={[root, child, grandchild, unrelated]}
          onClose={jest.fn()}
          onSaved={jest.fn()}
        />
      </Wrapper>,
    );

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Übergeordnete Einheit' }));
    // Editing "Informatik" (id 1): itself, "Backend" (child), and "Platform"
    // (grandchild) must all be excluded -- only "HR" plus the root option
    // ("— Keine (oberste Ebene) —") may be offered.
    expect(screen.queryByRole('option', { name: 'Informatik' })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Backend' })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Platform' })).not.toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'HR' })).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: '— Keine (oberste Ebene) —' }),
    ).toBeInTheDocument();
  });

  it('disables the unit_type dropdown (immutable after creation)', () => {
    const unit = makeUnit();
    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={unit}
          allOrgUnits={[unit]}
          onClose={jest.fn()}
          onSaved={jest.fn()}
        />
      </Wrapper>,
    );
    expect(screen.getByRole('combobox', { name: 'Typ' })).toHaveAttribute(
      'aria-disabled',
      'true',
    );
  });

  it('sends move_to_root: true when the parent is cleared to root', async () => {
    const parent = makeUnit({ id: 1, name: 'Informatik', parent_org_unit_id: null });
    const unit = makeUnit({ id: 2, name: 'Backend', parent_org_unit_id: 1 });
    mockedService.update.mockResolvedValue(unit);

    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={unit}
          allOrgUnits={[parent, unit]}
          onClose={jest.fn()}
          onSaved={jest.fn()}
        />
      </Wrapper>,
    );

    await selectDropdownOption('Übergeordnete Einheit', '— Keine (oberste Ebene) —');
    fireEvent.click(screen.getByTestId('ou-editor-btn-save'));

    await waitFor(() => expect(mockedService.update).toHaveBeenCalledTimes(1));
    expect(mockedService.update).toHaveBeenCalledWith(2, {
      name: 'Backend',
      parent_org_unit_id: null,
      move_to_root: true,
      role_id: null,
    });
  });

  it('sends move_to_root: false with the new parent id when re-parented', async () => {
    const parentA = makeUnit({ id: 1, name: 'Informatik', parent_org_unit_id: null });
    const parentB = makeUnit({ id: 3, name: 'HR', parent_org_unit_id: null });
    const unit = makeUnit({ id: 2, name: 'Backend', parent_org_unit_id: 1 });
    mockedService.update.mockResolvedValue(unit);

    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={unit}
          allOrgUnits={[parentA, parentB, unit]}
          onClose={jest.fn()}
          onSaved={jest.fn()}
        />
      </Wrapper>,
    );

    await selectDropdownOption('Übergeordnete Einheit', 'HR');
    fireEvent.click(screen.getByTestId('ou-editor-btn-save'));

    await waitFor(() => expect(mockedService.update).toHaveBeenCalledTimes(1));
    expect(mockedService.update).toHaveBeenCalledWith(2, {
      name: 'Backend',
      parent_org_unit_id: 3,
      move_to_root: false,
      role_id: null,
    });
  });

  it('preselects the currently granted role', async () => {
    mockedAdminService.listRoles.mockResolvedValue([
      makeRole({ id: 5, display_name: 'Backend-Grader' }),
      makeRole({ id: 6, display_name: 'Frontend-Grader' }),
    ]);
    const unit = makeUnit({ role_id: 5, role_name: 'Backend-Grader' });

    render(
      <Wrapper>
        <OrgUnitEditor open orgUnit={unit} allOrgUnits={[unit]} onClose={jest.fn()} onSaved={jest.fn()} />
      </Wrapper>,
    );

    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Verliehene Rolle' })).toHaveTextContent(
        'Backend-Grader',
      ),
    );
  });

  it('sends the cleared role_id when "none" is (re-)selected', async () => {
    mockedAdminService.listRoles.mockResolvedValue([
      makeRole({ id: 5, display_name: 'Backend-Grader' }),
    ]);
    const unit = makeUnit({ role_id: 5, role_name: 'Backend-Grader' });
    mockedService.update.mockResolvedValue(makeUnit());

    render(
      <Wrapper>
        <OrgUnitEditor open orgUnit={unit} allOrgUnits={[unit]} onClose={jest.fn()} onSaved={jest.fn()} />
      </Wrapper>,
    );

    await waitFor(() => expect(mockedAdminService.listRoles).toHaveBeenCalled());
    await selectDropdownOption('Verliehene Rolle', '— Keine —');
    fireEvent.click(screen.getByTestId('ou-editor-btn-save'));

    await waitFor(() => expect(mockedService.update).toHaveBeenCalledTimes(1));
    expect(mockedService.update).toHaveBeenCalledWith(1, {
      name: 'Informatik',
      parent_org_unit_id: null,
      move_to_root: true,
      role_id: null,
    });
  });
});
